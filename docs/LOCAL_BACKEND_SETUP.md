# Local Backend Setup

This package expects a local model backend that exposes an OpenAI-compatible chat completions endpoint.

## Supported first-class path
- llama.cpp server or another OpenAI-compatible local endpoint
- llamafile if configured to expose a compatible endpoint

## Example endpoint
- `http://127.0.0.1:8080/v1/chat/completions`

## Health check
Run:

```bash
python scripts/execution/check_local_backend.py --backend llamacpp_server
```

## Benchmark run
Run:

```bash
python scripts/execution/run_full_candidate_gate.py   --adapter openai_compatible   --prompt-profile minimal_doctrine   --model-name local_candidate_v1
```

## Notes
- Keep temperature low for evaluation runs.
- Point the adapter at a local endpoint, not a cloud service, if the goal is local cognition evaluation.
