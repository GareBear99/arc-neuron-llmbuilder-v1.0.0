# Main Branch Protection

This repository includes a GitHub API payload for protecting `main`.

Branch protection is not activated by committing a file. It must be applied by a repository owner/admin through GitHub Settings or the GitHub CLI.

## Apply with GitHub CLI

```bash
gh auth login
bash scripts/github/apply_main_branch_protection.sh GareBear99 arc-neuron-llmbuilder-v1.0.0 main
bash scripts/github/check_main_branch_protection.sh GareBear99 arc-neuron-llmbuilder-v1.0.0 main
```

## What the payload enforces

- Pull request required before merge
- One approval required
- Stale approvals dismissed after new commits
- Conversation resolution required
- Admins included
- Force pushes disabled
- Branch deletion disabled

Status checks are intentionally not required in the payload until CI is green, so branch protection can be turned on without locking the repo behind a failing workflow.
