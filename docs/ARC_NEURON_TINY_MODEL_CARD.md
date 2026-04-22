# ARC-Neuron Tiny 0.05M v0.1

## Identity
- Family: ARC-Neuron
- Tier: Tiny
- Parameters: ~0.05M
- Format: GGUF (minimal subset emitted by ARC Tiny export path)
- Precision: F32
- Architecture tag: `arc_tiny`

## Purpose
ARC-Neuron Tiny is the bootstrap model for the ARC-Neuron line. It exists to prove the complete local path:
- train
- export GGUF
- validate GGUF
- load GGUF
- generate locally

## Intended use
- regression baseline
- container-format validation
- runner smoke tests
- documentation of the ARC local model path

## Not intended for
- serious production use
- broad reasoning claims
- large-context coding work
- benchmarking against real general-purpose LLMs

## Artifact
- Primary artifact: `artifacts/gguf/ARC-Neuron-Tiny-0.05M-v0.1-F32.gguf`
- Legacy alias retained: `artifacts/gguf/ARC-Tiny-Demo-0.05M-v1.0-F32.gguf`

## Validation
```bash
python3 scripts/lab/validate_arc_tiny_gguf.py
python3 scripts/lab/run_arc_tiny_gguf.py --tokens 16
```

## Operational truth
ARC-Neuron Tiny is honest infrastructure proof, not a flagship intelligence claim.
