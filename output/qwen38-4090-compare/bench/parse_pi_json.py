#!/usr/bin/env python3
"""Parse Pi 0.84 --mode json stream. Counts tool_execution_start (not tool_start)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def parse(path: str) -> dict:
    tools = 0
    by: Counter[str] = Counter()
    turns = 0
    last_usage: dict = {}
    events = 0
    verify_inside = False
    with open(path, errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            events += 1
            t = o.get("type") or ""
            if t == "tool_execution_start":
                tools += 1
                name = o.get("name") or o.get("toolName") or o.get("tool") or "?"
                by[str(name)] += 1
                args = json.dumps(o.get("arguments") or o.get("args") or {}, ensure_ascii=False)
                if "verify.sh" in args:
                    verify_inside = True
            if t == "turn_end":
                turns += 1
            u = o.get("usage")
            if isinstance(u, dict):
                last_usage = u
            if t == "message_end" and isinstance(o.get("message"), dict):
                u = o["message"].get("usage")
                if isinstance(u, dict):
                    last_usage = u
    return {
        "events": events,
        "tool_calls": tools,
        "tool_by_name": dict(by),
        "turns": turns,
        "verify_inside_pi": verify_inside,
        "usage": last_usage,
    }


if __name__ == "__main__":
    print(json.dumps(parse(sys.argv[1]), ensure_ascii=False))
