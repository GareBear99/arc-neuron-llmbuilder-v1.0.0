#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import argparse
import json

from arc_tiny.gguf_io import read_gguf


def main() -> None:
    parser = argparse.ArgumentParser()
    default_gguf = REPO_ROOT / 'artifacts' / 'gguf' / 'ARC-Neuron-Tiny-0.05M-v0.1-F32.gguf'
    parser.add_argument('--gguf', default=str(default_gguf))
    args = parser.parse_args()

    metadata, tensors = read_gguf(args.gguf)
    summary = {
        'status': 'ok',
        'architecture': metadata.get('general.architecture'),
        'name': metadata.get('general.name'),
        'tensor_count': len(tensors),
        'alignment': metadata.get('general.alignment', 32),
        'sample_tensors': list(tensors.keys())[:8],
    }
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
