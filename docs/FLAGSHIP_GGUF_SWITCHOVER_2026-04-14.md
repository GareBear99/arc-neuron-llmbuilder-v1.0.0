# Flagship GGUF / Llamafile Switchover

This repo ships with a bundled local exemplar baseline so first run works immediately.

When your flagship GGUF is ready, switch the runtime in one step:

```bash
scripts/operator/register_gguf_runtime.sh --gguf /absolute/path/to/model.gguf --binary /absolute/path/to/llama-cli
```

Or use a final self-contained executable:

```bash
scripts/operator/register_gguf_runtime.sh --llamafile /absolute/path/to/model.llamafile
```

What this changes:
- sets `COGNITION_RUNTIME_ADAPTER=command`
- sets `COGNITION_MODEL_PATH` when using GGUF + binary
- sets `COGNITION_COMMAND_TEMPLATE`
- preserves timeout settings

After switching:

```bash
scripts/operator/runtime_status.sh
scripts/operator/run_local_prompt.sh "hello"
scripts/operator/benchmark_local_model.sh
```

The user-facing product story remains:

**Browser-based interface, local native GGUF execution, no server required.**
