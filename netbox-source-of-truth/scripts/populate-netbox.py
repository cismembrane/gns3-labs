#!/usr/bin/env python3
"""Populate an empty NetBox with the four-router eBGP ring from topology.py.

Safe to re-run against unchanged seed data: existing objects are matched and left
alone, and only interface description and enabled state are reconciled.

This is a bootstrap, not a reconciler. Changing an address in topology.py and
re-running adds a second IP to the interface rather than replacing the first, and
objects removed from topology.py are never deleted. After the first run NetBox
owns the data; change it there and re-run export-netbox.py.
"""

from __future__ import annotations

import argparse
import os
import sys

import topology

try:
    import pynetbox
except ImportError:
    sys.exit("pynetbox is not installed. Run: pip install -r requirements.txt")


class Reporter:
    """Counts and prints what the run did, so the summary is auditable."""

    def __init__(self) -> None:
        self.created = 0
        self.updated = 0
        self.unchanged = 0

    def record(self, action: str, label: str) -> None:
        if action == "created":
            self.created += 1
        elif action == "updated":
            self.updated += 1
        else:
            self.unchanged += 1
        print(f"  {action:9} {label}")

    def summary(self) -> None:
        print(
            f"\ncreated {self.created}, updated {self.updated}, "
            f"unchanged {self.unchanged}"
        )


def ensure(endpoint, lookup, create, label, reporter, update_fields=()):
    """Create the object if the lookup misses, otherwise reconcile update_fields.

    `lookup` holds NetBox *filter* parameters (device_id, interface_id) and
    `create` holds the full *create* payload (device, assigned_object_id). The two
    vocabularies differ, which is why they are separate arguments rather than one
    dict merged at call time.

    update_fields is restricted to scalar attributes on purpose. Comparing
    NetBox's nested related-object representations against the flat slugs and
    IDs used in create payloads produces false "changed" results.
    """
    matches = list(endpoint.filter(**lookup))
    if not matches:
        obj = endpoint.create(**create)
        reporter.record("created", label)
        return obj

    obj = matches[0]
    changes = {
        field: create[field]
        for field in update_fields
        if field in create and getattr(obj, field, None) != create[field]
    }
    if changes:
        for field, value in changes.items():
            setattr(obj, field, value)
        obj.save()
        reporter.record("updated", f"{label} ({', '.join(sorted(changes))})")
    else:
        reporter.record("exists", label)
    return obj


def ensure_organisation(nb, reporter):
    """Create the site, manufacturer, device type, role, and platform."""
    print("Organisation")
    site = ensure(
        nb.dcim.sites,
        {"slug": topology.SITE["slug"]},
        {
            "slug": topology.SITE["slug"],
            "name": topology.SITE["name"],
            "status": "active",
        },
        f"site {topology.SITE['slug']}",
        reporter,
    )
    manufacturer = ensure(
        nb.dcim.manufacturers,
        {"slug": topology.MANUFACTURER["slug"]},
        {
            "slug": topology.MANUFACTURER["slug"],
            "name": topology.MANUFACTURER["name"],
        },
        f"manufacturer {topology.MANUFACTURER['slug']}",
        reporter,
    )
    device_type = ensure(
        nb.dcim.device_types,
        {"slug": topology.DEVICE_TYPE["slug"]},
        {
            "slug": topology.DEVICE_TYPE["slug"],
            "model": topology.DEVICE_TYPE["model"],
            "manufacturer": manufacturer.id,
        },
        f"device type {topology.DEVICE_TYPE['slug']}",
        reporter,
    )
    role = ensure(
        nb.dcim.device_roles,
        {"slug": topology.DEVICE_ROLE["slug"]},
        {
            "slug": topology.DEVICE_ROLE["slug"],
            "name": topology.DEVICE_ROLE["name"],
            "color": "2196f3",
        },
        f"device role {topology.DEVICE_ROLE['slug']}",
        reporter,
    )
    platform = ensure(
        nb.dcim.platforms,
        {"slug": topology.PLATFORM["slug"]},
        {
            "slug": topology.PLATFORM["slug"],
            "name": topology.PLATFORM["name"],
        },
        f"platform {topology.PLATFORM['slug']}",
        reporter,
    )
    return site, device_type, role, platform


