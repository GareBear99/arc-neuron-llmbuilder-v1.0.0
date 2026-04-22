# Examples

This folder is intentionally light in v0.9.

Recommended first local exercises:
- inspect a native host binary
- generate a plan receipt
- generate a lowering receipt
- generate a decode preview
- generate a dispatch preview

Example:

```bash
cargo run -p obi-cli -- inspect /bin/echo
cargo run -p obi-cli -- plan /bin/echo
cargo run -p obi-cli -- lower /bin/echo
cargo run -p obi-cli -- decode /bin/echo
cargo run -p obi-cli -- dispatch /bin/echo
```
