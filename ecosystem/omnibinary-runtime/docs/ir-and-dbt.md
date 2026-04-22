# IR and DBT Notes

This document describes the v0.4 midpoint:

- `obi-ir` now carries a real typed IR shape instead of only string placeholders.
- The `obi plan <path>` command generates a deterministic **planning IR** receipt.
- This is still not guest decoding. It is the bridge between intake/classification and a later executable backend.

## Intended build order
1. Real guest decoder for one ISA pair.
2. Guest basic block builder.
3. Canonical IR lowering.
4. Baseline Cranelift emitter.
5. Block cache and invalidation metadata.
6. Personality-mediated syscalls.

## Why this matters
A production binary runtime fails if it jumps directly from intake to wishful JIT promises. The IR layer is where:
- side effects become explicit
- memory ops become explicit
- syscall boundaries become explicit
- cacheability becomes explicit
- deopt and invalidation hooks can attach later
