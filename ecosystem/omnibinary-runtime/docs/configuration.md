# Configuration

OmniBinary uses a simple runtime config model in this repo state.

## Discovery order
1. `OBI_CONFIG`
2. `./obi.toml`
3. `~/.config/omnibinary/obi.toml`
4. built-in defaults

## Current keys
- `cache_dir`
- `receipt_limit`
- `strict_policy`
- `allow_native_direct`
- `allow_native_attach`
- `allow_foreign_dbt`
- `allow_managed_portable`
- `emit_receipts`

The config is advisory in v0.7. It mainly hardens CLI behavior and repo ergonomics; it is not yet a full policy engine.
