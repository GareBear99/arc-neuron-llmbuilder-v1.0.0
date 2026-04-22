#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-/bin/echo}"
cargo run -p obi-cli -- preflight "$TARGET"
