# ARC Unified Stack Master Operator Control

This document defines the single top-level operator entrypoint for the current native ARC stack.

## Entrypoint

```bash
scripts/master/run_arc_master_control.sh <phase>
```

## Phases

- `status` — write a summary of the current integrated stack and known artifacts
- `truth-latch` — verify the bidirectional Omnibinary ↔ language-module roundtrip
- `tiny-floor` — validate and smoke-test ARC-Neuron Tiny
- `small-build` — build and smoke-test ARC-Neuron Small
- `small-v2-prep` — regenerate tokenizer-growth prep, Cleanroom supervised exports, and expanded gates
- `base-prep` — rebuild ARC-Neuron Base prep corpora and release artifacts
- `full-native-cycle` — execute the full native progression currently available from the unified package

## Current doctrine

The current package is complete on the repo side for the native stack up through:
- language truth governance
- Omnibinary truth latching
- Arc-RAR archive/rollback packaging
- ARC-Neuron Tiny regression floor
- ARC-Neuron Small native build
- ARC-Neuron Small v0.2 prep
- ARC-Neuron Base prep

This operator flow does **not** claim to replace long-run hardware training cycles. It is the top-level reproducible entrypoint for the governed native pipeline as it exists now.
