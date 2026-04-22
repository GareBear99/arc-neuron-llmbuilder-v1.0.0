# Language Onboarding — Current State (v0.24)

## Purpose

Safe onboarding of new languages without raw SQL edits. Submissions do not overwrite source-backed canonical data. Custom lineage is preserved with status and provenance and participates in arbitration.

## Full submission flow

### 1. Export a template
```bash
python -m arc_lang.cli.main export-language-template /tmp/lang_template.json
```

### 2. Fill the template
Required fields: `language_id` (format: `lang:xxx`), `name`.
Optional: `iso639_3`, `family`, `branch`, `parent_language_id`, `aliases`, `common_words`, `scripts`, `source_name`, `source_ref`, `confidence`, `notes`.

### 3. Submit
```bash
# From JSON file
python -m arc_lang.cli.main submit-language-json /tmp/my_language.json

# Inline
python -m arc_lang.cli.main submit-language-inline lang:mri "Māori" \
  --iso639-3 mri --family Austronesian --branch Polynesian \
  --aliases "te reo Māori" --source-name user_submission --confidence 0.85
```

### 4. Review
```bash
python -m arc_lang.cli.main list-language-submissions --status submitted
python -m arc_lang.cli.main review-target language_submission <submission_id> accepted_local --reviewer operator_1
```

### 5. Approve (promotes to canonical languages table)
```bash
python -m arc_lang.cli.main approve-language-submission <submission_id>
```

## Custom lineage assertions

When a language's genealogy is disputed, uncertain, or under review, add custom lineage assertions separately from canonical imports:

```bash
python -m arc_lang.cli.main add-custom-lineage lang:mri family:austronesian \
  --relation custom_member_of_family --confidence 0.8 \
  --source-name user_custom --notes "Māori is Polynesian branch of Austronesian"
```

Custom assertions participate in arbitration via `effective-lineage`. They are weighted by `status`, `review_decision`, and operator-set `source_weights`.

## Low-resource and Indigenous language support

- Partial metadata is explicitly allowed — `iso639_3`, `family`, `branch` are all optional.
- `language_capabilities` maturity starts at `none` by default; operators set it to `experimental` only when actual capability exists.
- `missing_phonology: false` is achievable with a single broad IPA hint profile — the package does not require full phonemic inventories.
- Coverage reports surface honest gap flags so operators know exactly what remains.

## Batch onboarding

For bulk submissions, use batch import:
```bash
python -m arc_lang.cli.main batch-import /path/to/submissions.json language_submissions --apply
```
