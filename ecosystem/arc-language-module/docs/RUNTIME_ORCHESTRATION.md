# Runtime Orchestration

This layer separates **knowledge truth** from **execution routing**.

## Why it exists

A language can have:
- reviewed lineage
- production detection
- seeded translation
- no speech support

Those are different facts and should not be collapsed into one fake "supported" bit.

## Runtime translation flow

1. Resolve or detect source language
2. Inspect source/target translation capabilities
3. Prefer local seeded phrase graph when available
4. If a non-local provider is requested and capability exists, return a routing plan or a backend-not-implemented result
5. Optionally route translated text to speech if the target language has speech maturity >= experimental

## Runtime speech flow

1. Resolve best speech capability for the target language
2. Enforce maturity gate
3. Dispatch to provider boundary
4. Keep provider output separate from canonical language truth

## Current providers

- `local_seed` for seeded phrase/lexeme translation
- `personaplex` as optional downstream speech provider
- `disabled` when no runtime speech provider should execute
