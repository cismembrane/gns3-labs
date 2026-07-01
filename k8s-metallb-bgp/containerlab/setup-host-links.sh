#!/usr/bin/env bash
# Addresses the host ends of the containerlab host links (k3s-r1, k3s-r4)
# and installs return routes into the FRR ring. Run with sudo after
# `containerlab deploy`. Mirrors what setup-taps.sh does for the GNS3 lab.
set -euo pipefail

ip addr replace 10.0.5.5/29 dev k3s-r1
ip link set k3s-r1 up
ip addr replace 10.0.6.5/29 dev k3s-r4
ip link set k3s-r4 up

# Return routes: prefer r1, fall back to r4.
ip route replace 10.0.0.0/16 via 10.0.5.1 dev k3s-r1 metric 100
ip route replace 10.0.0.0/16 via 10.0.6.4 dev k3s-r4 metric 200
for rid in 1.1.1.1 2.2.2.2 3.3.3.3 4.4.4.4; do
  ip route replace "$rid/32" via 10.0.5.1 dev k3s-r1 metric 100
  ip route replace "$rid/32" via 10.0.6.4 dev k3s-r4 metric 200
done

# Traffic can arrive via r4 while replies prefer r1; loose RPF avoids drops.
sysctl -qw net.ipv4.conf.k3s-r1.rp_filter=2 net.ipv4.conf.k3s-r4.rp_filter=2

echo "host links up: k3s-r1 (10.0.5.5/29), k3s-r4 (10.0.6.5/29)"
