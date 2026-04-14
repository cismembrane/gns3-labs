# Redundant OSPF Core with HSRP Access, EEM-Gated DHCP Relay, Authenticated NTP, and IOS DNS

A 4-router lab demonstrating OSPFv2 with MD5 authentication, a totally-stub access area, HSRP gateway redundancy, centralized DHCP on R2 with an EEM-controlled relay that follows HSRP state, plus core services (IOS DNS and authenticated NTP).

---

## Overview

This topology models a small core/access design:
- Core: R2 in OSPF Area 0 with uplinks to access ABRs (R3/R4), originates a default learned from a static route to R1.
- Access: R3/R4 are HSRP peers on the user VLAN and ABRs into a totally-stub Area 10 (access interfaces are passive).
- Services: R1 provides IOS DNS and authenticated NTP; it does not run OSPF.

All devices use local `admin` for SSH (`login local`, `transport input ssh`). Config archive hides keys.

---

## Topology

		 R1
         |
         R2
       /   \
     R3     R4
       \   /
        SW1
      /     \
    PC1     PC2

No IPs in the diagram; see addressing tables below.

---

## Addressing Summary

### Loopbacks

| Device | Interface | Address          |
|:-----:|:---------:|:------------------|
| R1    | Lo0       | 10.255.255.1/32  |
| R2    | Lo0       | 10.255.255.2/32  |
| R3    | Lo0       | 10.255.255.3/32  |
| R4    | Lo0       | 10.255.255.4/32  |

### Transit & LAN

| Link     | Network         | Endpoint A         | Endpoint B         |
|----------|-----------------|--------------------|--------------------|
| R1 - R2  | 203.0.113.0/30  | R1: 203.0.113.1    | R2: 203.0.113.2    |
| R2 - R3  | 10.0.0.0/30     | R3: 10.0.0.1       | R2: 10.0.0.2       |
| R2 - R4  | 10.0.1.0/30     | R4: 10.0.1.1       | R2: 10.0.1.2       |
| LAN      | 192.168.10.0/24 | R3: 192.168.10.2   | R4: 192.168.10.3   |

### HSRP (VLAN 192.168.10.0/24)

| Group | VIP           | R3 / Priority                | R4 / Priority               | Notes               |
|-------|---------------|------------------------------|-----------------------------|---------------------|
| 10    | 192.168.10.1  | 192.168.10.2 / 110 (preempt) | 192.168.10.3 / 90 (preempt) | R3 typically Active |

---

## Routing

- OSPF process 1 on R2/R3/R4  
- Area 0: R2–R3 (10.0.0.0/30), R2–R4 (10.0.1.0/30), and the ABRs’ loopbacks (R2/R3/R4 Lo0 in area 0)  
- Area 10 (totally-stub): 192.168.10.0/24 behind R3/R4; access interfaces are passive  
- Authentication: OSPF MD5 on area 0 links (message-digest configured end-to-end)  
- Default: R2 has `ip route 0.0.0.0/0 203.0.113.1` and `default-information originate` toward Area 0  
- R1: static `ip route 0.0.0.0/0 203.0.113.2`; no OSPF

---

## DHCP

- Server: Centralized on R2
- Pool: `192.168.10.0/24` with exclusions `192.168.10.1–10`  
- Default gateway: `192.168.10.1` (HSRP VIP)  
- DNS server: `10.255.255.1` (R1)  
- Domain: `test.com`  

### EEM-Gated Relay (R3/R4)

- Goal: Only the HSRP Active node relays DHCP, keeping `giaddr` aligned to the active gateway and preventing duplicate offers.

R3 (LAN = Fa0/1)  
- Applet enables `ip helper-address 10.0.0.2` when HSRP goes Active and removes it when it leaves Active.  
- Notes: Config initially contains the helper; EEM ensures convergence to the correct state on transitions.

R4 (LAN = Fa0/0)  
- Applet removes/adds helper on Active transition (idempotent “no/add” pair), and removes on leaving Active.  
- Pattern is unanchored (works across platforms/IOS messages).

---

## Core Services

| Service     | Location | Details                                                                            |
|-------------|----------|------------------------------------------------------------------------------------|
| DNS         | R1       | `ip dns server` with static hosts: `r1.test.com` … `r4.test.com` → 10.255.255.1–.4 |
| NTP         | R1       | `ntp master` with auth key 1; `ntp authenticate` and `ntp trusted-key 1`           |
| NTP Clients | R2/R3/R4 | `ntp server 10.255.255.1 key 1`, `ntp source Loopback0`, auth/trusted configured   |

---

## Management & Hardening

- SSH-only on VTY (`transport input ssh`) with `login local` (user `admin` defined on all devices)  
- Config archive with `hidekeys`; logging buffered; `exec-timeout` applied on VTYs  
- Domain `test.com` on devices (R1 disables DNS lookup to avoid CLI hangs)

---

## Key Interface Notes

| Device | Interfaces & Purpose                                                                        |
|--------|---------------------------------------------------------------------------------------------|
| R1     | `Fa1/0` → R2 (`203.0.113.1/30`); default via `203.0.113.2`                                  |
| R2     | `Fa1/0` → R1 (`203.0.113.2/30`); `Fa0/0` → R3 (`10.0.0.2/30`); `Fa0/1` → R4 (`10.0.1.2/30`) |
| R3     | `Fa0/0` → R2 (`10.0.0.1/30`); `Fa0/1` → LAN (`192.168.10.2/24`, HSRP G10)                   |
| R4     | `Fa0/1` → R2 (`10.0.1.1/30`); `Fa0/0` → LAN (`192.168.10.3/24`, HSRP G10)                   |

---

## Verification Checklist

### HSRP
- `show standby brief` (R3/R4) → VIP `192.168.10.1`, R3 Active (110), R4 Standby (90).

### OSPF
- `show ip ospf neighbor` (R2/R3/R4) → FULL on /30 links (p2p).  
- `show ip route` → R3/R4 learn only a default in Area 10.  
- `show ip ospf interface` → message-digest enabled on Area 0 links.

### DHCP
- Client on LAN receives IP in `192.168.10.0/24`, GW `192.168.10.1`, DNS `10.255.255.1`.  
- Force HSRP failover (e.g., lower R3 priority or shut/no shut). New Active should own the helper and leases still arrive from R2.

### NTP
- `show ntp associations` → R2/R3/R4 synced to `10.255.255.1` with key 1 (auth).

### Edge Reachability
- From R3: `traceroute 203.0.113.1` → `10.0.0.2` (R2) → `203.0.113.1` (R1).

---

## Design Notes

- Totally-stub Area 10 keeps access simple; ABRs inject only a default toward the LAN.  
- OSPF MD5 on the uplinks thwarts trivial neighbor spoofing in demos.  
- EEM-gated relay ensures DHCP `giaddr` matches the active gateway, avoiding duplicate offers and keeping state consistent across failovers.

---

## Reproduce Quickly

Use GNS3 or EVE-NG with IOS 12.4 images.  
Wire links per the topology, paste the provided configs, and validate using the checklist above.

## To do

Add a TACACS or RADIUS server in the future.
