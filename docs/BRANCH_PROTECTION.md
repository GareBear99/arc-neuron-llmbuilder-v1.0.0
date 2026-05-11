# Main Branch Protection

Branch protection is a GitHub repository setting. It is not activated by committing files alone.

This repo includes the payload and helper scripts required to apply the rule from the terminal.

## Apply protection

```bash
gh auth login
bash scripts/github/apply_main_branch_protection.sh GareBear99 arc-neuron-llmbuilder-v1.0.0 main
```

## Verify protection

```bash
bash scripts/github/check_main_branch_protection.sh GareBear99 arc-neuron-llmbuilder-v1.0.0 main
```

## Manual route

GitHub repo → Settings → Branches → Add branch protection rule → Branch name pattern: `main`

Recommended settings:

- Require a pull request before merging
- Require 1 approval
- Require conversation resolution before merging
- Include administrators
- Do not allow force pushes
- Do not allow deletions

## Notes

The `.github/branch-protection-main.json` file is the source-controlled policy payload. The active rule still must be applied through GitHub settings or the GitHub API.
