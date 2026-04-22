# v2.1 Code Operator Layer

This upgrade adds the missing deterministic code editing layer for ARC Lucifer.

## Added components
- `src/code_editing/line_map.py`
- `src/code_editing/symbol_index.py`
- `src/code_editing/patch_schema.py`
- `src/code_editing/patch_engine.py`
- `src/code_editing/verifier.py`
- `src/code_editing/planner.py`
- `src/self_improve/promotion.py`

## New CLI commands
- `lucifer code index <path>`
- `lucifer code verify <path>`
- `lucifer code plan <path> <instruction> [--symbol name]`
- `lucifer code replace-range <path> <start_line> <end_line> <replacement_text>`
- `lucifer code replace-symbol <path> <symbol_name> <replacement_text>`
- `lucifer self-improve validate-run <run_id> [--timeout 120]`
- `lucifer self-improve promote <run_id> [--force]`

## Behavior
- exact line-range edits
- Python symbol-aware block replacement
- parser verification after patching
- persisted patch receipts in the kernel
- self-improvement worktree validation and promotion gate

## What this closes
This is the missing Warp-style grounded editor layer: line-anchored editing, symbol-aware targeting, patch verification, and sandbox promotion scaffolding.
