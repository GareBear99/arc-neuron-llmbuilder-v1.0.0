
# Decode Preview Smoke

Run:

```bash
cargo run -p obi-cli -- decode /bin/echo
cargo run -p obi-cli -- dispatch /bin/echo
```

Expected:
- decode receipt written to cache
- dispatch receipt written to cache
- receipts index updated
