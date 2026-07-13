#!/usr/bin/env bash
# Creates an isolated "external client" for data-plane testing:
#
#   client netns (10.0.7.2/29) -- client-veth -- br-client -- tap3 -- Cloud4 -- R3 Gi0/5 (10.0.7.3/29)
#
# WHY THIS EXISTS: curl run on the k3s node itself never touches the network.
# kube-proxy hooks LoadBalancer VIPs into the nat OUTPUT chain, so locally
# originated traffic to a VIP is DNAT'd straight to the pod before the routing
# decision -- it never crosses tap1/tap2 or the ring, and a failover test run
# from the node passes even with BGP fully down. Traffic sourced from this
# namespace enters the topology at R3, follows BGP best path through the ring,
# and reaches the node through tap1/tap2 like a real external client.
#
# The bridge is required because GNS3 must open tap3 in the root namespace;
# the veth pair carries the segment into the namespace.
#
# Not persistent across reboots; rerun after restarting (same as setup-taps.sh).
# Teardown: ip netns del client; ip link del br-client; ip link del tap3;
#           ip link del client-veth; the iptables rules below.
set -euo pipefail
user="$(whoami)"

NS=client
BR=br-client
VETH_HOST=client-veth
VETH_NS=client-eth
TAP=tap3
CLIENT_ADDR=10.0.7.2/29
GATEWAY=10.0.7.3

# tap3 stays in the root namespace so GNS3 can bind it to Cloud4.
if ! ip link show "$TAP" &>/dev/null; then
  sudo ip tuntap add dev "$TAP" mode tap user "$user"
fi
sudo ip link set "$TAP" up

if ! sudo ip netns list | grep -qw "$NS"; then
  sudo ip netns add "$NS"
fi

if ! ip link show "$VETH_HOST" &>/dev/null; then
  sudo ip link add "$VETH_HOST" type veth peer name "$VETH_NS"
  sudo ip link set "$VETH_NS" netns "$NS"
fi

if ! ip link show "$BR" &>/dev/null; then
  sudo ip link add "$BR" type bridge
fi
sudo ip link set "$BR" up
sudo ip link set "$TAP" master "$BR"
sudo ip link set "$VETH_HOST" master "$BR" up

sudo ip -n "$NS" link set lo up
sudo ip -n "$NS" link set "$VETH_NS" up
sudo ip -n "$NS" addr replace "$CLIENT_ADDR" dev "$VETH_NS"
sudo ip -n "$NS" route replace default via "$GATEWAY"

# k3s runs with br_netfilter loaded and bridge-nf-call-iptables=1 (flannel and
# kube-proxy depend on it). That pushes BRIDGED packets through the host's
# iptables, so without an exemption the KUBE-SERVICES nat PREROUTING rules
# would DNAT the client's VIP traffic while it is still being bridged inside
# br-client -- recreating the exact node-local short-circuit this client
# exists to avoid. NOTRACK in the raw table skips conntrack (and therefore
# all NAT) for traffic bridged through br-client; the FORWARD accepts keep a
# DROP policy (docker, firewalls) from filtering the bridged frames, since
# untracked packets never match ESTABLISHED rules.
exempt() {
  local dev="$1"
  sudo iptables -t raw -C PREROUTING -m physdev --physdev-in "$dev" -j NOTRACK 2>/dev/null || \
    sudo iptables -t raw -A PREROUTING -m physdev --physdev-in "$dev" -j NOTRACK
  sudo iptables -C FORWARD -m physdev --physdev-in "$dev" --physdev-is-bridged -j ACCEPT 2>/dev/null || \
    sudo iptables -I FORWARD 1 -m physdev --physdev-in "$dev" --physdev-is-bridged -j ACCEPT
}
exempt "$TAP"
exempt "$VETH_HOST"

echo "client netns up: $CLIENT_ADDR behind $BR/$TAP, default via $GATEWAY"
echo "Bind $TAP to Cloud4 in GNS3 (linked to R3 Gi0/5), then verify:"
echo "  sudo ip netns exec $NS ping -c3 $GATEWAY        # R3 client-facing interface"
echo "  sudo ip netns exec $NS ping -c3 1.1.1.1         # across the ring"
echo "  sudo ip netns exec $NS curl http://172.16.10.10 # VIP via BGP data plane"
