#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
cp README.md "$ROOT/README.md"
cp ROADMAP.md "$ROOT/ROADMAP.md"
mkdir -p "$ROOT/docs"
cp docs/OPEN_REVIEW_AND_3_LICENSE_DIRECTION.md "$ROOT/docs/OPEN_REVIEW_AND_3_LICENSE_DIRECTION.md"
cp README_roadmap_license_language.patch "$ROOT/README_roadmap_license_language.patch"
echo "Applied roadmap/license/language README drop-in."
