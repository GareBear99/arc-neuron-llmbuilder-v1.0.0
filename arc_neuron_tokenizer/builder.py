from __future__ import annotations

import json
import re
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Iterable

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_\-]{1,31}|[0-9]+|[^\w\s]", re.UNICODE)
SPECIAL_TOKENS = ["<pad>", "<bos>", "<eos>", "<unk>", "<sys>", "<usr>", "<asst>", "<receipt>", "<archive>", "<runtime>"]


def iter_texts(paths: Iterable[Path]) -> Iterable[str]:
    for path in paths:
        if not path.exists():
            continue
        if path.suffix == ".jsonl":
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    if isinstance(obj, dict):
                        for k in ("prompt", "target", "notes"):
                            val = obj.get(k)
                            if isinstance(val, str):
                                yield val
                        msgs = obj.get("messages")
                        if isinstance(msgs, list):
                            for msg in msgs:
                                if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                                    yield msg["content"]
                    else:
                        yield str(obj)
        else:
            yield path.read_text(encoding="utf-8", errors="ignore")


def build_tokenizer_growth_pack(repo_root: Path, vocab_target: int = 512) -> dict:
    dataset_paths = [
        repo_root / "datasets" / "arc_neuron_small" / "arc_neuron_small_sft.jsonl",
        repo_root / "datasets" / "arc_neuron_base" / "arc_neuron_base_sft.jsonl",
        repo_root / "datasets" / "runtime_mindshape" / "cleanroom_seed_records.jsonl",
        repo_root / "datasets" / "language_reasoning" / "language_module_seed_records.jsonl",
        repo_root / "datasets" / "system_of_record" / "arc_core_seed_records.jsonl",
        repo_root / "datasets" / "receipt_archive" / "arc_rar_seed_records.jsonl",
    ]
    out_dir = repo_root / "artifacts" / "tokenizer"
    report_dir = repo_root / "reports" / "arc_neuron_small_v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    counter: Counter[str] = Counter()
    byte_counter: Counter[int] = Counter()
    for text in iter_texts(dataset_paths):
        counter.update(TOKEN_RE.findall(text))
        byte_counter.update(text.encode("utf-8", errors="ignore"))

    vocab = list(SPECIAL_TOKENS)
    for i in range(256):
        vocab.append(f"<byte:{i}>")
    for tok, _ in counter.most_common(max(0, vocab_target - len(vocab))):
        if tok not in vocab:
            vocab.append(tok)
        if len(vocab) >= vocab_target:
            break

    tokenizer = {
        "name": "ARC-Neuron tokenizer growth pack",
        "version": "v0.2",
        "model": "hybrid_byte_wordpiece",
        "special_tokens": SPECIAL_TOKENS,
        "vocab": vocab,
        "stats": {
            "vocab_size": len(vocab),
            "unique_surface_candidates": len(counter),
            "top_surface_tokens": counter.most_common(50),
            "top_bytes": byte_counter.most_common(32),
        },
    }
    tok_path = out_dir / "arc_neuron_small_v0.2_tokenizer.json"
    tok_path.write_text(json.dumps(tokenizer, indent=2, ensure_ascii=False), encoding="utf-8")

    suggestions = {
        "status": "ok",
        "target_vocab_size": vocab_target,
        "top_growth_candidates": [tok for tok, _ in counter.most_common(128) if tok not in SPECIAL_TOKENS][:128],
        "receipt_domains": ["language", "runtime", "archive", "state", "tooling"],
        "sha256": sha256(tok_path.read_bytes()).hexdigest(),
    }
    sug_path = report_dir / "tokenizer_growth_manifest.json"
    sug_path.write_text(json.dumps(suggestions, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"tokenizer_path": tok_path, "manifest_path": sug_path, "vocab_size": len(vocab)}
