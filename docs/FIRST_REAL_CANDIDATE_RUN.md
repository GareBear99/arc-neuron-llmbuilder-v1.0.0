# First Real Candidate Run

This runbook is the first non-scaffold phase of the project.

## Goal
Take one real local model candidate and run it through the lab end to end:
1. backend health check
2. baseline benchmark run
3. score outputs
4. write experiment log
5. compare against incumbent
6. decide whether the candidate is worth shaping

## Day 0 target
Use one real candidate from `configs/base_model_candidates.yaml` and one real backend entry from `configs/local_backends.yaml`.

## Sequence

### 1. Set environment
Copy `.env.local-model.example` to `.env.local-model` and fill in the backend URL and model name.

### 2. Verify backend
Run:
```bash
make smoke-local
python scripts/execution/check_local_backend.py
```

### 3. Bootstrap experiment
Run:
```bash
python scripts/execution/bootstrap_experiment.py
```

### 4. Run candidate baseline
Run:
```bash
python scripts/execution/run_full_candidate_gate.py
```

### 5. Inspect artifacts
Check:
- `results/scoreboard.json`
- `results/experiments.jsonl`
- `reports/`

### 6. Only then start shaping
If the candidate is viable, prepare the distillation corpus and begin LoRA/SFT.

## Pass conditions
- backend reachable
- benchmark execution completes
- scoring completes
- promotion decision writes a report
- experiment log is updated

## Fail-fast conditions
- backend unreachable
- malformed outputs
- prompt-profile collapse
- obvious overconfidence or repair regression
