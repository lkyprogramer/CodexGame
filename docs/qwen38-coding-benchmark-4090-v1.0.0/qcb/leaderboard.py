from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

from .metrics import aggregate_results
from .statistics import holm_adjust, mcnemar_exact, paired_rows, stratified_paired_bootstrap
from .util import read_jsonl, utc_now


@dataclass(frozen=True)
class LeaderboardEntry:
    model_id: str
    source: str
    lane: str
    suite: str
    rows: list[dict[str, Any]]
    summary: dict[str, Any]

    @property
    def keys(self) -> set[tuple[str, int]]:
        return {(row["task"]["id"], int(row.get("seed", 0))) for row in self.rows}


def load_entries(result_files: list[str | Path]) -> list[LeaderboardEntry]:
    entries: list[LeaderboardEntry] = []
    seen: set[str] = set()
    for source in result_files:
        rows = read_jsonl(source)
        if not rows:
            raise ValueError(f"Empty result file: {source}")
        model_id = str(rows[0].get("model", {}).get("id", Path(source).stem))
        lane = str(rows[0].get("lane", "unknown"))
        suite = str(rows[0].get("suite", "unknown"))
        if model_id in seen:
            raise ValueError(f"Duplicate model id in leaderboard inputs: {model_id}")
        if any(str(row.get("lane")) != lane or str(row.get("suite")) != suite for row in rows):
            raise ValueError(f"Mixed lane or suite inside result file: {source}")
        seen.add(model_id)
        entries.append(
            LeaderboardEntry(
                model_id=model_id,
                source=str(Path(source)),
                lane=lane,
                suite=suite,
                rows=rows,
                summary=aggregate_results(rows),
            )
        )
    if not entries:
        raise ValueError("No result files")
    lanes = {entry.lane for entry in entries}
    suites = {entry.suite for entry in entries}
    if len(lanes) != 1 or len(suites) != 1:
        raise ValueError(f"Leaderboard inputs must share one lane and suite; lanes={sorted(lanes)}, suites={sorted(suites)}")
    return entries


def _quality_gates(entries: list[LeaderboardEntry]) -> dict[str, dict[str, Any]]:
    best_hard = max(float(entry.summary["hard_task_success_rate"]) for entry in entries)
    best_worst = max(float(entry.summary["worst_category_index"] or 0.0) for entry in entries)
    best_invalid = min(float(entry.summary["invalid_output_rate"]) for entry in entries)
    reference_keys = max((entry.keys for entry in entries), key=len)

    decisions: dict[str, dict[str, Any]] = {}
    for entry in entries:
        hard = float(entry.summary["hard_task_success_rate"])
        worst = float(entry.summary["worst_category_index"] or 0.0)
        invalid = float(entry.summary["invalid_output_rate"])
        complete = entry.keys == reference_keys
        checks = {
            "complete_pairing": complete,
            "hard_noninferiority": hard >= best_hard - 0.03,
            "worst_category_protection": worst >= best_worst - 0.08,
            "invalid_output_gate": invalid <= min(0.08, best_invalid + 0.03),
        }
        decisions[entry.model_id] = {
            "eligible": all(checks.values()),
            "checks": checks,
        }
    return decisions


def build_leaderboard(result_files: list[str | Path]) -> dict[str, Any]:
    entries = load_entries(result_files)
    gates = _quality_gates(entries)

    def rank_key(entry: LeaderboardEntry) -> tuple[Any, ...]:
        s = entry.summary
        success_time = s.get("median_success_wall_seconds")
        tokens = s.get("median_generated_tokens")
        return (
            0 if gates[entry.model_id]["eligible"] else 1,
            -float(s["category_balanced_index"] or 0.0),
            -float(s["hard_task_success_rate"]),
            -float(s["worst_category_index"] or 0.0),
            float(success_time) if success_time is not None else float("inf"),
            float(tokens) if tokens is not None else float("inf"),
            entry.model_id,
        )

    ordered = sorted(entries, key=rank_key)

    pairwise: list[dict[str, Any]] = []
    raw_p_values: dict[str, float] = {}
    for left, right in combinations(sorted(entries, key=lambda entry: entry.model_id), 2):
        complete = left.keys == right.keys
        item: dict[str, Any] = {
            "model_a": left.model_id,
            "model_b": right.model_id,
            "complete_pairing": complete,
            "paired_runs": 0,
            "hard_success_bootstrap": None,
            "mcnemar": None,
            "holm_adjusted_p": None,
        }
        if complete:
            pairs = paired_rows(left.rows, right.rows)
            bootstrap = stratified_paired_bootstrap(
                pairs,
                lambda row: 1.0 if row.get("verification", {}).get("passed") else 0.0,
                iterations=5000,
                seed=20260820 + len(pairwise),
            )
            mcnemar = mcnemar_exact(pairs)
            item.update({
                "paired_runs": len(pairs),
                "hard_success_bootstrap": bootstrap,
                "mcnemar": mcnemar,
            })
            key = f"{left.model_id}__vs__{right.model_id}"
            raw_p_values[key] = float(mcnemar["p_value_two_sided"])
            item["comparison_key"] = key
        pairwise.append(item)

    adjusted = holm_adjust(raw_p_values) if raw_p_values else {}
    for item in pairwise:
        key = item.get("comparison_key")
        if key:
            item["holm_adjusted_p"] = adjusted[key]

    return {
        "generated_at": utc_now(),
        "lane": ordered[0].lane,
        "suite": ordered[0].suite,
        "quality_gate": {
            "hard_success_margin": 0.03,
            "worst_category_margin": 0.08,
            "invalid_output_absolute_max": 0.08,
            "invalid_output_relative_margin": 0.03,
        },
        "models": [
            {
                "rank": index,
                "model_id": entry.model_id,
                "source": entry.source,
                "eligible": gates[entry.model_id]["eligible"],
                "gate_checks": gates[entry.model_id]["checks"],
                "summary": entry.summary,
            }
            for index, entry in enumerate(ordered, 1)
        ],
        "pairwise": pairwise,
    }


