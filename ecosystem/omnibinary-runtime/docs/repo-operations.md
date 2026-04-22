# Repo Operations

## Recommended local validation
```bash
cargo fmt
cargo check
cargo test
cargo run -p obi-cli -- doctor
cargo run -p obi-cli -- support
cargo run -p obi-cli -- init-config
```

## Release doctrine
Do not tag this repo as production-ready until all of the following are real:
- one real guest decoder
- one real IR-to-host executable path
- one real block cache with invalidation metadata
- one real personality adapter for syscall mediation
- brokered sandbox/process model
- compile/test validation on a supported CI runner


## v1.1 additions
- `obi env-report` writes a deterministic environment/debug receipt.
- `obi receipt-summary` aggregates receipt categories and latest entries.
- `obi clear-cache` clears generated local receipts and index state.
