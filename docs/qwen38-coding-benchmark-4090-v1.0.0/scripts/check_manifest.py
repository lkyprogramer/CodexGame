#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qcb.util import sha256_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify MANIFEST.sha256 and detect missing/unexpected release files")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    manifest = root / "MANIFEST.sha256"
    if not manifest.is_file():
        print("MANIFEST.sha256 is missing", file=sys.stderr)
        return 1
    expected: dict[str, str] = {}
    errors: list[str] = []
    for line_no, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            digest, relative = line.split("  ", 1)
        except ValueError:
            errors.append(f"Malformed manifest line {line_no}")
            continue
        if relative in expected:
            errors.append(f"Duplicate manifest entry: {relative}")
        expected[relative] = digest

    for relative, digest in expected.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"Missing: {relative}")
        elif sha256_file(path) != digest:
            errors.append(f"Hash mismatch: {relative}")

    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.relative_to(root).as_posix() != "MANIFEST.sha256"
        and "__pycache__" not in path.relative_to(root).parts
        and path.suffix != ".pyc"
        and ".git" not in path.relative_to(root).parts
    }
    unexpected = sorted(actual - set(expected))
    errors.extend(f"Unexpected: {relative}" for relative in unexpected)

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"MANIFEST OK: {len(expected)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
