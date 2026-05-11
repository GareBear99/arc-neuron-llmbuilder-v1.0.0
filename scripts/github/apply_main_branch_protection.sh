#!/usr/bin/env bash
set -euo pipefail

OWNER="${1:-GareBear99}"
REPO="${2:-ARC-Neuron-LLMBuilder}"
BRANCH="${3:-main}"
PAYLOAD=".github/branch-protection-main.json"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI is required. Install gh, then run gh auth login." >&2
  exit 1
fi

if [ ! -f "$PAYLOAD" ]; then
  echo "ERROR: Missing $PAYLOAD. Run this from the repo root." >&2
  exit 1
fi

echo "Applying branch protection to ${OWNER}/${REPO}:${BRANCH}"
echo "Payload: ${PAYLOAD}"

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/${OWNER}/${REPO}/branches/${BRANCH}/protection" \
  --input "$PAYLOAD"

echo "Done. Verify in GitHub: Settings → Branches → Branch protection rules."
