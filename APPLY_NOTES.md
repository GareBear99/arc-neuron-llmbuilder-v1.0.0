# Apply Notes — Branch Protection Code Fix

This drop-in fixes the branch protection/funding mismatch in the current repo package.

## What was wrong

- `.github/branch-protection-main.json` was referenced but missing from the uploaded repo package.
- Buy Me a Coffee was present only as a commented example, so GitHub would not show it as an active funding route.
- Root-level patch files from earlier drop-ins were committed into the public repo root.
- Branch protection still has to be applied through GitHub settings/API; repo files only document and automate the operation.

## Drop in

Copy these files into the repo root:

```text
.github/FUNDING.yml
.github/branch-protection-main.json
.github/workflows/branch-protection-audit.yml
docs/BRANCH_PROTECTION.md
scripts/github/apply_main_branch_protection.sh
scripts/github/check_main_branch_protection.sh
scripts/github/cleanup_dropin_artifacts.sh
APPLY_NOTES.md
```

## Commit cleanup + config

```bash
chmod +x scripts/github/*.sh
bash scripts/github/cleanup_dropin_artifacts.sh

git add .github/FUNDING.yml .github/branch-protection-main.json .github/workflows/branch-protection-audit.yml docs/BRANCH_PROTECTION.md scripts/github/apply_main_branch_protection.sh scripts/github/check_main_branch_protection.sh scripts/github/cleanup_dropin_artifacts.sh APPLY_NOTES.md
git rm -f AI_BRIEFING_FOR_VIBE_CODERS.patch BRANCH_PROTECTION_FUNDING_FLOW.patch README_BRANCH_BMC_FLOW.patch README_protosynth_integration.patch README_roadmap_license_language.patch APPLY_ROADMAP_LICENSE_LANGUAGE.sh 2>/dev/null || true
git commit -m "Add branch protection automation and clean repo artifacts"
git push
```

## Apply actual GitHub branch protection

```bash
gh auth login
bash scripts/github/apply_main_branch_protection.sh GareBear99 arc-neuron-llmbuilder-v1.0.0 main
bash scripts/github/check_main_branch_protection.sh GareBear99 arc-neuron-llmbuilder-v1.0.0 main
```

If your Buy Me a Coffee handle is not `GareBear99`, edit `.github/FUNDING.yml` before committing.
