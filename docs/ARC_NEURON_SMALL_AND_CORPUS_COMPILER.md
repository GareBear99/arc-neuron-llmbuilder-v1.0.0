# ARC-Neuron Small + Corpus Compiler v1

This package promotes the ARC stack from Tiny-only proof into the first native-growth milestone:

- unified corpus compiler across ARC stack source packages
- ARC-Neuron Small research model
- ANCF canonical wrapper
- GGUF deployment artifact
- Omnibinary learning ledger
- Arc-RAR release bundle

## Corpus compiler v1
The compiler pulls constrained text surfaces from the uploaded ARC stack packages:
- ARC Language Module
- ARC Cognition Core
- ARC Core
- Cleanroom Runtime
- Omnibinary Runtime
- Arc-RAR

Outputs:
- `datasets/arc_neuron_small/arc_neuron_small_sft.jsonl`
- `datasets/arc_neuron_small/arc_neuron_small_next_token.txt`
- `reports/arc_neuron_small/corpus_manifest.json`

## ARC-Neuron Small
The model is a byte-level decoder-only transformer research build with a larger configuration than ARC-Neuron Tiny:
- block size: 128
- layers: 3
- heads: 4
- embedding dim: 64

Artifacts:
- `artifacts/gguf/ARC-Neuron-Small-0.18M-v0.1-F32.gguf`
- `artifacts/ancf/ARC-Neuron-Small-0.18M-v0.1.ancf`
- `artifacts/omnibinary/arc-neuron-small-learning-ledger.obin`
- `artifacts/archives/arc-neuron-small-release.arcrar.zip`

## Operator flow
```bash
scripts/operator/build_arc_neuron_small.sh
```

## Boundary
This remains a native research model and not a frontier foundation model. The value of this step is to prove:
- unified corpus shaping
- native model growth inside ARC rules
- canonical ANCF + deploy GGUF pairing
- release receipts through Omnibinary and Arc-RAR
