# Native GGUF Bootstrap From Uploaded ARC Stack

This closes everything that can be closed **without inventing missing neural weights**.

## What is finished now

- Training readiness gate passes.
- Distillation corpus preparation works.
- Supporting corpus ingestion runs against the uploaded ARC stack:
  - ARC Core
  - ARC Lucifer Cleanroom Runtime
  - OmniBinary Runtime
  - Arc-RAR
  - ARC Language Module
- Candidate artifact chain runs end-to-end in scaffold mode.
- A concrete GGUF build env template is generated for this stack.

## One-command bootstrap

```bash
python3 scripts/bootstrap/bootstrap_arc_stack.py
```

Outputs:
- `reports/bootstrap_arc_stack/bootstrap_manifest.json`
- `reports/bootstrap_arc_stack/real_gguf_build.env.bootstrap`
- refreshed dataset/manifests under `datasets/*` and `reports/*`
- candidate artifact manifests under `exports/candidates/arc_stack_bootstrap/*`

## Honest boundary

The remaining external dependency is still the same:
- a real upstream pretrained/merged model directory
- the actual `convert_hf_to_gguf.py` tool
- `llama-quantize`
- `llama-cli` or `llamafile`

Without those, the repo can only complete the **scaffolded artifact chain**, not produce a truthful flagship `.gguf` file.

## Final handoff once weights exist

1. Fill `reports/bootstrap_arc_stack/real_gguf_build.env.bootstrap`
2. Copy it to:
   - `configs/production/real_gguf_build.env`
3. Run:

```bash
scripts/production/build_real_gguf_handoff.sh
scripts/operator/register_real_gguf_artifact.sh --gguf /absolute/path/model.gguf --binary /absolute/path/llama-cli
scripts/operator/validate_flagship_runtime.sh
```

## Why this solves the native path cleanly

It removes ambiguity between:
- repo/data/control-plane state
- candidate artifact state
- final upstream model-family conversion state

That means native runtime issues stop being mixed together with training/export issues.
