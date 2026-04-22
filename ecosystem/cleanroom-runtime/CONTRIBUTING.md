# Contributing

## Workflow
- Keep the ARC kernel authoritative.
- Preserve backwards compatibility for persisted events and receipts.
- Prefer deterministic changes over model-dependent behavior in core paths.
- Add or update tests for every behavioral change.

## Local dev
```bash
/usr/local/bin/python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
pytest -q
```

## Pull requests
- Include a short rationale.
- Describe operator-facing behavior changes.
- Call out schema, receipt, or persistence changes explicitly.
- Update docs when commands or workflows change.
