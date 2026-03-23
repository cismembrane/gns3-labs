# DMVPN Phase 3 with IPsec: GNS3 Lab

## Overview

This is a hub-and-spoke DMVPN Phase 3 deployment with IPsec encryption over a simulated ISP underlay. I built it to understand how Phase 3 shortcut tunnels actually form. Not just the theory, but watching the NHRP redirect fire on the hub, the resolution request go out from the spoke, and the shortcut route get installed in real time. The lab runs EIGRP as the overlay routing protocol and uses IKEv1 with pre-shared keys to keep the focus on DMVPN mechanics rather than PKI.

This maps directly to CCNP ENCOR objectives under VPN technologies. The IPsec component also crosses into security territory, since understanding encrypted tunnel behavior matters for traffic analysis and incident response in blue-team and SOC work.

## Topology

```
                    ┌──────────────────────┐
                    │   R4 (ISP Transit)   │
                    │                      │
                    │  f0/0  f1/0    f1/1  │
                    └───┬─────┬───────┬────┘
                        │     │       │
              10.0.1.0/30  10.0.2.0/30  10.0.3.0/30
                        │     │       │
                    f0/0│ f1/0│  f1/1 │
                  ┌─────┴─┐ ┌─┴────┐ ┌┴─────┐
                  │  R1   │ │  R2  │ │  R3  │
                  │  Hub  │ │Spoke1│ │Spoke2│
                  └───┬───┘ └──┬───┘ └──┬───┘
                      │        │         │
             ─────────┼────────┼─────────┼─────── DMVPN Overlay
             Tunnel0  │        │         │        172.16.0.0/24
             172.16.0.1   172.16.0.2  172.16.0.3
                      │        │         │
                   Lo0│     Lo0│      Lo0│
               192.168.1.0  192.168.2.0  192.168.3.0
                   /24          /24         /24
```

Four routers total. R4 is a minimal ISP transit box: Layer 3 forwarding only, no dynamic routing, no overlay awareness. R1 is the hub (headquarters). R2 and R3 are spokes (branch offices). Each site has a `Loopback0` simulating a LAN segment behind it.

## Technologies & Protocols

- **DMVPN Phase 3**: mGRE with `ip nhrp redirect` (hub) and `ip nhrp shortcut` (spokes)
- **NHRP**: dynamic tunnel endpoint resolution and spoke-to-spoke shortcut signaling
- **IPsec IKEv1**: AES-256, SHA-256, DH group 14, pre-shared keys, transport mode
- **EIGRP AS 100**: overlay routing across the DMVPN cloud
- **GNS3**: Cisco c7200 `adventerprisek9`

## Lab Objectives

I configured and validated four things in this lab. First, a working DMVPN Phase 3 hub-and-spoke topology with R1 as the hub and R2/R3 as spokes, connected through R4 as a simulated ISP. Second, IPsec encryption on the overlay using `tunnel protection ipsec profile` with no crypto maps and no ACLs, just the profile bound to the tunnel interface. Third, EIGRP neighbor adjacencies over `Tunnel0` with full reachability between all three LAN segments (`192.168.1.0/24`, `192.168.2.0/24`, `192.168.3.0/24`). Fourth, and this is the actual point of the lab, Phase 3 shortcut creation. Traffic from R2 to R3's LAN initially routes through the hub. The hub fires an NHRP Traffic Indication back to R2. R2 resolves R3's NBMA address directly and installs a shortcut route. Subsequent traffic bypasses the hub.

## IP Addressing

### Underlay (Physical Links to ISP)

| Link      | Interface     | IP Address    |
|-----------|---------------|---------------|
| R1↔ R4    | R1 `f0/0`     | `10.0.1.1/30` |
| R4↔ R1    | R4 `f0/0`     | `10.0.1.2/30` |
| R2↔ R4    | R2 `f1/0`     | `10.0.2.1/30` |
| R4↔ R2    | R4 `f1/0`     | `10.0.2.2/30` |
| R3↔ R4    | R3 `f1/1`     | `10.0.3.1/30` |
| R4↔ R3    | `f1/1`        | `10.0.3.2/30` |

