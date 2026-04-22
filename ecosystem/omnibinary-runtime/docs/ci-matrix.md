# CI Matrix

## Immediate target matrix
- Ubuntu latest / stable Rust
- Ubuntu latest / beta Rust

## Production target matrix
- Ubuntu latest / stable Rust
- macOS latest / stable Rust
- Windows latest / stable Rust

## Release blockers
- cargo fmt --check
- cargo check --workspace
- cargo test --workspace
- smoke script success
- doctor status success
