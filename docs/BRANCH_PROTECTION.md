# Main Branch Protection

This repository should protect `main` so the public release line cannot be overwritten, force-pushed, or merged without review.

> Important: branch protection is a GitHub repository setting. Committing this file documents the intended policy, but the repo owner/admin still has to enable the rule in GitHub or apply the helper script below.

## Recommended baseline

Use this baseline for `main`:

- Require a pull request before merging.
- Require at least 1 approving review.
- Dismiss stale approvals when new commits are pushed.
- Require review from Code Owners when the changed files match `CODEOWNERS`.
- Require status checks to pass before merging.
- Require branches to be up to date before merging.
- Require conversation resolution before merging.
- Require linear history.
- Do not allow force pushes.
- Do not allow deletions.
- Include administrators, unless you intentionally need an emergency bypass.

## GitHub UI path

1. Open the repository on GitHub.
2. Go to **Settings → Branches**.
3. Under **Branch protection rules**, choose **Add rule**.
4. Set **Branch name pattern** to `main`.
5. Enable the recommended baseline above.
6. Save changes.

## Optional CLI apply path

This repo includes an optional helper script:

```bash
bash scripts/github/apply_main_branch_protection.sh GareBear99 ARC-Neuron-LLMBuilder
```

Requirements:

- GitHub CLI installed: `gh`
- logged in with a token that has repository administration access
- permission to edit branch protection settings

The script uses `.github/branch-protection-main.json` as the protection payload.

## Why this matters for ARC-Neuron

ARC-Neuron LLMBuilder is built around receipts, rollback, benchmark evidence, and promotion gates. The repository should follow the same discipline:

```text
no silent overwrites
no force-push history loss
no unreviewed release-line mutation
no branch deletion accidents
```

That keeps the public record aligned with the governance doctrine of the project.
