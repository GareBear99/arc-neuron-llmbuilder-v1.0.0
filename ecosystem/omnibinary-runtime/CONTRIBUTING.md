# Contributing

## Current standard
This repository is a production-track scaffold, not a finished runtime.

Contributions should:
- preserve truthful capability claims
- add tests with each behavior change when practical
- avoid claiming cross-ISA execution until a real decoder/JIT path exists
- keep receipts deterministic and machine-readable
- prefer explicit blockers over silent fallback

## Suggested workflow
1. Run `cargo fmt`
2. Run `cargo check`
3. Run `cargo test`
4. Exercise the CLI preview paths against a known local binary
5. Update docs when support levels or lane behavior changes
