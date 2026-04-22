# OmniBinary Runtime

OmniBinary Runtime is a **native-first binary intake and execution-fabric scaffold**.

It is designed to answer three practical questions for any target program:
1. **What is this file?**
2. **What is the best supported way to handle it on this machine?**
3. **What is still missing before seamless cross-ISA or cross-personality execution is real?**

This repository is positioned as a **production-track handoff repo**: strong on intake, reporting, planning, cache/receipt discipline, and maintainership surfaces; not yet complete as a universal translated execution runtime.

## Current status

- **Repo/package handoff:** ready
- **Native proof path:** present
- **Planning/reporting surface:** strong
- **First real translation milestone:** ready to implement
- **Universal production-ready runtime:** not yet complete

See `FINAL_READINESS_VERDICT.md`, `PRODUCT_STATUS.json`, and `docs/roadmap.md` for the canonical status.

## What it does today

- Inspects binaries and executable-like files
- Detects likely format and handling path
- Profiles the host environment
- Selects an execution lane
- Runs compatible native targets through a proof path
- Produces structured receipts, audits, readiness reports, and blocker reports
- Persists cache/report artifacts for later review
- Provides a clear implementation roadmap for the real execution core

## What it does not do yet

The missing center is still the true runtime core:

- real guest ISA decoder
- real canonical lowering from decoded guest blocks
- real Cranelift-emitted translated host blocks
- translated block cache reuse and invalidation for real DBT
- syscall personality mediation
- sandbox/broker execution plane
- machine-validated compile/test/benchmark evidence on supported systems

## Intended audience

- systems/runtime engineers
- compiler and JIT engineers
- reverse-engineering and binary tooling developers
- maintainers who need a disciplined repo and roadmap before the low-level runtime work lands

## Quick start

```bash
cargo fmt --check
cargo check --workspace
cargo test --workspace
cargo run -p obi-cli -- doctor
cargo run -p obi-cli -- status
cargo run -p obi-cli -- support
cargo run -p obi-cli -- inspect /bin/echo
cargo run -p obi-cli -- explain /bin/echo
cargo run -p obi-cli -- plan /bin/echo
cargo run -p obi-cli -- lower /bin/echo
cargo run -p obi-cli -- decode /bin/echo
cargo run -p obi-cli -- dispatch /bin/echo
cargo run -p obi-cli -- preflight /bin/echo
cargo run -p obi-cli -- truth-ledger
cargo run -p obi-cli -- readiness-report
cargo run -p obi-cli -- release-blockers
cargo run -p obi-cli -- repo-audit
cargo run -p obi-cli -- run /bin/echo -- hello world
```

## Core commands

### Target-oriented
- `obi inspect <path>` — identify the target and collect intake metadata
- `obi explain <path>` — explain lane choice and support posture
- `obi plan <path>` — produce the planning receipt
- `obi lower <path>` — produce a lowering preview
- `obi decode <path>` — produce a decode preview
- `obi dispatch <path>` — produce a dispatch preview
- `obi preflight <path>` — summarize readiness for one target
- `obi run <path> -- ...` — execute the native proof path when supported

### Repo / maintainer-oriented
- `obi doctor`
- `obi status`
- `obi support`
- `obi readiness-report`
- `obi release-blockers`
- `obi impl-backlog`
- `obi truth-ledger`
- `obi completion-map`
- `obi runtime-core-score`
- `obi machine-evidence-plan`
- `obi repo-audit`
- `obi report-pack`

## Roadmap

The project now has a clearer production roadmap:

### Phase 1 — Present repo state
- stable intake and receipt surfaces
- native proof path
- planning / preview lanes
- maintainer and audit tooling

### Phase 2 — First real execution milestone
- one real guest ISA decoder
- one real lowering path into canonical IR
- one real Cranelift-emitted host block
- one minimal dispatch re-entry loop
- translated block metadata and reuse rules

### Phase 3 — Productization of execution core
- block invalidation
- syscall personality mediation
- sandbox / broker plane
- benchmark evidence
- supported-host CI matrix and reproducibility proof

Read the full roadmap in `docs/roadmap.md`.

## Recommended entrypoints

- Product status: `PRODUCT_STATUS.json`
- Final verdict: `FINAL_READINESS_VERDICT.md`
- Go-live plan: `docs/go-live-plan.md`
- Runtime sequence: `docs/runtime-core-implementation-sequence.md`
- Validation runbook: `docs/local-validation-runbook.md`
- Backlog: `docs/implementation-backlog.md`

## Repo standards

This repo aims to be:
- explicit about what is implemented
- explicit about what is preview-only
- explicit about what is blocked
- easy to hand off to another engineer without hidden assumptions

## License

MIT
