#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qcb.leaderboard import build_leaderboard, render_leaderboard
from qcb.util import dump_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a quality-gated multi-model leaderboard")
    parser.add_argument("--input", action="append", required=True, help="One JSONL result file; repeat for each model")
    parser.add_argument("--output", required=True, help="Markdown output")
    parser.add_argument("--json", help="Optional machine-readable output")
    args = parser.parse_args()
    data = build_leaderboard(args.input)
    render_leaderboard(data, args.output)
    if args.json:
        dump_json(args.json, data)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
