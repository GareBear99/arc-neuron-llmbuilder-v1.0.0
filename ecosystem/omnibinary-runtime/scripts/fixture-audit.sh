#!/usr/bin/env bash
set -euo pipefail
echo "[obi] fixture audit"
find tests/fixtures -maxdepth 2 -type f | sort || true
