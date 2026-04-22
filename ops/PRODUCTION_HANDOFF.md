# Production Handoff

## What this repo is
A production-ready alpha cognition lab scaffold for evaluating, comparing, and promoting candidate local cognition models.

## What this repo is not
- A trained frontier model
- A completed fine-tuning stack
- A proven Claude-class/Maverick-class checkpoint

## Required external dependencies
- A real local model backend (llama.cpp server or OpenAI-compatible endpoint)
- A real base model candidate
- Real benchmark and dataset expansion beyond seed levels

## Operator startup sequence
1. Configure `.env` from `.env.example`.
2. Point `configs/local_backends.yaml` and `configs/model_runtime.yaml` to the target backend.
3. Run repo validation.
4. Run backend health check.
5. Bootstrap experiment.
6. Run candidate gate.
7. Review reports before promotion.

## Minimum release gate
- Validation passes
- Tests pass
- Backend health check passes
- Candidate benchmark run completes
- Promotion decision report generated
- Quantization retention report generated
