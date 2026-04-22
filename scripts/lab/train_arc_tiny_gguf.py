#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


import argparse
import json
import math
import random

import numpy as np
import torch

from arc_tiny.gguf_io import write_gguf
from arc_tiny.model import TinyConfig, TinyTransformerLM


def collect_corpus(repo_root: Path, max_chars: int = 220_000) -> bytes:
    allowed = {".md", ".py", ".txt", ".yaml", ".yml", ".json", ".toml", ".sh", ".csv"}
    chunks: list[str] = []
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        rel = path.relative_to(repo_root)
        rel_text = str(rel)
        if any(part in rel.parts for part in {".git", "__pycache__", "artifacts"}):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not text.strip():
            continue
        chunks.append(f"\n\n# FILE: {rel_text}\n{text[:5000]}")
        if sum(len(c) for c in chunks) >= max_chars:
            break
    corpus = "\n".join(chunks)
    if not corpus:
        corpus = "ARC cognition core tiny demo corpus."
    return corpus.encode("utf-8", errors="ignore")[:max_chars]


def get_batch(data: torch.Tensor, block_size: int, batch_size: int, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    ix = torch.randint(0, len(data) - block_size - 1, (batch_size,))
    x = torch.stack([data[i : i + block_size] for i in ix]).to(device)
    y = torch.stack([data[i + 1 : i + block_size + 1] for i in ix]).to(device)
    return x, y


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--outdir", default=None)
    parser.add_argument("--steps", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--seed", type=int, default=1337)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    repo_root = Path(args.repo_root).resolve()
    outdir = Path(args.outdir) if args.outdir else repo_root / "artifacts" / "gguf"
    report_dir = repo_root / "reports" / "arc_tiny_demo"
    outdir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    corpus = collect_corpus(repo_root)
    data = torch.tensor(list(corpus), dtype=torch.long)

    torch.set_num_threads(1)
    config = TinyConfig(vocab_size=256, block_size=64, n_layer=1, n_head=2, n_embd=32)
    device = torch.device("cpu")
    model = TinyTransformerLM(config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3)

    losses: list[float] = []
    model.train()
    for step in range(args.steps):
        x, y = get_batch(data, config.block_size, args.batch_size, device)
        _logits, loss = model(x, y)
        assert loss is not None
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.item()))

    model.eval()
    prompt = b"ARC cognition core"
    prompt_ids = torch.tensor([list(prompt)], dtype=torch.long, device=device)
    out = model.generate(prompt_ids, max_new_tokens=32, temperature=0.9)[0].tolist()
    sample_text = bytes(out).decode("utf-8", errors="ignore")

    state = {k: v.detach().cpu().numpy().astype(np.float32) for k, v in model.state_dict().items()}
    metadata = {
        "general.architecture": "arc_tiny",
        "general.alignment": 32,
        "general.name": "ARC Tiny Demo",
        "general.author": "OpenAI for Gary Doman",
        "general.version": "v1.0",
        "general.description": "Tiny byte-level autoregressive transformer exported as minimal GGUF subset for local demo inference.",
        "general.license": "MIT",
        "general.basename": "ARC-Tiny-Demo",
        "general.size_label": "0.05M",
        "general.file_type": 0,
        "arc_tiny.block_size": config.block_size,
        "arc_tiny.vocab_size": config.vocab_size,
        "arc_tiny.n_layer": config.n_layer,
        "arc_tiny.n_head": config.n_head,
        "arc_tiny.n_embd": config.n_embd,
        "tokenizer.ggml.model": "byte",
        "tokenizer.ggml.pre": "byte-level",
        "tokenizer.ggml.tokens": [f"{i}" for i in range(256)],
    }

    gguf_path = outdir / "ARC-Tiny-Demo-0.05M-v1.0-F32.gguf"
    pt_path = outdir / "arc-tiny-demo.pt"
    json_path = outdir / "arc-tiny-demo.json"
    write_gguf(gguf_path, metadata, state)
    torch.save({"config": config.__dict__, "state_dict": model.state_dict()}, pt_path)
    json_path.write_text(json.dumps({"metadata": metadata, "sample": sample_text}, indent=2), encoding="utf-8")

    report = {
        "status": "ok",
        "seed": args.seed,
        "steps": args.steps,
        "batch_size": args.batch_size,
        "repo_root": str(repo_root),
        "corpus_bytes": int(len(corpus)),
        "final_loss": losses[-1],
        "initial_loss": losses[0],
        "sample": sample_text,
        "gguf_path": str(gguf_path.relative_to(repo_root)),
        "pt_path": str(pt_path.relative_to(repo_root)),
        "json_path": str(json_path.relative_to(repo_root)),
        "parameter_count": int(sum(p.numel() for p in model.parameters())),
    }
    (report_dir / "training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()