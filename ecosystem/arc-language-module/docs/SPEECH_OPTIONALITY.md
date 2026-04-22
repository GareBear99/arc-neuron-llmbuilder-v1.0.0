# Speech Optionality — Current State (v0.24)

## Design principle

Speech synthesis is optional by design. Language truth (graph, lineage, profiles) is fully independent from audio output capability. Text-only mode is the default and is fully supported for all operations.

## Provider states

All speech providers can be in one of three states:
- `disabled` — explicitly disabled; returns `ok: false` with `reason: speech_disabled`
- `dry_run: true` — accepts requests but does not attempt synthesis; returns routing info only
- `dry_run: false` (live) — attempts actual synthesis; requires provider runtime

## Implemented providers

| Provider | Kind | Status |
|----------|------|--------|
| `disabled` | Local | Always available. Returns explicit disabled response. |
| `personaplex` | Boundary stub | Wired as boundary; no live NVIDIA runtime in this package. Returns dry-run payload. |

## Runtime routing

`route_runtime_speech` checks:
1. Language capability maturity for `speech` (from `language_capabilities`)
2. Provider health (from `provider_health`)
3. Operator policy `allow_external_providers`

If the provider is offline or blocked by policy, routing fails explicitly with a receipt.

## CLI

```bash
# Dry run (safe, no external calls)
python -m arc_lang.cli.main runtime-speak "hello" lang:eng --provider disabled

# Live attempt (will fail unless provider is actually wired)
python -m arc_lang.cli.main runtime-speak "hello" lang:eng --provider personaplex --live
```

## Adding a real speech provider

1. Implement a `SpeechProvider` subclass in `speech_provider.py`
2. Register it in `get_provider()`
3. Register the provider name in `provider_registry`
4. Set health via `set-provider-health`
5. Set language `speech` capability maturity via `set-language-capability`

The package architecture imposes no constraints on the synthesis technology — TTS engines, cloud APIs, and local models are all valid targets.
