# Main Branch Protection

This repository should protect `main` so the public release line cannot be overwritten, force-pushed, deleted, or merged without review.

> Important: branch protection is a GitHub repository setting. Committing `.github/branch-protection-main.json` documents the intended policy, but it does **not** activate protection by itself. The repo owner/admin must apply the rule in GitHub settings or run the helper script below.

## Current intended rule

The committed protection payload lives here:

```text
.github/branch-protection-main.json
```

It is configured for:

- branch name: `main`
- pull request review required before merging
- 1 approving review required
- stale approvals dismissed after new commits
- Code Owners review required where `CODEOWNERS` matches
- status check required: `validate-and-test`
- branches required to be up to date before merging
- conversation resolution required
- linear history required
- administrators included
- force pushes disabled
- branch deletions disabled

## Apply with GitHub CLI

From the repo root:

```bash
gh auth login
bash scripts/github/apply_main_branch_protection.sh GareBear99 ARC-Neuron-LLMBuilder main
```

Then verify:

```bash
bash scripts/github/check_main_branch_protection.sh GareBear99 ARC-Neuron-LLMBuilder main
```

Or directly:

```bash
gh api repos/GareBear99/ARC-Neuron-LLMBuilder/branches/main/protection
```

## Manual GitHub UI path

1. Open the repository on GitHub.
2. Go to **Settings → Branches**.
3. Under **Branch protection rules**, choose **Add branch protection rule**.
4. Set **Branch name pattern** to `main`.
5. Enable the intended rule above.
6. Save changes.

## If GitHub still says `main` is not protected

Check these first:

```bash
gh auth status
gh repo view GareBear99/ARC-Neuron-LLMBuilder --json nameWithOwner,viewerPermission
bash scripts/github/check_main_branch_protection.sh GareBear99 ARC-Neuron-LLMBuilder main
```

Common causes:

- the branch protection JSON exists in the repo, but the setting was never applied
- the GitHub CLI account does not have admin permission on the repo
- the script was run from the wrong repo root
- the repo name or owner argument was different from the actual GitHub repository
- the GitHub page needs a refresh after the API call

## Why this matters for ARC-Neuron

ARC-Neuron LLMBuilder is built around receipts, rollback, benchmark evidence, and promotion gates. The repository should follow the same discipline:

```text
no silent overwrites
no force-push history loss
no unreviewed release-line mutation
no branch deletion accidents
```

That keeps the public record aligned with the governance doctrine of the project.
