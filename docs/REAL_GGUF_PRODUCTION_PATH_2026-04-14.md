# Real GGUF Production Path

This repo is complete as the local runtime/control plane.

It does **not** internally invent a flagship GGUF from repo text alone. A real flagship GGUF still requires:
- a chosen upstream base model family
- real adapter/fine-tune outputs
- a real merge command for that family
- a real GGUF conversion toolchain

## Locked production path

1. Copy `configs/production/real_gguf_build.env.example` to `configs/production/real_gguf_build.env` and edit it.
2. Point it at your:
   - merged model directory
   - `convert_hf_to_gguf.py`
   - `llama-quantize`
   - runtime binary / llamafile binary
3. Run:

```bash
scripts/production/build_real_gguf_handoff.sh
```

This produces:
- fp16 GGUF
- quantized GGUF
- final `.llamafile`-style executable
- a manifest with hashes and sizes

## Switch cognition-core to the real artifact

For GGUF + binary:

```bash
scripts/operator/register_real_gguf_artifact.sh --gguf /absolute/path/model.gguf --binary /absolute/path/llama-cli
```

For final `.llamafile`:

```bash
scripts/operator/register_real_gguf_artifact.sh --llamafile /absolute/path/model.llamafile
```

Then use the normal local flow:

```bash
scripts/operator/runtime_status.sh
scripts/operator/run_local_prompt.sh "hello"
scripts/operator/benchmark_local_model.sh
```

## Honest boundary

This repo now owns the runtime and switchover side completely.
The only external remaining dependency is the upstream model-family toolchain used to produce the final flagship GGUF.
