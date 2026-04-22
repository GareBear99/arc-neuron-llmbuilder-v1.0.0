# Phase 4 Functioning Model — 2026-04-14

Cognition-core now includes a **real native functioning model path**.

## What was added
- `adapters/exemplar_adapter.py`
- `scripts/training/train_exemplar_candidate.py`
- `scripts/execution/run_functioning_candidate.py`
- `tests/test_functioning_model.py`
- `docs/FUNCTIONING_MODEL_STATUS_2026-04-14.md`

## What it does
The new `exemplar` adapter loads a deterministic local artifact built from curated JSONL corpora already in the repo and the supporting package ingestions.

## Verified result
Candidate: `darpa_functional`
- artifact built successfully
- benchmark run completed successfully
- scored output file generated successfully
- current overall weighted score: `0.3458`
- full candidate gate still passes for the scaffold lane

## Honest status
This is a real runnable model path and closes the biggest honesty gap in the repo.
It is **not** yet the final GGUF-trained candidate path.
The remaining hard blockers are still the true external trainer / merge / GGUF exporter loop and retention validation against a produced quantized artifact.
