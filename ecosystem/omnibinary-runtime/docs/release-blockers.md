# Release Blockers

This document tracks the blockers that still prevent OmniBinary from being honestly described as a production universal runtime. Use `obi release-blockers` to emit the machine-readable view.

## Current blockers
- No real guest ISA decoder in tree
- No runnable translated host blocks emitted through Cranelift
- No syscall personality mediation backend
- No brokered sandbox execution plane
- No supported-machine compile/test evidence bundled with the release

## Unblock order
1. Real aarch64 smoke decoder
2. Canonical lowering
3. One runnable host block
4. Tiny re-entry dispatch loop
5. Machine-validated smoke fixture
