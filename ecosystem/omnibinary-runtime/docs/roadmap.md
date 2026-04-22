# Roadmap

## Product framing

OmniBinary Runtime should be developed in three layers:
1. **Trusted repo/package layer** — intake, reporting, maintainership, release hygiene
2. **First executable translation layer** — one real guest-to-host path that actually runs
3. **Production runtime layer** — cache invalidation, personalities, sandboxing, evidence, and support matrix

## Phase A — Current baseline

Already in repo:
- intake and target classification
- lane selection
- native proof-path execution
- receipts and cache/report surfaces
- readiness, blocker, truth, and audit commands
- production-track docs and maintainer scripts

Exit criteria:
- local `cargo check` / `cargo test` pass on supported machines
- receipts generated for inspect/plan/lower/decode/dispatch/run flows
- repo-audit and readiness-report are green enough for active implementation

## Phase B — First real translation milestone

Build one real execution slice:
- host: Linux x86_64
- guest: Linux aarch64 user-space CLI subset
- decode one real guest basic block
- lower into canonical IR
- emit one runnable host block through Cranelift
- execute via a tiny re-entry dispatch loop
- record block-cache metadata and invariants

Exit criteria:
- one fixture binary decodes successfully
- one lowered block emits host code
- one translated block executes under a controlled test
- one repeat run shows block reuse metadata

## Phase C — Runtime hardening

Add the missing core production systems:
- translated block cache reuse and invalidation
- page-write / self-modifying code handling rules
- syscall personality mediation
- crash classification and fault receipts
- execution sandbox / broker plane
- benchmark and latency measurement harness

Exit criteria:
- stable translated execution for the first supported slice
- structured failure modes for unsupported targets
- machine-generated benchmarks and validation artifacts

## Phase D — Product readiness

Once the execution core exists, add:
- supported platform matrix
- CI matrix across supported hosts
- benchmark baselines and regression policy
- release candidate checklist
- packaging and distribution strategy
- maintainer ownership for each execution lane

Exit criteria:
- reproducible builds on supported systems
- benchmark evidence attached to release candidates
- clear support tiers for file format, ISA, and personality

## Priorities

### Highest priority now
1. real decoder
2. real lowering path
3. real Cranelift-emitted block
4. real dispatch re-entry

### Next priority
5. block cache reuse/invalidation
6. syscall personality mediation
7. sandbox/broker plane

### Final productization priority
8. machine validation evidence
9. performance evidence
10. release support matrix
