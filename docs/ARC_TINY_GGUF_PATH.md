# ARC Tiny GGUF Path

This repo now includes a minimal end-to-end local model path that can:
- train a tiny byte-level autoregressive transformer on repo text
- export the weights to a minimal GGUF v3 subset
- load that `.gguf` back with a pure NumPy runner
- generate text locally for proof-of-path validation

## Important boundary
This is a **tiny demo model** proving the container + training + load + run path. It is **not** a competitive flagship model and it is **not** a drop-in `llama.cpp` architecture.

## Files
- `scripts/lab/train_arc_tiny_gguf.py`
- `scripts/lab/run_arc_tiny_gguf.py`
- `arc_tiny/model.py`
- `arc_tiny/gguf_io.py`
- `artifacts/gguf/ARC-Tiny-Demo-0.05M-v1.0-F32.gguf`

## Train / export
```bash
python3 scripts/lab/train_arc_tiny_gguf.py
```

## Run
```bash
python3 scripts/lab/run_arc_tiny_gguf.py --gguf artifacts/gguf/ARC-Tiny-Demo-0.05M-v1.0-F32.gguf --tokens 16
```

## Why it exists
The uploaded ARC stack still does not include a serious pretrained checkpoint. This tiny path closes the honest gap by proving that the repo can:
1. produce a real `.gguf` file
2. read it back
3. run local autoregressive generation

The next serious step remains the same: plug in real pretrained weights and convert/export a supported high-capability model for the flagship runtime.
