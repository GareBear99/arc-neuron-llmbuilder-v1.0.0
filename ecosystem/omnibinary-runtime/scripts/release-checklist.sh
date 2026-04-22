#!/usr/bin/env bash
set -euo pipefail

echo "[obi] release checklist"
echo "1. cargo fmt --check"
echo "2. cargo check --workspace"
echo "3. cargo test --workspace"
echo "4. ./scripts/smoke.sh"
echo "5. review BUILD_STATUS.md and docs/production-gaps.md"
echo "6. tag release only if core status matches documentation"
