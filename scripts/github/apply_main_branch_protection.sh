#!/usr/bin/env bash
set -euo pipefail

OWNER="${1:-GareBear99}"
REPO="${2:-arc-neuron-llmbuilder-v1.0.0}"
BRANCH="${3:-main}"
PAYLOAD="${4:-.github/branch-protection-main.json}"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI is not installed. Install gh first: https://cli.github.com/" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI is not authenticated. Run: gh auth login" >&2
  exit 1
fi

if [ ! -f "$PAYLOAD" ]; then
  echo "ERROR: Missing branch protection payload: $PAYLOAD" >&2
  exit 1
fi

echo "Applying branch protection to ${OWNER}/${REPO}:${BRANCH}"

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "repos/${OWNER}/${REPO}/branches/${BRANCH}/protection" \
  --input "$PAYLOAD" >/tmp/arc_branch_protection_apply.json

echo "Branch protection API call completed. Verifying..."

gh api \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "repos/${OWNER}/${REPO}/branches/${BRANCH}/protection" \
  --jq '{protected:true, required_status_checks:.required_status_checks, required_pull_request_reviews:.required_pull_request_reviews, enforce_admins:.enforce_admins, allow_force_pushes:.allow_force_pushes, allow_deletions:.allow_deletions, required_conversation_resolution:.required_conversation_resolution}'

echo "Done. Refresh GitHub after this succeeds."
