# Smoke Tests

Suggested local checks:

```bash
cargo fmt
cargo check
cargo test
cargo run -p obi-cli -- doctor
cargo run -p obi-cli -- cache-dir
cargo run -p obi-cli -- inspect /bin/echo
cargo run -p obi-cli -- explain /bin/echo
cargo run -p obi-cli -- run /bin/echo -- hello world
cargo run -p obi-cli -- receipts 10
```

Expected truths:
- `doctor` should say the scaffold is **not production-ready**.
- `inspect` should emit a decision receipt.
- `run` should only work on same-host native inputs in the current repo state.
- `receipts` should show previously emitted receipt index entries.
