# V2 支撑材料：`scripts/tqllm_eval.py`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: scripts/tqllm_eval.py -->
<!-- payload-sha256: 129015de77e705c6e3631c8e0921135c447eb6122f646c09acaabc96de8177f9 -->
<!-- payload-bytes: 1628 -->

<!-- payload-begin -->
````python
#!/usr/bin/env python3
"""Run local planning calculations. Does not connect to or change a server."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from tqllm_tools import estimate_budget, eligible_remote_chunks, summarize_rounds


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("budget", "rounds", "coverage"))
    parser.add_argument("input", type=Path, help="JSON object (budget/coverage) or array (rounds)")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        if args.mode == "budget":
            result = estimate_budget(data)
        elif args.mode == "rounds":
            result = summarize_rounds(data)
        else:
            ids = eligible_remote_chunks(data["total_tokens"], data["recent"], data.get("chunk_size", 16))
            result = {"scope": "CPU_COVERAGE_ORACLE", "eligible_chunks": len(ids),
                      "first": ids[0] if ids else None, "last": ids[-1] if ids else None}
        text = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
````
<!-- payload-end -->
