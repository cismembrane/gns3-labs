#!/bin/bash
# Strips instance-specific metadata from an exported Grafana dashboard JSON.
# Usage: ./strip-dashboard.sh input.json > output.json

set -euo pipefail
jq '
  del(.metadata.uid) |
  del(.metadata.resourceVersion) |
  del(.metadata.generation) |
  del(.metadata.creationTimestamp) |
  del(.metadata.labels) |
  del(.metadata.annotations."grafana.app/createdBy") |
  del(.metadata.annotations."grafana.app/updatedBy") |
  del(.metadata.annotations."grafana.app/updatedTimestamp") |
  del(.metadata.annotations."grafana.app/saved-from-ui")
' "${1:-/dev/stdin}"