def render_leaderboard(data: dict[str, Any], output_md: str | Path) -> None:
    def fmt(value: Any, digits: int = 3) -> str:
        if value is None:
            return "N/A"
        if isinstance(value, float):
            return f"{value:.{digits}f}"
        return str(value)

    lines = [
        "# QCB-4090 多模型排行榜",
        "",
        f"- 赛道：`{data['lane']}`",
        f"- 测试集：`{data['suite']}`",
        f"- 生成时间：`{data['generated_at']}`",
        "",
        "> 排名先应用质量门槛，再按 Category Balanced Index、Hard Success、Worst Category、成功任务耗时和生成 Token 排序。Normalized 与 Optimized 赛道不得合榜。",
        "",
        "| 排名 | 模型 | 合格 | Hard Success | CBI | Worst Category | Invalid | 成功耗时(s) | 生成 Token |",
        "|---:|---|:---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in data["models"]:
        s = item["summary"]
        lines.append(
            f"| {item['rank']} | {item['model_id']} | {'是' if item['eligible'] else '否'} | "
            f"{fmt(s['hard_task_success_rate'])} | {fmt(s['category_balanced_index'])} | "
            f"{fmt(s['worst_category_index'])} | {fmt(s['invalid_output_rate'])} | "
            f"{fmt(s['median_success_wall_seconds'], 1)} | {fmt(s['median_generated_tokens'], 1)} |"
        )
    lines.extend([
        "",
        "## 质量门槛明细",
        "",
        "| 模型 | 完整配对 | Hard 非劣 | 最差类别保护 | 无效输出门槛 |",
        "|---|:---:|:---:|:---:|:---:|",
    ])
    for item in data["models"]:
        c = item["gate_checks"]
        lines.append(
            f"| {item['model_id']} | {'✓' if c['complete_pairing'] else '✗'} | "
            f"{'✓' if c['hard_noninferiority'] else '✗'} | "
            f"{'✓' if c['worst_category_protection'] else '✗'} | "
            f"{'✓' if c['invalid_output_gate'] else '✗'} |"
        )
    lines.extend([
        "",
        "## Pairwise 配对统计",
        "",
        "| A | B | 完整配对 | Runs | Hard B-A | 95% CI | McNemar p | Holm p |",
        "|---|---|:---:|---:|---:|---:|---:|---:|",
    ])
    for item in data.get("pairwise", []):
        bootstrap = item.get("hard_success_bootstrap") or {}
        mcnemar = item.get("mcnemar") or {}
        ci = (
            f"[{fmt(bootstrap.get('ci95_low'))}, {fmt(bootstrap.get('ci95_high'))}]"
            if bootstrap
            else "N/A"
        )
        lines.append(
            f"| {item['model_a']} | {item['model_b']} | {'是' if item['complete_pairing'] else '否'} | "
            f"{item['paired_runs']} | {fmt(bootstrap.get('observed_difference'))} | {ci} | "
            f"{fmt(mcnemar.get('p_value_two_sided'), 4)} | {fmt(item.get('holm_adjusted_p'), 4)} |"
        )
    lines.extend([
        "",
        "## 使用限制",
        "",
        "该榜只说明同一基准版本、相同 Lane、相同 Suite 和完整配对记录下的相对结果。效率只在质量门槛内参与排序；快速失败不会被当成性能优势。Pairwise p 值使用 Holm 校正，但仍必须结合效应量和置信区间解释。",
    ])
    Path(output_md).parent.mkdir(parents=True, exist_ok=True)
    Path(output_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
