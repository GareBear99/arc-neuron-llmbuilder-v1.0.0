#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import random
import sys
import zipfile
from hashlib import sha256
from pathlib import Path
from typing import Iterable

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from arc_neuron_small.model import SmallConfig, SmallTransformerLM
from arc_tiny.gguf_io import write_gguf
from runtime.learning_spine import LearningEvent, build_arc_rar_bundle, mint_ancf_from_gguf, write_omnibinary_ledger


ALLOWED_SUFFIXES = {".md", ".py", ".txt", ".yaml", ".yml", ".json", ".toml", ".sh", ".csv", ".sql"}
UPLOADS = [
    "arc-language-module-replay-compaction.zip",
    "arc-cognition-core-arc-neuron-nextgen-contract-pack.zip",
    "ARC-Core-main (18).zip",
    "arc-lucifer-cleanroom-runtime-main (16).zip",
    "omnibinary-runtime-main (1).zip",
    "Arc-RAR-main (3).zip",
]


def iter_zip_text(zip_path: Path, limit_per_file: int = 8000) -> Iterable[tuple[str, str]]:
    with zipfile.ZipFile(zip_path) as zf:
        for name in sorted(zf.namelist()):
            if name.endswith("/"):
                continue
            suffix = Path(name).suffix.lower()
            if suffix not in ALLOWED_SUFFIXES:
                continue
            if any(part in name for part in ["__pycache__", "/artifacts/", "/dist/"]):
                continue
            try:
                raw = zf.read(name)
                text = raw.decode("utf-8", errors="ignore")
            except Exception:
                continue
            text = text.strip()
            if not text:
                continue
            yield name, text[:limit_per_file]


def compile_corpus(repo_root: Path) -> dict:
    dataset_dir = repo_root / "datasets" / "arc_neuron_small"
    report_dir = repo_root / "reports" / "arc_neuron_small"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    sft_path = dataset_dir / "arc_neuron_small_sft.jsonl"
    nt_path = dataset_dir / "arc_neuron_small_next_token.txt"
    manifest_path = report_dir / "corpus_manifest.json"

    records = []
    corpus_chunks = []
    source_counts: dict[str, int] = {}
    missing = []
    for filename in UPLOADS:
        zpath = repo_root.parent / filename
        if not zpath.exists():
            missing.append(filename)
            continue
        count = 0
        for name, text in iter_zip_text(zpath):
            source_key = zpath.name
            source_counts[source_key] = source_counts.get(source_key, 0) + 1
            count += 1
            prompt = f"Summarize the purpose of {name} inside {zpath.stem}."
            response = text[:1400]
            records.append({
                "messages": [
                    {"role": "system", "content": "You are ARC-Neuron Small, a governed local reasoning model inside the ARC stack."},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": response},
                ],
                "source_zip": zpath.name,
                "source_path": name,
            })
            corpus_chunks.append(f"\n\n# SOURCE ZIP: {zpath.name}\n# FILE: {name}\n{text}")
            if count >= 40:
                break
    if not records:
        records = [{"messages": [{"role": "system", "content": "ARC-Neuron Small fallback corpus."}, {"role": "user", "content": "What are you?"}, {"role": "assistant", "content": "A governed local ARC research model."}]}]
        corpus_chunks = ["ARC-Neuron Small fallback corpus."]

    with sft_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    corpus_text = "\n".join(corpus_chunks)[:500_000]
    nt_path.write_text(corpus_text, encoding="utf-8")
    manifest = {
        "status": "ok",
        "record_count": len(records),
        "source_counts": source_counts,
        "missing_uploads": missing,
        "sft_path": str(sft_path.relative_to(repo_root)),
        "next_token_path": str(nt_path.relative_to(repo_root)),
        "corpus_sha256": sha256(corpus_text.encode("utf-8")).hexdigest(),
        "bytes": len(corpus_text.encode("utf-8")),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"manifest": manifest, "sft_path": sft_path, "next_token_path": nt_path, "corpus_text": corpus_text}


def get_batch(data: torch.Tensor, block_size: int, batch_size: int, device: torch.device):
    ix = torch.randint(0, len(data) - block_size - 1, (batch_size,))
    x = torch.stack([data[i : i + block_size] for i in ix]).to(device)
    y = torch.stack([data[i + 1 : i + block_size + 1] for i in ix]).to(device)
    return x, y


