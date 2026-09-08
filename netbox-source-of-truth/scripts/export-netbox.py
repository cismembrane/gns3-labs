#!/usr/bin/env python3
"""Dump the lab's NetBox objects to a committed static-inventory fixture.

Phase 7 of the lab. The fixture at inventory/netbox-export.yml does three jobs:

  1. It is the inventory CI renders from, so the render job needs no NetBox and
     no secrets on a hosted runner.
  2. It is the human-readable snapshot of what NetBox holds. This lab has no
     host_vars/ directory; the fixture is what you read and what shows up in a
     diff when someone changes an IP address or a BGP neighbour in NetBox.
  3. It is a regression check. CI re-renders from it and compares against the
     committed rendered/ output.

The host vars it emits mirror what netbox.netbox.nb_inventory produces with the
options in inventory/netbox.yml (plurals: false, config_context: true,
interfaces: true, plus the compose block). It is a trimmed projection -- only the
keys the templates actually consume, so the file stays readable -- but the shapes
and names match, which is what lets one set of templates serve both paths.

Two sources:

  --source netbox   (default) read the live NetBox API. This is authoritative.
  --source seed     read scripts/topology.py directly, no NetBox required. For
                    bootstrapping the fixture before NetBox exists, and for
                    regenerating it on a machine that cannot reach the lab.

Usage:
    export NETBOX_API=http://netbox-host:8000
    export NETBOX_TOKEN=nbt_<key>.<plaintext>   # see .env.example
    python3 scripts/export-netbox.py
    python3 scripts/export-netbox.py --source seed
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import topology

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is not installed. Run: pip install -r requirements.txt")

LAB_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = LAB_ROOT / "inventory" / "netbox-export.yml"

HEADER = """\
---
# GENERATED FILE -- DO NOT EDIT BY HAND.
#
# Regenerate with:  python3 scripts/export-netbox.py
#
# NetBox is the source of truth for everything below. Editing this file changes
# what CI renders but not what the routers get from a live run, so the two drift
# apart silently. Change the data in NetBox and re-run the export instead.
#
# Host var shapes mirror netbox.netbox.nb_inventory as configured in
# inventory/netbox.yml. Connection credentials live in group_vars/routers.yml.
"""


def host_vars(ansible_host, interfaces, bgp):
    """Assemble one host's vars in nb_inventory's key order and shapes."""
    return {
        "ansible_host": ansible_host,
        "site": topology.SITE["slug"],
        "role": topology.DEVICE_ROLE["slug"],
        "platform": topology.PLATFORM["slug"],
        # Produced by the `compose` block in inventory/netbox.yml, which lifts
        # these out of the NetBox config context into the names bgp.j2 uses.
        "asn": bgp["asn"],
        "router_id": bgp["router_id"],
        "bgp_neighbors": bgp["neighbors"],
        "bgp_networks": bgp["networks"],
        # Produced by `interfaces: true`. NetBox interface objects, trimmed to the
        # keys templates/interfaces.j2 reads.
        "interfaces": interfaces,
    }


def from_seed():
    """Build the fixture from topology.py without touching NetBox."""
    hosts = {}
    for spec in sorted(topology.DEVICES, key=lambda d: d["name"]):
        interfaces = []
        ansible_host = None
        for iface in sorted(spec["interfaces"], key=lambda i: i["name"]):
            interfaces.append(
                {
                    "name": iface["name"],
                    "description": iface["description"],
                    "enabled": True,
                    "ip_addresses": [{"address": iface["address"]}],
                }
            )
            if iface.get("mgmt"):
                ansible_host = iface["address"].split("/")[0]
        hosts[spec["name"]] = host_vars(ansible_host, interfaces, spec["bgp"])
    return hosts


def device_bgp(device):
    """Pull the bgp block out of the device's rendered config context.

    NetBox merges local context data into config_context, so this picks up what
    populate-netbox.py wrote even though no global ConfigContext object exists.
    """
    context = getattr(device, "config_context", None) or {}
    if not context:
        context = device.local_context_data or {}
    bgp = context.get("bgp")
    if not bgp:
        raise SystemExit(
            f"{device.name} has no bgp config context in NetBox. "
            "Run scripts/populate-netbox.py first."
        )
    return bgp


def from_netbox(url, token, verify_ssl):
    """Build the fixture from the live NetBox API."""
    try:
        import pynetbox
    except ImportError:
        sys.exit("pynetbox is not installed. Run: pip install -r requirements.txt")

    nb = pynetbox.api(url.rstrip("/"), token=token)
    nb.http_session.verify = verify_ssl

    devices = list(
        nb.dcim.devices.filter(
            site=topology.SITE["slug"],
            role=topology.DEVICE_ROLE["slug"],
        )
    )
    if not devices:
        raise SystemExit(
            f"no devices found in NetBox for site={topology.SITE['slug']} "
            f"role={topology.DEVICE_ROLE['slug']}. "
            "Run scripts/populate-netbox.py first."
        )

    hosts = {}
    for device in sorted(devices, key=lambda d: d.name):
        interfaces = []
        for iface in sorted(
            nb.dcim.interfaces.filter(device_id=device.id), key=lambda i: i.name
        ):
            addresses = [
                {"address": str(ip.address)}
                for ip in sorted(
                    nb.ipam.ip_addresses.filter(interface_id=iface.id),
                    key=lambda ip: str(ip.address),
                )
            ]
            interfaces.append(
                {
                    "name": iface.name,
                    "description": iface.description or "",
                    "enabled": bool(iface.enabled),
                    "ip_addresses": addresses,
                }
            )
        if not device.primary_ip4:
            raise SystemExit(
                f"{device.name} has no primary IPv4 address in NetBox. "
                "nb_inventory needs it to set ansible_host."
            )
        hosts[device.name] = host_vars(
            str(device.primary_ip4.address).split("/")[0],
            interfaces,
            device_bgp(device),
        )
    return hosts


def write_fixture(hosts, output):
    inventory = {"all": {"children": {"routers": {"hosts": hosts}}}}
    body = yaml.safe_dump(
        inventory,
        sort_keys=False,
        default_flow_style=False,
        width=100,
        indent=2,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(HEADER + body, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source",
        choices=("netbox", "seed"),
        default="netbox",
        help="where to read the data from (default: netbox)",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("NETBOX_API"),
        help="NetBox base URL (default: $NETBOX_API)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("NETBOX_TOKEN"),
        help="NetBox API token (default: $NETBOX_TOKEN)",
    )
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        help="verify TLS certificates (off by default for self-signed lab certs)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"fixture path (default: {DEFAULT_OUTPUT.relative_to(LAB_ROOT)})",
    )
    args = parser.parse_args()

    if args.source == "seed":
        hosts = from_seed()
    else:
        if not args.url or not args.token:
            parser.error(
                "NETBOX_API and NETBOX_TOKEN must be set for --source netbox "
                "(or use --url/--token, or --source seed)"
            )
        hosts = from_netbox(args.url, args.token, args.verify_ssl)

    write_fixture(hosts, args.output)
    print(f"wrote {args.output} from {args.source}: {len(hosts)} hosts")
    print("\nNext: ansible-playbook -i inventory/netbox-export.yml render.yml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
