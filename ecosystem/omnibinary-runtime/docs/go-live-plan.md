# Go-Live Plan

## Phase 1 — Machine Validation
- Run `cargo check --workspace`
- Run `cargo test --workspace`
- Capture receipts and report-pack output
- Generate benchmark baselines for native lane

## Phase 2 — First Real Translation Slice
- Pick guest/host pair: aarch64 guest on x86_64 Linux host
- Implement one basic-block decoder
- Lower one decoded block into canonical IR
- Emit one runnable block via Cranelift
- Record translation receipt and cache metadata

## Phase 3 — Safety + Broker
- Split controller, compiler worker, execution sandbox
- Add capability-gated broker for filesystem/network/process access
- Validate crash containment

## Phase 4 — Product Claim Threshold
Only after Phases 1–3 and supported-machine evidence should the project claim production readiness for a narrow, explicit support matrix.
