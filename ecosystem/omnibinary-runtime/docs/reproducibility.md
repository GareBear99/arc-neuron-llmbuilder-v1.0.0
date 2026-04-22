# Reproducibility

OmniBinary should prefer deterministic outputs wherever practical.

## Current rules
- receipts contain timestamps but maintain stable schemas
- lane selection should remain deterministic for the same input and config
- cache key hints must derive from binary identity, host profile, policy, and optimizer version

## Future rules
- translated artifact hashes must include decoder and lowering version IDs
- benchmark fixtures should pin exact sample inputs
