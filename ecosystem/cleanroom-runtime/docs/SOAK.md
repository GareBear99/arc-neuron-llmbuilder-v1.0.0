# Soak Harness

The repository now includes a deterministic soak harness for repeatable runtime-stability receipts.

## Command

```bash
python scripts/soak.py --workspace . --iterations 10 --output artifacts/soak_receipt.json
```

## What it proves

This harness proves that the runtime can repeatedly:

- boot the local kernel and runtime
- execute bounded deterministic actions
- persist receipts and state growth
- emit a machine-readable summary for later comparison

## What it does not prove

This harness does **not** prove:

- real GGUF quality on a chosen model
- hardware-driver stability for robotics/BLE/video stacks
- multi-day uninterrupted autonomy on the final machine

Use it as a release-candidate gate and a baseline receipt generator, not as a substitute for real-world field validation.
