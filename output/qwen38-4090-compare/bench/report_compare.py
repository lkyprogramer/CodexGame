#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = Path(os.environ.get("RESULTS_ROOT", str(ROOT / "results")))


def loadj(p: Path, default):
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def pi_stats(backend: str) -> dict:
    p = RES / backend / "pi_cases.csv"
    rows = []
    if p.exists():
        with p.open() as f:
            rows = list(csv.DictReader(f))
    walls = []
    tools = []
    npass = 0
    for r in rows:
        ok = (
            r.get("pi_exit") == "0"
            and r.get("verify_exit") == "0"
            and r.get("protected_ok") == "true"
            and r.get("source_changed") == "true"
        )
        if ok:
            npass += 1
        if r.get("elapsed_s"):
            walls.append(float(r["elapsed_s"]))
        if r.get("tool_calls"):
            tools.append(float(r["tool_calls"]))
    s = sum(walls) if walls else None
    return {
        "java_pass": f"{npass}/{len(rows)}" if rows else "null",
        "java_n": len(rows),
        "java_ok": npass == 3 and len(rows) == 3,
        "elapsed_sum": s,
        "elapsed_p50": statistics.median(walls) if walls else None,
        "tasks_per_hour": round(3600.0 / s, 2) if s else None,
        "tool_calls_p50": statistics.median(tools) if tools else None,
        "cases": rows,
    }


def http_map(backend: str) -> dict:
    rows = loadj(RES / backend / "http_bench.json", [])
    return {r.get("tag"): r for r in rows}


def cache_map(backend: str) -> dict:
    rows = loadj(RES / backend / "cache_bench.json", [])
    return {r.get("tag"): r for r in rows}


def append_ok(cm: dict) -> bool | None:
    a, c = cm.get("cache-append") or {}, cm.get("cache-cold") or {}
    if not a:
        return None
    pt = a.get("prompt_tokens") or 0
    cached = a.get("cached_tokens") or 0
    if pt and cached and cached >= pt * 0.5:
        return True
    if c.get("ttft_s") and a.get("ttft_s") is not None:
        return a["ttft_s"] <= c["ttft_s"] * 0.5
    return False


def row(backend: str) -> dict:
    pi = pi_stats(backend)
    hm, cm = http_map(backend), cache_map(backend)
    deep, mid, short = hm.get("deep") or {}, hm.get("mid") or {}, hm.get("short") or {}
    append = cm.get("cache-append") or {}
    cold = cm.get("cache-cold") or {}
    meta = loadj(RES / backend / "meta.json", {})
    cap = (deep.get("prompt_tokens") or 0) >= 185000 and deep.get("ok") and deep.get("needle_ok")
    speed = (deep.get("decode_tps") or 0) >= 20 if deep else False
    return {
        "backend": backend,
        **meta,
        **{k: pi[k] for k in ("java_pass", "java_ok", "elapsed_p50", "tasks_per_hour", "tool_calls_p50")},
        "short_decode": (short.get("decode_tps") if short else None),
        "mid_decode": (mid.get("decode_tps") if mid else None),
        "deep_prompt": deep.get("prompt_tokens"),
        "deep_decode": deep.get("decode_tps"),
        "deep_ttft": deep.get("ttft_s"),
        "deep_needle": deep.get("needle_ok"),
        "capacity_gate": cap,
        "deep_speed_gate": speed,
        "append_ttft": append.get("ttft_s"),
        "append_cached": append.get("cached_tokens"),
        "cold_ttft": cold.get("ttft_s"),
        "append_cache_gate": append_ok(cm),
    }


def main() -> None:
    backends = [p.name for p in RES.iterdir() if p.is_dir() and (p / "pi_cases.csv").exists() or (p / "http_bench.json").exists()]
    backends = sorted({p.name for p in RES.iterdir() if p.is_dir()})
    rows = [row(b) for b in backends if b in ("work", "ninfer", "vllm")]
    (RES / "compare_rows.json").write_text(json.dumps(rows, indent=2) + "\n")
    lines = [
        "# WORK vs NInfer comparison",
        "",
        f"thinking={os.environ.get('THINKING', '?')}  RESULTS_ROOT={RES}",
        "",
        "| backend | java | tasks/h | p50 wall s | tools/task | 4k decode | 64k decode | 185k prompt | 185k decode | 185k TTFT | append TTFT | append cached | capacity | deep≥20 | append cache |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for r in rows:
        lines.append(
            "| {backend} | {java_pass} | {tasks_per_hour} | {elapsed_p50} | {tool_calls_p50} | {short_decode} | {mid_decode} | {deep_prompt} | {deep_decode} | {deep_ttft} | {append_ttft} | {append_cached} | {capacity_gate} | {deep_speed_gate} | {append_cache_gate} |".format(
                **{k: ("" if r.get(k) is None else r.get(k)) for k in r}
            )
        )
    (RES / "COMPARE.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(rows, indent=2))
    print("wrote", RES / "COMPARE.md")


if __name__ == "__main__":
    main()
