# Functioning Model Status — 2026-04-14

This repo now includes a **real native functioning model path** that does not depend on unavailable external trainers.

## What it is
A local exemplar-retrieval model trained from curated JSONL corpora already inside cognition-core and its supporting package ingestions.

## What it does
- builds an artifact under `exports/candidates/<candidate>/exemplar_train/exemplar_model.json`
- loads that artifact through the `exemplar` adapter
- answers benchmark prompts by retrieving the strongest matching exemplars and synthesizing a bounded response
- can be benchmarked and scored end to end with the existing execution spine

## Honest limitations
- it is not a frontier generative model
- it is not LoRA / DPO / GGUF-derived yet
- it is a deterministic local specialist baseline proving that cognition-core can produce and run a real candidate today

## Why this matters
It closes the biggest honesty gap: the repo now contains a working local model path instead of only scaffolding around future model paths.
