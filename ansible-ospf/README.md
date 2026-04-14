# Ansible OSPF Deployment on Cisco 7200 Routers in GNS3

## Walkthrough

YouTube walkthrough: https://youtu.be/7IEfZew-7wQ

## Overview

This lab uses Ansible to build a four-router OSPF topology in GNS3 on Cisco 7200 images. The workflow starts by pushing a base management baseline, then moves the routed links onto physical interfaces, runs a precheck to confirm interface state and platform reachability, deploys OSPF from a Jinja template, and validates neighbor formation and protocol state from all four routers.

This one is really about taking a small routed lab and making the build repeatable. Instead of hand-configuring interfaces and OSPF on each box, the playbooks pull from inventory, group vars, and per-router host vars and push the right config to the right place.

## What this lab does

This lab demonstrates a few things working together:

- Jinja-based OSPF config rendering
- Routed point-to-point links placed on physical interfaces
- A clean deployment flow: base config, interface config, precheck, OSPF deploy, OSPF validation
- Local capture of validation output for each router

The interface descriptions also make it clear this lab was refactored from earlier VLAN-based transit links.

## Topology

The lab is built around four routers named `R1` through `R4`, each with a management interface on the `172.16.99.0/24` network and multiple routed transit links using /30s.

From the host variable files and validation output, the routed topology is:

- `R1` to `R2` on `10.0.1.0/30`
- `R2` to `R4` on `10.0.2.0/30`
- `R3` to `R4` on `10.0.3.0/30`
- `R1` to `R3` on `10.0.4.0/30`
- `R1` to `R4` on `10.0.5.0/30`

Management addressing is:

- `R1` `FastEthernet3/1` -> `172.16.99.11/24`
- `R2` `FastEthernet3/1` -> `172.16.99.12/24`
- `R3` `FastEthernet3/1` -> `172.16.99.13/24`
- `R4` `FastEthernet3/1` -> `172.16.99.14/24`

```text
      ┌─────────┐                                   ┌─────────┐      
      │         │                                   │         │      
      │   R1    │            10.0.1.0/30            │   R2    │      
      │         ┼───────────────────────────────────┼         │      
      │         │                                   │         │      
      └────┬────┘                                   └────┬────┘      
           │                                             │           
           │                                             │           
           │                                             │           
		   │ 10.0.4.0/30                     10.0.2.0/30 │
           │                                             │           
           │                                             │           
           │                                             │           
           │                                             │           
      ┌────┼────┐                                   ┌────┼────┐      
      │         │                                   │         │      
      │   R3    │                                   │   R4    │      
      │         ┼───────────────────────────────────┼         │      
      │         │            10.0.3.0/30            │         │      
      └─────────┘                                   └─────────┘      
					Additional: R1-R4 10.0.5.0/30
```
	
## Tools used

- Ansible Core 2.16.3
- Ubuntu
- GNS3
- Cisco IOS 7200 image `C7200-ADVENTERPRISEK9-M Version 15.3(3)XB12`
- Jinja2 template rendering

## How the lab is structured

`ansible.cfg` sets the local inventory, turns off host key checking, uses the YAML stdout callback, and sets connection and command timeouts.

`inventory-ios.ini` defines the four routers and sets the connection model for Cisco IOS.

`group_vars/ios.yml` holds shared OSPF settings and validation commands, plus the base management values like domain name, credentials, SSH modulus size, DNS server, and NTP server (not used in this lab).

Each router has its own `host_vars` file. That is where per-device intent lives:
- management interface and address
- OSPF router ID
- routed transit interfaces
- OSPF network statements

The playbooks break the deployment into stages:

- `playbooks/base-config.yml` pushes the common management and access baseline
- `playbooks/interface-config.yml` applies management and IP addressing to physical interfaces
- `playbooks/precheck.yml` confirms interface state and basic platform visibility
- `playbooks/ospf-deploy.yml` renders OSPF config from `templates/ospf-router.j2` and pushes it
- `playbooks/ospf-validate.yml` runs the OSPF checks and saves the output locally under `outputs/`

The OSPF template is simple on purpose. It builds `router ospf {{ ospf_process_id }}`, sets the router ID, then loops through `ospf_networks` for each router. Passive interfaces are supported in the template, but in this lab all `ospf_passive_interfaces` lists are empty.

## Deployment workflow

The lab was deployed in this order:

- `ansible-playbook playbooks/base-config.yml -v --diff`
- `ansible-playbook playbooks/interface-config.yml -v --diff`
- `ansible-playbook playbooks/precheck.yml -v`
- `ansible-playbook playbooks/ospf-deploy.yml -v --diff`
- `ansible-playbook playbooks/ospf-validate.yml -v`

### 1. Base config

The base playbook does the initial cleanup and management prep across all four routers.

It checks existing SSH status first with `show ip ssh`. In this run, SSH was already enabled on every router and RSA keys already existed, so the conditional RSA key generation step was skipped everywhere.

The base config then applies:

- `no ip domain-lookup`
- `ip domain-name test.com`
- `enable secret admin` (already applied manually)
- `username admin privilege 15 secret admin` (already applied manually)
- `ip ssh authentication-retries 3`

The actual playbook also includes service timestamps, login success/failure logging, ip ssh version 2, and ip ssh time-out 60.

Console and VTY access are standardized:

- console timeout set to 10 minutes
- VTY login set to local authentication
- VTY transport locked to SSH
- VTY timeout set to 15 minutes

NTP was attempted as an optional baseline and returned ok with no change. (NTP server not used in this lab)

### 2. Interface config

