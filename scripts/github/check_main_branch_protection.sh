#!/usr/bin/env bash
set -euo pipefail

OWNER="${1:-GareBear99}"
REPO="${2:-ARC-Neuron-LLMBuilder}"
BRANCH="${3:-main}"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI is required. Install gh, then run: gh auth login" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI is not authenticated. Run: gh auth login" >&2
  exit 1
fi

echo "Checking branch protection for ${OWNER}/${REPO}:${BRANCH}"

gh api   -H "Accept: application/vnd.github+json"   "/repos/${OWNER}/${REPO}/branches/${BRANCH}/protection"   --jq '{required_status_checks: .required_status_checks.contexts, enforce_admins: .enforce_admins.enabled, required_reviews: .required_pull_request_reviews.required_approving_review_count, dismiss_stale_reviews: .required_pull_request_reviews.dismiss_stale_reviews, code_owner_reviews: .required_pull_request_reviews.require_code_owner_reviews, linear_history: .required_linear_history.enabled, conversation_resolution: .required_conversation_resolution.enabled, force_pushes_allowed: .allow_force_pushes.enabled, deletions_allowed: .allow_deletions.enabled}'

echo "Protected branch check complete."
