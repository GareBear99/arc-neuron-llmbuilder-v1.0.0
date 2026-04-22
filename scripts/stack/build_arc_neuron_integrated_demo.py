#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
import time
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch

from arc_tiny.gguf_io import write_gguf
from arc_tiny.model import TinyConfig, TinyTransformerLM
from runtime.learning_spine import LearningEvent, build_arc_rar_bundle, mint_ancf_from_gguf, sha256_file, write_omnibinary_ledger


def collect_texts_from_repo(repo_root: Path, max_chars: int) -> list[str]:
    allowed = {".md", ".py", ".txt", ".yaml", ".yml", ".json", ".toml", ".sh", ".csv", ".rs", ".swift", ".cs", ".html"}
    chunks: list[str] = []
    total = 0
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        if any(part in path.parts for part in {".git", "__pycache__", "artifacts", "dist", "build"}):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not text.strip():
            continue
        chunk = f"\n\n# REPO_FILE: {path.relative_to(repo_root)}\n{text[:5000]}"
        chunks.append(chunk)
        total += len(chunk)
        if total >= max_chars:
            break
    return chunks


def collect_texts_from_zip(zip_path: Path, max_chars: int) -> list[str]:
    allowed = {".md", ".py", ".txt", ".yaml", ".yml", ".json", ".toml", ".sh", ".csv", ".rs", ".swift", ".cs", ".html"}
    chunks: list[str] = []
    total = 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in sorted(zf.infolist(), key=lambda i: i.filename):
            suffix = Path(info.filename).suffix.lower()
            if info.is_dir() or suffix not in allowed:
                continue
            try:
                text = zf.read(info.filename).decode("utf-8", errors="ignore")
            except Exception:
                continue
            if not text.strip():
                continue
            chunk = f"\n\n# ZIP_FILE: {zip_path.name}:{info.filename}\n{text[:5000]}"
            chunks.append(chunk)
            total += len(chunk)
            if total >= max_chars:
                break
    return chunks


