#!/usr/bin/env python3
"""Estimate proposed Predictor parameters and full Teacher-label storage; not GPU peak."""
from __future__ import annotations
import argparse
import json
from typing import Any


def estimate(split: int, rank: int, tokens: int) -> dict[str, Any]:
    if split not in (32, 40, 48):
        raise ValueError('split must be 32, 40 or 48')
    if rank <= 0 or tokens < 0:
        raise ValueError('rank must be positive and tokens must be nonnegative')
    attention = (64 - split) // 4
    gdn = 3 * attention
    outputs = attention * 2048 + gdn * (10240 + 96) + 5120
    # One affine RMSNorm, one biased shared projection and independent biased heads.
    parameters = 5120 + 5120 * rank + rank + rank * outputs + outputs
    per_token = 2 * 5120 + 2 * 5120 + attention * 2 * 2048 + gdn * (2 * 10240 + 4 * 96)
    label_bytes = tokens * per_token
    return {
        'split_layer': split, 'rank': rank, 'labeled_tokens': tokens,
        'attention_layers': attention, 'gdn_layers': gdn,
        'head_output_channels': outputs, 'parameters': parameters,
        'bf16_weight_mib': round(parameters * 2 / 2**20, 3),
        'bytes_per_labeled_token': per_token, 'label_bytes': label_bytes,
        'label_gib': round(label_bytes / 2**30, 3),
        'excludes': ['anchor states', 'optimizer state', 'workspace', 'duplicate shards', 'metadata'],
        'measured': False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--split', type=int, choices=[32, 40, 48], default=48)
    p.add_argument('--rank', type=int, default=256)
    p.add_argument('--tokens', type=int, default=100000)
    a = p.parse_args()
    try:
        result = estimate(a.split, a.rank, a.tokens)
    except ValueError as e:
        p.error(str(e))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
