"""arc_neuron_small.model — ARC-Neuron Small preset.

This module is intentionally thin.  All architecture lives in
arc_core.transformer; only the default config values differ from Tiny.

Small tier: ~0.18M params, block_size=128, 3 layers, 4 heads, embd=64.
"""
from __future__ import annotations

from dataclasses import dataclass

from arc_core.transformer import CausalTransformerLM, TransformerConfig


@dataclass
class SmallConfig(TransformerConfig):
    """ARC-Neuron Small default hyperparameters."""
    vocab_size: int = 256
    block_size: int = 128
    n_layer: int = 3
    n_head: int = 4
    n_embd: int = 64
    dropout: float = 0.0


# Canonical alias expected by downstream scripts and tests.
SmallTransformerLM = CausalTransformerLM

__all__ = ["SmallConfig", "SmallTransformerLM", "CausalTransformerLM"]
