# Ansible eBGP Lab

Automated deployment of a four-router eBGP linear chain on Cisco c7200 routers in GNS3. Each router runs in its own autonomous system with full prefix advertisement via BGP network statements.

## Topology

Four c7200 routers in a linear eBGP chain across AS 65001 through AS 65004. Each router peers exclusively with its immediate neighbors over point-to-point /29 transit links. Every router connects to a VPC on a dedicated 192.168.x.0/24 LAN segment via FastEthernet3/1.

```
R1 (AS 65001) --- R2 (AS 65002) --- R3 (AS 65003) --- R4 (AS 65004)
|                 |                  |                  |
PC1               PC2               PC3               PC4
192.168.1.0/24    192.168.2.0/24    192.168.3.0/24    192.168.4.0/24
```

### Addressing

| Device | Interface | Address | Description |
|--------|-----------|---------|-------------|
| R1 | Loopback0 | 1.1.1.1/32 | Router ID |
| R1 | Fa0/0 | 10.0.1.1/29 | Transit to R2 |
| R1 | Fa3/1 | 192.168.1.254/24 | LAN |
| R2 | Loopback0 | 2.2.2.2/32 | Router ID |
| R2 | Fa0/0 | 10.0.1.2/29 | Transit to R1 |
| R2 | Fa1/0 | 10.0.2.2/29 | Transit to R3 |
| R2 | Fa3/1 | 192.168.2.254/24 | LAN |
| R3 | Loopback0 | 3.3.3.3/32 | Router ID |
| R3 | Fa1/0 | 10.0.2.3/29 | Transit to R2 |
| R3 | Fa1/1 | 10.0.3.3/29 | Transit to R4 |
| R3 | Fa3/1 | 192.168.3.254/24 | LAN |
| R4 | Loopback0 | 4.4.4.4/32 | Router ID |
| R4 | Fa1/1 | 10.0.3.4/29 | Transit to R3 |
| R4 | Fa3/1 | 192.168.4.254/24 | LAN |

### eBGP Peering

| Router | Neighbor | Local AS | Remote AS |
|--------|----------|----------|-----------|
| R1 | 10.0.1.2 | 65001 | 65002 |
| R2 | 10.0.1.1 | 65002 | 65001 |
| R2 | 10.0.2.3 | 65002 | 65003 |
| R3 | 10.0.2.2 | 65003 | 65002 |
| R3 | 10.0.3.4 | 65003 | 65004 |
| R4 | 10.0.3.3 | 65004 | 65003 |

## Prerequisites

- GNS3 with c7200 Dynamips image configured
- SSH enabled on all routers with credentials matching `group_vars/routers.yml`
- Ansible 2.14+ with `cisco.ios` and `ansible.netcommon` collections installed
- Management reachability from the Ansible control node to each router

```bash
ansible-galaxy collection install cisco.ios ansible.netcommon
```

## Project Structure

```
ansible-ebgp/
├── ansible.cfg
├── inventory.yml
├── group_vars/
│   └── routers.yml          # Connection and credential defaults
├── host_vars/
│   ├── R1.yml               # Per-router interfaces, BGP neighbors, networks
│   ├── R2.yml
│   ├── R3.yml
│   └── R4.yml
├── templates/
│   ├── interfaces.j2        # Interface and hostname config
│   └── bgp.j2               # BGP process, neighbors, address-family
├── deploy.yml                # Push config to all routers
└── verify.yml                # Validate BGP state and reachability
```

## Usage

Update `inventory.yml` with the management IP or GNS3 console addresses for each router. Update `group_vars/routers.yml` with the correct credentials.

Deploy the configuration:

```bash
ansible-playbook deploy.yml
```

Verify BGP state and end-to-end reachability:

```bash
ansible-playbook verify.yml
```

## Verification Targets

The verify playbook checks three conditions per router. First, `show ip bgp summary` output must contain no neighbors in Idle state. Second, no neighbors stuck in Active state, which indicates a TCP session that cannot establish. Third, on R1 and R4 specifically, ping tests from the loopback source to the far-end LAN gateway confirm end-to-end forwarding across all three eBGP hops.

Expected BGP table on R1 after convergence includes eight prefixes: four loopback /32s and four LAN /24s. Routes to R4's prefixes (4.4.4.4/32 and 192.168.4.0/24) should show an AS path of 65002 65003 65004, confirming the full chain is operational.
