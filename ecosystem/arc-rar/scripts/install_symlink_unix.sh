#!/usr/bin/env bash
set -euo pipefail

TARGET=${1:-}
LINK_PATH=${2:-/usr/local/bin/arc-rar}

if [[ -z "$TARGET" ]]; then
  echo "usage: $0 /absolute/path/to/arc-rar [/usr/local/bin/arc-rar]"
  exit 1
fi

if [[ ! -x "$TARGET" ]]; then
  echo "target is not executable: $TARGET"
  exit 1
fi

sudo ln -sf "$TARGET" "$LINK_PATH"
echo "linked $LINK_PATH -> $TARGET"
