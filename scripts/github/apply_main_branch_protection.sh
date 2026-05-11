#!/usr/bin/env bash
set -euo pipefail

OWNER="${1:-GareBear99}"
REPO="${2:-arc-neuron-llmbuilder-v1.0.0}"
BRANCH="${3:-main}"
CONFIG="${4:-.github/branch-protection-main.json}"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI is not installed. Install gh first: https://cli.github.com/" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI is not authenticated. Run: gh auth login" >&2
  exit 1
fi

if [ ! -f "$CONFIG" ]; then
  echo "ERROR: Missing branch protection payload: $CONFIG" >&2
  exit 1
fi

echo "Applying branch protection to ${OWNER}/${REPO}:${BRANCH} using ${CONFIG}"

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "repos/${OWNER}/${REPO}/branches/${BRANCH}/protection" \
  --input "$CONFIG" >/tmp/arc_branch_protection_apply.json

echo "Branch protection API call completed. Verifying..."

gh api \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "repos/${OWNER}/${REPO}/branches/${BRANCH}/protection" \
  --jq '{protected:true, required_pull_request_reviews:.required_pull_request_reviews.required_approving_review_count, enforce_admins:(.enforce_admins.enabled // .enforce_admins), allow_force_pushes:(.allow_force_pushes.enabled // .allow_force_pushes), allow_deletions:(.allow_deletions.enabled // .allow_deletions), required_conversation_resolution:(.required_conversation_resolution.enabled // .required_conversation_resolution)}'

echo "Done. If GitHub still warns that main is not protected, refresh the repository page or confirm the repo name/owner is correct."
