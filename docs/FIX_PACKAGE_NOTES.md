# Fix Package Notes

This package cleans the repository root, repairs CI workflow YAML, adds the missing branch protection payload, keeps Buy Me a Coffee funding active, and includes scripts to apply/check branch protection through GitHub CLI.

Removed root packaging artifacts:

- `AI_BRIEFING_FOR_VIBE_CODERS.patch`
- `BRANCH_PROTECTION_FUNDING_FLOW.patch`
- `README_BRANCH_BMC_FLOW.patch`
- `README_protosynth_integration.patch`
- `README_roadmap_license_language.patch`
- `APPLY_ROADMAP_LICENSE_LANGUAGE.sh`
- `APPLY_NOTES.md`

Branch protection still needs to be applied through GitHub after commit/push:

```bash
bash scripts/github/apply_main_branch_protection.sh GareBear99 arc-neuron-llmbuilder-v1.0.0 main
```
