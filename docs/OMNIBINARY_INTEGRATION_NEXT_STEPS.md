# OmniBinary Integration Next Steps

## What this pack completes
This pack converts OmniBinary Runtime v2.2 from a runtime-side repo into model-facing assets:
- source manifest
- model/runtime boundary spec
- SFT seed records
- preference pairs
- evaluation tasks
- validation script

## What belongs in the GGUF
- inspect-before-act behavior
- binary + host classification reasoning
- execution-lane selection reasoning
- preflight-before-run behavior
- blocker-aware honesty
- receipt/evidence-first output habits
- preview-vs-real-execution distinction

## What stays in the runtime
- actual decoder / lowering code
- loader/JIT/DBT implementations
- block cache implementation
- sandboxing and syscall personality layers
- machine-specific compatibility logic

## Immediate next step after this pack
Merge these records into the existing distillation corpus and benchmark the first real candidate model on:
- lane selection
- preflight reasoning
- blocker detection
- receipt correctness
- preview-vs-execute discipline
