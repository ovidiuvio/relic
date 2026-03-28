#!/usr/bin/env bash
# Seed script: demo environment
# Populates the environment with realistic-looking demo relics for showcasing.
#
# Usage:
#   RELIC_BASE_URL=https://demo.relic.example.com bash k8s/seeds/demo.sh
#
# Optional env vars:
#   RELIC_CLIENT_KEY   client key to use (auto-generated if not set)
#   RELIC_SEED_COUNT   number of relics to create (default: 50)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

BASE_URL="${RELIC_BASE_URL:?RELIC_BASE_URL is required}"
SEED_COUNT="${RELIC_SEED_COUNT:-50}"
CLIENT_KEY="${RELIC_CLIENT_KEY:-$(openssl rand -hex 16)}"

echo "Seeding demo environment at ${BASE_URL}"
echo "  Count:      ${SEED_COUNT}"
echo "  Client key: ${CLIENT_KEY}"
echo ""

# Wait for backend readiness
echo "Waiting for backend..."
for i in $(seq 1 30); do
  if curl -sf "${BASE_URL}/api/v1/version" > /dev/null 2>&1; then
    echo "Backend ready"
    break
  fi
  echo "  attempt $i/30..."
  sleep 3
done

# Run the existing seed script
python3 "${REPO_ROOT}/scripts/seed_relics.py" \
  --url "${BASE_URL}" \
  --client-key "${CLIENT_KEY}" \
  --count "${SEED_COUNT}"

echo ""
echo "Demo seed complete. Client key: ${CLIENT_KEY}"
echo "Add this as ADMIN_CLIENT_IDS to promote to admin."
