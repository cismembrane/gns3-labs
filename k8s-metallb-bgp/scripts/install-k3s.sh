#!/usr/bin/env bash
# Installs single-node k3s and MetalLB on the lab host.
#
# ServiceLB (klipper-lb) is k3s's built-in LoadBalancer implementation and
# must be disabled or it will claim every LoadBalancer service before MetalLB
# can. Traefik is disabled because this lab doesn't use an ingress controller.
#
# --write-kubeconfig-mode 644 makes /etc/rancher/k3s/k3s.yaml readable by the
# invoking user so helm and kubectl run without sudo. This exposes cluster-admin
# credentials to any local user, which is acceptable for a throwaway lab only.
set -euo pipefail
METALLB_CHART_VERSION="${METALLB_CHART_VERSION:-0.15.2}"
K3S_VERSION="${K3S_VERSION:-v1.36.2+k3s1}"
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# --- k3s ---
if ! command -v k3s &>/dev/null; then
  curl -sfL https://get.k3s.io | \
    INSTALL_K3S_VERSION="$K3S_VERSION" \
    INSTALL_K3S_EXEC="--disable servicelb --disable traefik --write-kubeconfig-mode 644" sh -
fi

# k3s's systemd unit returns before the API server is serving and before the
# node registers, so a bare `wait --all` races into an empty cluster and fails
# with "no matching resources found". Poll until the node object exists first.
echo "waiting for node to register..."
until k3s kubectl get nodes 2>/dev/null | grep -q .; do
  sleep 2
done
k3s kubectl wait --for=condition=Ready node --all --timeout=120s

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
k3s kubectl -n metallb-system wait --for=condition=Available \
  deployment/metallb-controller --timeout=180s

echo "k3s and MetalLB are up. Next:"
echo "  k3s kubectl apply -f k8s/metallb-config.yaml"
echo "  k3s kubectl apply -f k8s/whoami.yaml -f k8s/nginx-hello.yaml"
