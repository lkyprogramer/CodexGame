#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

RES = Path("/Users/luo/Documents/github/CodexGame/output/qwen38-4090-compare/results/rewrite")
OUT = Path("/Users/luo/Documents/github/CodexGame/output/qwen38-27b-4090-ninfer/reports/12-rewrite-checkpoint.md")


def load(p: Path):
    if not p.exists():
        return []
    return json.loads(p.read_text())


def row_line(r: dict) -> str:
    return (
        f"| {r.get('tag')} | {r.get('prompt_tokens')} | {r.get('reused_tokens')} | "
        f"{r.get('reuse_pct')} | {r.get('prefix_reuse_path')} | {r.get('ttft_s')} | "
        f"{r.get('draft_tokens')}/{r.get('accepted_draft_tokens')} | {r.get('cache_source')} |"
    )


def gate_b(rows: list[dict]) -> tuple[bool, list[str]]:
    notes = []
    ok = True
    by = {r.get("tag"): r for r in rows}

    def need(tag, pct, ttft=None):
        nonlocal ok
        r = next((x for x in rows if x.get("tag", "").endswith(tag)), None)
        if not r:
            notes.append(f"{tag}: missing")
            ok = False
            return
        if (r.get("reuse_pct") or 0) < pct:
            notes.append(f"{tag}: reuse {r.get('reuse_pct')} < {pct}")
            ok = False
        if ttft is not None and (r.get("ttft_s") or 99) > ttft:
            notes.append(f"{tag}: ttft {r.get('ttft_s')} > {ttft}")
            ok = False

    need("T1-append", 90, 5)
    need("T2-newest-user", 80)
    t3 = next((x for x in rows if str(x.get("tag","")).endswith("T3-recent-2")), None)
    if t3:
        if (t3.get("reuse_pct") or 0) < 70:
            notes.append(f"T3: reuse {t3.get('reuse_pct')} < 70 (TTFT {t3.get('ttft_s')})")
            # 5x TTFT vs A-T1 not computed here unless A row present
            ok = False
    else:
        notes.append("T3 missing")
        ok = False
    return ok, notes


def java_csv(p: Path):
    if not p.exists():
        return None
    lines = [ln.strip() for ln in p.read_text().splitlines() if ln.strip()]
    if len(lines) < 2:
        return {"n": 0, "pass": 0}
    rows = []
    for ln in lines[1:]:
        parts = ln.split(",")
        if len(parts) < 6:
            continue
        rows.append((parts[0], parts[1], parts[2], parts[5]))
    passed = sum(1 for r in rows if r[1] == "0" and r[2] == "0")
    return {"n": len(rows), "pass": passed, "raw": rows}


def main() -> None:
    a = load(RES / "phase_a.json")
    b = load(RES / "phase_b.json")
    http = load(RES / "ninfer-rk8" / "http_bench.json")
    if not http:
        http = load(RES / "rk8" / "http_bench.json")
    b_ok, notes = gate_b(b)
    lines = [
        "# OpenClaw rewrite / turn-checkpoints 8",
        "",
        "镜像 `44a2c6c`。A 无 ring，B `--turn-checkpoints 8`。测完应已 restore 现网。",
        "",
        "## A baseline",
        "",
        "| tag | prompt | reused | % | path | TTFT | draft acc | cache_source |",
        "|---|---:|---:|---:|---|---:|---|---|",
    ]
    for r in a:
        lines.append(row_line(r))
    lines += ["", "## B checkpoints=8", "",
              "| tag | prompt | reused | % | path | TTFT | draft acc | cache_source |",
              "|---|---:|---:|---:|---|---:|---|---|"]
    for r in b:
        lines.append(row_line(r))
    lines += ["", "## B gates", "", f"- **{'PASS' if b_ok else 'FAIL'}**: " + ("; ".join(notes) or "T1/T2/T3 ok")]
    if b_ok:
        lines.append("- **不必移植 auto-long-anchor**（本轮 T1–T3 过门）。")
    else:
        lines.append("- auto-long-anchor 仍是候选；本轮未写引擎代码。")
    soak = java_csv(RES / "soak" / "pi_cases.csv")
    rk8j = java_csv(RES / "ninfer-rk8" / "pi_cases.csv") or java_csv(RES / "rk8" / "pi_cases.csv")
    lines += ["", "## C soak Java", ""]
    if soak:
        lines.append(f"- {soak['pass']}/{soak['n']} pass; " + ", ".join(f"{n} {e}s" for n,_,_,e in soak.get("raw", [])))
    else:
        lines.append("- 无 soak csv")
    lines += ["", "## D rk8v4 200192", ""]
    if isinstance(http, list):
        by = {x.get("tag"): x for x in http if isinstance(x, dict)}
        deep = by.get("deep") or {}
        lines.append(
            f"- 184k decode={deep.get('decode_tps')} TTFT={deep.get('ttft_s')} needle={deep.get('needle_ok')}"
        )
    if rk8j:
        lines.append(f"- Java {rk8j['pass']}/{rk8j['n']}")
        if rk8j["pass"] != rk8j["n"]:
            lines.append("- **淘汰**：Java 非 3/3")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
