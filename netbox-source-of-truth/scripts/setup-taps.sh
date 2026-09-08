#!/usr/bin/env bash
# Creates the single TAP interface this lab expects on the GNS3 host:
#   tap0 -> management segment (192.168.0.0/24), bound to Cloud1 / Switch1
#
# This is the trimmed counterpart to k8s-metallb-bgp/scripts/setup-taps.sh. That
# lab needed tap1/tap2 for the k3s transit links and tap3 for the client netns,
# plus static return routes into the ring. None of that applies here: the topology
# is the same four-router eBGP ring minus the k3s links, so the only host-to-lab
# reachability this lab needs is SSH from the control node to 192.168.0.1-.4.
#
# NO RING RETURN ROUTES ON PURPOSE. Adding `10.0.x.0/29 via 192.168.0.1` would
# look useful and would not work: the management network is not advertised into
# BGP, so a router further round the ring has no route back to 192.168.0.100 and
# the replies never return. Reachability to the transit subnets and loopbacks is
# checked on the devices by verify.yml, not from this host.
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

echo
echo "Done. In GNS3, bind tap0 to Cloud1 and wire it to Switch1, then verify:"
echo "  ping 192.168.0.1   # R1 management"
echo "  ping 192.168.0.2   # R2 management"
echo "  ping 192.168.0.3   # R3 management"
echo "  ping 192.168.0.4   # R4 management"
echo
echo "Once ssh admin@192.168.0.1 through .4 work, the routers are ready for deploy.yml."
