# AI Briefing for Vibe Coders and Assistant Operators

This document is the operating brief for AI coding assistants, vibe coders, reviewers, and automated contributors working on ARC-Neuron LLMBuilder.

The goal is simple: move fast without breaking the evidence trail.

ARC-Neuron is not treated as a random prototype folder. It is part of a larger local-first ARC ecosystem where model-building, provenance, benchmarks, language structure, visual cognition, runtime execution, and archival receipts must remain connected.

---

## Prime Directive

Preserve knowledge, preserve lineage, and preserve the path that produced the result.

Do not overwrite, flatten, hide, or misrepresent the chain of evidence that led to a change. Every meaningful update should make the project easier to audit, reproduce, test, compare, and roll back.

In practice:

- do not delete receipts just because a new result is better
- do not replace benchmark context without explaining the change
- do not blur experimental code into stable code without labels
- do not claim production readiness unless tests, docs, and artifacts support it
- do not erase older open-review history while moving toward 3.0 commercial licensing
- do not break the local-first/offline direction unless the dependency is clearly optional

---

## ARC Development Standard

Use a DARPA-style engineering mindset: disciplined, evidence-first, threat-aware, reproducible, and boring where correctness matters.

This does not mean overclaiming affiliation or status. It means applying a high-reliability build standard:

1. Define the mission of the change.
2. Identify the files touched.
3. Preserve the old behavior or document why it changed.
4. Add or update tests when behavior changes.
5. Add receipts, logs, or validation notes when a claim is made.
6. Keep the repo understandable to outside reviewers.
7. Prefer small, inspectable changes over huge mystery rewrites.

---

## Non-Negotiable Project Standards

### 1. Local-first by default

ARC-Neuron should remain useful without requiring a remote SaaS dependency.

Allowed:

- local Python scripts
- local datasets
- local benchmark receipts
- optional remote APIs for demos or adapters when clearly labeled
- optional server paths when the local path still exists

Avoid:

- making cloud access mandatory
- hiding core functionality behind remote services
- adding network calls without disclosure
- storing sensitive user data outside the local project without explicit design notes

### 2. Receipts over vibes

A feature is not “done” just because it sounds good in the README.

For each capability, prefer at least one of:

- test output
- benchmark record
- sample command
- example artifact
- validation report
- screenshot or diagram when relevant
- known limitation note

### 3. Math first, render second

The project should favor low-weight, deterministic systems before heavy presentation layers.

For UI, visualization, and ProtoSynth integration work:

- model the data first
- define the state transitions
- validate the output path
- then improve the visual layer

Do not make the UI imply capabilities that the backend cannot support.

### 4. Deterministic where possible

Prefer reproducible seeds, explicit configs, pinned assumptions, and stable paths.

When randomness is required:

- expose the seed
- log the seed
- make the run replayable when possible

### 5. Governance before promotion

Do not promote a model, dataset, benchmark, runtime route, or system stage without evidence.

Promotion should include:

- what changed
- why it changed
- what passed
- what failed or remains unknown
- rollback path

### 6. No fake production claims

Use honest labels:

- scaffold
- prototype
- experimental
- validation pass
- release candidate
- production-ready

Only use “production-ready” when installation, tests, failure modes, docs, and expected user workflow are all covered.

---

## License and Roadmap Awareness

ARC-Neuron has an intentional open-review corridor before the protected 3.0 direction.

Working assumption:

```text
1.0+      public foundation / self-coded baseline / open review
2.0       development bridge / expanded systems / open-source review window
2.1-2.9   internal-progress corridor / no formal 2.9 release required
3.0       commercial base-model milestone / updated protective license direction
```

Do not write docs that imply the 3.0 commercial artifacts, future weights, or protected packaged systems are automatically covered by the same open terms as the 1.0 foundation.

Also do not erase the open-review path. The route to 3.0 should remain independently inspectable even if later commercial outputs become protected.

---

## Language Module Doctrine

The language module is not just a dataset booster.

