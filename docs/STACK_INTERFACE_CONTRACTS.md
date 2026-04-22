# ARC-Neuron Stack Interface Contracts

This document freezes the cross-layer contracts for the ARC-Neuron system.

## Layers
1. ARC Core — intent routing, task/state spine, approvals, promotion control
2. Cleanroom Runtime — governed execution, replay receipts, rollback semantics
3. Omnibinary — native binary ledger for learned deltas, receipts, and host-side durable binary state
4. Arc-RAR — durable archive packaging for rollback bundles, lineage bundles, and release receipts
5. ARC Language Module — canonical lexical truth layer
6. ANCF — canonical neural artifact container
7. GGUF — deploy/export runtime artifact
8. ARC-Neuron — learned model family

## Contract rules
- Language truth never exists only in weights.
- Learned deltas must be ledgered in Omnibinary before promotion.
- Promotion candidates must be archived through Arc-RAR before release acceptance.
- ANCF is the canonical artifact; GGUF is the deployable export.
- ARC Core is the authority for promotion decisions.
- Cleanroom receipts are the replayable operational truth for runtime behavior.
- Model-family registry changes require a new release receipt.

## Required artifacts for a promoted release
- canonical `.ancf`
- deployable `.gguf`
- model card
- benchmark gate results
- Omnibinary ledger receipt
- Arc-RAR archive bundle
- release manifest with hashes

## Promotion states
- `tiny_regression_floor`
- `base_prep`
- `base_candidate`
- `base_release`
- `core_candidate`
- `core_release`

## Current canonical state
- Tiny regression floor exists
- Base prep exists
- Base release contract exists
- External stronger checkpoint still required for serious capability jump
