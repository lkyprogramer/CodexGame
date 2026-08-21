#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qcb.util import sha256_file


def manifest_files(root: Path) -> list[Path]:
    result = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.as_posix() == "MANIFEST.sha256":
            continue
        if "__pycache__" in relative.parts or path.suffix == ".pyc" or ".git" in relative.parts:
            continue
        result.append(path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate MANIFEST.sha256 for every release file")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    target = root / "MANIFEST.sha256"
    lines = [f"{sha256_file(path)}  {path.relative_to(root).as_posix()}" for path in manifest_files(root)]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{target}: {len(lines)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