Its purpose is to provide a structured lexical spine for ARC-Neuron using multilingual lineage, symbols, mathematics, orthography, transliteration, and meaning-family relationships.

When writing about this system, keep the distinction clear:

```text
Dataset scaling: more text -> more examples -> bigger model -> better imitation
ARC lexical direction: structured language truth -> compression -> symbol grounding -> higher intelligence density
```

Do not claim that lexical configuration alone creates a finished frontier model. The accurate claim is that stronger lexical structure may improve output efficiency, interpretability, benchmark behavior, and low-weight reasoning per parameter.

Parameter count alone is not the benchmark. ARC-Neuron should be judged by:

- benchmark pass records
- lexical coverage
- local runtime viability
- output usefulness per parameter
- reproducibility
- governance receipts
- dataset quality
- rollback and auditability

---

## ProtoSynth Integration Standard

ProtoSynth is the visual/spatial cognition layer. ARC-Neuron is the model-building and cognition pipeline.

Correct relationship:

```text
ARC-Neuron LLMBuilder = builds and validates the cognition path
ProtoSynth = visualizes, navigates, and spatially projects that path
ARC Core = governs decisions and receipts
Arc-RAR / Omnibinary = preserve archives, source state, and binary lineage
Cleanroom Runtime = executes local model/runtime workflows safely
```

When adding ProtoSynth integration:

- do not turn visualization into proof by itself
- connect visuals to real files, benchmark records, model states, or receipts
- keep preview imagery labeled as visual roadmap or integration preview when not live-connected
- keep the system lightweight and inspectable

---

## Vibe Coding Rules

Vibe coding is allowed, but unverified chaos is not.

Before changing code:

1. Read the nearby files first.
2. Identify the exact behavior being changed.
3. Make the smallest useful edit.
4. Run the relevant test or command.
5. Update docs if the user-facing behavior changed.
6. Leave notes when something could not be tested.

Do not:

- rewrite entire files unnecessarily
- rename public commands without migration notes
- remove comments that explain safety or provenance
- delete tests to make a run pass
- fabricate benchmark results
- add dependencies without explaining why
- mix future roadmap claims into current capability lists

---

## Required Change Checklist

For every meaningful PR or assistant-generated patch, answer these before merge:

```text
Mission:
Files changed:
User-facing behavior changed:
Tests run:
Receipts updated:
Docs updated:
Known risks:
Rollback path:
```

If a change cannot be tested, write:

```text
Not tested: <reason>
Risk: <what could break>
Suggested validation: <command or manual check>
```

---

## Documentation Tone

The public tone should be strong but defensible.

Preferred wording:

- “designed to”
- “intended to”
- “validated by”
- “currently supports”
- “planned for”
- “experimental”
- “local-first”
- “open-review corridor”
- “commercial 3.0 direction”

Avoid unsupported wording:

- “guaranteed”
- “better than every model”
- “fully autonomous AGI”
- “military-grade” as a factual claim
- “production-ready” without receipts
- “solves language” without benchmark proof

Use “DARPA-style” or “high-assurance” as an engineering standard, not as an affiliation claim.

---

## Public Repo Flow

Keep the repo clean for reviewers:

- README = clear overview, quickstart, proof, ecosystem links
- ROADMAP = staged direction and version policy
- docs/ = deeper explanations and standards
- TEST_REPORT.md = validation status and commands
- SUPPORT.md = funding/support links, including Buy Me a Coffee
- CONTRIBUTING.md = contributor workflow and safety expectations
- .github/ = funding, templates, branch protection docs, CI

Do not bury critical claims only in screenshots or social posts. If it matters, it belongs in markdown with a reproducible path.

---

## Final Instruction to AI Assistants

Build like the next reviewer is skeptical, technical, and fair.

Make the project easier to verify. Make every claim easier to trace. Make every future version easier to compare against the past.

Speed is useful only when the evidence survives it.

**If all else fails - ##"Do What DARPA Would Do"##**
