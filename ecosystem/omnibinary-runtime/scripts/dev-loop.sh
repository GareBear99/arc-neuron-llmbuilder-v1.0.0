#!/usr/bin/env bash
set -euo pipefail
cargo fmt --check
cargo check --workspace
cargo test --workspace
cargo run -p obi-cli -- doctor
cargo run -p obi-cli -- status
cargo run -p obi-cli -- support
