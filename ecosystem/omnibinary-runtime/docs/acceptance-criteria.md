# Acceptance Criteria

## Repo Foundation Acceptance
A repo build qualifies as a strong scaffold when all of the following are true:
- `cargo check` passes on at least one supported host toolchain
- `cargo test` passes on at least one supported host toolchain
- `obi doctor` emits a truthful structured report
- `obi status` explains what exists and what is still missing
- native direct execution works for a same-host test binary
- inspect / explain / plan / lower / decode / dispatch receipts are persisted to cache

## First Real Translation Milestone Acceptance
This milestone is reached only when all of the following are true:
- one real guest ISA decoder is implemented
- one guest basic block can be decoded into canonical IR
- one host block can be emitted through Cranelift from that IR
- a translated block cache record is written and re-used
- a dispatch loop can execute and re-enter compiled blocks
- invalidation metadata exists for rewritten or invalidated code regions
- the runtime can clearly state which syscalls or helpers remain unsupported

## Production Readiness Acceptance
Production readiness requires more than code generation.
It requires:
- supported host/guest matrix documented and tested
- crash receipts and error paths verified
- sandbox/broker model implemented for untrusted execution
- personality mediation for supported guest OS expectations
- CI compile/test matrix running on real supported environments
- fuzzing or adversarial parser coverage for intake and decoder surfaces
- release packaging, signing, and versioned compatibility guarantees
- security response and disclosure workflow in force
