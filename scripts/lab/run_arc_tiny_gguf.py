#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


import argparse
import json

import numpy as np

from arc_tiny.gguf_io import read_gguf


def layer_norm(x: np.ndarray, weight: np.ndarray, bias: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    mean = x.mean(axis=-1, keepdims=True)
    var = ((x - mean) ** 2).mean(axis=-1, keepdims=True)
    return ((x - mean) / np.sqrt(var + eps)) * weight + bias


def linear(x: np.ndarray, weight: np.ndarray, bias: np.ndarray | None = None) -> np.ndarray:
    y = x @ weight.T
    if bias is not None:
        y = y + bias
    return y


def gelu(x: np.ndarray) -> np.ndarray:
    return 0.5 * x * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (x + 0.044715 * np.power(x, 3))))


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)


def sample_from_probs(probs: np.ndarray, rng: np.random.Generator) -> int:
    probs = probs / probs.sum()
    return int(rng.choice(len(probs), p=probs))


def forward(tokens: list[int], metadata: dict[str, object], tensors: dict[str, np.ndarray]) -> np.ndarray:
    block_size = int(metadata["arc_tiny.block_size"])
    n_layer = int(metadata["arc_tiny.n_layer"])
    n_head = int(metadata["arc_tiny.n_head"])
    n_embd = int(metadata["arc_tiny.n_embd"])
    head_dim = n_embd // n_head

    idx = np.array(tokens[-block_size:], dtype=np.int64)
    t = idx.shape[0]
    x = tensors["token_emb.weight"][idx] + tensors["pos_emb.weight"][np.arange(t)]

    for layer in range(n_layer):
        prefix = f"blocks.{layer}."
        h = layer_norm(x, tensors[prefix + "ln1.weight"], tensors[prefix + "ln1.bias"])
        qkv = linear(h, tensors[prefix + "attn.qkv.weight"], tensors[prefix + "attn.qkv.bias"])
        q, k, v = np.split(qkv, 3, axis=-1)
        q = q.reshape(t, n_head, head_dim).transpose(1, 0, 2)
        k = k.reshape(t, n_head, head_dim).transpose(1, 0, 2)
        v = v.reshape(t, n_head, head_dim).transpose(1, 0, 2)
        scores = np.matmul(q, np.transpose(k, (0, 2, 1))) * (head_dim ** -0.5)
        causal = np.triu(np.ones((t, t), dtype=bool), k=1)
        scores[:, causal] = -1e9
        probs = softmax(scores, axis=-1)
        y = np.matmul(probs, v).transpose(1, 0, 2).reshape(t, n_embd)
        x = x + linear(y, tensors[prefix + "attn.proj.weight"], tensors[prefix + "attn.proj.bias"])

        h2 = layer_norm(x, tensors[prefix + "ln2.weight"], tensors[prefix + "ln2.bias"])
        mlp = linear(h2, tensors[prefix + "mlp.fc.weight"], tensors[prefix + "mlp.fc.bias"])
        mlp = gelu(mlp)
        mlp = linear(mlp, tensors[prefix + "mlp.proj.weight"], tensors[prefix + "mlp.proj.bias"])
        x = x + mlp

    x = layer_norm(x, tensors["ln_f.weight"], tensors["ln_f.bias"])
    logits = x[-1] @ tensors["head.weight"].T
    return logits.astype(np.float64)


def generate(gguf_path: Path, prompt: bytes, max_new_tokens: int, temperature: float, seed: int) -> str:
    metadata, tensors = read_gguf(gguf_path)
    rng = np.random.default_rng(seed)
    tokens = list(prompt)
    for _ in range(max_new_tokens):
        logits = forward(tokens, metadata, tensors)
        logits = logits / max(temperature, 1e-6)
        probs = softmax(logits)
        next_token = sample_from_probs(probs, rng)
        tokens.append(next_token)
    return bytes(tokens).decode("utf-8", errors="ignore")


def main() -> None:
    parser = argparse.ArgumentParser()
    default_gguf = REPO_ROOT / "artifacts" / "gguf" / "ARC-Neuron-Tiny-0.05M-v0.1-F32.gguf"
    parser.add_argument("--gguf", default=str(default_gguf))
    parser.add_argument("--prompt", default="ARC cognition core")
    parser.add_argument("--tokens", type=int, default=32)
    parser.add_argument("--temperature", type=float, default=0.9)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    text = generate(Path(args.gguf), args.prompt.encode("utf-8"), args.tokens, args.temperature, args.seed)
    if args.json:
        print(json.dumps({"prompt": args.prompt, "completion": text}, indent=2))
    else:
        print(text)


if __name__ == "__main__":
    main()