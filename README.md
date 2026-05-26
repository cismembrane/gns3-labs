# GNS3 Labs

[![Lint](https://github.com/cismembrane/gns3-labs/actions/workflows/lint.yml/badge.svg)](https://github.com/cismembrane/gns3-labs/actions/workflows/lint.yml)

Hands-on network engineering labs built in GNS3, covering CCNP ENCOR routing, switching, VPN, and first-hop redundancy topics alongside Ansible-driven automation. Each lab includes full router configurations, topology diagrams, and documentation explaining not just what was configured but why.

## Labs

| Lab | Description | Key Technologies | Video |
| --- | --- | --- | --- |
| [bgp-grafana-monitoring](bgp-grafana-monitoring) | Four-router eBGP ring (AS 65001–65004) with a monitoring stack on top. Ansible configures the routers and SNMPv3, snmp_exporter walks BGP4-MIB, Prometheus scrapes it, Grafana renders peer state, session uptime, and update rates across all eight directional peerings. Prometheus alerts cover peer-not-established, session flapping, and exporter reachability. [GNS3 rebuild notes](bgp-grafana-monitoring/gns3/README.md). | eBGP, Ansible, SNMPv3, snmp_exporter, Prometheus, Grafana, BGP4-MIB, Docker Compose | [▶ Watch](https://www.youtube.com/watch?v=QE9bilhj34w) |
| [ansible-bgp](ansible-bgp) | Four-router eBGP topology across AS 65001–65004, deployed and verified with Ansible using Jinja2 templates and host_vars | eBGP, Ansible, Jinja2, paramiko, BGP neighbor verification | [▶ Watch](https://www.youtube.com/watch?v=1HKZocY5SMY) |
| [dmvpn-phase3-ipsec](dmvpn-phase3-ipsec) | Hub-and-spoke DMVPN with dynamic spoke-to-spoke tunnels and IPsec transport encryption | DMVPN Phase 3, NHRP shortcuts, IPsec, EIGRP, GRE mGRE | [▶ Watch](https://www.youtube.com/watch?v=CdZ0fmA12-E) |
| [ansible-ospf](ansible-ospf) | Automated OSPF deployment across a multi-router topology using Ansible | Ansible, OSPF, Jinja2 templates, ios\_config module | [▶ Watch](https://www.youtube.com/watch?v=7IEfZew-7wQ) |
| [ansible-lab](ansible-lab) | Baseline Ansible environment for pushing configurations to GNS3 routers | Ansible, GNS3 integration, network automation fundamentals | [▶ Watch](https://www.youtube.com/watch?v=cSly8RQOZYU) |
| [redundant-ospf-hsrp-eem-dhcp](redundant-ospf-hsrp-eem-dhcp) | Redundant OSPF core with HSRP at the access layer, EEM-gated DHCP relay, authenticated NTP, and DNS | OSPF totally stubby areas, HSRP, EEM applets, DHCP relay, NTP authentication | |
| [eigrp-delay-manipulation](eigrp-delay-manipulation) | EIGRP path selection using interface delay to influence feasible successor calculation | EIGRP composite metric, delay tuning, feasible distance, reported distance | |
| [glbp-basic](glbp-basic) | Gateway Load Balancing Protocol with AVG election and AVF load distribution | GLBP, AVG, AVF, round-robin forwarding | |
| [proxy-arp](proxy-arp) | Proxy ARP behavior across a stretched subnet with packet capture analysis | Proxy ARP, ARP, L2/L3 boundary behavior | |

## Scripts

[restconf-netconf-scripts](restconf-netconf-scripts) contains Python scripts that talk to a Cisco IOS XE device over RESTCONF and NETCONF. Discovery, interface reads, and full PUT/PATCH/DELETE lifecycle examples on a loopback and a static route. Targets the DevNet Always-On sandbox. See the [directory README](restconf-netconf-scripts/README.md) for details.

## How to Use These Labs

Each lab directory contains a `README.md` with the full topology, IP addressing, configuration walkthrough, and verification steps. Router configs are in the `configs/` directory. GNS3 project files are included where applicable, built against Cisco c7200 `adventerprisek9` images running on Dynamips, with IOSvL2 images used in some labs for Layer 2 switching.

To import a lab, open the `.gns3` project file in GNS3 and remap the IOS image to your local copy if the filename differs.

## Automation and Validation

The Ansible labs split deploy and verify into separate playbooks. Config gets pushed via Jinja2 templates with per-router variables in `host_vars/`. The verify playbooks run `ansible.builtin.assert` against the device after deployment. BGP fails the run if any neighbor sits in Idle or Active. OSPF fails if no neighbor reaches FULL or the routing table carries no OSPF routes.

Router and SNMP passwords in `bgp-grafana-monitoring` are encrypted with ansible-vault and stored in `group_vars/routers.yml`. `.env.example` and `.vault_pass.example` list the variables you need without committing the values.

Two workflows run on every push via GitHub Actions. `lint.yml` runs yamllint, ansible-lint, and markdownlint. `ansible-syntax.yml` runs `ansible-playbook --syntax-check` across the `ansible-bgp`, `ansible-lab`, and `ansible-ospf` playbooks. `bgp-grafana-monitoring` playbooks are excluded until CI has a vault secret. The same lint checks run locally through pre-commit before each commit, versions pinned to match.

## Links

* [YouTube: BGP Observability with SNMPv3, Prometheus, and Grafana](https://www.youtube.com/watch?v=QE9bilhj34w)
* [YouTube: BGP Across Four Autonomous Systems, Deployed with Ansible](https://www.youtube.com/watch?v=1HKZocY5SMY)
* [YouTube: DMVPN Phase 3 with IPsec — Full GNS3 Lab Walkthrough](https://www.youtube.com/watch?v=CdZ0fmA12-E)
* [YouTube: Automating a 4-Router OSPF Lab with Ansible](https://www.youtube.com/watch?v=7IEfZew-7wQ)
* [YouTube: Basic Ansible Baseline Push and Validation in GNS3](https://www.youtube.com/watch?v=cSly8RQOZYU)
* [YouTube Channel](https://youtube.com/@cismembrane)
