# Proxy ARP Stretched Subnet Lab

Two VPCS hosts on separate LAN segments communicate as if they share a flat 192.168.10.0/24 subnet. A pair of IOS routers sit between them, using static /32 host routes and proxy ARP to hide the routed hop. Built in GNS3 with Dynamips.

## Topology
```
         10.0.0.0/30
              (Fa0/1 10.0.0.1)        (10.0.0.2 Fa0/1)
                     +------+      +------+
                     |  R1  |------|  R2  |
                     +------+      +------+
              Fa0/0 192.168.10.1    192.168.10.2 Fa0/0
                   |                            |
            192.168.10.0/24              192.168.10.0/24
                   |                            |
            +--------------+            +--------------+
            |     PC1      |            |      PC2     |
            | 192.168.10.10|            | 192.168.10.20|
            |     /24      |            |      /24     |
            +--------------+            +--------------+
```

R1 and R2 are connected by a 10.0.0.0/30 point-to-point link (Fa0/1 on both routers). Each router's Fa0/0 faces a local LAN segment addressed out of 192.168.10.0/24. PC1 sits on R1's LAN at 192.168.10.10/24. PC2 sits on R2's LAN at 192.168.10.20/24. Neither host has a default gateway configured; both assume every 192.168.10.x address is local and will ARP directly for it.

## Addressing

| Node | Interface | IP Address      | Mask              |
|------|-----------|-----------------|-------------------|
| PC1  | eth0      | 192.168.10.10   | 255.255.255.0     |
| PC2  | eth0      | 192.168.10.20   | 255.255.255.0     |
| R1   | Fa0/0     | 192.168.10.1    | 255.255.255.0     |
| R1   | Fa0/1     | 10.0.0.1        | 255.255.255.252   |
| R2   | Fa0/1     | 10.0.0.2        | 255.255.255.252   |
| R2   | Fa0/0     | 192.168.10.2    | 255.255.255.0     |

## R1 Configuration

```
hostname R1
!
interface FastEthernet0/0
 ip address 192.168.10.1 255.255.255.0
 duplex auto
 speed auto
!
interface FastEthernet0/1
 ip address 10.0.0.1 255.255.255.252
 no ip redirects
 ip route-cache same-interface
 duplex auto
 speed auto
!
ip route 192.168.10.0 255.255.255.0 10.0.0.2
ip route 192.168.10.20 255.255.255.255 10.0.0.2
```

Fa0/0 is the LAN-facing interface toward PC1. Fa0/1 is the point-to-point link to R2. The /32 static route for 192.168.10.20 points at R2's side of the link (10.0.0.2), which gives R1 a routing table entry for PC2's address. Proxy ARP is enabled by default on Cisco IOS LAN interfaces, so R1 will answer ARP requests on Fa0/0 for any destination it has a route to within the same subnet range. That /32 route is what makes proxy ARP work here.

## R2 Configuration

```
hostname R2
!
interface FastEthernet0/0
 ip address 192.168.10.2 255.255.255.0
 duplex auto
 speed auto
!
interface FastEthernet0/1
 ip address 10.0.0.2 255.255.255.252
 duplex auto
 speed auto
!
ip route 192.168.10.10 255.255.255.255 10.0.0.1
```

Same structure in reverse. Fa0/0 faces PC2, and the /32 static route for 192.168.10.10 points at R1 (10.0.0.1) across the point-to-point link.

## Traffic Flow

When PC1 sends traffic to 192.168.10.20, it ARPs for that address directly because it believes 192.168.10.20 is on its local /24 segment. R1's Fa0/0 receives the ARP broadcast. R1 has a /32 route for 192.168.10.20 via 10.0.0.2, so it responds to the ARP with its own MAC address on behalf of the remote host. PC1 caches that MAC, and all subsequent frames destined for 192.168.10.20 go to R1. R1 forwards them across the 10.0.0.0/30 link to R2, which delivers them to PC2 on its local segment.

The return path from PC2 to PC1 works the same way. PC2 ARPs for 192.168.10.10, R2 answers via proxy ARP (or forwards based on its /32 route), and traffic crosses the point-to-point link back to R1, which delivers it to PC1.

## Verification
```
PC1> ping 192.168.10.20
PC2> ping 192.168.10.10
```
```
R1# show ip arp
R1# show ip route 192.168.10.20
R2# show ip route 192.168.10.10
R2# show ip arp
```

The ARP tables on both routers should show learned entries for the local host on Fa0/0 and the remote router on Fa0/1. The /32 static routes should be visible in the routing table pointing across the 10.0.0.0/30 link. Pings between PC1 and PC2 should succeed.

## Notes

This pattern stretches a single subnet across a routed boundary without changing host masks or adding default gateways. It works because proxy ARP lets a router answer ARP requests on behalf of hosts it can reach through its routing table, and the /32 static routes give it the specific entries it needs to do so. Production networks avoid this in favor of proper subnetting and explicit gateways, but it isolates the proxy ARP mechanism cleanly for study.