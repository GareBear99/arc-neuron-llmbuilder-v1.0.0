# Testing Strategy

## Current state
This repository currently emphasizes scaffold correctness and documentation clarity.
It does not yet provide backend-level execution validation for foreign binaries.

## Test layers
1. Unit tests for parsing, receipts, cache indexing, and config.
2. CLI smoke tests for inspect/plan/lower/decode/dispatch/status.
3. Host matrix validation on supported CI builders.
4. Golden receipts for deterministic preview outputs.
5. Future differential tests for guest decode and canonical lowering.

## Future high-value additions
- fuzz intake/parser boundaries
- cache corruption recovery tests
- personality-layer contract tests
- DBT invalidation tests