def ensure_device(nb, spec, site, device_type, role, platform, reporter):
    """Create the device shell. NetBox 4.x names the role field `role`."""
    return ensure(
        nb.dcim.devices,
        {"name": spec["name"]},
        {
            "name": spec["name"],
            "device_type": device_type.id,
            "role": role.id,
            "site": site.id,
            "platform": platform.id,
            "status": "active",
        },
        f"device {spec['name']}",
        reporter,
    )


def ensure_interfaces(nb, device, spec, reporter):
    """Create interfaces and their IP addresses; return the mgmt IP object."""
    mgmt_ip = None
    for iface_spec in spec["interfaces"]:
        iface = ensure(
            nb.dcim.interfaces,
            {"device_id": device.id, "name": iface_spec["name"]},
            {
                "device": device.id,
                "name": iface_spec["name"],
                "type": iface_spec["type"],
                "description": iface_spec["description"],
                "enabled": True,
            },
            f"{device.name} {iface_spec['name']}",
            reporter,
            update_fields=("description", "enabled"),
        )
        ip = ensure(
            nb.ipam.ip_addresses,
            {
                "address": iface_spec["address"],
                "interface_id": iface.id,
            },
            {
                "address": iface_spec["address"],
                "assigned_object_type": "dcim.interface",
                "assigned_object_id": iface.id,
                "status": "active",
            },
            f"{device.name} {iface_spec['name']} {iface_spec['address']}",
            reporter,
        )
        if iface_spec.get("mgmt"):
            mgmt_ip = ip
    return mgmt_ip


def ensure_primary_ip(device, mgmt_ip, reporter):
    """nb_inventory turns primary_ip4 into ansible_host, so this is load-bearing."""
    if mgmt_ip is None:
        reporter.record("skipped", f"{device.name} primary IP (no mgmt interface)")
        return
    current = device.primary_ip4.id if device.primary_ip4 else None
    if current == mgmt_ip.id:
        reporter.record("exists", f"{device.name} primary IP {mgmt_ip.address}")
        return
    device.primary_ip4 = mgmt_ip.id
    device.save()
    reporter.record("updated", f"{device.name} primary IP {mgmt_ip.address}")


def ensure_config_context(device, spec, reporter):
    """Store per-device BGP data as NetBox local config context.

    Local context data is merged into the device's rendered config_context, which
    is what nb_inventory exposes as the `config_context` host var. The schema
    matches what templates/bgp.j2 consumes, so no translation layer is needed.

    The netbox-bgp plugin would model real per-session objects instead. That is
    deliberately deferred -- it couples the lab to a plugin release matching the
    pinned NetBox version.
    """
    desired = {"bgp": spec["bgp"]}
    if device.local_context_data == desired:
        reporter.record("exists", f"{device.name} BGP config context")
        return
    device.local_context_data = desired
    device.save()
    reporter.record("updated", f"{device.name} BGP config context")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
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
    args = parser.parse_args()

    if not args.url or not args.token:
        parser.error("NETBOX_API and NETBOX_TOKEN must be set (or use --url/--token)")

    nb = pynetbox.api(args.url.rstrip("/"), token=args.token)
    nb.http_session.verify = args.verify_ssl

    try:
        version = nb.version
    except Exception as exc:  # noqa: BLE001 - surface any connection failure plainly
        print(f"cannot reach NetBox at {args.url}: {exc}", file=sys.stderr)
        return 1
    print(f"NetBox {version} at {args.url}\n")

    reporter = Reporter()
    site, device_type, role, platform = ensure_organisation(nb, reporter)

    for spec in topology.DEVICES:
        print(f"\n{spec['name']}")
        device = ensure_device(nb, spec, site, device_type, role, platform, reporter)
        mgmt_ip = ensure_interfaces(nb, device, spec, reporter)
        device = nb.dcim.devices.get(device.id)
        ensure_primary_ip(device, mgmt_ip, reporter)
        ensure_config_context(device, spec, reporter)

    reporter.summary()
    print("\nNext: python3 scripts/export-netbox.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
