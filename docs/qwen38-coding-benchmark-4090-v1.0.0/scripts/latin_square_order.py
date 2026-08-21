#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json


def latin_square(items: list[str]) -> list[list[str]]:
    if len(items) < 2:
        raise ValueError("At least two model IDs are required")
    if len(items) != len(set(items)):
        raise ValueError("Model IDs must be unique")
    return [items[offset:] + items[:offset] for offset in range(len(items))]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate cyclic Latin-square run blocks")
    parser.add_argument("models", nargs="+")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    blocks = latin_square(args.models)
    if args.as_json:
        print(json.dumps({"models": args.models, "blocks": blocks}, ensure_ascii=False, indent=2))
    else:
        for index, block in enumerate(blocks, 1):
            print(f"Block {index:02d}: " + " -> ".join(block))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
