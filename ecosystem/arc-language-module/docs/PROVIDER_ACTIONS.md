# Provider Actions

This layer turns translation install plans into provider-specific action catalogs and execution receipts.

## Goals
- keep runtime/package actions auditable
- support dry-run and apply modes
- block host mutation unless explicitly allowed
- preserve manual steps when no safe installer hook exists

## Current providers
- `argos_local`
  - `install_dependency`
  - `map_runtime_codes`
  - `install_language_pair`
  - `verify_ready`
- `argos_bridge` / `nllb_bridge`
  - `configure_live_bridge`

## Safety model
- `dry_run=True` is the default
- shell-changing actions require `allow_mutation=True`
- manual-only actions produce receipts and guidance without pretending execution happened

## Receipt model
Every action produces a `provider_action_receipt` record with:
- provider name
- action name
- dry-run/apply flags
- request payload
- response payload
- notes
- timestamp