def build_corpus(repo_root: Path, zip_inputs: list[Path], max_chars: int) -> tuple[bytes, list[dict[str, object]]]:
    sources: list[dict[str, object]] = []
    pieces = collect_texts_from_repo(repo_root, max_chars // 2)
    sources.append({"source": "repo", "pieces": len(pieces), "chars": sum(len(p) for p in pieces)})
    remaining = max(1, max_chars - sum(len(p) for p in pieces))
    for zip_path in zip_inputs:
        zip_pieces = collect_texts_from_zip(zip_path, max(20_000, remaining // max(1, len(zip_inputs))))
        pieces.extend(zip_pieces)
        sources.append({"source": zip_path.name, "pieces": len(zip_pieces), "chars": sum(len(p) for p in zip_pieces), "sha256": sha256_file(zip_path)})
    corpus = "\n".join(pieces)
    if not corpus:
        corpus = "ARC-Neuron integrated demo corpus."
    return corpus.encode("utf-8", errors="ignore")[:max_chars], sources


def get_batch(data: torch.Tensor, block_size: int, batch_size: int, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    ix = torch.randint(0, len(data) - block_size - 1, (batch_size,))
    x = torch.stack([data[i : i + block_size] for i in ix]).to(device)
    y = torch.stack([data[i + 1 : i + block_size + 1] for i in ix]).to(device)
    return x, y


def train_model(corpus: bytes, steps: int, batch_size: int, seed: int) -> tuple[TinyTransformerLM, TinyConfig, list[float], str]:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    data = torch.tensor(list(corpus), dtype=torch.long)
    torch.set_num_threads(1)
    config = TinyConfig(vocab_size=256, block_size=96, n_layer=2, n_head=4, n_embd=48)
    device = torch.device("cpu")
    model = TinyTransformerLM(config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3)
    losses: list[float] = []
    model.train()
    for _ in range(steps):
        x, y = get_batch(data, config.block_size, batch_size, device)
        _logits, loss = model(x, y)
        assert loss is not None
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.item()))
    model.eval()
    prompt = b"ARC-Neuron"
    prompt_ids = torch.tensor([list(prompt)], dtype=torch.long, device=device)
    out = model.generate(prompt_ids, max_new_tokens=40, temperature=0.85)[0].tolist()
    sample = bytes(out).decode("utf-8", errors="ignore")
    return model, config, losses, sample


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--zip-input", action="append", default=[])
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--max-chars", type=int, default=350_000)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    zip_inputs = [Path(z).resolve() for z in args.zip_input if Path(z).exists()]

    artifacts_gguf = repo_root / "artifacts" / "gguf"
    artifacts_ancf = repo_root / "artifacts" / "ancf"
    artifacts_obi = repo_root / "artifacts" / "omnibinary"
    artifacts_archives = repo_root / "artifacts" / "archives"
    report_dir = repo_root / "reports" / "arc_neuron_integrated"
    for p in [artifacts_gguf, artifacts_ancf, artifacts_obi, artifacts_archives, report_dir]:
        p.mkdir(parents=True, exist_ok=True)

    corpus, source_stats = build_corpus(repo_root, zip_inputs, args.max_chars)
    model, config, losses, sample_text = train_model(corpus, args.steps, args.batch_size, args.seed)

    state = {k: v.detach().cpu().numpy().astype(np.float32) for k, v in model.state_dict().items()}
    metadata = {
        "general.architecture": "arc_tiny",
        "general.alignment": 32,
        "general.name": "ARC-Neuron Tiny Integrated",
        "general.author": "OpenAI for Gary Doman",
        "general.version": "v0.2",
        "general.description": "Integrated ARC-Neuron tiny demo trained from cognition-core plus uploaded ARC stack source texts.",
        "general.license": "MIT",
        "general.basename": "ARC-Neuron-Tiny-Integrated",
        "general.size_label": "0.07M",
        "general.file_type": 0,
        "arc_tiny.block_size": config.block_size,
        "arc_tiny.vocab_size": config.vocab_size,
        "arc_tiny.n_layer": config.n_layer,
        "arc_tiny.n_head": config.n_head,
        "arc_tiny.n_embd": config.n_embd,
        "tokenizer.ggml.model": "byte",
        "tokenizer.ggml.pre": "byte-level",
        "tokenizer.ggml.tokens": [f"{i}" for i in range(256)],
        "arc_neuron.integration.omnibinary": True,
        "arc_neuron.integration.arc_rar": True,
        "arc_neuron.integration.cleanroom": True,
        "arc_neuron.integration.arc_core": True,
    }
    gguf_name = "ARC-Neuron-Tiny-Integrated-0.07M-v0.2-F32.gguf"
    gguf_path = artifacts_gguf / gguf_name
    pt_path = artifacts_gguf / "arc-neuron-tiny-integrated.pt"
    json_path = artifacts_gguf / "arc-neuron-tiny-integrated.json"
    write_gguf(gguf_path, metadata, state)
    torch.save({"config": config.__dict__, "state_dict": model.state_dict()}, pt_path)
    json_path.write_text(json.dumps({"metadata": metadata, "sample": sample_text, "sources": source_stats}, indent=2), encoding="utf-8")

    now = int(time.time())
    events = [
        LearningEvent(ts_utc=now, source="arc_language_module", event_type="lexicon_seed_attached", payload={"sources": [s for s in source_stats if "language" in str(s.get("source", "")).lower()]}),
        LearningEvent(ts_utc=now, source="omnibinary", event_type="binary_learning_store_created", payload={"target": "artifacts/omnibinary/arc-neuron-learning-ledger.obin"}),
        LearningEvent(ts_utc=now, source="arc_rar", event_type="rollback_bundle_created", payload={"target": "artifacts/archives/arc-neuron-integrated-demo.arcrar.zip"}),
        LearningEvent(ts_utc=now, source="arc_neuron", event_type="gguf_exported", payload={"gguf": gguf_name, "sha256": sha256_file(gguf_path)}),
    ]
    obi_path = artifacts_obi / "arc-neuron-learning-ledger.obin"
    obi_report = write_omnibinary_ledger(obi_path, events)

    ancf_meta = {
        "name": metadata["general.name"],
        "version": metadata["general.version"],
        "canonical_runtime_spine": ["ARC Core", "Cleanroom Runtime", "Omnibinary", "Arc-RAR"],
        "gguf_artifact": gguf_name,
        "gguf_sha256": sha256_file(gguf_path),
        "tokenizer_type": "byte",
        "parameter_count": int(sum(p.numel() for p in model.parameters())),
        "source_stats": source_stats,
    }
    ancf_path = artifacts_ancf / "ARC-Neuron-Tiny-Integrated-0.07M-v0.2.ancf"
    ancf_report = mint_ancf_from_gguf(ancf_path, gguf_path, ancf_meta)

    archive_manifest = {
        "format": "arc_rar_demo_bundle",
        "created_utc": now,
        "gguf": gguf_name,
        "ancf": ancf_path.name,
        "omnibinary_ledger": obi_path.name,
        "sample": sample_text,
        "source_stats": source_stats,
    }
    archive_path = artifacts_archives / "arc-neuron-integrated-demo.arcrar.zip"
    archive_report = build_arc_rar_bundle(archive_path, [gguf_path, ancf_path, obi_path, json_path], archive_manifest)

    modelcard = {
        "name": metadata["general.name"],
        "family": "ARC-Neuron",
        "tier": "Tiny Integrated",
        "artifact": gguf_name,
        "purpose": "Integrated end-to-end demo with Omnibinary learning ledger and Arc-RAR rollback/archive bundle.",
        "limits": [
            "Tiny research-scale model only",
            "Not a frontier pretrained checkpoint",
            "Demonstrates full local artifact and archive path rather than final flagship capability",
        ],
        "spine": ["ARC Core", "Cleanroom Runtime", "Omnibinary", "Arc-RAR", "ARC Language Module"],
    }
    modelcard_path = artifacts_gguf / "ARC-Neuron-Tiny-Integrated-0.07M-v0.2.modelcard.json"
    modelcard_path.write_text(json.dumps(modelcard, indent=2), encoding="utf-8")

    report = {
        "status": "ok",
        "seed": args.seed,
        "steps": args.steps,
        "batch_size": args.batch_size,
        "corpus_bytes": len(corpus),
        "source_stats": source_stats,
        "initial_loss": losses[0],
        "final_loss": losses[-1],
        "sample": sample_text,
        "gguf_path": str(gguf_path.relative_to(repo_root)),
        "ancf_path": str(ancf_path.relative_to(repo_root)),
        "omnibinary_ledger": str(obi_path.relative_to(repo_root)),
        "arc_rar_bundle": str(archive_path.relative_to(repo_root)),
        "parameter_count": int(sum(p.numel() for p in model.parameters())),
        "obi_report": obi_report,
        "ancf_report": ancf_report,
        "archive_report": archive_report,
    }
    (report_dir / "integrated_build_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
