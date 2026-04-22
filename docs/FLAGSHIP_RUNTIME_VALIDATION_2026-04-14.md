# Flagship Runtime Validation (2026-04-14)

This repo is complete as a **local runtime and control plane**. The last external dependency is the actual flagship GGUF or `.llamafile` artifact produced from the chosen upstream model family.

Once that artifact exists and is registered, the authoritative validation path is:

```bash
scripts/operator/validate_flagship_runtime.sh
```

## What this proves

It proves the active local runtime can:
- resolve the configured adapter
- locate the native binary or bundled exemplar artifact
- pass the runtime doctor
- answer a direct prompt
- complete a benchmark run
- write runtime receipts locally

## Recommended flow

### Bundled baseline

```bash
scripts/operator/setup_local_user_runtime.sh
scripts/operator/validate_flagship_runtime.sh
```

### Real GGUF with local binary

```bash
scripts/operator/register_real_gguf_artifact.sh --gguf /absolute/path/model.gguf --binary /absolute/path/llama-cli
scripts/operator/validate_flagship_runtime.sh
```

### Final `.llamafile`

```bash
scripts/operator/register_real_gguf_artifact.sh --llamafile /absolute/path/model.llamafile
scripts/operator/validate_flagship_runtime.sh
```

## Honest boundary

If the validation script fails in `command` mode, the failure is not in the local control plane by default. It usually means one of these external conditions is still unresolved:
- the GGUF path is wrong
- the binary path is wrong
- the `.llamafile` is missing or not executable
- the upstream artifact itself does not run correctly on the machine

That is the real final boundary between this repo and the chosen upstream model family/toolchain.
