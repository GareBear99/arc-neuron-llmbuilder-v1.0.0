# Provider Runtime Audit — Current State (v0.24)

## Three sources of runtime truth

**Registry truth** (`provider_registry`) — which providers are known, enabled, and local-only. 10 providers seeded: `local_detect`, `local_seed`, `local_graph`, `local_map`, `mirror_mock`, `argos_local`, `argos_bridge`, `nllb_bridge`, `disabled`, `personaplex`.

**Health truth** (`provider_health`) — latest observed health snapshot per provider. Statuses: `healthy | degraded | offline`. Stored with `latency_ms` and `error_rate`. Offline providers are blocked by the runtime orchestrator.

**Receipt truth** (`job_receipts`) — every runtime translation/speech request stores full request payload, response payload, status, and notes. `provider_action_receipts` stores provider action execution records.

## Diagnostics

```bash
# Current health of all providers
python -m arc_lang.cli.main provider-diagnostics

# Health of a specific provider
python -m arc_lang.cli.main provider-diagnostics argos_local

# Translation readiness for a specific pair
python -m arc_lang.cli.main translation-readiness lang:eng lang:spa --provider argos_local

# Readiness matrix (all known languages vs a provider)
python -m arc_lang.cli.main translation-readiness-matrix --provider local_seed --limit 10

# List all runtime receipts
python -m arc_lang.cli.main list-runtime-receipts --limit 20
```

## Registering and updating providers

```bash
python -m arc_lang.cli.main register-provider my_nmt_service translation --notes "Custom NMT bridge"
python -m arc_lang.cli.main set-provider-health my_nmt_service healthy --latency-ms 180
python -m arc_lang.cli.main list-providers --provider-type translation
```

## Policy controls

Provider blocking is governed by `operator_policies`. Key policy keys:

| Policy key | Effect |
|-----------|--------|
| `allow_external_providers` | `false` blocks all bridge-style (non-local) providers |
| `require_dry_run` | `true` forces dry_run on all runtime requests |

```bash
python -m arc_lang.cli.main show-policy
python -m arc_lang.cli.main set-policy allow_external_providers false
```

## Evidence bundles

Full operator evidence export bundles together: system status, provider list, install plans, job receipts, provider action receipts, and per-language lineage.

```bash
python -m arc_lang.cli.main export-evidence evidence_bundle.json \
  --language-id lang:eng --language-id lang:spa
```
