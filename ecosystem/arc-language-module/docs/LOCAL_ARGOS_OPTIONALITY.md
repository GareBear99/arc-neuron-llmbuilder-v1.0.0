# Optional Local Argos Backend

This version adds `argos_local` as an **optional offline translation backend**.

## Role
- Executes local translation only when `argostranslate` is installed and a matching language pair package exists.
- Does **not** replace the language/lineage graph as the source of truth.
- Stays behind the same runtime orchestration, provider health, and receipt pipeline used by other backends.

## Honest behavior
The backend returns explicit states instead of pretending support:
- `translation_backend_dependency_missing`
- `translation_backend_dependency_failed`
- `translation_backend_language_code_unmapped`
- `translation_backend_language_pair_missing`
- `translation_backend_runtime_failed`

## Runtime mapping
Internal language IDs remain canonical. The backend maps internal `iso639-3` codes into runtime codes for Argos execution only.

## Why this matters
This is the first real path beyond seed-only translation while still respecting the offline/local doctrine.
