# Local Validation Runbook

```bash
cargo fmt --check
cargo check --workspace
cargo test --workspace
cargo run -p obi-cli -- repo-audit
cargo run -p obi-cli -- report-pack
cargo run -p obi-cli -- readiness-report
cargo run -p obi-cli -- release-blockers
cargo run -p obi-cli -- runtime-core-score
cargo run -p obi-cli -- machine-evidence-plan
cargo run -p obi-cli -- preflight /bin/echo
cargo run -p obi-cli -- run /bin/echo -- hello world
```

## Success Criteria
- Workspace compiles
- Tests pass
- Reports generate cleanly
- Native lane works on target machine
- Remaining blockers are narrowed to execution-core implementation only
