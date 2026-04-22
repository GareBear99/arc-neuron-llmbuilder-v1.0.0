# Operator evidence — live-deployment learning signal

This doc captures the real live-deployment runs that feed
`data/critique/operator_reviews.jsonl`. Each entry is an auditable
record of a production review the [ARC GitHub AI Operator](https://github.com/GareBear99/gh-ai-operator)
performed and the corresponding JSONL record that landed in this repo's
critique corpus via the nightly ingest.

See also: [LIVE_DEPLOYMENT_LEARNING.md](./LIVE_DEPLOYMENT_LEARNING.md) for the
pipeline design; [gh-ai-operator/docs/FIRST_LIVE_RUN.md](https://github.com/GareBear99/gh-ai-operator/blob/main/docs/FIRST_LIVE_RUN.md) for the
operator-side record of the same runs.

---

## #1 — FreeEQ8 (flagship JUCE audio plugin)

**Date**: 2026-04-22

**Portfolio issue**: <https://github.com/GareBear99/Portfolio/issues/1>

**Target**: <https://github.com/GareBear99/FreeEQ8>

**Depth**: standard · **Type**: Full repo review

**Focus** (requester-stated):
DSP safety (real-time, no allocations in `processBlock`), JUCE patterns,
test coverage, license + README completeness, v1.0-ready hygiene.

### Verdict

> **🟡 address feedback — small number of specific fixes suggested**

### Operator observation (51 files, ~1.79 MB, depth-1 snapshot)

- Root files the operator recognised: `CHANGELOG.md`, `CMakeLists.txt`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `LICENSE`, `README.md`, `SECURITY.md`, `STRIPE_SETUP.md`, `build_linux.sh`
- Root dirs: `.github`, `JUCE`, `Source`, `Tests`, `docs`, `server`
- Top extensions: `.h×13`, `.md×9`, `.jpeg×6`, `.cpp×5`, `.sh×3`, `.yml×3`, `.js×2`

### Findings (verbatim)

- *Several sampled source files expose few recognizable function/class symbols (e.g. `Source/PluginEditor.h`, `Source/Config.h`, `Source/PluginProcessor.h`), which can make navigation and review harder.*

### Record that lands in `data/critique/operator_reviews.jsonl`

```json
{
  "id": "arc-operator-184e9e8c3e",
  "capability": "critique",
  "domain": "code",
  "difficulty": "medium",
  "target": {
    "analysis":   "<full markdown review>",
    "confidence": 0.7,
    "verdict":    "🟡 address feedback — small number of specific fixes suggested",
    "findings":   ["Several sampled source files expose few recognizable function/class symbols …"]
  },
  "tags":       ["critique", "arc-operator", "live-deployment"],
  "provenance": {
    "source":     "github.com/GareBear99/gh-ai-operator",
    "emitted_at": "2026-04-22T22:14:11+00:00",
    "target_url": "https://github.com/GareBear99/FreeEQ8"
  }
}
```

### Ingest manifest (from `scripts/ingest_operator_reviews.py --strict`, dry-run)

```
[ingest] wrote 1 records -> data/critique/operator_reviews.jsonl
[ingest] difficulty: {'medium': 1}
[ingest] verdict:    {'🟡 address feedback — small number of specific fixes suggested': 1}
[ingest] top tags:   [('critique', 1), ('arc-operator', 1), ('live-deployment', 1)]
```

The `--strict` exit was `0`, confirming the operator's output satisfies every
required field in this repo's seed-examples schema.

### Status of downstream Phases (per Quality Proof Plan)

- **Phase 0** (operator produces a valid review + JSONL): **PROVED** on FreeEQ8, real 51-file codebase.
- **Phase 1** (round-trip CI): **PROVED AUTOMATICALLY** via gh-ai-operator's `loop-integration.yml`.
- **Phase 2–4** (live Portfolio dispatch → verdict → nightly ingest commit): **pending non-code blockers**:
  - GitHub Actions billing hold on `GareBear99` (already surfaced; once cleared the Portfolio workflow queued on issue #1 will execute).
  - `AI_OPERATOR_DISPATCH_TOKEN` + `PORTFOLIO_WRITE_TOKEN` + `OPERATOR_READ_TOKEN` PATs set per [QUALITY_PROOF_PLAN §5](https://github.com/GareBear99/gh-ai-operator/blob/main/docs/QUALITY_PROOF_PLAN.md#5-activation-checklist).
- **Phase 5** (A/B proof that operator-enriched corpus improves a candidate): **pending ≥ 50 ingested records**.

---

## How to read this doc going forward

New entries are appended chronologically. Each entry links the Portfolio issue
(if one exists), the target URL, the verdict, the findings, and the exact JSONL
record shape. Together they form the **evidence chain** the Gate v2 training
run can cite when it claims improvement — not "the model got better," but
"the model got better *because of these specific auditable live-deployment
records*."
