#!/usr/bin/env python3
"""Assemble 2026-08-18 reports from remote raw/results after the run."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REMOTE = ROOT  # after rsync, raw/ and results/ live here
REPORTS = ROOT / "reports"
RESULTS = ROOT / "results"
RAW = ROOT / "raw"


def load(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(c) if c is not None else "" for c in row) + " |")
    return "\n".join(out)


def median(values: list[float]) -> str:
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return "n/a"
    return f"{statistics.median(nums):.2f}"


def write(name: str, body: str) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / name).write_text(body.rstrip() + "\n", encoding="utf-8")


def main() -> None:
    s2 = load(RESULTS / "s2-matrix.json") or load(RESULTS / "s2-partial.json") or []
    s1 = load(RESULTS / "s1.json") or {}
    s3 = load(RESULTS / "s3.json") or {}
    s3off = load(RESULTS / "s3-off.json") or {}
    s3b4 = None
    s3b32 = None
    for path in RESULTS.glob("s3*.json"):
        data = load(path) or {}
        if data.get("lane") == "s3_budget4096":
            s3b4 = data
        if data.get("lane") == "s3_budget32768":
            s3b32 = data
    s4 = load(RESULTS / "s4.json") or {}
    s4b = load(RESULTS / "s4-baseline.json") or {}
    s5 = load(RESULTS / "s5.json") or {}
    s5f = load(RESULTS / "s5-f16.json") or {}
    s6 = load(RESULTS / "s6.json") or {}

    s2_rows = []
    for item in s2:
        if "error" in item:
            s2_rows.append([item.get("lane"), "ERROR", item.get("error"), "", "", ""])
            continue
        speeds = {}
        accs = []
        quality = ""
        junk = 0
        for rec in item.get("results") or []:
            cid = rec.get("id") or ""
            if cid.startswith("speed_"):
                ntok = cid.split("_")[1]
                speeds.setdefault(ntok, []).append(rec.get("decode_tokens_per_s"))
                if rec.get("draft_acceptance_rate") is not None:
                    accs.append(rec["draft_acceptance_rate"])
            if rec.get("junk_repeat"):
                junk += 1
            if cid == "quality_topk":
                quality = f"{rec.get('task_pass')} ({rec.get('task_detail')})"
        s2_rows.append([
            item.get("lane"),
            median(speeds.get("256") or []),
            median(speeds.get("1024") or []),
            median(speeds.get("2048") or []),
            median(accs),
            quality,
            junk,
        ])
    write("s2-mtp-matrix.md", "\n".join([
        "# S2 MTP 矩阵（32K q8 KV，thinking off 测速）",
        "",
        md_table(["lane", "256 tok/s", "1024 tok/s", "2048 tok/s", "accept", "quality_topk", "junk"], s2_rows),
        "",
        "测速请求关闭 thinking，避免把思考税算进 MTP 深度对比。quality_topk 使用 medium thinking。",
    ]))

    def suite_rows(data: dict[str, Any]) -> list[list[Any]]:
        rows = []
        for rec in data.get("results") or []:
            rows.append([
                rec.get("id"),
                rec.get("task_pass"),
                rec.get("task_detail"),
                rec.get("elapsed_s"),
                rec.get("reasoning_tokens_approx"),
                rec.get("junk_repeat") or rec.get("empty_content"),
            ])
        return rows

    write("s1-protocol.md", "# S1 协议门禁\n\n" + md_table(
        ["case", "pass", "detail", "elapsed", "reason_tok", "bad"], suite_rows(s1)
    ))
    write("s3-reasoning.md", "# S3 Reasoning\n\n" + md_table(
        ["case", "pass", "detail", "elapsed", "reason_tok", "bad"],
        suite_rows(s3) + suite_rows(s3off) + suite_rows(s3b4 or {}) + suite_rows(s3b32 or {}),
    ))
    write("s4-work-quality.md", "# S4 工作质量\n\n## Qwen3.8\n\n" + md_table(
        ["case", "pass", "detail", "elapsed", "reason_tok", "bad"], suite_rows(s4)
    ) + "\n\n## Qwen3.6 baseline\n\n" + md_table(
        ["case", "pass", "detail", "elapsed", "reason_tok", "bad"], suite_rows(s4b)
    ))
    write("s5-long-context.md", "# S5 长上下文交叉事实\n\n" + md_table(
        ["case", "pass", "detail", "elapsed", "reason_tok", "bad"], suite_rows(s5) + suite_rows(s5f)
    ))
    write("s6-cache.md", "# S6 Prompt cache\n\n" + md_table(
        ["id", "phase", "prompt_ms", "cache_n", "prompt_tokens", "pass"],
        [[r.get("id"), r.get("phase"), r.get("prompt_ms"), r.get("cache_n"), r.get("prompt_tokens"), r.get("task_pass")]
         for r in (s6.get("results") or [])],
    ))

    def pass_rate(data: dict[str, Any], prefix: str | None = None) -> tuple[int, int]:
        recs = data.get("results") or []
        if prefix:
            recs = [r for r in recs if str(r.get("id") or r.get("base") or "").startswith(prefix) or str(r.get("base") or "").startswith(prefix)]
        total = len(recs)
        passed = sum(1 for r in recs if r.get("task_pass"))
        return passed, total

    s1p = pass_rate(s1)
    s4p = pass_rate(s4)
    safety = [r for r in (s4.get("results") or []) if str(r.get("id", "")).startswith("s4_safety")]
    safety_ok = all(r.get("task_pass") for r in safety) if safety else False
    junk_any = any(r.get("junk_repeat") for item in s2 if "results" in item for r in item["results"])
    n4 = next((item for item in s2 if item.get("lane") == "s2_mtp_n4_p0_ctx32"), None)
    n2 = next((item for item in s2 if item.get("lane") == "s2_mtp_n2_p0_ctx32"), None)

    if s1p[1] and s1p[0] == s1p[1] and s4p[1] and s4p[0] / s4p[1] >= 0.75 and safety_ok and not junk_any:
        decision = "灰度 work-balanced"
    elif s1p[0] >= max(1, s1p[1] - 2) and s4p[1] and s4p[0] / s4p[1] >= 0.5:
        decision = "仅旁路继续调"
    else:
        decision = "不上，保留 3.6"

    body = [
        "# 最终结论",
        "",
        f"**决策：{decision}**",
        "",
        f"- S1 协议：{s1p[0]}/{s1p[1]}",
        f"- S4 工作题：{s4p[0]}/{s4p[1]}",
        f"- 安全题全部通过：{safety_ok}",
        f"- S2 出现 junk：{junk_any}",
        f"- n=2 lane 存在：{bool(n2)}；n=4 lane 存在：{bool(n4)}",
        "",
        "细节见同目录 s1–s6 报告。",
    ]
    write("final-decision.md", "\n".join(body))
    print("wrote reports to", REPORTS)


if __name__ == "__main__":
    main()
