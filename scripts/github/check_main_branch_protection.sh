#!/usr/bin/env bash
set -euo pipefail

OWNER="${1:-GareBear99}"
REPO="${2:-arc-neuron-llmbuilder-v1.0.0}"
BRANCH="${3:-main}"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI is not installed." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI is not authenticated. Run: gh auth login" >&2
  exit 1
fi

set +e
OUT=$(gh api \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "repos/${OWNER}/${REPO}/branches/${BRANCH}/protection" 2>&1)
STATUS=$?
set -e

if [ "$STATUS" -ne 0 ]; then
  echo "NOT PROTECTED or API access failed for ${OWNER}/${REPO}:${BRANCH}"
  echo "$OUT"
  exit 1
fi

echo "$OUT" | jq '{protected:true, required_status_checks:.required_status_checks, required_pull_request_reviews:.required_pull_request_reviews, enforce_admins:.enforce_admins, allow_force_pushes:.allow_force_pushes, allow_deletions:.allow_deletions, required_conversation_resolution:.required_conversation_resolution}'
