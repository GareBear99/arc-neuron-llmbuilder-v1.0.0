# Contributing

Thanks for contributing to ARC-Core.

## Ground rules
- keep changes deterministic where possible
- do not weaken role gates or receipt integrity casually
- prefer explicit schemas and bounded workflow over hidden magic
- include tests for workflow-affecting behavior
- keep docs aligned with the real implementation surface

## Development
```bash
cd ARC_Console
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```
