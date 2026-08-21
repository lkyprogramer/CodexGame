#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qcb.catalog import load_task


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic, visible-files-only context bundle for diagnostics")
    parser.add_argument("task_id")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    args = parser.parse_args()

    task = load_task(ROOT, args.task_id)
    chunks = [f"# Task {task.id}: {task.title}\n\n{task.prompt}\n", "\n# Visible repository files\n"]
    used = sum(len(x.encode("utf-8")) for x in chunks)
    for path in sorted(task.workspace_dir.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(task.workspace_dir)
        body = path.read_text(encoding="utf-8", errors="replace")
        chunk = f"\n## FILE: {relative}\n```\n{body}\n```\n"
        size = len(chunk.encode("utf-8"))
        if used + size > args.max_bytes:
            chunks.append(f"\n<!-- TRUNCATED before {relative}; max-bytes={args.max_bytes} -->\n")
            break
        chunks.append(chunk)
        used += size
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(chunks), encoding="utf-8")
    print(f"{target} ({used} bytes before marker)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
