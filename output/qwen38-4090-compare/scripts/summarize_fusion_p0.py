#!/usr/bin/env python3
"""Build fusion P0 markdown from results/fusion/* json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUS = ROOT / "results" / "fusion"
OUT = Path(
    "/Users/luo/Documents/github/CodexGame/output/qwen38-27b-4090-ninfer/reports/08-fusion-p0.md"
)
BASELINE = {
    "n3_221k": {"short": 117, "mid": 98, "long": 102, "deep": 87.5, "deep_ttft": 96, "append_ttft": 3.5},
    "n4": {"deep": 94.1},
    "n5": {"deep": 76.4},
}


def load(p: Path):
    if not p.exists():
        return None
    return json.loads(p.read_text())


def http_row(d):
    if not d:
        return {}
    by = {x.get("tag"): x for x in d if isinstance(x, dict)}
    out = {}
    for tag in ("short", "mid", "long", "deep"):
        r = by.get(tag) or {}
        out[tag] = r
    return out


def cache_row(d):
    if not d:
        return {}
    return {x.get("tag"): x for x in d if isinstance(x, dict)}


def fmt(v, nd=1):
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "Y" if v else "N"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def java_summary(backend: Path):
    csv = backend / "pi_cases.csv"
    if not csv.exists():
        return None
    lines = [ln.strip() for ln in csv.read_text().splitlines() if ln.strip()]
    if len(lines) < 2:
        return {"n": 0, "pass": 0, "p50": None, "raw": []}
    rows = []
    for ln in lines[1:]:
        parts = ln.split(",")
        # name,pi_exit,verify_exit,protected,changed,elapsed,tools,turns
        if len(parts) < 6:
            continue
        rows.append(
            {
                "name": parts[0],
                "pi": parts[1],
                "verify": parts[2],
                "elapsed": int(parts[5]) if parts[5].isdigit() else None,
            }
        )
    elapsed = sorted(r["elapsed"] for r in rows if r["elapsed"] is not None)
    p50 = elapsed[len(elapsed) // 2] if elapsed else None
    passed = sum(1 for r in rows if r["pi"] == "0" and r["verify"] == "0")
    return {"n": len(rows), "pass": passed, "p50": p50, "raw": rows}


def main() -> None:
    dirs = sorted([p for p in FUS.iterdir() if p.is_dir()])
    lines = [
        "# Fusion P0 实测报告",
        "",
        "thinking=off。基线 n=3 / 221184 / rk4v4-e8：4k/64k/120k/184k decode **117 / 98 / 102 / 87.5** t/s。",
        "A1 已结论：默认 draft=3；n=5 有害。本档验证 A2 262k、A2b L3、A3 rk2v4-e8。",
        "",
        "## HTTP 阶梯",
        "",
        "| 档 | 4k t/s | 64k | 120k | 184k | 184k TTFT | 184k 针 | 4k 针 |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for d in dirs:
        http = http_row(load(d / "http_bench.json"))
        if not http:
            continue
        deep = http.get("deep") or {}
        short = http.get("short") or {}
        lines.append(
            "| `{name}` | {s} | {m} | {l} | {de} | {tt} | {dn} | {sn} |".format(
                name=d.name,
                s=fmt((http.get("short") or {}).get("decode_tps")),
                m=fmt((http.get("mid") or {}).get("decode_tps")),
                l=fmt((http.get("long") or {}).get("decode_tps")),
                de=fmt(deep.get("decode_tps")),
                tt=fmt(deep.get("ttft_s")),
                dn=fmt(deep.get("needle_ok")),
                sn=fmt(short.get("needle_ok")),
            )
        )
    lines += [
        "",
        "## cache-append",
        "",
        "| 档 | cold TTFT | exact TTFT | append TTFT | cold cached | exact cached |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for d in dirs:
        cache = cache_row(load(d / "cache_bench.json"))
        if not cache:
            continue
        c, e, a = cache.get("cache-cold") or {}, cache.get("cache-exact") or {}, cache.get("cache-append") or {}
        lines.append(
            "| `{name}` | {ct} | {et} | {at} | {cc} | {ec} |".format(
                name=d.name,
                ct=fmt(c.get("ttft_s")),
                et=fmt(e.get("ttft_s")),
                at=fmt(a.get("ttft_s")),
                cc=fmt(c.get("cached_tokens"), 0),
                ec=fmt(e.get("cached_tokens"), 0),
            )
        )
    lines += ["", "## Java 三题", ""]
    any_java = False
    for d in dirs:
        js = java_summary(d)
        if not js:
            continue
        any_java = True
        lines.append(
            f"- `{d.name}`: {js['pass']}/{js['n']} pass, p50={js['p50']}s; "
            + ", ".join(f"{r['name']} pi={r['pi']} v={r['verify']} {r['elapsed']}s" for r in js["raw"])
        )
    if not any_java:
        lines.append("（本轮无 Java 结果）")
    lines += [
        "",
        "## 对照与结论门槛",
        "",
        f"- 184k decode 不低于基线 87.5 的 95%（**{87.5 * 0.95:.1f}** t/s）才算 A2 速度过关。",
        "- 184k decode < 80 或针失败 → 该档作废。",
        "- A3 还要求 Java 3/3。",
        "- P1 cherry-pick（E8 bfi、draft-head MMA、auto-long-anchors）本轮不重建镜像。",
        "",
        "原始 JSON：`output/qwen38-4090-compare/results/fusion/`.",
        "",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
