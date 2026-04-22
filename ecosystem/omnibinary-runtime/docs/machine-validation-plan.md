# Machine Validation Plan

Validate on supported Linux x86_64 hosts with Cargo installed.

Required gates:
- cargo check --workspace
- cargo test --workspace
- native-direct smoke test
- inspect/plan/lower/decode/dispatch/cache-validate/slice-report smoke runs
- cache clear/rebuild cycle
- fixture audit

Stretch gates:
- first real translated basic block
- Cranelift emission smoke
- personality mediation smoke
