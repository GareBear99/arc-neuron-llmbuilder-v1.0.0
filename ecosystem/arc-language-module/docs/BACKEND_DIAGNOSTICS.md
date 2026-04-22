# Backend Diagnostics — Current State (v0.24)

## What is implemented

`backend_diagnostics` service provides three operator-facing diagnostic tools:

### 1. Provider diagnostics (`get_provider_diagnostics`)

Returns for each provider (or a specific provider):
- Registration record from `provider_registry`
- Latest health snapshot from `provider_health`
- Usability determination (enabled + health check)
- Translation backend descriptor if applicable
- Install plan readiness if applicable

```bash
python -m arc_lang.cli.main provider-diagnostics
python -m arc_lang.cli.main provider-diagnostics argos_local
```

### 2. Translation pair readiness (`get_translation_pair_readiness`)

For a given source→target language pair and provider:
- Source and target language records from DB
- Source and target capability maturity
- Provider health
- Install plan readiness status
- Explicit readiness verdict: `ready | degraded | not_ready | unknown`

```bash
python -m arc_lang.cli.main translation-readiness lang:eng lang:spa --provider local_seed
python -m arc_lang.cli.main translation-readiness lang:nav lang:eng --provider argos_local
```

### 3. Readiness matrix (`get_translation_readiness_matrix`)

Cross-product readiness for all known languages vs a provider (or all providers). Useful for identifying which pairs are actually executable vs which are stubs.

```bash
python -m arc_lang.cli.main translation-readiness-matrix --provider argos_local --limit 20
python -m arc_lang.cli.main translation-readiness-matrix --target-language-id lang:eng
```

## Backend manifests

`backend_manifests` table declares provider-level expectations:
- `execution_mode`: `local | optional_local | external_bridge | optional_external`
- `supported_pairs_json`: language pair list (if known statically)
- `dependency_json`: required packages or services
- `health_policy_json`: how to assess health for this backend

```bash
python -m arc_lang.cli.main system-status   # includes backend manifest summary
```

4 manifests seeded: `local_seed`, `argos_local`, `argos_bridge`, `nllb_bridge`.

## Honest readiness semantics

A pair is `ready` only when:
1. Both source and target languages have capability maturity ≥ `seeded`
2. Provider is registered, enabled, and health is not `offline`
3. Policy `allow_external_providers` is not blocking the provider

If any condition fails, the diagnostic returns the specific blocking reason — never a vague "unavailable".
