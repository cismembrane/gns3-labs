# GNS3 Labs

Hands-on network engineering labs built in GNS3, covering CCNP ENCOR routing, switching, VPN, and first-hop redundancy topics alongside Ansible-driven automation. Each lab includes full router configurations, topology diagrams, and documentation explaining not just what was configured but why.

## Labs

| Lab | Description | Key Technologies |
|-----|-------------|------------------|
| [ansible-bgp](ansible-bgp/) | Four-router eBGP topology across AS 65001–65004, automated with Ansible. Jinja2 templates render per-router configs from host_vars. Separate deploy and verify playbooks with BGP neighbor state assertions and end-to-end reachability checks. | eBGP (AS 65001-65004), Ansible, Jinja2 templates, cisco.ios collection, assert-based verification
| [dmvpn-phase3-ipsec](dmvpn-phase3-ipsec/) | Hub-and-spoke DMVPN with dynamic spoke-to-spoke tunnels and IPsec transport encryption | DMVPN Phase 3, NHRP shortcuts, IPsec, EIGRP, GRE mGRE |
| [ansible-ospf](ansible-ospf/) | Automated OSPF deployment across a multi-router topology using Ansible | Ansible, OSPF, Jinja2 templates, ios_config module |
| [ansible-lab](ansible-lab/) | Baseline Ansible environment for pushing configurations to GNS3 routers | Ansible, GNS3 integration, network automation fundamentals |
| [redundant-ospf-hsrp-eem-dhcp](redundant-ospf-hsrp-eem-dhcp/) | Redundant OSPF core with HSRP at the access layer, EEM-gated DHCP relay, authenticated NTP, and DNS | OSPF totally stubby areas, HSRP, EEM applets, DHCP relay, NTP authentication |
| [eigrp-delay-manipulation](eigrp-delay-manipulation/) | EIGRP path selection using interface delay to influence feasible successor calculation | EIGRP composite metric, delay tuning, feasible distance, reported distance |
| [glbp-basic](glbp-basic/) | Gateway Load Balancing Protocol with AVG election and AVF load distribution | GLBP, AVG, AVF, round-robin forwarding |
| [proxy-arp](proxy-arp/) | Proxy ARP behavior across a stretched subnet with packet capture analysis | Proxy ARP, ARP, L2/L3 boundary behavior |

## How to Use These Labs

Each lab directory contains a `README.md` with the full topology, IP addressing, configuration walkthrough, and verification steps. Router configs are in the `configs/` directory. GNS3 project files are included where applicable, built against Cisco c7200 `adventerprisek9` images running on Dynamips, with IOSvL2 images used in some labs for Layer 2 switching.

To import a lab, open the `.gns3` project file in GNS3 and remap the IOS image to your local copy if the filename differs.

## Links

- [YouTube: DMVPN Phase 3 with IPsec Walkthrough](https://youtube.com/@cismembrane)
- [LinkedIn](https://linkedin.com/in/cismembrane)
