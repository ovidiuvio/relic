#!/usr/bin/env bash
# Tear down a named environment from the k3d cluster.
#
# Usage:
#   ./teardown-env.sh --env pr-42 --domain relic.example.com [--destroy-data]
#
# Options:
#   --env ENV         Environment name
#   --domain DOMAIN   Base domain
#   --destroy-data    Also drop the database and MinIO bucket (always true for dynamic envs)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/lib/colors.sh"
source "${SCRIPT_DIR}/lib/cloudflare.sh"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
ENV=""
DOMAIN="${K8S_DOMAIN:-relic.example.com}"
DESTROY_DATA=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --env)          ENV="$2";        shift 2 ;;
    --domain)       DOMAIN="$2";     shift 2 ;;
    --destroy-data) DESTROY_DATA=true; shift ;;
    *) error "Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ -z "${ENV}" ]]; then
  error "Usage: $0 --env <name> --domain <domain> [--destroy-data]"
  exit 1
fi

NAMESPACE="relic-${ENV}"
DB_NAME="relic_$(echo "${ENV}" | tr '-' '_')"
DB_USER="${DB_NAME}_user"
MINIO_BUCKET="relic-${ENV}"
HOSTNAME="${ENV}.${DOMAIN}"
OVERLAY_DIR="${K8S_DIR}/overlays/${ENV}"
TUNNEL_NAME="tunnel-${ENV}"

# Dynamic envs always destroy data and clean up their overlay dir
IS_DYNAMIC_ENV=false
[[ ! -f "${K8S_DIR}/overlays/${ENV}/kustomization.yaml" ]] && IS_DYNAMIC_ENV=true
"${IS_DYNAMIC_ENV}" && DESTROY_DATA=true

# Load cluster secrets
SECRETS_FILE="${K8S_DIR}/.cluster-secrets.env"
if [[ -f "${SECRETS_FILE}" ]]; then
  # shellcheck source=/dev/null
  source "${SECRETS_FILE}"
fi

# ---------------------------------------------------------------------------
# Step 1: Delete Cloudflare Tunnel and DNS record
# ---------------------------------------------------------------------------
step "Removing Cloudflare tunnel and DNS for '${ENV}'"

cf_check_credentials

# Load per-env secrets to get the tunnel ID
SECRETS_ENV_FILE="${OVERLAY_DIR}/secrets/env.sh"
TUNNEL_ID=""
if [[ -f "${SECRETS_ENV_FILE}" ]]; then
  # shellcheck source=/dev/null
  source "${SECRETS_ENV_FILE}"
fi

# Fall back to API lookup if ID not stored locally
if [[ -z "${TUNNEL_ID:-}" ]]; then
  TUNNEL_ID="$(cf_get_tunnel_id "${TUNNEL_NAME}")"
fi

cf_delete_dns_record "${HOSTNAME}" && success "DNS record for ${HOSTNAME} removed"
cf_delete_tunnel "${TUNNEL_ID}"    && success "Tunnel '${TUNNEL_NAME}' deleted"

# ---------------------------------------------------------------------------
# Step 2: Destroy data (database + bucket)
# ---------------------------------------------------------------------------
if "${DESTROY_DATA}"; then
  step "Destroying data for '${ENV}'"

  DROP_DB_JOB="destroy-db-${ENV}"
  kubectl delete job "${DROP_DB_JOB}" -n shared --ignore-not-found=true
  kubectl apply -f - <<JOB
apiVersion: batch/v1
kind: Job
metadata:
  name: ${DROP_DB_JOB}
  namespace: shared
spec:
  ttlSecondsAfterFinished: 60
  template:
    spec:
      restartPolicy: OnFailure
      containers:
        - name: psql
          image: postgres:16-alpine
          command:
            - /bin/sh
            - -c
            - |
              export PGPASSWORD="\${PG_ROOT_PASSWORD}"
              psql -h postgres.shared.svc.cluster.local -U postgres -c \
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}';"
              psql -h postgres.shared.svc.cluster.local -U postgres -c \
                "DROP DATABASE IF EXISTS ${DB_NAME};"
              psql -h postgres.shared.svc.cluster.local -U postgres -c \
                "DROP USER IF EXISTS ${DB_USER};"
              echo "Done."
          env:
            - name: PG_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: postgres-password
JOB
  kubectl wait --for=condition=complete "job/${DROP_DB_JOB}" -n shared --timeout=60s \
    || warn "DB drop job timed out — may still be running"
  success "Database '${DB_NAME}' dropped"

  RM_BUCKET_JOB="destroy-minio-${ENV}"
  kubectl delete job "${RM_BUCKET_JOB}" -n shared --ignore-not-found=true
  kubectl apply -f - <<JOB
apiVersion: batch/v1
kind: Job
metadata:
  name: ${RM_BUCKET_JOB}
  namespace: shared
spec:
  ttlSecondsAfterFinished: 60
  template:
    spec:
      restartPolicy: OnFailure
      containers:
        - name: mc
          image: minio/mc:latest
          command:
            - /bin/sh
            - -c
            - |
              mc alias set minio http://minio.shared.svc.cluster.local:9000 minioadmin "\${MINIO_ROOT_PASSWORD}"
              mc rb --force "minio/${MINIO_BUCKET}" || echo "Bucket not found — skipping"
              echo "Done."
          env:
            - name: MINIO_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: minio-secret
                  key: root-password
JOB
  kubectl wait --for=condition=complete "job/${RM_BUCKET_JOB}" -n shared --timeout=60s \
    || warn "Bucket removal job timed out"
  success "Bucket '${MINIO_BUCKET}' removed"
fi

# ---------------------------------------------------------------------------
# Step 3: Delete namespace (cascades to all pods, services, secrets, etc.)
# ---------------------------------------------------------------------------
step "Deleting namespace: ${NAMESPACE}"
kubectl delete namespace "${NAMESPACE}" --ignore-not-found=true
success "Namespace '${NAMESPACE}' deleted"

# ---------------------------------------------------------------------------
# Step 4: Clean up overlay (dynamic envs only)
# ---------------------------------------------------------------------------
if "${IS_DYNAMIC_ENV}"; then
  if [[ -d "${OVERLAY_DIR}" ]]; then
    rm -rf "${OVERLAY_DIR}"
    success "Overlay directory removed: ${OVERLAY_DIR}"
  fi
fi

step "Teardown complete"
info "Environment '${ENV}' has been removed"
