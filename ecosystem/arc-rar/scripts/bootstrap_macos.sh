#!/usr/bin/env bash
set -euo pipefail

echo "[Arc-RAR] macOS bootstrap starting"
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew not found. Install Homebrew first, then rerun this script."
  exit 1
fi
brew update
brew install rust jq p7zip libarchive unrar || true

echo "Done. Verify with: arc-rar backend doctor"
