# Benchmark Direction

This document describes what the repository can measure now and what should be measured next to strengthen public proof.

## Current measurable paths
- low-risk analysis flow
- file write/read roundtrip
- destructive action gating
- SQLite replay survival
- trace generation
- persistent loop goal completion
- smoke-test command-path verification

## Next benchmark tiers
- multi-step repo modification tasks
- tool failure recovery quality
- branch selection quality
- validator precision and recall
- latency and cost tracking per model backend
- long-run stability under repeated persistent-loop execution
- quality comparison across attached GGUF / llamafile backends

## What would make benchmark docs stronger

The next public benchmark pass should add:
- exact hardware used
- exact model/backend used
- input task set
- pass/fail criteria
- median runtime and tail latency
- failure-rate notes
- before/after comparison tables for self-improvement cycles
