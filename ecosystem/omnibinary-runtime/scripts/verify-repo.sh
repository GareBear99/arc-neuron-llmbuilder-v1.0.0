#!/usr/bin/env bash
set -euo pipefail
required=(
  Cargo.toml
  README.md
  BUILD_STATUS.md
  LICENSE
  SECURITY.md
  CONTRIBUTING.md
  CHANGELOG.md
  .github/workflows/rust.yml
)
for f in "${required[@]}"; do
  [[ -e "$f" ]] || { echo "missing: $f"; exit 1; }
done
printf 'repo scaffold verification passed\n'
