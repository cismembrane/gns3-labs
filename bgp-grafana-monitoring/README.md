# BGP Observability with SNMPv3, Prometheus, and Grafana

Monitoring stack for a four-router eBGP GNS3 lab (AS 65001–65004). SNMPv3 polling into snmp_exporter, scraped by Prometheus, rendered in Grafana. The dashboard tracks BGP session state, uptime, and update rates across all eight directional peerings in the ring.

Router config is built by Ansible, and the monitoring stack deploys from `docker-compose.yml`. Both pipelines are in this repo.

---

## Topology and Data Flow

Four routers peer in a ring: R1 (AS 65001) ↔ R2 (AS 65002) ↔ R3 (AS 65003) ↔ R4 (AS 65004) ↔ R1. Every router holds two eBGP sessions, so SNMP reports eight directional peering states total.

Prometheus runs two scrape jobs against snmp_exporter. The `snmp_routers` job requests the `if_mib` module for interface counters and state. The `snmp_bgp` job requests the `bgp4` module for BGP4-MIB entries covering peer state, uptime, and update counters. Both jobs scrape every 30 seconds, which triggers a fresh SNMP walk against each target router. Grafana reads the combined data from Prometheus via PromQL and renders the dashboard at `monitoring/grafana/dashboards/bgp-health.json`.

SNMPv3 is used instead of v2c so auth and priv are in play. The difference doesn't matter inside a lab, but I'd rather not have a plaintext community string pattern sitting in a public repo.

---

## Deployment

The routers are configured first. Three Ansible playbooks run in sequence: `deploy.yml` pushes interface and BGP config, `verify.yml` confirms the sessions came up, and `configure-snmp.yml` enables SNMPv3. Once SNMPv3 is listening, the monitoring stack stands up via `docker-compose.yml`.

Three services in `docker-compose.yml`: `snmp_exporter` v0.30.1, `prometheus` v3.1.0, `grafana` 13.1.0. All run with `network_mode: host`.

Host networking is the key choice. The containers need to reach the GNS3 routers' management IPs, which live on the host's network. Host mode means SNMP polls leave the host's stack directly, with no bridge routing or port mapping to fight. Prometheus scrapes over localhost to `:9116`, and Grafana listens on host `:3000`.

Grafana is provisioned declaratively. `./monitoring/grafana/provisioning` is mounted into the container so the Prometheus datasource and `bgp-health.json` dashboard load on startup without any UI clicking. Admin credentials come from `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD` env vars, defaulting to `admin/admin`.

