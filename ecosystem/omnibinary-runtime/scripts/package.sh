#!/usr/bin/env bash
set -euo pipefail
name="omnibinary-runtime-$(date +%Y%m%d-%H%M%S).zip"
zip -r "$name" . -x "target/*" ".git/*" ".obi-cache/*"
printf 'created %s\n' "$name"
