"""arc_tiny.model — ARC-Neuron Tiny preset.

This module is intentionally thin.  All architecture lives in
arc_core.transformer; only the default config values differ here.

Tiny tier: ~0.05M params, block_size=64, 2 layers, 4 heads, embd=64.
"""
from __future__ import annotations

from dataclasses import dataclass

from arc_core.transformer import CausalTransformerLM, TransformerConfig


@dataclass
class TinyConfig(TransformerConfig):
    """ARC-Neuron Tiny default hyperparameters."""
    vocab_size: int = 256
    block_size: int = 64
    n_layer: int = 2
    n_head: int = 4
    n_embd: int = 64
    dropout: float = 0.0


# Canonical alias expected by downstream scripts and tests.
TinyTransformerLM = CausalTransformerLM

__all__ = ["TinyConfig", "TinyTransformerLM", "CausalTransformerLM"]
