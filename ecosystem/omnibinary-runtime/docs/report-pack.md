# Report Pack

`obi report-pack` summarizes whether the major machine-readable maintainer reports have already been generated into the local cache.

This is useful when building an evidence bundle before release review or machine-validation handoff.

Expected reports currently tracked:
- doctor
- readiness-report
- lane-matrix
- release-blockers
- impl-backlog
- truth-ledger
- completion-map
- evidence-pack
- runtime-core-score
- machine-evidence-plan
- repo-audit

This command does not prove runtime completeness. It only reports local report-generation coverage.
