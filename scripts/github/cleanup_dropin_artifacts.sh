#!/usr/bin/env bash
set -euo pipefail

# Removes patch/apply artifacts that were accidentally committed to the public repo root.
# Keeps real docs, source, configs, scripts, and benchmark materials.

rm -f \
  AI_BRIEFING_FOR_VIBE_CODERS.patch \
  BRANCH_PROTECTION_FUNDING_FLOW.patch \
  README_BRANCH_BMC_FLOW.patch \
  README_protosynth_integration.patch \
  README_roadmap_license_language.patch \
  APPLY_ROADMAP_LICENSE_LANGUAGE.sh

echo "Cleaned root-level drop-in patch/apply artifacts. Review with: git status --short"
