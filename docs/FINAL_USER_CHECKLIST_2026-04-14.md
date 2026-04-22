# Final User Checklist (2026-04-14)

1. Run `scripts/operator/setup_local_user_runtime.sh`.
2. Run `scripts/operator/runtime_status.sh`.
3. Edit `.env.direct-runtime` with either an exemplar path or a GGUF + local binary command template.
4. Test one prompt with `scripts/operator/run_local_prompt.sh "hello"`.
5. Run `scripts/operator/benchmark_local_model.sh` once the local runtime path works.
6. Check `reports/user_runs/` for runtime receipts.

Product boundary: browser UI may wrap this later, but authoritative execution remains local and direct.


## Quick GGUF / llamafile switchover

When you are ready to move from the bundled baseline to your own local model, use:

```bash
scripts/operator/register_gguf_runtime.sh --gguf /absolute/path/to/model.gguf --binary /absolute/path/to/llama-cli
```

Or for a final self-contained executable:

```bash
scripts/operator/register_gguf_runtime.sh --llamafile /absolute/path/to/model.llamafile
```

Then verify with:

```bash
scripts/operator/runtime_status.sh
scripts/operator/run_local_prompt.sh "hello"
```
