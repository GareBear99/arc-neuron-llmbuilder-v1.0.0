# ARC-Neuron Base Prep

This package freezes the current ARC-Neuron Tiny integrated path as the regression floor and adds the first serious ARC-Neuron Base preparation bundle.

## What this prep adds
- A unified SFT corpus assembled from:
  - ARC Core
  - Cleanroom Runtime
  - Omnibinary Runtime
  - Arc-RAR
  - ARC Language Module
- Benchmark gate tasks for the first ARC-Neuron Base promotion pass.
- An Omnibinary learning ledger receipt for the corpus-seeding event.
- An Arc-RAR archive bundle containing the dataset, gate tasks, manifest, and ledger.

## Generated artifacts
- `datasets/arc_neuron_base/arc_neuron_base_sft.jsonl`
- `benchmarks/arc_neuron_base/gate_tasks.jsonl`
- `reports/arc_neuron_base_prep/prep_manifest.json`
- `reports/arc_neuron_base_prep/build_result.json`
- `artifacts/omnibinary/arc-neuron-base-prep-ledger.obin`
- `artifacts/archives/arc-neuron-base-prep.arcrar.zip`

## Current counts
- 136 SFT records
- 5 benchmark gate tasks
- language module grounding derived from the current module database snapshot

## Intent
This is the bridge from ARC-Neuron Tiny to ARC-Neuron Base.
It does not pretend to be the final high-capability checkpoint. It prepares the corpus, gates, and archival lineage so a stronger upstream checkpoint can be dropped into the production fine-tune/export path without architecture drift.

## Next action
Use this prep bundle with the production candidate chain once a stronger upstream base checkpoint is available.
