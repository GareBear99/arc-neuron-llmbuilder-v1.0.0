# ANCF Canonical Artifact

ANCF is the canonical ARC neural artifact wrapper in this repo-side demo path.

Current demo structure:
- header magic: `ANCF`
- version: `1`
- canonical metadata JSON payload
- embedded GGUF payload bytes

Purpose:
- preserve provenance and ARC-specific lineage around a deployable GGUF model
- keep runtime/export compatibility separate from archival truth

This demo implementation is intentionally minimal and is a staging point for a fuller deterministic tensor container.
