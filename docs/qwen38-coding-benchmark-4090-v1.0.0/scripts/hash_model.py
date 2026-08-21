#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qcb.util import sha256_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate a model file SHA-256")
    parser.add_argument("file")
    args = parser.parse_args()
    path = Path(args.file).resolve()
    if not path.is_file():
        parser.error(f"not a file: {path}")
    print(f"{sha256_file(path)}  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
