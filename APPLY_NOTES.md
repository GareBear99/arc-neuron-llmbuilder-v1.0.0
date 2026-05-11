# Apply Notes — Branch Protection + Funding Flow

This drop-in adds the missing branch protection payload and makes the branch-protection flow explicit.

## Added / Updated

```text
.github/branch-protection-main.json
.github/FUNDING.yml
.github/workflows/branch-protection-audit.yml
README.md
SUPPORT.md
docs/BRANCH_PROTECTION.md
scripts/github/apply_main_branch_protection.sh
scripts/github/check_main_branch_protection.sh
```

## Commit

```bash
git add .github/branch-protection-main.json .github/FUNDING.yml .github/workflows/branch-protection-audit.yml README.md SUPPORT.md docs/BRANCH_PROTECTION.md scripts/github/apply_main_branch_protection.sh scripts/github/check_main_branch_protection.sh APPLY_NOTES.md
git commit -m "Add branch protection payload and funding flow"
git push
```

## Activate branch protection on GitHub

Committing the JSON does not activate the GitHub setting. After pushing, run:

```bash
gh auth login
bash scripts/github/apply_main_branch_protection.sh GareBear99 ARC-Neuron-LLMBuilder main
bash scripts/github/check_main_branch_protection.sh GareBear99 ARC-Neuron-LLMBuilder main
```

Or use GitHub UI:

```text
Repo → Settings → Branches → Add branch protection rule → main
```
