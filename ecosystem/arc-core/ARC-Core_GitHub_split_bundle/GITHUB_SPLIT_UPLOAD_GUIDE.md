# ARC-Core GitHub Split Upload Guide

All split packages unpack into the same root folder:

`ARC-Core-main/`

That means you can drag each package into GitHub for the same repository and they will merge into one coherent tree instead of creating mismatched folders.

## Recommended upload order

1. `ARC-Core_part_01_root_bootstrap.zip`
2. `ARC-Core_part_02_core_api.zip`
3. `ARC-Core_part_03_services_geo.zip`
4. `ARC-Core_part_04_ui_web.zip`
5. `ARC-Core_part_05_tests_docs_data.zip`

## Important notes

- The signing key is intentionally **not** included. The app auto-generates it on first run.
- `arc.db` is intentionally excluded. Seed demo data locally with `python seed_demo.py`.
- If GitHub asks whether to replace files, choose the option that preserves folder structure and adds new files.

## Local boot after upload

```bash
cd ARC_Console
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed_demo.py
uvicorn run_arc:app --reload
```