The interface playbook first asserts that each router has the required management and routed interface data in host_vars. All assertions passed.

It then configures the management interface on FastEthernet3/1 for each router and brings it up. The management interfaces have IP addresses assigned and are brought up as part of the manual config done before the Ansible deployment.

After that it pushes all transit links as routed physical interfaces. This lab initially used IOSvL2 images. These images displayed instability during the use of the `no switchport` command and were switched to IOSv images. These proved too too resource-intensive for the machine they were being used on. 

C3600 router images were then used, but SSH complained about outdated SSH encryption algorithms. 

C7200 router images were then used, to the same effect with SSH algorithms. 

The errors were finally overridden with client-side SSH command-line options and the C7200 router images were chosen despite this drawback. The interfaces are no longer living on SVIs or VLAN interfaces. The descriptions still preserve that history:

- TRANSIT (was Vlan10)
- TRANSIT (was Vlan20)
- TRANSIT (was Vlan30)
- TRANSIT (was Vlan40)
- TRANSIT (was Vlan50)

The resulting interface layout was:

R1
- FastEthernet0/0  10.0.1.1/30
- FastEthernet1/0  10.0.4.1/30
- FastEthernet3/0  10.0.5.1/30
- FastEthernet3/1  172.16.99.11/24

R2
- FastEthernet0/0  10.0.1.2/30
- FastEthernet2/0  10.0.2.1/30
- FastEthernet3/1  172.16.99.12/24

R3
- FastEthernet1/0  10.0.4.2/30
- FastEthernet1/1  10.0.3.1/30
- FastEthernet3/1  172.16.99.13/24

R4
- FastEthernet1/1  10.0.3.2/30
- FastEthernet2/0  10.0.2.2/30
- FastEthernet3/0  10.0.5.2/30
- FastEthernet3/1  172.16.99.14/24

The sanity check after interface deployment confirmed that the interfaces were up/up and that each router had the expected connected routes for its local /30 links plus the management subnet.

### 3. Precheck

The precheck playbook runs two commands:

- `show ip interface brief`
- `show version | include IOS`

This confirms two useful things before routing goes on:

- the interface state is where it should be after interface deployment

- all targets are Cisco IOS 7200 devices running 15.3(3)XB12

At this point, the network is built at Layer 3 but OSPF is not yet deployed.

### 4. OSPF deployment

The OSPF deploy playbook renders the router process config from templates/ospf-router.j2 using shared group vars and router-specific host vars.

Rendered examples from the run:

R1
- `router ospf 1`
- `router-id 1.1.1.1`
- `network 10.0.1.0 0.0.0.3 area 0`
- `network 10.0.4.0 0.0.0.3 area 0`
- `network 10.0.5.0 0.0.0.3 area 0`

R4
- `router ospf 1`
- `router-id 4.4.4.4`
- `network 10.0.5.0 0.0.0.3 area 0`
- `network 10.0.2.0 0.0.0.3 area 0`
- `network 10.0.3.0 0.0.0.3 area 0`

Every router reported Changed: True, which makes sense because this looks like the first OSPF push in the sequence.

### 5. OSPF validation

The validation playbook runs the command set defined in group_vars/ios.yml:

- `show ip ospf neighbor`
- `show ip route ospf`
- `show ip protocols`

It prints the output for each router and also saves a local file per device:

- `outputs/R1-ospf-validation.txt`
- `outputs/R2-ospf-validation.txt`
- `outputs/R3-ospf-validation.txt`
- `outputs/R4-ospf-validation.txt`

### Deployment steps

- `ansible-playbook playbooks/base-config.yml -v --diff`
- `ansible-playbook playbooks/interface-config.yml -v --diff`
- `ansible-playbook playbooks/precheck.yml -v`
- `ansible-playbook playbooks/ospf-deploy.yml -v --diff`
- `ansible-playbook playbooks/ospf-validate.yml -v`

### Validation

The validation output shows that OSPF formed neighbors on every expected transit link.

Neighbor state

R1 sees three neighbors:

- 2.2.2.2 on 10.0.1.2
- 3.3.3.3 on 10.0.4.2
- 4.4.4.4 on 10.0.5.2

R2 sees two neighbors:

- 1.1.1.1 on 10.0.1.1
- 4.4.4.4 on 10.0.2.2

R3 sees two neighbors:

- 1.1.1.1 on 10.0.4.1
- 4.4.4.4 on 10.0.3.2

R4 sees three neighbors:

- 1.1.1.1 on 10.0.5.1
- 2.2.2.2 on 10.0.2.1
- 3.3.3.3 on 10.0.3.1

OSPF process state

`show ip protocols` confirms on all four routers that:

- OSPF process ID is 1
- area is 0
- router IDs are correct
- the correct network statements were applied per router

### Results

The lab deployed cleanly.

Base config:

- all four routers reachable
- all four routers updated
- no unreachable hosts
- no failed tasks
- RSA generation correctly skipped because SSH was already enabled

Interface config:

- all required host variables present
- management and transit interfaces configured successfully
- connected route sanity check matched the intended per-router links

Precheck:

- all four routers responded
- all four identified as Cisco 7200 IOS devices

OSPF deploy:

- OSPF process pushed successfully to all four routers
- all four routers reported changes

OSPF validation:

- all four routers returned neighbor and protocol output successfully
- local validation artifacts were written for all four routers
- no failures or unreachable devices

### Notes

This repo is data-driven enough to be easy to extend. Adding a new router mostly comes down to adding inventory and host vars, then defining its routed links and OSPF networks.
