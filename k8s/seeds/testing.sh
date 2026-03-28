#!/usr/bin/env bash
# Seed script: testing environment
# Populates the environment with a small, known set of fixture relics
# suitable for integration test assertions.
#
# Usage:
#   RELIC_BASE_URL=https://testing.relic.example.com bash k8s/seeds/testing.sh
#
# Optional env vars:
#   RELIC_CLIENT_KEY   client key to use (written to .testing-client-key for reference)
#   RELIC_SEED_COUNT   number of relics to create (default: 20)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

BASE_URL="${RELIC_BASE_URL:?RELIC_BASE_URL is required}"
SEED_COUNT="${RELIC_SEED_COUNT:-20}"
CLIENT_KEY="${RELIC_CLIENT_KEY:-$(openssl rand -hex 16)}"

echo "Seeding testing environment at ${BASE_URL}"
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

# Run the existing seed script with a smaller count for faster test setup
python3 "${REPO_ROOT}/scripts/seed_relics.py" \
  --url "${BASE_URL}" \
  --client-key "${CLIENT_KEY}" \
  --count "${SEED_COUNT}"

echo ""
echo "Testing seed complete."
echo "  RELIC_CLIENT_KEY=${CLIENT_KEY}"
echo "  RELIC_BASE_URL=${BASE_URL}"
