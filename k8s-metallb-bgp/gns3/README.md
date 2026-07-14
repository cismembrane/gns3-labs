# GNS3 Project Notes

Rebuild notes for the GNS3 side of the k8s-metallb-bgp lab. The main README covers the Kubernetes side and the full workflow; this file covers only the topology.

The topology is the same four-router IOSv eBGP ring used in `bgp-grafana-monitoring`, plus three extra links. Cloud2 (tap1) to R1, Cloud3 (tap2) to R4, and Cloud4 (tap3) to R3.

---

## Topology

```text
        R1 AS 65001 <-> R2 AS 65002
            ^                v
        R4 AS 65004 <-> R3 AS 65003

        R1 Gi0/5 <-> Cloud2 (tap1) <-> k3s node (AS 65100)
        R4 Gi0/5 <-> Cloud3 (tap2) <-> k3s node (AS 65100)
        R3 Gi0/5 <-> Cloud4 (tap3) <-> client netns (no BGP)
```

The k3s node is attached through the tap1 and tap2 interfaces. It holds one eBGP session to R1 and one to R4, both originated by MetalLB. The client is a network namespace on the same host, attached behind R3 via `tap3`/Cloud4. It exists so data-plane tests originate outside the node (node-local curls are DNAT'd by kube-proxy before routing and never cross the ring).

---

## Physical Link Map

| Link      | Router A | Interface          | IP Address  | Router B / Host | Interface          | IP Address  | Transit Subnet |
|-----------|----------|--------------------|-------------|-----------------|--------------------|-------------|----------------|
| R1 to R2  | R1       | GigabitEthernet0/0 | 10.0.1.1/29 | R2              | GigabitEthernet0/0 | 10.0.1.2/29 | 10.0.1.0/29    |
| R2 to R3  | R2       | GigabitEthernet0/1 | 10.0.2.2/29 | R3              | GigabitEthernet0/1 | 10.0.2.3/29 | 10.0.2.0/29    |
| R3 to R4  | R3       | GigabitEthernet0/2 | 10.0.3.3/29 | R4              | GigabitEthernet0/2 | 10.0.3.4/29 | 10.0.3.0/29    |
| R4 to R1  | R4       | GigabitEthernet0/3 | 10.0.4.4/29 | R1              | GigabitEthernet0/3 | 10.0.4.1/29 | 10.0.4.0/29    |
| R1 to k3s | R1       | GigabitEthernet0/5 | 10.0.5.1/29 | k3s host        | tap1               | 10.0.5.5/29 | 10.0.5.0/29    |
| R4 to k3s | R4       | GigabitEthernet0/5 | 10.0.6.4/29 | k3s host        | tap2               | 10.0.6.5/29 | 10.0.6.0/29    |
| R3 to client | R3    | GigabitEthernet0/5 | 10.0.7.3/29 | client netns    | tap3               | 10.0.7.2/29 | 10.0.7.0/29    |

Management, same pattern as the other labs:

| Link          | Interface          | Switch Interface |
|---------------|--------------------|------------------|
| R1 to SW1     | GigabitEthernet0/4 | Ethernet0        |
| R2 to SW1     | GigabitEthernet0/4 | Ethernet1        |
| R3 to SW1     | GigabitEthernet0/4 | Ethernet2        |
| R4 to SW1     | GigabitEthernet0/4 | Ethernet3        |
| Cloud1 to SW1 | tap0               | Ethernet4        |
| Cloud2 to R1  | tap1               | Ethernet5        |
| Cloud3 to R4  | tap2               | Ethernet6        |
| Cloud4 to R3  | tap3               | (direct to R3 Gi0/5) |

## BGP Neighbor Map

| Router | Local AS | Neighbor    | Neighbor AS | Neighbor IP |
|--------|----------|-------------|-------------|-------------|
| R1     | 65001    | R2          | 65002       | 10.0.1.2    |
| R1     | 65001    | R4          | 65004       | 10.0.4.4    |
| R1     | 65001    | k3s/MetalLB | 65100       | 10.0.5.5    |
| R2     | 65002    | R1          | 65001       | 10.0.1.1    |
| R2     | 65002    | R3          | 65003       | 10.0.2.3    |
| R3     | 65003    | R2          | 65002       | 10.0.2.2    |
| R3     | 65003    | R4          | 65004       | 10.0.3.4    |
| R4     | 65004    | R3          | 65003       | 10.0.3.3    |
| R4     | 65004    | R1          | 65001       | 10.0.4.1    |
| R4     | 65004    | k3s/MetalLB | 65100       | 10.0.6.5    |

## Management Address Map

| Device   | Management Interface | Management IP    |
|----------|----------------------|------------------|
| R1       | GigabitEthernet0/4   | 192.168.0.1/24   |
| R2       | GigabitEthernet0/4   | 192.168.0.2/24   |
| R3       | GigabitEthernet0/4   | 192.168.0.3/24   |
| R4       | GigabitEthernet0/4   | 192.168.0.4/24   |
| k3s host | tap0                 | 192.168.0.100/24 |

## k3s Transit Links

| Interface | IP           | Peers | Router IP  |
|-----------|--------------|-------|------------|
| tap1      | 10.0.5.5/29  | R1    | 10.0.5.1   |
| tap2      | 10.0.6.5/29  | R4    | 10.0.6.4   |

---

## Requirements

- A Cisco IOSv qcow2 image registered as a GNS3 QEMU appliance. The project references it as `virtioa.qcow2`. IOSv is licensed Cisco software and is not in this repo. Supply your own and register it before importing the project.
- Four IOSv router nodes named `R1` through `R4`, with at least six network adapters each (Gi0/0 through Gi0/5).
- One GNS3 Ethernet Switch `SW1` for the management segment.
- Four GNS3 Cloud nodes: `Cloud1` (tap0, management), `Cloud2` (tap1, R1 transit), `Cloud3` (tap2, R4 transit), `Cloud4` (tap3, R3 client segment).
- A Linux GNS3 host that will run k3s.

## Host Connectivity

`../scripts/setup-taps.sh` creates the three k3s-side TAP interfaces, addresses them, and installs the return routes into the ring. `../scripts/setup-client-netns.sh` creates `tap3`, the `br-client` bridge, and the client namespace behind R3. Run both, then bind each TAP to its Cloud node in GNS3 and wire the links per the tables above.

TAPs and the client namespace do not survive a reboot. Rerun both scripts after restarting the host.

Validate before moving on:

```text
ping 192.168.0.1   # R1 management via tap0
ping 10.0.5.1      # R1 transit via tap1 (after deploy.yml has run)
ping 10.0.6.4      # R4 transit via tap2 (after deploy.yml has run)
sudo ip netns exec client ping 10.0.7.3   # R3 from the client (after deploy.yml has run)
```

## Bootstrap

Each router needs SSH reachability before Ansible can configure it. Credentials are admin/admin in this lab.

Once `ssh admin@192.168.0.1` through `.4` work, return to the lab root and run the workflow in the [main README](../README.md).
