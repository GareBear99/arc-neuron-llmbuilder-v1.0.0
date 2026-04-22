# ARC-Neuron Small v0.2 Prep

This package closes the three highest-value gaps after ARC-Neuron Small v0.1:

1. Tokenizer growth pack
2. Cleanroom supervised export loop
3. Expanded benchmark gates

## What is emitted
- `artifacts/tokenizer/arc_neuron_small_v0.2_tokenizer.json`
- `reports/arc_neuron_small_v2/tokenizer_growth_manifest.json`
- `datasets/cleanroom_supervised/cleanroom_sft.jsonl`
- `datasets/cleanroom_supervised/cleanroom_preference.jsonl`
- `datasets/cleanroom_supervised/cleanroom_trace_receipts.jsonl`
- `benchmarks/arc_neuron_small_v2/gate_tasks.jsonl`
- `artifacts/ancf/ARC-Neuron-Small-Prep-v0.2.ancf`
- `artifacts/omnibinary/arc-neuron-small-v0.2-prep-ledger.obin`
- `artifacts/archives/arc-neuron-small-v0.2-prep.arcrar.zip`

## Why this matters
This stage does not pretend ARC-Neuron Small already uses the grown tokenizer inside deployed weights. It creates the governed inputs required for the next promotion.

## Next milestone
The next promotion after this prep pack is an ARC-Neuron Small v0.2 model rebuild using the tokenizer pack and cleanroom export lanes as first-class training inputs.
