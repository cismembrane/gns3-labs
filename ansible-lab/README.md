# GNS3 IOSvL2 to Ubuntu Cloud Ansible Baseline Push Lab

## Overview

This lab shows a simple, real workflow:

- Build a small GNS3 topology with two Cisco IOSvL2 nodes
- Connect the topology to my Ubuntu host through a GNS3 Cloud node
- Use Ansible from Ubuntu to push a baseline config
- Run pre-checks and post-checks to validate the changes

This is hands-on networking + automation focused on management connectivity and repeatable config deployment.

## Lab Goal

Prove end-to-end management connectivity from my Ubuntu box into Cisco devices running in GNS3, then use Ansible to push a baseline IOS configuration and validate that the changes were applied.

## Topology

- `MLS1` (Cisco IOSvL2)
- `MLS2` (Cisco IOSvL2)
- `Cloud1` (GNS3 Cloud node connected to Ubuntu host)

Logical layout shown in GNS3:

`MLS1 <-> MLS2 <-> Cloud1 <-> Ubuntu host`

## Hostname Note

The switches were originally named `MLS1` and `MLS2` in the GNS3 topology.

In the Ansible inventory, the devices were defined with inventory hostnames `R1` and `R2`. The baseline playbook uses:

- `hostname {{ inventory_hostname }}`

Because of that, when the playbook was run, Ansible changed the device hostnames from `MLS1` / `MLS2` to `R1` / `R2`.

This is expected behavior in this lab and confirms that the config push applied successfully to both devices.

## Tools and Components

Ubuntu (Ansible control node), GNS3, two Cisco IOSvL2 nodes, a GNS3 Cloud node, Ansible, the 'cisco.ios' collection, and `ansible.netcommon.network_cli`.

## How Connectivity Was Built (GNS3 Cloud <-> Ubuntu)

This lab uses a GNS3 Cloud node to connect the virtual lab to the Ubuntu host so Ansible on Ubuntu can reach the Cisco management IPs.

What is visible from the screenshots and confirmed in setup:

- `MLS2` is directly connected to `Cloud1`
- `Cloud1` is bound to the Ubuntu host interface `tap-gns3`
- The Ansible inventory targets `172.16.99.11` and `172.16.99.12`

### IP Address Chart

| Device | Interface | IP Address    | Subnet Mask   | Prefix         | Network          | Broadcast           |
|------------|---------------|---------------------|-----------------------|-------------------|----------------------|---------------------------|
| R1       | Vlan1      | 172.16.99.11 | 255.255.255.0 | 172.16.99.0 | 172.16.99.255 | Management SVI |
| R2       | Vlan1      | 172.16.99.12 | 255.255.255.0 | 172.16.99.0 | 172.16.99.255 | Management SVI |

## Repository Contents

- `ansible-lab.gns3` - GNS3 project file
- `ansible.cfg` - Project-local Ansible configuration used when running from this directory
- `inventory-ios.ini` - Static inventory (INI format) with IOS targets and connection variables
- `baseline.yml` - Playbook that runs pre-checks, pushes baseline config, and runs post-checks

## Ansible Workflow

### Local Ansible config (`ansible.cfg`)

- `inventory = inventory-ios.ini`
- `host_key_checking = False`
- `stdout_callback = yaml`
- persistent connection timeout settings
- pipelining enabled
- `ansible.netcommon.network_cli` using `paramiko`

### Inventory (`inventory-ios.ini`)

The inventory screenshot shows:

- group: `[ios]`
- `R1 ansible_host=172.16.99.11`
- `R2 ansible_host=172.16.99.12`

It also defines:

- `ansible_connection=ansible.netcommon.network_cli`
- `ansible_network_os=cisco.ios.ios`
- username/password auth
- `become` settings for enable mode

### Playbook (`baseline.yml`)

The playbook is a baseline IOS config + validation workflow:

- `hosts: ios`
- `gather_facts: false`

Vars visible in the screenshot:

- `domain_name: test.com`
- `ntp_server: 172.16.99.1`

Pre-checks use `cisco.ios.ios_command` to capture state with commands like:

- `show version | i uptime|System image|Model number`
- `show ip int brief`
- `show run | i hostname|ip domain-name|username|ip ssh`

Then it prints output via `ansible.builtin.debug`.

Config push uses `cisco.ios.ios_config` to apply baseline settings including:

- hostname set from `{{ inventory_hostname }}`
- `ip domain-name {{ domain_name }}`
- service timestamps (debug/log with msec)
- `ip ssh version 2`
- `ip ssh time-out 60`
- `ip ssh authentication-retries 2`
- `login block-for 60 attempts 3 within 60`
- `no ip http server`
- `no ip http secure-server`
- `logging buffered 64000`
- `ntp server {{ ntp_server }}`

`save_when: modified` is enabled.

Post-checks validate that the expected config is present after the push.

## How to Run the Lab

### Prereqs

- GNS3 topology is up
- Ubuntu host can reach the Cisco management IPs through `Cloud1` (`tap-gns3`)
- SSH is enabled on both IOSvL2 devices
- Ansible is installed on Ubuntu
- Required collections are installed (`cisco.ios`, `ansible.netcommon`)

### Run steps

From the lab directory:

```bash
cd ~/gns3-labs/ansible-lab
ansible-playbook -i inventory-ios.ini baseline.yml --check --diff -vvv