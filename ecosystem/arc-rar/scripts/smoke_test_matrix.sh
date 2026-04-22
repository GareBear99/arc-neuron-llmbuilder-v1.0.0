#!/usr/bin/env bash
set -euo pipefail

echo "Arc-RAR smoke test matrix"
command -v arc-rar >/dev/null 2>&1 || { echo "arc-rar not found on PATH"; exit 1; }

arc-rar backend doctor --json || true
arc-rar gui status --json || true

echo "Create sample fixture dir"
TMPDIR=$(mktemp -d)
mkdir -p "$TMPDIR/in"
echo hello > "$TMPDIR/in/hello.txt"
arc-rar create "$TMPDIR/sample.zip" "$TMPDIR/in" --format zip --json || true
[ -f "$TMPDIR/sample.zip" ] && arc-rar info "$TMPDIR/sample.zip" --json || true
[ -f "$TMPDIR/sample.zip" ] && arc-rar test "$TMPDIR/sample.zip" --json || true

echo "Done. Temp dir: $TMPDIR"
