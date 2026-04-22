#!/usr/bin/env bash
set -euo pipefail
echo "1) Implement real aarch64 block decoder"
echo "2) Lower decoded ops into canonical IR"
echo "3) Emit one runnable host block via Cranelift"
echo "4) Store block cache metadata + invalidation causes"
echo "5) Mediate one Linux userspace syscall surface"
echo "6) Run translated code in brokered sandbox process"
