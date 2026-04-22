# Package Lifecycle and Install Planning

This layer turns backend diagnostics into actionable next steps.

## Goals
- tell the operator exactly why a translation pair is not runnable
- produce install or configuration steps per provider/language pair
- store install plans as auditable local records
- keep runtime truth separate from package readiness

## Current provider behavior

### `local_seed`
- no external package install required
- only covers seeded phrase/lexeme translations

### `mirror_mock`
- no external package install required
- only valid for same-language identity testing

### `argos_local`
- requires the optional `argostranslate` dependency
- also requires the exact runtime language pair package to be installed locally
- install plans surface whether the missing item is:
  - the dependency itself
  - a runtime language code mapping
  - the exact source→target package pair

### boundary providers
- `argos_bridge`
- `nllb_bridge`

These remain bridge/configuration targets in this package. Their install plans focus on adapter/bridge setup rather than local package installation.

## API
- `GET /runtime/install-plan/translation`
- `POST /runtime/install-plan/translation/record`
- `GET /runtime/install-plans`

## CLI
- `arc-lang translation-install-plan <src> <dst> --provider argos_local`
- `arc-lang record-translation-install-plan <src> <dst> --provider argos_local --note "operator note"`
- `arc-lang list-translation-install-plans`

## Why this exists
The system can now answer both:
- "Is this pair runnable?"
- "What exactly must I install or configure next to make it runnable?"