def train_and_export(repo_root: Path, corpus_text: str, steps: int = 140, seed: int = 1337) -> dict:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(1)

    outdir = repo_root / "artifacts" / "gguf"
    report_dir = repo_root / "reports" / "arc_neuron_small"
    outdir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    data = torch.tensor(list(corpus_text.encode("utf-8", errors="ignore")), dtype=torch.long)
    config = SmallConfig(vocab_size=256, block_size=128, n_layer=3, n_head=4, n_embd=64)
    model = SmallTransformerLM(config)
    device = torch.device("cpu")
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1.5e-3)

    losses = []
    model.train()
    for _ in range(steps):
        x, y = get_batch(data, config.block_size, 10, device)
        _, loss = model(x, y)
        assert loss is not None
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.item()))

    model.eval()
    prompt = b"ARC-Neuron language spine"
    prompt_ids = torch.tensor([list(prompt)], dtype=torch.long, device=device)
    out = model.generate(prompt_ids, max_new_tokens=48, temperature=0.85)[0].tolist()
    sample_text = bytes(out).decode("utf-8", errors="ignore")

    state = {k: v.detach().cpu().numpy().astype(np.float32) for k, v in model.state_dict().items()}
    metadata = {
        "general.architecture": "arc_neuron_small",
        "general.alignment": 32,
        "general.name": "ARC-Neuron Small",
        "general.author": "OpenAI for Gary Doman",
        "general.version": "v0.1",
        "general.description": "ARC-Neuron Small research build trained on unified ARC stack corpus compiler output.",
        "general.license": "MIT",
        "general.basename": "ARC-Neuron-Small",
        "general.size_label": "0.18M",
        "general.file_type": 0,
        "arc_neuron_small.block_size": config.block_size,
        "arc_neuron_small.vocab_size": config.vocab_size,
        "arc_neuron_small.n_layer": config.n_layer,
        "arc_neuron_small.n_head": config.n_head,
        "arc_neuron_small.n_embd": config.n_embd,
        "tokenizer.ggml.model": "byte",
        "tokenizer.ggml.pre": "byte-level",
        "tokenizer.ggml.tokens": [f"{i}" for i in range(256)],
    }

    gguf_path = outdir / "ARC-Neuron-Small-0.18M-v0.1-F32.gguf"
    pt_path = outdir / "arc-neuron-small.pt"
    json_path = outdir / "arc-neuron-small.json"
    write_gguf(gguf_path, metadata, state)
    torch.save({"config": config.__dict__, "state_dict": model.state_dict()}, pt_path)
    json_path.write_text(json.dumps({"metadata": metadata, "sample": sample_text}, indent=2), encoding="utf-8")

    ancf_dir = repo_root / "artifacts" / "ancf"
    arch_dir = repo_root / "artifacts" / "archives"
    omni_dir = repo_root / "artifacts" / "omnibinary"
    ancf_dir.mkdir(parents=True, exist_ok=True)
    arch_dir.mkdir(parents=True, exist_ok=True)
    omni_dir.mkdir(parents=True, exist_ok=True)
    ancf_path = ancf_dir / "ARC-Neuron-Small-0.18M-v0.1.ancf"
    ledger_path = omni_dir / "arc-neuron-small-learning-ledger.obin"
    archive_path = arch_dir / "arc-neuron-small-release.arcrar.zip"

    model_info = {
        "family": "ARC-Neuron",
        "artifact": gguf_path.name,
        "sample": sample_text,
        "parameter_count": int(sum(p.numel() for p in model.parameters())),
        "corpus_manifest": "reports/arc_neuron_small/corpus_manifest.json",
    }
    mint_ancf_from_gguf(ancf_path, gguf_path, model_info)
    events = [
        LearningEvent(ts_utc=int(__import__("time").time()), source="arc_neuron_small", event_type="corpus_compiled", payload={"records": len(corpus_text), "manifest": "reports/arc_neuron_small/corpus_manifest.json"}),
        LearningEvent(ts_utc=int(__import__("time").time()), source="arc_neuron_small", event_type="artifact_emitted", payload={"gguf": gguf_path.name, "ancf": ancf_path.name, "loss": losses[-1]}),
    ]
    write_omnibinary_ledger(ledger_path, events)
    build_arc_rar_bundle(
        archive_path,
        [gguf_path, ancf_path, ledger_path, json_path, repo_root / "reports" / "arc_neuron_small" / "corpus_manifest.json"],
        {"family": "ARC-Neuron", "artifact": gguf_path.name, "ancf": ancf_path.name, "ledger": ledger_path.name},
    )

    report = {
        "status": "ok",
        "steps": steps,
        "seed": seed,
        "final_loss": losses[-1],
        "initial_loss": losses[0],
        "sample": sample_text,
        "gguf_path": str(gguf_path.relative_to(repo_root)),
        "pt_path": str(pt_path.relative_to(repo_root)),
        "ancf_path": str(ancf_path.relative_to(repo_root)),
        "ledger_path": str(ledger_path.relative_to(repo_root)),
        "archive_path": str(archive_path.relative_to(repo_root)),
        "parameter_count": model_info["parameter_count"],
    }
    (report_dir / "small_training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    repo_root = REPO_ROOT
    compiled = compile_corpus(repo_root)
    report = train_and_export(repo_root, compiled["corpus_text"])
    final = {
        "status": "ok",
        "corpus": compiled["manifest"],
        "training": report,
    }
    out = repo_root / "reports" / "arc_neuron_small" / "build_result.json"
    out.write_text(json.dumps(final, indent=2), encoding="utf-8")
    print(json.dumps(final, indent=2))


if __name__ == "__main__":
    main()
