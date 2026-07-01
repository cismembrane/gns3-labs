#!/usr/bin/env bash
# Creates the three TAP interfaces the lab expects on the GNS3 host:
#   tap0 -> management segment (192.168.0.0/24), bound to Cloud1 / SW1
#   tap1 -> k3s transit to R1 (10.0.5.0/29), bound to Cloud2
#   tap2 -> k3s transit to R4 (10.0.6.0/29), bound to Cloud3
#
# Also installs the return routes the k3s node needs so traffic sourced from
# the ring (transit subnets and router loopbacks) can get back. TAPs created
# this way do not survive a reboot; rerun after restarting the host.
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

# Return routes into the ring. Transit subnets and loopbacks are covered by
# 10.0.0.0/16 and the four /32 router IDs. Prefer R1; R4 is the backup path
# used when the R1 link is down (higher metric).
sudo ip route replace 10.0.0.0/16 via 10.0.5.1 dev tap1 metric 100
sudo ip route replace 10.0.0.0/16 via 10.0.6.4 dev tap2 metric 200
for rid in 1.1.1.1 2.2.2.2 3.3.3.3 4.4.4.4; do
  sudo ip route replace "$rid/32" via 10.0.5.1 dev tap1 metric 100
  sudo ip route replace "$rid/32" via 10.0.6.4 dev tap2 metric 200
done

echo "Done. Bind tap0/tap1/tap2 to their Cloud nodes in GNS3, then verify:"
echo "  ping 192.168.0.1   # R1 management"
echo "  ping 10.0.5.1      # R1 k3s transit"
echo "  ping 10.0.6.4      # R4 k3s transit"
