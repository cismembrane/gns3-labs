# GLBP Lab (Gateway Load Balancing Protocol)

## Lab Prerequisites

- GNS3 installed and functional
- Cisco IOS router images that support GLBP (c3660-a3jk9s-mz.124-15.T14.image was used for this lab)

## Lab Objective

Demonstrate the configuration and behavior of GLBP in a dual-router topology where client PCs share the load across multiple default gateways. Validate failover and load balancing functionality.

## Topology Diagram


 +--------+                      +--------+
 |  R1    |                      |   R2   |
 +--------+                      +--------+ 
         |                        |
      +-----------------------------+
      |            SW1              |
      +-----------------------------+
       |                           |
 +--------+                       +--------+
 |  PC1   |                       |  PC2   |
 +--------+                       +--------+

## Topology Overview


- R1 and R2 are configured as members of GLBP group 1
- PC1 and PC2 use a shared virtual default gateway
- Traffic is load-balanced across both routers using GLBP's AVF feature.

## Lab Devices

| Device | Role        | IP Address        | Notes                        |
|--------|-------------|-------------------|------------------------------|
| PC1    | Client      | 192.168.1.10      | Default GW: GLBP virtual IP  |
| PC2    | Client      | 192.168.1.11      | Default GW: GLBP virtual IP  |
| R1     | Gateway 1   | 192.168.1.1       | GLBP AVF                     |
| R2     | Gateway 2   | 192.168.1.2       | GLBP AVF                     |
| SW1    | Switch      | None              | Connects all LAN devices     |                          |

| Link         | Interface A       | Interface B       | Purpose                         |
|--------------|-------------------|-------------------|---------------------------------|
| R1 <-> R2    | R1 Fa0/0          | R2 Fa0/0          | Internal communication for GLBP |
| PC1 <-> SW1  | PC1 Eth0          | SW1 Eth0          | PC1 access to GLBP gateway      |
| PC2 <-> SW1  | PC2 Eth0          | SW1 Eth1          | PC2 access to GLBP gateway      |
| SW1 <-> R1   | SW1 Eth2          | R1 Fa0/1          | GLBP LAN side link              |                         |
| SW1 <-> R2   | SW1 Eth3          | R2 Fa0/1          | GLBP LAN side link              |

## Configuration Steps

### R1

interface Fa0/1
 ip address 192.168.1.1 255.255.255.0
 glbp 1 ip 192.168.1.254
 glbp 1 priority 110
 glbp 1 preempt
 glbp 1 load-balancing round-robin

interface Fa0/0
ip address 192.168.2.1 255.255.255.0

### R2

interface Fa0/1
ip address 192.168.1.2 255.255.255.0
 glbp 1 ip 192.168.1.254
 glbp 1 priority 100
 glbp 1 preempt
 glbp 1 load-balancing round-robin

interface Fa0/0
ip address 192.168.2.2 255.255.255.0

### PC1

 ip 192.168.1.10/24 192.168.1.254

### PC2

ip 192.168.1.11/24 192.168.1.254

## Validation

1. On PC1/PC2: ping 192.168.1.254
2. Inspect ARP cache: arp - note which router's virtual MAC is in use
3. On R1/R2: show glbp brief to confirm Active/Standby and AVF roles

Expected: PCs alternate replies when round-robin load-balancing is working. After shutting down R1, R2 becomes AVG until R1 is back and preempts.

R1 show glbp brief output:
Interface   Grp  Fwd Pri State    Address         Active router   Standby router
Fa0/1       1    -   110 Active   192.168.1.254   local           192.168.1.2
Fa0/1       1    1   -   Active   0007.b400.0101  local           -
Fa0/1       1    2   -   Listen   0007.b400.0102  192.168.1.2     -

R2 show glbp brief output:
Interface   Grp  Fwd Pri State    Address         Active router   Standby router
Fa0/1       1    -   100 Standby  192.168.1.254   192.168.1.1     local
Fa0/1       1    1   -   Listen   0007.b400.0101  192.168.1.1     -
Fa0/1       1    2   -   Active   0007.b400.0102  local           -

## References

- [Cisco GLBP Configuration Guide (IOS)](https://www.cisco.com/en/US/docs/ios/12_2t/12_2t15/feature/guide/ft_glbp.html)

## Metadata

- Platform: GNS3
- Protocols Used: GLBP
- Created: 24 June 2025
- Author: cismembrane@gmail.com

