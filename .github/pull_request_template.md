<!-- Thanks for contributing to ARC-Neuron LLMBuilder. Please fill this out fully. -->

## Summary

<!-- What does this PR do in one sentence? -->

## Type of change

- [ ] Bug fix
- [ ] New feature / capability
- [ ] Documentation
- [ ] Benchmark addition / scorer update
- [ ] Governance change (touches Gate v2, floor model, Arc-RAR, Omnibinary)
- [ ] Cross-repo integration (link the sibling PR/issue)

## Governance invariants

The ten invariants live in [GOVERNANCE_DOCTRINE.md](../GOVERNANCE_DOCTRINE.md).

- [ ] This PR preserves all ten governance invariants.
- [ ] If any invariant is redefined, it is called out explicitly below and the CHANGELOG is updated.

<!-- If redefined, list which and why: -->

## Evidence

- [ ] `python3 -m pytest tests/ -q` passes locally.
- [ ] If this changes scoring or gate behavior, `scripts/ops/run_n_cycles.py --cycles 3` was run and the stability verdict is attached.
- [ ] If this affects Omnibinary or Arc-RAR formats, `scripts/ops/benchmark_omnibinary.py` numbers are attached and the `demo_proof_workflow.py` run is green end-to-end.
- [ ] New public APIs have tests in `tests/`.

## Documentation

- [ ] README, ARCHITECTURE, GOVERNANCE_DOCTRINE, QUICKSTART, USAGE, FAQ, GLOSSARY, or ROADMAP updated as needed.
- [ ] CHANGELOG entry added under the unreleased section (or a new version).

## Linked issues

<!-- Closes #123, Related to #456 -->

## Screenshots / output (optional)

<!-- Paste relevant receipts, scoreboard diffs, or promotion_decision.json snippets here. -->
