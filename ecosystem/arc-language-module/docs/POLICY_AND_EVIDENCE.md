
# Policy + Evidence Layer

v18 adds three operational hardening pieces:

1. **System status** — a single operator-facing summary of graph, providers, governance, receipts, and policies.
2. **Operator policy** — explicit policy keys that block unsafe or premature live execution.
3. **Evidence export** — JSON evidence bundles for review, handoff, or audit.

## Default policies

- `runtime_default_dry_run=true`
- `allow_external_providers=true`
- `allow_mutation_actions=false`
- `allow_live_speech=false`

These defaults preserve the local-first, fail-loud posture.

## Evidence bundle

The evidence exporter can include:

- system status
- providers
- lineage for selected language IDs
- install plans
- runtime receipts
- provider action receipts

This creates an exportable state snapshot without needing direct database access.