### DMVPN Overlay (Tunnel0)

| Router | Role  | Tunnel IP       | NBMA Address |
|--------|-------|-----------------|--------------|
| R1     | Hub   | `172.16.0.1/24` | `10.0.1.1`   |
| R2     | Spoke | `172.16.0.2/24` | `10.0.2.1`   |
| R3     | Spoke | `172.16.0.3/24` | `10.0.3.1`   |

### LAN Segments (Loopback0)

| Router | Loopback0        |
|--------|------------------|
| R1     | `192.168.1.1/24` |
| R2     | `192.168.2.1/24` |
| R3     | `192.168.3.1/24` |

## Configuration Highlights

### IPsec (Same on All Three Routers)

```
crypto isakmp policy 1
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 86400

crypto isakmp key DMVPN_LAB_KEY address 0.0.0.0

crypto ipsec transform-set DMVPN_TS esp-aes 256 esp-sha256-hmac
 mode transport

crypto ipsec profile DMVPN_PROFILE
 set transform-set DMVPN_TS
```

The wildcard `address 0.0.0.0` on the pre-shared key is intentional. DMVPN spokes form IPsec SAs dynamically when Phase 3 shortcuts trigger, so the hub can't know every spoke's address ahead of time. Transport mode instead of tunnel mode because the mGRE tunnel already handles encapsulation; wrapping another IP header around it would just waste bytes.

### Hub Tunnel (R1)

```
interface Tunnel0
 ip address 172.16.0.1 255.255.255.0
 ip nhrp authentication NHRPKEY
 ip nhrp map multicast dynamic
 ip nhrp network-id 1
 ip nhrp redirect
 tunnel source FastEthernet0/0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile DMVPN_PROFILE
```

Two commands matter here. `ip nhrp map multicast dynamic` lets the hub accept multicast registrations from any spoke. Without this, EIGRP hellos don't cross the tunnel and you get no neighbor adjacencies. `ip nhrp redirect` is the Phase 3 trigger. When the hub sees spoke-to-spoke traffic flowing through it, it sends a Traffic Indication back to the originating spoke telling it to resolve the destination directly. The `tunnel key 100` must match across every router in this DMVPN cloud to prevent accidental peering if you're running multiple overlays on the same transport.

### Spoke Tunnel (R2, R3 is identical except for IPs)

```
interface Tunnel0
 ip address 172.16.0.2 255.255.255.0
 ip nhrp authentication NHRPKEY
 ip nhrp map multicast 10.0.1.1
 ip nhrp map 172.16.0.1 10.0.1.1
 ip nhrp network-id 1
 ip nhrp nhs 172.16.0.1
 ip nhrp shortcut
 tunnel source FastEthernet1/0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile DMVPN_PROFILE
```

`ip nhrp map 172.16.0.1 10.0.1.1` is the static mapping that tells the spoke where the hub lives on the underlay. `ip nhrp nhs 172.16.0.1` designates the hub as the Next Hop Server. `ip nhrp shortcut` is the spoke-side Phase 3 trigger. When this spoke receives a Traffic Indication from the hub, it fires an NHRP Resolution Request directly to the other spoke and installs a shortcut route that overrides the EIGRP-learned path. `ip nhrp map multicast 10.0.1.1` forwards EIGRP hellos to the hub's NBMA address.

### EIGRP

```
router eigrp 100
 network 172.16.0.0 0.0.0.255
 network 192.168.1.0 0.0.0.255
 no auto-summary
```

