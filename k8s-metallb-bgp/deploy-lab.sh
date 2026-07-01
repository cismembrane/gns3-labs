#!/usr/bin/env bash
# One-command deploy of the entire lab: TAPs, router bootstrap, Ansible
# config, k3s + MetalLB, demo services, verification.
#
# Assumes the GNS3 project file has been imported and nodes are running.
# Stages run in order; use --from <stage> to resume after a failure.
# Stages: taps bootstrap routers cluster services verify
#
# Requires: GNS3 server running with the imported IOSv project,
# ansible + cisco.ios collection, python3, curl, sudo.
set -euo pipefail
cd "$(dirname "$0")"

STAGES=(taps bootstrap routers cluster services verify)
FROM="${2:-taps}"
[[ "${1:-}" == "--from" ]] || FROM="taps"

stage_active=false
run_stage() {
  local stage="$1"
  [[ "$stage" == "$FROM" ]] && stage_active=true
  $stage_active || { echo "== skipping $stage"; return 1; }
  echo "== stage: $stage"
}

wait_for_ssh() {
  # Only check that each router's SSH port is answering -- do not log in. The
  # routers use password auth (no key), so an actual ssh login blocks on a
  # password prompt and hangs the rerun once the config is already applied.
  # Ansible (over paramiko) does the real authenticated login in the next stage.
  local ip deadline=$((SECONDS + 300))
  for ip in 192.168.0.{1..4}; do
    until timeout 3 bash -c "exec 3<>/dev/tcp/$ip/22" 2>/dev/null; do
      ((SECONDS < deadline)) || { echo "SSH to $ip never came up"; exit 1; }
      sleep 10
    done
    echo "ssh up: $ip"
  done
}

if run_stage taps; then
  ./scripts/setup-taps.sh
fi

if run_stage bootstrap; then
  python3 scripts/bootstrap-routers.py
  wait_for_ssh
fi

if run_stage routers; then
  ansible-playbook deploy.yml
  echo "waiting 45s for BGP convergence"
  sleep 45
  ansible-playbook verify.yml
fi

if run_stage cluster; then
  ./scripts/install-k3s.sh
fi

if run_stage services; then
  sudo k3s kubectl apply -f k8s/metallb-config.yaml
  sudo k3s kubectl apply -f k8s/whoami.yaml -f k8s/nginx-hello.yaml
  sudo k3s kubectl wait --for=jsonpath='{.status.loadBalancer.ingress}' \
    svc/whoami svc/nginx-hello --timeout=120s
  echo "waiting 30s for MetalLB sessions and route propagation"
  sleep 30
fi

if run_stage verify; then
  ansible-playbook verify-k8s-routes.yml
  echo "== HTTP checks"
  curl -fsS --max-time 5 http://172.16.10.10 | head -5
  curl -fsS --max-time 5 http://172.16.10.20 | head -5
  echo "== lab is up"
fi
