# Governance Workflow

This module now has a formal local governance path so new languages and custom lineage claims can scale without overwriting canonical imports.

## Review targets

- `language_submission`
- `custom_lineage`

## Decisions

- `needs_review`
- `accepted_local`
- `rejected`
- `disputed`

## Capability maturity

Each language can also track implementation maturity by capability:

- `none`
- `seeded`
- `experimental`
- `reviewed`
- `production`

Typical capability names:

- `detection`
- `lineage`
- `translation`
- `transliteration`
- `speech`
- `etymology`

## Examples

Review a pending language submission and accept it locally:

```bash
arc-lang review-target language_submission <submission_id> accepted_local --notes "Reviewed against local source pack"
```

Mark a custom lineage claim as disputed:

```bash
arc-lang review-target custom_lineage <assertion_id> disputed --notes "Competing family label in secondary source"
```

Set language capability maturity:

```bash
arc-lang set-language-capability lang:moh detection reviewed --confidence 0.82
arc-lang set-language-capability lang:moh lineage reviewed --confidence 0.90
arc-lang set-language-capability lang:moh translation experimental --confidence 0.55
```

Read readiness summary:

```bash
arc-lang language-readiness lang:moh
```

## Design rules

- Imported source-backed data remains canonical.
- Custom assertions remain separate and reviewable.
- Review decisions are append-only records.
- Capability maturity is operational, not genealogical truth.


## Arbitration and effective truth

Raw evidence remains preserved. The system computes an effective lineage view by scoring each claim using confidence, source authority, custom status, latest review decision, and dispute penalties. Conflicts are flagged when competing destinations are close enough in score that a human reviewer should inspect them.
