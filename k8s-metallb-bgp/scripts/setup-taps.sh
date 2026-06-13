#!/usr/bin/env bash
# Creates the three TAP interfaces the lab expects on the GNS3 host:
#   tap0 -> management segment (192.168.0.0/24), bound to Cloud1 / SW1
#   tap1 -> k3s transit to R1 (10.0.5.0/29), bound to Cloud2
#   tap2 -> k3s transit to R4 (10.0.6.0/29), bound to Cloud3
#
# Also installs return routes into the ring so traffic sourced from the
# k3s host can reach the transit subnets and router loopbacks.
#
# FAILOVER CAVEAT: the metric-100/metric-200 pair only fails over when tap1
# itself goes down on this host (interface removed, Cloud2 unbound). It does
# NOT fail over if R1 the router dies while tap1 stays up: the kernel keeps
# the connected 10.0.5.0/29 segment reachable, leaves the metric-100 route
# installed, and traffic to the ring blackholes instead of rolling to tap2.
# Real R1-failure redundancy requires a routing daemon (FRR/BIRD) on the k3s
# host that learns these prefixes over BGP and follows session state. The
# static backup here covers host-side TAP loss only.
#
# TAPs created this way do not survive a reboot; rerun after restarting.
set -euo pipefail
user="$(whoami)"

make_tap() {
  local dev="$1" addr="$2"
  if ! ip link show "$dev" &>/dev/null; then
    sudo ip tuntap add dev "$dev" mode tap user "$user"
  fi
  sudo ip link set "$dev" up
  sudo ip addr replace "$addr" dev "$dev"
  echo "$dev up at $addr"
}

make_tap tap0 192.168.0.100/24
make_tap tap1 10.0.5.5/29
make_tap tap2 10.0.6.5/29

# Return routes into the ring, scoped to what actually lives behind it:
# the four inter-router transit /29s and the four router loopback /32s.
# Deliberately NOT 10.0.0.0/16 -- a /16 can swallow the MetalLB service pool
# and hairpin host-originated service traffic out to R1. Directly connected
# segments (192.168.0.0/24, 10.0.5.0/29, 10.0.6.0/29) need no route here.
# Primary via R1 (tap1, metric 100); backup via R4 (tap2, metric 200),
# subject to the failover caveat above.
ring_dests=(
  10.0.1.0/29 10.0.2.0/29 10.0.3.0/29 10.0.4.0/29
  1.1.1.1/32 2.2.2.2/32 3.3.3.3/32 4.4.4.4/32
)
for dst in "${ring_dests[@]}"; do
  sudo ip route replace "$dst" via 10.0.5.1 dev tap1 metric 100
  sudo ip route replace "$dst" via 10.0.6.4 dev tap2 metric 200
done

echo "Done. Bind tap0/tap1/tap2 to their Cloud nodes in GNS3, then verify:"
echo "  ping 192.168.0.1   # R1 management   (connected via tap0)"
echo "  ping 10.0.5.1      # R1 k3s transit  (connected via tap1)"
echo "  ping 10.0.6.4      # R4 k3s transit  (connected via tap2)"
echo "  ping 2.2.2.2       # R2 loopback     (exercises the return routes)"
