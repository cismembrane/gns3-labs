# EIGRP Path Selection via Interface Delay Manipulation

## Overview

This lab demonstrates how EIGRP uses interface delay as a component of its composite metric to influence path selection. By increasing the delay on a specific interface, you can observe how EIGRP dynamically recalculates best paths and adjusts the routing table accordingly.

## Lab Topology

        R1
       / | \
     R2-R3-R4
       \ | /
         R5

R5 has three potential paths to reach R1:

- R5 -> R2 -> R1
- R5 -> R3 -> R1
- R5 -> R4 -> R1

Each link is point-to-point using /30 subnets. Each router has a loopback for identification (e.g., R1 = 1.1.1.1/32).

## Interfaces

| Router | Interface       | IP Address   | Connected To | Peer Interface  | Peer IP   |
| ------ | --------------- | ------------ | ------------ | --------------- | --------- |
| R1     | Loopback0       | 1.1.1.1/32   | —            | —               | —         |
| R1     | FastEthernet0/0 | 10.1.12.1/30 | R2           | FastEthernet0/0 | 10.1.12.2 |
| R1     | FastEthernet0/1 | 10.1.13.1/30 | R3           | FastEthernet0/0 | 10.1.13.2 |
| R1     | FastEthernet1/0 | 10.1.14.1/30 | R4           | FastEthernet0/0 | 10.1.14.2 |
| R2     | Loopback0       | 2.2.2.2/32   | —            | —               | —         |
| R2     | FastEthernet0/0 | 10.1.12.2/30 | R1           | FastEthernet0/0 | 10.1.12.1 |
| R2     | FastEthernet0/1 | 10.1.15.1/30 | R3           | FastEthernet0/1 | 10.1.15.2 |
| R2     | FastEthernet1/0 | 10.1.17.1/30 | R5           | FastEthernet0/0 | 10.1.17.2 |
| R2     | FastEthernet2/0 | 10.1.18.2/30 | R5           | FastEthernet0/1 | 10.1.18.1 |
| R3     | Loopback0       | 3.3.3.3/32   | —            | —               | —         |
| R3     | FastEthernet0/0 | 10.1.13.2/30 | R1           | FastEthernet0/1 | 10.1.13.1 |
| R3     | FastEthernet0/1 | 10.1.15.2/30 | R2           | FastEthernet0/1 | 10.1.15.1 |
| R3     | FastEthernet1/0 | 10.1.16.1/30 | R4           | FastEthernet0/1 | 10.1.16.2 |
| R4     | Loopback0       | 4.4.4.4/32   | —            | —               | —         |
| R4     | FastEthernet0/0 | 10.1.14.2/30 | R1           | FastEthernet1/0 | 10.1.14.1 |
| R4     | FastEthernet0/1 | 10.1.16.2/30 | R3           | FastEthernet1/0 | 10.1.16.1 |
| R4     | FastEthernet1/0 | 10.1.19.1/30 | R5           | FastEthernet1/0 | 10.1.19.2 |
| R5     | Loopback0       | 5.5.5.5/32   | —            | —               | —         |
| R5     | FastEthernet0/0 | 10.1.17.2/30 | R2           | FastEthernet1/0 | 10.1.17.1 |
| R5     | FastEthernet0/1 | 10.1.18.1/30 | R2           | FastEthernet2/0 | 10.1.18.2 |
| R5     | FastEthernet1/0 | 10.1.19.2/30 | R4           | FastEthernet1/0 | 10.1.19.1 |

## Objectives

- Apply delay to Interface F0/0 on R3
- Observe changes in R5's EIGRP routing behavior

## Configuration Steps

Step 1: Confirm Baseline

On R5:

show ip route

Expected:

D       1.1.1.1 [90/158720] via 10.1.19.1, 00:00:58, FastEthernet1/0
                [90/158720] via 10.1.18.1, 00:00:58, FastEthernet0/1
                [90/158720] via 10.1.17.1, 00:00:58, FastEthernet0/0

Step 2: Apply Delay To Interface FastEthernet0/0 On R3

On R3:

interface FastEthernet0/0
delay 10000

Since EIGRP calculates metric based on outbound interface delay, this change makes the R3 path less preferred.

Step 3: Confirm that the routing table on R5 has changed

show ip route

Expected:

D       1.1.1.1 [90/158720] via 10.1.19.1, 00:00:20, FastEthernet1/0
                [90/158720] via 10.1.17.1, 00:00:20, FastEthernet0/0

R3’s path is no longer present due to increased delay.

## Conclusion

This lab demonstrates how EIGRP uses composite metrics to influence path selection. Increasing delay on interface F0/0 on R3 causes the routing table on R5 to change. This behavior demonstrates that EIGRP dynamically recalculates routes based on metric changes. 

