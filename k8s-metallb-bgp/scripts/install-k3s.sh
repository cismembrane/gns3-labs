#!/usr/bin/env bash
# Installs single-node k3s and MetalLB on the lab host.
#
# ServiceLB (klipper-lb) is k3s's built-in LoadBalancer implementation and
# must be disabled or it will claim every LoadBalancer service before MetalLB
# can. Traefik is disabled because this lab doesn't use an ingress controller.
set -euo pipefail

METALLB_CHART_VERSION="${METALLB_CHART_VERSION:-0.15.2}"

# --- k3s ---
if ! command -v k3s &>/dev/null; then
  curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable servicelb --disable traefik" sh -
fi

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
sudo k3s kubectl wait --for=condition=Ready node --all --timeout=120s

# --- Helm ---
if ! command -v helm &>/dev/null; then
  curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi

# --- MetalLB ---
helm repo add metallb https://metallb.github.io/metallb
helm repo update
helm upgrade --install metallb metallb/metallb \
  --namespace metallb-system --create-namespace \
  --version "$METALLB_CHART_VERSION"

sudo k3s kubectl -n metallb-system wait --for=condition=Available \
  deployment/metallb-controller --timeout=180s

echo "k3s and MetalLB are up. Next:"
echo "  sudo k3s kubectl apply -f k8s/metallb-config.yaml"
echo "  sudo k3s kubectl apply -f k8s/whoami.yaml -f k8s/nginx-hello.yaml"
