# ARC-Neuron LLMBuilder — Branch Protection + Buy Me a Coffee Flow Update

Drop these files into the repository root, preserving folders.

## What changed

- Added Buy Me a Coffee support to README badges, SUPPORT, CONTRIBUTING, ECOSYSTEM, ROADMAP, issue contact links, and `.github/FUNDING.yml`.
- Added a main-branch protection guide so the repo no longer has an undocumented protection gap.
- Added an optional GitHub CLI helper and branch-protection JSON payload.
- Cleaned the README flow so the support, roadmap, protection, and ProtoSynth sections read in the same order as the table of contents.
- Fixed the unclosed `<sub>` topic line at the top of the README.

## Apply

```bash
cp -R . /path/to/ARC-Neuron-LLMBuilder/
cd /path/to/ARC-Neuron-LLMBuilder
chmod +x scripts/github/apply_main_branch_protection.sh

git add README.md SUPPORT.md CONTRIBUTING.md ECOSYSTEM.md ROADMAP.md \
  .github/FUNDING.yml .github/ISSUE_TEMPLATE/config.yml \
  .github/branch-protection-main.json docs/BRANCH_PROTECTION.md \
  scripts/github/apply_main_branch_protection.sh

git commit -m "Add support links and branch protection guidance"
git push
```

## Turn on branch protection

Committing the files documents the rule, but GitHub still needs the repo setting enabled.

UI path:

```text
GitHub repo → Settings → Branches → Add branch protection rule → main
```

Optional CLI path:

```bash
bash scripts/github/apply_main_branch_protection.sh GareBear99 ARC-Neuron-LLMBuilder
```

You need a logged-in `gh` token with admin rights for that repo.
