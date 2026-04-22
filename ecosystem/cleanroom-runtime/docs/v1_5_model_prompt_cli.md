# v1.5 model prompt CLI

This upgrade turns `lucifer prompt` into a real managed local-model path when llamafile configuration is present.

## Model prompt flow

- If no llamafile configuration is present, `lucifer prompt` continues to route through the deterministic runtime.
- If `--binary-path` / `--model-path` or `ARC_LUCIFER_LLAMAFILE_*` environment variables are set, the CLI configures a managed offline llamafile backend.
- `--stream` prints streamed text live while the runtime still records completion metrics and stream lifecycle events.

## Environment variables

- `ARC_LUCIFER_LLAMAFILE_BINARY`
- `ARC_LUCIFER_LLAMAFILE_MODEL`
- `ARC_LUCIFER_LLAMAFILE_HOST`
- `ARC_LUCIFER_LLAMAFILE_PORT`
- `ARC_LUCIFER_LLAMAFILE_STARTUP_TIMEOUT`
- `ARC_LUCIFER_LLAMAFILE_IDLE_TIMEOUT`
- `ARC_LUCIFER_LLAMAFILE_KEEP_ALIVE`
- `ARC_LUCIFER_USE_MODEL=1`

## Example

```bash
ARC_LUCIFER_LLAMAFILE_BINARY=./llamafile ARC_LUCIFER_LLAMAFILE_MODEL=./model.gguf PYTHONPATH=src python -m lucifer_runtime.cli prompt "Explain the current state" --stream
```
