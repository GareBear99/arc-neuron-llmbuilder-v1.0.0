
# v2.9 model profiles and training export

This release keeps the runtime open-ended for future custom GGUF learning work.

## Model profiles
Profiles live under `.arc_lucifer/model_profiles.json` and can describe:
- local GGUF/llamafile paths
- future external endpoints
- custom metadata and intended use
- whether a profile is training-ready

The active profile is merged into prompt/runtime settings automatically.

## Training export
`lucifer train export-supervised --output corpus.jsonl`
exports:
- operator inputs
- model runs
- receipts

`lucifer train export-preferences --output prefs.jsonl`
exports preference pairs from candidate scoring state.

These corpora are JSONL so they stay open-ended for future custom training,
GGUF conversion, or external fine-tune tooling.
