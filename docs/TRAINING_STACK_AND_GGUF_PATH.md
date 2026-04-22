
# Training Stack and GGUF Completion Path

This document defines the practical path from the current lab scaffold to a real candidate GGUF cognition engine.

## Goal
Shape a strong open-weight base model into a cognition engine that preserves:
- planning
- critique
- repair
- compression
- calibrated uncertainty
- structured output discipline

## Stage order
1. Prepare distillation corpus
2. Run supervised LoRA/SFT shaping
3. Run preference shaping for revision and boundedness
4. Evaluate against benchmark suites
5. Merge promoted adapters into exportable checkpoints
6. Export GGUF variants
7. Run quantization-retention checks
8. Promote only passing variants

## Honest boundary
This repo now contains the package-level path. A real Claude-class result still depends on a strong base model, real training runs, and real retention measurements.
