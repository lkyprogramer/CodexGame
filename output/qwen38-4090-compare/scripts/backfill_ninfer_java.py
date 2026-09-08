#!/usr/bin/env python3
"""Fill NInfer Agent columns from already-run pi.jsonl (no GPU)."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT.parent / "qwen38-27b-4090-ninfer" / "results" / "pi-java"
DST = ROOT / "results" / "ninfer"
DST.mkdir(parents=True, exist_ok=True)
parse = ROOT / "bench" / "parse_pi_json.py"

rows = []
old = SRC / "pi_cases.csv"
by = {}
if old.exists():
    with old.open() as f:
        for r in csv.DictReader(f):
            by[r["case"]] = r

for name in [
    "java-agent-1-idempotency",
    "java-agent-2-retry-contract",
    "java-agent-3-reconnect-loop",
]:
    js = SRC / name / "pi.jsonl"
    outd = DST / "pi" / name
    outd.mkdir(parents=True, exist_ok=True)
    met = json.loads(subprocess.check_output([sys.executable, str(parse), str(js)], text=True))
    (outd / "metrics.json").write_text(json.dumps(met, indent=2) + "\n")
    base = by.get(name, {})
    rows.append(
        {
            "case": name,
            "pi_exit": base.get("pi_exit", ""),
            "verify_exit": base.get("verify_exit", ""),
            "protected_ok": base.get("protected_ok", ""),
            "source_changed": base.get("source_changed", ""),
            "elapsed_s": base.get("elapsed_s", ""),
            "tool_calls": met.get("tool_calls", 0),
            "turns": met.get("turns", 0),
            "tool_by_name": json.dumps(met.get("tool_by_name") or {}, separators=(",", ":")),
            "verify_inside_pi": met.get("verify_inside_pi"),
        }
    )

fields = [
    "case",
    "pi_exit",
    "verify_exit",
    "protected_ok",
    "source_changed",
    "elapsed_s",
    "tool_calls",
    "turns",
    "tool_by_name",
    "verify_inside_pi",
]
with (DST / "pi_cases.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
print(json.dumps(rows, indent=2))
