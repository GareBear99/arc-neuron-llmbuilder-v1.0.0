
# Lowering Preview Smoke Test

```bash
cargo run -p obi-cli -- lower /bin/echo
```

Expected:
- a `LoweringReceipt` JSON payload
- translation block summaries present
- compilation preview present
- a saved receipt under the cache `lowers/` directory
```
