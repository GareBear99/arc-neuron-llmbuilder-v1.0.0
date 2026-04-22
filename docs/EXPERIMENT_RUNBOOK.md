# Experiment Runbook

## Purpose
Every meaningful run should leave behind structured evidence.

## Required run sequence
1. Validate repo
2. Check backend health
3. Run model benchmarks
4. Score outputs
5. Attempt promotion
6. Run quantization-retention report
7. Record experiment metadata

## Minimum experiment metadata
- model_name
- adapter
- backend endpoint
- prompt_profile
- benchmark input file
- scored output file
- promotion decision
- quantization report path
- notes

## Rule
No checkpoint should be described as improved unless an experiment record exists.
