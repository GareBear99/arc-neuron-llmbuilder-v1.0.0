#!/usr/bin/env bash
set -euo pipefail

OWNER="${1:-GareBear99}"
REPO="${2:-ARC-Neuron-LLMBuilder}"
BRANCH="${3:-main}"
PAYLOAD=".github/branch-protection-main.json"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI is required. Install gh, then run: gh auth login" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI is not authenticated. Run: gh auth login" >&2
  exit 1
fi

if [ ! -f "$PAYLOAD" ]; then
  echo "ERROR: Missing $PAYLOAD. Run this from the repo root." >&2
  exit 1
fi

echo "Applying branch protection to ${OWNER}/${REPO}:${BRANCH}"
echo "Payload: ${PAYLOAD}"

gh api   --method PUT   -H "Accept: application/vnd.github+json"   "/repos/${OWNER}/${REPO}/branches/${BRANCH}/protection"   --input "$PAYLOAD"

echo
echo "Branch protection API call completed. Verifying..."
gh api   -H "Accept: application/vnd.github+json"   "/repos/${OWNER}/${REPO}/branches/${BRANCH}/protection"   --jq '{protected: true, required_status_checks: .required_status_checks.contexts, enforce_admins: .enforce_admins.enabled, required_reviews: .required_pull_request_reviews.required_approving_review_count, linear_history: .required_linear_history.enabled, conversation_resolution: .required_conversation_resolution.enabled, force_pushes_allowed: .allow_force_pushes.enabled, deletions_allowed: .allow_deletions.enabled}'

echo
echo "Done. If GitHub still warns that main is unprotected, refresh the repository page or verify at:"
echo "Settings → Branches → Branch protection rules → main"