I deliberately did not configure `no ip next-hop-self eigrp 100` on the hub. The hub rewrites the next-hop to itself, so initial spoke-to-spoke traffic flows through the hub. That traffic is what triggers the NHRP redirect. If you preserved the original next-hop (which is what you'd do in Phase 2), the spoke would try to resolve the other spoke immediately through NHRP without the redirect mechanism. Phase 3 removes that constraint.

### Underlay Routing

Static default routes on each site, pointed at R4:

```
! R1
ip route 0.0.0.0 0.0.0.0 10.0.1.2

! R2
ip route 0.0.0.0 0.0.0.0 10.0.2.2

! R3
ip route 0.0.0.0 0.0.0.0 10.0.3.2
```

## Verification & Testing

### NHRP State

```
show ip nhrp
show ip nhrp nhs detail
show dmvpn
```

On the hub, `show ip nhrp` displays dynamic entries for both spokes with their NBMA addresses. On the spokes, you see the static hub mapping plus any dynamic shortcut entries that get created after Phase 3 fires.

### IPsec

```
show crypto isakmp sa
show crypto ipsec sa
show crypto session detail
```

Each spoke should have an IKE SA with the hub after the tunnel comes up. After a Phase 3 shortcut triggers, you'll see an additional IPsec SA formed directly between the two spokes. That's the spoke-to-spoke encryption session that didn't exist before the redirect.

### EIGRP

```
show ip eigrp neighbors
show ip eigrp topology
show ip route eigrp
```

All three routers should show EIGRP adjacencies over `Tunnel0`. The routing table should have EIGRP-learned routes to all three LAN segments.

### Phase 3 Shortcut: The Actual Test

This is what the whole lab is for. From R2:

```
ping 192.168.3.1 source 192.168.2.1
```

First few pings go through the hub. After the hub sends the NHRP redirect, R2 builds a direct shortcut to R3.

Verify it:

```
show ip nhrp shortcut
show ip route nhrp
traceroute 192.168.3.1 source 192.168.2.1
```

Before the shortcut, traceroute shows: `R2 → 172.16.0.1 (R1 hub) → R3`. After the shortcut, traceroute shows: `R2 → R3` directly, no hub hop.

One thing to know: a single ICMP packet might not trigger the redirect. If the shortcut doesn't appear, generate sustained traffic and check again. You can also run `debug nhrp` on the hub to watch the Traffic Indication messages go out in real time.

## Troubleshooting

**Tunnel won't come up.** Check underlay reachability first. From each spoke, ping the hub's NBMA address (`10.0.1.1`). If that fails, it's a default route or R4 interface issue.

**NHRP registration failing.** The `ip nhrp authentication` key, `ip nhrp network-id`, and `tunnel key` must all match across every router. Mismatched values here are silent failures.

**IPsec not forming.** Run `debug crypto isakmp` and `debug crypto ipsec` on the spoke. Usual suspects: mismatched ISAKMP policy parameters (encryption, hash, DH group), wrong pre-shared key, or the underlay blocking UDP 500/4500 (not an issue in this lab since R4 is just a router).

**EIGRP neighbors not forming.** This is almost always a multicast mapping problem. The hub needs `ip nhrp map multicast dynamic`. Each spoke needs `ip nhrp map multicast 10.0.1.1`. Without these, EIGRP hellos don't traverse the tunnel.

**Phase 3 shortcut not triggering.** Verify `ip nhrp redirect` on the hub and `ip nhrp shortcut` on both spokes. Generate sustained traffic, not just one ping. Use `debug nhrp` on the hub to confirm Traffic Indication messages are being sent.

## Key Takeaways

In Phase 2, the routing protocol has to preserve the original next-hop for spoke-to-spoke NHRP resolution to work. Phase 3 removes that constraint. The hub rewrites the next-hop to itself (standard EIGRP behavior), initial traffic flows through the hub on the data plane, and the hub's NHRP redirect kicks off a separate control-plane process where the originating spoke resolves the destination spoke's NBMA address directly. The shortcut gets installed as an NHRP route that overrides the EIGRP path. That separation between control plane and data plane is the thing Phase 3 actually demonstrates.

Binding the IPsec profile to the tunnel with `tunnel protection ipsec profile` means new SAs form automatically when Phase 3 shortcuts are created, with no per-spoke-pair IPsec config needed. Being able to read `show crypto session detail` and correlate SAs with tunnel endpoints is useful for diagnosing encrypted tunnel problems in production.

## Prerequisites

- **GNS3** with Cisco c7200 `adventerprisek9`
- Four router instances (one ISP transit, one hub, two spokes)
- Working knowledge of GRE, NHRP, IPsec IKEv1, and EIGRP

## Full Router Configs

<details>
<summary>R4 (ISP Transit)</summary>

```
hostname R4

interface FastEthernet0/0
 description TO_R1
 ip address 10.0.1.2 255.255.255.252
 no shutdown

interface FastEthernet1/0
 description TO_R2
 ip address 10.0.2.2 255.255.255.252
 no shutdown

interface FastEthernet1/1
 description TO_R3
 ip address 10.0.3.2 255.255.255.252
 no shutdown

end
```

</details>

<details>
<summary>R1 (Hub)</summary>

```
hostname R1

interface FastEthernet0/0
 description TO_R4
 ip address 10.0.1.1 255.255.255.252
 no shutdown

interface Loopback0
 ip address 192.168.1.1 255.255.255.0

ip route 0.0.0.0 0.0.0.0 10.0.1.2

crypto isakmp policy 1
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 86400

crypto isakmp key DMVPN_LAB_KEY address 0.0.0.0

crypto ipsec transform-set DMVPN_TS esp-aes 256 esp-sha256-hmac
 mode transport

crypto ipsec profile DMVPN_PROFILE
 set transform-set DMVPN_TS

interface Tunnel0
 ip address 172.16.0.1 255.255.255.0
 ip nhrp authentication NHRPKEY
 ip nhrp map multicast dynamic
 ip nhrp network-id 1
 ip nhrp redirect
 tunnel source FastEthernet0/0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile DMVPN_PROFILE

router eigrp 100
 network 172.16.0.0 0.0.0.255
 network 192.168.1.0 0.0.0.255
 no auto-summary

end
```

</details>

<details>
<summary>R2 (Spoke 1)</summary>

```
hostname R2

interface FastEthernet1/0
 description TO_R4
 ip address 10.0.2.1 255.255.255.252
 no shutdown

interface Loopback0
 ip address 192.168.2.1 255.255.255.0

ip route 0.0.0.0 0.0.0.0 10.0.2.2

crypto isakmp policy 1
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 86400

crypto isakmp key DMVPN_LAB_KEY address 0.0.0.0

crypto ipsec transform-set DMVPN_TS esp-aes 256 esp-sha256-hmac
 mode transport

crypto ipsec profile DMVPN_PROFILE
 set transform-set DMVPN_TS

interface Tunnel0
 ip address 172.16.0.2 255.255.255.0
 ip nhrp authentication NHRPKEY
 ip nhrp map multicast 10.0.1.1
 ip nhrp map 172.16.0.1 10.0.1.1
 ip nhrp network-id 1
 ip nhrp nhs 172.16.0.1
 ip nhrp shortcut
 tunnel source FastEthernet1/0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile DMVPN_PROFILE

router eigrp 100
 network 172.16.0.0 0.0.0.255
 network 192.168.2.0 0.0.0.255
 no auto-summary

end
```

</details>

<details>
<summary>R3 (Spoke 2)</summary>

```
hostname R3

interface FastEthernet1/1
 description TO_R4
 ip address 10.0.3.1 255.255.255.252
 no shutdown

interface Loopback0
 ip address 192.168.3.1 255.255.255.0

ip route 0.0.0.0 0.0.0.0 10.0.3.2

crypto isakmp policy 1
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 86400

crypto isakmp key DMVPN_LAB_KEY address 0.0.0.0

crypto ipsec transform-set DMVPN_TS esp-aes 256 esp-sha256-hmac
 mode transport

crypto ipsec profile DMVPN_PROFILE
 set transform-set DMVPN_TS

interface Tunnel0
 ip address 172.16.0.3 255.255.255.0
 ip nhrp authentication NHRPKEY
 ip nhrp map multicast 10.0.1.1
 ip nhrp map 172.16.0.1 10.0.1.1
 ip nhrp network-id 1
 ip nhrp nhs 172.16.0.1
 ip nhrp shortcut
 tunnel source FastEthernet1/1
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile DMVPN_PROFILE

router eigrp 100
 network 172.16.0.0 0.0.0.255
 network 192.168.3.0 0.0.0.255
 no auto-summary

end
```

</details>
