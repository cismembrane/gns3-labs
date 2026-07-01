#!/usr/bin/env python3
"""Verify the containerlab FRR ring and (optionally) MetalLB service routes.

Checks, via vtysh JSON output inside each clab container:
  1. Every configured BGP session is Established (the MetalLB sessions on
     r1/r4 are skipped with --ring-only, for the pre-cluster phase).
  2. With services up: every router knows 172.16.10.10/32 and .20/32, and
     r3's paths for the whoami VIP all originate from AS 65100.

Exits nonzero on any failure. Run with sudo (docker exec).
"""

import argparse
import json
import subprocess
import sys

ROUTERS = ["r1", "r2", "r3", "r4"]
METALLB_ASN = 65100
SERVICE_VIPS = ["172.16.10.10/32", "172.16.10.20/32"]
CONTAINER = "clab-metallb-ring-{}"

failures = []


def vtysh_json(router, command):
    out = subprocess.run(
        ["docker", "exec", CONTAINER.format(router), "vtysh", "-c", command],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def check(ok, message):
    print(("PASS" if ok else "FAIL"), message)
    if not ok:
        failures.append(message)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ring-only", action="store_true",
                    help="skip MetalLB peers and service-route checks")
    args = ap.parse_args()

    for router in ROUTERS:
        summary = vtysh_json(router, "show bgp ipv4 unicast summary json")
        for peer_ip, peer in summary.get("ipv4Unicast", {}).get("peers", {}).items():
            if args.ring_only and peer.get("remoteAs") == METALLB_ASN:
                continue
            check(peer.get("state") == "Established",
                  f"{router}: peer {peer_ip} (AS {peer.get('remoteAs')}) "
                  f"state={peer.get('state')}")

    if not args.ring_only:
        for router in ROUTERS:
            for vip in SERVICE_VIPS:
                entry = vtysh_json(router, f"show bgp ipv4 unicast {vip} json")
                check(bool(entry.get("paths")), f"{router}: has BGP entry for {vip}")

        # r3 is two AS hops out in both directions; every path for the whoami
        # VIP must originate from the MetalLB AS.
        entry = vtysh_json("r3", f"show bgp ipv4 unicast {SERVICE_VIPS[0]} json")
        paths = entry.get("paths", [])
        origin_ok = paths and all(
            p.get("aspath", {}).get("segments", [{}])[-1]
             .get("list", [None])[-1] == METALLB_ASN
            for p in paths
        )
        check(origin_ok,
              f"r3: all {len(paths)} path(s) for {SERVICE_VIPS[0]} originate "
              f"from AS {METALLB_ASN}")

    if failures:
        sys.exit(f"{len(failures)} check(s) failed")
    print("all checks passed")


if __name__ == "__main__":
    main()
