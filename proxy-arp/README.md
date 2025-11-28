# Proxy ARP “Stretched Subnet” Lab (GNS3)

This lab demonstrates how to let two hosts talk as if they are on the same /24 network even though they are separated by routers. The trick is a combination of static host routes and standard proxy ARP on Cisco IOS.

The topology is built in GNS3 using two IOS routers and two VPCS hosts.

---

## Topology

Logical diagram:

PC1 ─ R1 ──────── R2 ─ PC2  
192.168.10.0/24 ─ 10.0.0.0/30 ─ 192.168.10.0/24

ASCII diagram:

     10.0.0.0/30
          (Fa0/1 10.0.0.1)        (10.0.0.2 Fa0/1)
                 +------+      +------+
                 |  R1  |------|  R2  |
                 +------+      +------+
          Fa0/0 192.168.10.1    192.168.10.2 Fa0/0
               |                            |
               |                            |
        192.168.10.0/24              192.168.10.0/24
               |                            |
        +--------------+            +--------------+
        |     PC1      |            |      PC2     |
        | 192.168.10.10|            | 192.168.10.20|
        |     /24      |            |      /24     |
        +--------------+            +--------------+

---

## Addressing

|Node | Int   | IP address    | Mask            | Notes                         |
|-----|-------|---------------|-----------------|-------------------------------|
| PC1 | eth0  | 192.168.10.10 | 255.255.255.0   | No default gateway configured |
| PC2 | eth0  | 192.168.10.20 | 255.255.255.0   | No default gateway configured |
| R1  | Fa0/0 | 192.168.10.1  | 255.255.255.0   | Connected to PC1              |
| R1  | Fa0/1 | 10.0.0.1      | 255.255.255.252 | Point-to-point to R2          |
| R2  | Fa0/1 | 10.0.0.2      | 255.255.255.252 | Point-to-point to R1          |
| R2  | Fa0/0 | 192.168.10.2  | 255.255.255.0   | Connected to PC2              |

Both PCs think they are on the same 192.168.10.0/24 network. There is no default gateway on either host; if they want to talk to each other, they ARP directly for the peer’s IP.

---

## R1 Configuration (relevant parts)

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

Notes on R1:

- Fa0/0 is the LAN facing PC1 (192.168.10.0/24).
    
- Fa0/1 is the point-to-point link to R2 (10.0.0.0/30).
    
- A static /32 route points 192.168.10.20 at R2 (10.0.0.2).
    
- On Cisco IOS, proxy ARP is enabled by default on LAN interfaces like Fa0/0. R1 will answer ARP requests on Fa0/0 for any destination it has a route to, as long as the destination appears to be in the same subnet as the interface.

---

## R2 Configuration (relevant parts)

`hostname R2 ! interface FastEthernet0/0  ip address 192.168.10.2 255.255.255.0  duplex auto  speed auto ! interface FastEthernet0/1  ip address 10.0.0.2 255.255.255.252  duplex auto  speed auto ! ip route 192.168.10.10 255.255.255.255 10.0.0.1`

Notes on R2:

- Fa0/0 is the LAN facing PC2 (192.168.10.0/24).
    
- A static host route points 192.168.10.10 toward R1 (10.0.0.1) over the 10.0.0.0/30 link.
    

---

## How the lab works

### From PC2 to PC1

1. PC2 wants to talk to 192.168.10.10. Because the destination is in the same /24, PC2 ARPs for 192.168.10.10.
    
2. The traffic reaches R2, which has a /32 static route for 192.168.10.10 via 10.0.0.1 and forwards packets across the 10.0.0.0/30 link to R1.
    
3. R1 receives the packets, does a route lookup, and sees 192.168.10.0/24 as directly connected on Fa0/0. It forwards the packets directly to PC1.
    

### From PC1 to PC2 (proxy ARP path)

1. PC1 wants to talk to 192.168.10.20. It believes this is a local host in the same /24, so it ARPs for 192.168.10.20.
    
2. The ARP broadcast hits R1’s Fa0/0. Because proxy ARP is enabled by default and R1 has a /32 static route for 192.168.10.20 via 10.0.0.2, R1 knows it can reach that IP through R2.
    
3. R1 responds to the ARP on behalf of the remote host, returning its own MAC address as the “MAC of 192.168.10.20.”
    
4. PC1 installs that MAC in its ARP cache and sends frames destined to 192.168.10.20 to R1’s MAC address.
    
5. R1 forwards the traffic across the 10.0.0.0/30 link to R2, which then sends it to PC2 on its local LAN.
    

The end result is that both PCs behave as if they are on a flat 192.168.10.0/24 network, but there is a routed hop in the middle. Proxy ARP on R1 hides the Layer-3 hop from PC1.

---

## Verification

Basic connectivity checks:

`PC1> ping 192.168.10.20`
`PC2> ping 192.168.10.10`

On R1, check ARP and routing:

`R1# show ip arp`
`R1# show ip route 192.168.10.10` 
`R1# show ip route 192.168.10.20`

On R2:

`R2# show ip route 192.168.10.10`
`R2# show ip arp`

You should see host routes for 192.168.10.10 and 192.168.10.20 pointing across the 10.0.0.0/30 link, and successful pings between PC1 and PC2.

---

## Takeaways

This lab shows how proxy ARP can be used to “stretch” a subnet across a routed link without changing host masks or configuring default gateways on the endpoints. It’s useful for understanding:

- ARP behavior on Cisco IOS
    
- Static /32 host routes
    
- How routers can hide Layer-3 topology from legacy hosts
    

In production designs this pattern is generally avoided in favor of clean subnetting and explicit default gateways, but as a learning tool it’s a good way to see what proxy ARP is doing under the hood.