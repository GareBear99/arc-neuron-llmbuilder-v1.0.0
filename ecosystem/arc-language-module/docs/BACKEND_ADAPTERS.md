# Backend Adapters

Version 0.13 adds a translation backend adapter layer.

## Built-in translation backends

- `local_seed`
  - Executes seeded phrase/lexeme graph translation immediately.
  - This is the first real working translation adapter.

- `mirror_mock`
  - Same-language identity backend for pipeline testing, normalization flows, and health checks.

- `argos_bridge`
  - Boundary stub only. Accepts dry-run dispatches and records payloads, but does not execute live translation in this package.

- `nllb_bridge`
  - Boundary stub only. Accepts dry-run dispatches and records payloads, but does not execute live translation in this package.

## Why this matters

The runtime can now distinguish between:
- a provider that has a real adapter in this package
- a provider that only has a boundary stub
- a provider that is not backed by any adapter

That makes runtime receipts and health status more meaningful because a request can now be:
- executed
- blocked at the boundary
- refused for lack of adapter

## Usage

```bash
arc-lang list-translation-backends
arc-lang runtime-translate hola lang:eng
arc-lang runtime-translate hello lang:eng --source-language-id lang:eng --preferred-translation-provider mirror_mock
arc-lang runtime-translate bonjour lang:eng --source-language-id lang:fra --preferred-translation-provider nllb_bridge
```
