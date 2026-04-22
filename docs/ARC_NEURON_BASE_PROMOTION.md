# ARC-Neuron Base Promotion

This package freezes ARC-Neuron Tiny as the regression floor and adds the production-side contract for promoting **ARC-Neuron Base** from an external pretrained checkpoint.

## Goal
Produce a serious ARC-Neuron Base release with:
- external base checkpoint / merged checkpoint
- SFT corpus from `datasets/arc_neuron_base/arc_neuron_base_sft.jsonl`
- gate tasks from `benchmarks/arc_neuron_base/gate_tasks.jsonl`
- Omnibinary ledger receipt
- Arc-RAR archive bundle
- ANCF canonical artifact
- GGUF deployment artifact

## Required external inputs
- a supported upstream checkpoint directory
- a real trainer / merger / GGUF exporter configured in `configs/training/external_runtime.yaml`
- runtime binaries for local inference validation

## One-command operator path
```bash
cp configs/training/external_runtime.arc_neuron_base.example.yaml configs/training/external_runtime.yaml
# edit commands/paths
scripts/operator/promote_arc_neuron_base.sh /absolute/path/to/base-model-dir
```

## Outputs
The promotion script writes a timestamped run directory under `reports/arc_neuron_base_release/` and, on success, creates:
- `artifacts/gguf/ARC-Neuron-Base-*.gguf`
- `artifacts/ancf/ARC-Neuron-Base-*.ancf`
- `artifacts/omnibinary/arc-neuron-base-release-ledger.obin`
- `artifacts/archives/arc-neuron-base-release.arcrar.zip`

## Design rule
- **ANCF** is the canonical ARC artifact.
- **GGUF** is the deployment/export artifact.
- **Omnibinary** stores learning and release receipts in binary form.
- **Arc-RAR** stores rollback/release bundles.
