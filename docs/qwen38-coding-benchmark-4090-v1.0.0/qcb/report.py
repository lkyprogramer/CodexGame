from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .metrics import CATEGORY_ORDER, aggregate_results
from .statistics import mcnemar_exact, paired_rows, stratified_paired_bootstrap
from .util import dump_json, percentile, read_jsonl, utc_now


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _pct(value: Any, digits: int = 1) -> str:
    if value is None:
        return "N/A"
    return f"{float(value) * 100:.{digits}f}%"


def _homogeneous(rows: list[dict[str, Any]], source: str | Path) -> tuple[str, str, str]:
    if not rows:
        raise ValueError(f"No rows in {source}")
    model = str(rows[0].get("model", {}).get("id", "unknown"))
    lane = str(rows[0].get("lane", "unknown"))
    suite = str(rows[0].get("suite", "unknown"))
    for row in rows:
        if str(row.get("model", {}).get("id")) != model:
            raise ValueError(f"Mixed model IDs in {source}")
        if str(row.get("lane")) != lane or str(row.get("suite")) != suite:
            raise ValueError(f"Mixed lane or suite in {source}")
    keys = [(str(row["task"]["id"]), int(row.get("seed", 0))) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"Duplicate task/seed pairs in {source}")
    return model, lane, suite


def _task_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row["task"]["id"])].append(row)
    result: list[dict[str, Any]] = []
    for task_id in sorted(groups):
        group = groups[task_id]
        passes = [1.0 if row.get("verification", {}).get("passed") else 0.0 for row in group]
        partial = [float(row.get("verification", {}).get("score", 0.0)) for row in group]
        times = [float(row.get("timing", {}).get("wall_seconds", 0.0)) for row in group]
        tokens = [
            float(row.get("usage", {}).get("completion_tokens"))
            for row in group
            if isinstance(row.get("usage", {}).get("completion_tokens"), (int, float))
        ]
        result.append(
            {
                "task_id": task_id,
                "title": group[0]["task"].get("title", ""),
                "category": group[0]["task"].get("category", ""),
                "runs": len(group),
                "pass_rate": sum(passes) / len(passes),
                "partial_rate": sum(partial) / len(partial),
                "median_wall_seconds": percentile(times, 0.5),
                "median_generated_tokens": percentile(tokens, 0.5),
                "outcomes": dict(Counter(str(row.get("outcome", "unknown")) for row in group)),
            }
        )
    return result


def generate_model_report(
    result_file: str | Path,
    output_md: str | Path,
    output_json: str | Path | None = None,
) -> dict[str, Any]:
    rows = read_jsonl(result_file)
    model_id, lane, suite = _homogeneous(rows, result_file)
    summary = aggregate_results(rows)
    first = rows[0]
    tasks = _task_summaries(rows)
    synthetic = any(bool(row.get("synthetic")) for row in rows)
    report = {
        "generated_at": utc_now(),
        "synthetic": synthetic,
        "benchmark": first.get("benchmark", {}),
        "model": first.get("model", {}),
        "endpoint": first.get("endpoint", {}),
        "inference": first.get("inference", {}),
        "lane": lane,
        "suite": suite,
        "summary": summary,
        "tasks": tasks,
    }

    model = report["model"]
    inference = report["inference"]
    lines = [f"# {model_id} — QCB-4090 测试报告", ""]
    if synthetic:
        lines.extend([
            "> **警告：这是合成数据，只用于验证报告管线，不代表任何真实模型性能。**",
            "",
        ])
    lines.extend(
        [
            "## 1. 实验身份",
            "",
            "| 项目 | 值 |",
            "|---|---|",
            f"| 基准版本 | `{report['benchmark'].get('version', 'unknown')}` |",
            f"| 模型 | `{model_id}` |",
            f"| 家族 | `{model.get('family', 'unknown')}` |",
            f"| 量化 | `{model.get('quantization', 'unknown')}` |",
            f"| Template | `{model.get('template_id', 'unknown')}` |",
            f"| 模型 SHA-256 | `{model.get('sha256', '') or 'N/A'}` |",
            f"| Hash 状态 | `{model.get('hash_status', 'unknown')}` |",
            f"| 赛道 | `{lane}` |",
            f"| Suite | `{suite}` |",
            f"| Context | `{inference.get('context_size', 'N/A')}` |",
            f"| Reasoning effort | `{inference.get('reasoning_effort', 'N/A')}` |",
            f"| MTP | `{inference.get('mtp_enabled', 'N/A')}` |",
            f"| Seeds | `{summary['seeds']}` |",
            "",
            "## 2. 数据完整性",
            "",
            "| 指标 | 结果 |",
            "|---|---:|",
            f"| 运行数 | {summary['runs']} |",
            f"| 唯一题目 | {summary['unique_tasks']} |",
            f"| 重复 task/seed | {summary['duplicate_task_seed_pairs']} |",
            f"| Reasoning Token 覆盖率 | {_pct(summary['reasoning_token_coverage_rate'])} |",
            f"| GPU 采样覆盖率 | {_pct(summary['gpu_coverage_rate'])} |",
            f"| Endpoint timing 覆盖率 | {_pct(summary['endpoint_timing_coverage_rate'])} |",
            f"| 基础设施错误率 | {_pct(summary['infrastructure_error_rate'])} |",
            "",
            "## 3. 质量结果",
            "",
            "| 指标 | 结果 |",
            "|---|---:|",
            f"| Hard Task Success Rate | {_pct(summary['hard_task_success_rate'])} |",
            f"| Partial Test Pass Rate | {_pct(summary['partial_test_pass_rate'])} |",
            f"| Category Balanced Index | {_pct(summary['category_balanced_index'])} |",
            f"| Worst Category Index | {_pct(summary['worst_category_index'])} |",
            f"| Invalid Output Rate | {_pct(summary['invalid_output_rate'])} |",
            f"| 不稳定题目率 | {_pct(summary['unstable_task_rate'])} |",
            "",
            "## 4. 六类能力矩阵",
            "",
            "| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for category in CATEGORY_ORDER:
        item = summary["categories"].get(category)
        if not item:
            continue
        lines.append(
            f"| {category} | {item['unique_tasks']} | {item['runs']} | {_pct(item['hard_success_rate'])} | "
            f"{_pct(item['partial_pass_rate'])} | {_pct(item['category_index'])} | "
            f"{_fmt(item['median_success_wall_seconds'], 1)} |"
        )

    lines.extend(
        [
            "",
            "## 5. 成功任务效率",
            "",
            "| 指标 | 结果 |",
            "|---|---:|",
            f"| 成功任务耗时中位数 | {_fmt(summary['median_success_wall_seconds'], 1)} s |",
            f"| 成功任务耗时 P90 | {_fmt(summary['p90_success_wall_seconds'], 1)} s |",
            f"| 成功任务生成 Token 中位数 | {_fmt(summary['median_success_generated_tokens'], 1)} |",
            f"| Reasoning Token 中位数 | {_fmt(summary['median_reasoning_tokens'], 1)} |",
            f"| 成功任务/Wall-hour | {_fmt(summary['successful_tasks_per_wall_hour'], 2)} |",
            f"| Prompt tok/s 中位数 | {_fmt(summary['median_prompt_tokens_per_second'], 1)} |",
            f"| Decode tok/s 中位数 | {_fmt(summary['median_decode_tokens_per_second'], 1)} |",
            f"| MTP acceptance | {_pct(summary['mtp_acceptance_rate'])} |",
            "",
            "## 6. Agent 与工具行为",
            "",
            "| 指标 | 结果 |",
            "|---|---:|",
            f"| Tool calls | {summary['tool_calls']} |",
            f"| Invalid tool calls | {summary['invalid_tool_calls']} |",
            f"| Valid tool-call rate | {_pct(summary['valid_tool_call_rate'])} |",
            f"| Tool operation success | {_pct(summary['tool_operation_success_rate'])} |",
            f"| Public test runs | {summary['public_test_runs']} |",
            f"| Public-test recovery candidates | {summary['public_test_recovery_candidates']} |",
            f"| Public-test recovery rate | {_pct(summary['public_test_recovery_rate'])} |",
            "",
            "## 7. RTX 4090 运行指标",
            "",
            "| 指标 | 结果 |",
            "|---|---:|",
            f"| Peak VRAM | {_fmt(summary['peak_vram_mb'], 0)} MB |",
            f"| Median average GPU utilization | {_fmt(summary['median_average_gpu_utilization_pct'], 1)}% |",
            f"| Peak power | {_fmt(summary['peak_power_w'], 1)} W |",
            f"| Peak temperature | {_fmt(summary['peak_temperature_c'], 1)} °C |",
            "",
            "## 8. 每题结果",
            "",
            "| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for item in tasks:
        lines.append(
            f"| {item['task_id']} | {item['category']} | {item['runs']} | {_pct(item['pass_rate'])} | "
            f"{_pct(item['partial_rate'])} | {_fmt(item['median_wall_seconds'], 1)} | "
            f"{_fmt(item['median_generated_tokens'], 1)} |"
        )

    lines.extend(
        [
            "",
            "## 9. 失败与输出状态",
            "",
            "| Outcome | 数量 |",
            "|---|---:|",
        ]
    )
    for name, count in sorted(summary["outcome_counts"].items()):
        lines.append(f"| `{name}` | {count} |")
    lines.extend(
        [
            "",
            "## 10. 解释约束",
            "",
            "- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。",
            "- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。",
            "- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。",
            "- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。",
        ]
    )

    Path(output_md).parent.mkdir(parents=True, exist_ok=True)
    Path(output_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    if output_json:
        dump_json(output_json, report)
    return report


def generate_comparison_report(
    a_file: str | Path,
    b_file: str | Path,
    output_md: str | Path,
    output_json: str | Path | None = None,
) -> dict[str, Any]:
    a = read_jsonl(a_file)
    b = read_jsonl(b_file)
    a_name, a_lane, a_suite = _homogeneous(a, a_file)
    b_name, b_lane, b_suite = _homogeneous(b, b_file)
    if a_lane != b_lane or a_suite != b_suite:
        raise ValueError(f"Cannot compare different lane/suite: A={a_lane}/{a_suite}, B={b_lane}/{b_suite}")
    a_keys = {(row["task"]["id"], int(row.get("seed", 0))) for row in a}
    b_keys = {(row["task"]["id"], int(row.get("seed", 0))) for row in b}
    if a_keys != b_keys:
        raise ValueError(
            f"Result files are not completely paired: only_a={len(a_keys-b_keys)}, only_b={len(b_keys-a_keys)}"
        )

    pairs = paired_rows(a, b)
    hard_bootstrap = stratified_paired_bootstrap(
        pairs,
        lambda row: 1.0 if row.get("verification", {}).get("passed") else 0.0,
        iterations=10000,
    )
    partial_bootstrap = stratified_paired_bootstrap(
        pairs,
        lambda row: float(row.get("verification", {}).get("score", 0.0)),
        iterations=10000,
        seed=20260821,
    )
    mcnemar = mcnemar_exact(pairs)
    a_summary = aggregate_results(a)
    b_summary = aggregate_results(b)

    category_rows: list[dict[str, Any]] = []
    for category in CATEGORY_ORDER:
        left = a_summary["categories"].get(category)
        right = b_summary["categories"].get(category)
        if not left or not right:
            continue
        category_rows.append(
            {
                "category": category,
                "a_index": left["category_index"],
                "b_index": right["category_index"],
                "difference": right["category_index"] - left["category_index"],
            }
        )

    decisions = {
        "hard_success_noninferior_by_3pp": hard_bootstrap["ci95_low"] >= -0.03,
        "worst_category_within_8pp": (b_summary["worst_category_index"] or 0.0) >= (a_summary["worst_category_index"] or 0.0) - 0.08,
        "invalid_output_acceptable": b_summary["invalid_output_rate"] <= min(0.08, a_summary["invalid_output_rate"] + 0.03),
        "cbi_improves_by_2pp": (b_summary["category_balanced_index"] or 0.0) >= (a_summary["category_balanced_index"] or 0.0) + 0.02,
    }
    decisions["eligible_to_claim_practical_win"] = all(decisions.values())

    report = {
        "generated_at": utc_now(),
        "lane": a_lane,
        "suite": a_suite,
        "model_a": a_name,
        "model_b": b_name,
        "paired_runs": len(pairs),
        "a_summary": a_summary,
        "b_summary": b_summary,
        "hard_success_bootstrap": hard_bootstrap,
        "partial_score_bootstrap": partial_bootstrap,
        "mcnemar": mcnemar,
        "categories": category_rows,
        "decision_checks": decisions,
    }

    lines = [
        f"# QCB-4090 模型对比：{a_name} vs {b_name}",
        "",
        f"- 赛道：`{a_lane}`",
        f"- Suite：`{a_suite}`",
        f"- 完整配对运行数：{len(pairs)}",
        "",
        "## 总体对比",
        "",
        "| 指标 | A | B | B-A |",
        "|---|---:|---:|---:|",
        f"| Hard Success | {_pct(a_summary['hard_task_success_rate'])} | {_pct(b_summary['hard_task_success_rate'])} | {_pct(b_summary['hard_task_success_rate']-a_summary['hard_task_success_rate'])} |",
        f"| Partial Pass | {_pct(a_summary['partial_test_pass_rate'])} | {_pct(b_summary['partial_test_pass_rate'])} | {_pct(b_summary['partial_test_pass_rate']-a_summary['partial_test_pass_rate'])} |",
        f"| Balanced Index | {_pct(a_summary['category_balanced_index'])} | {_pct(b_summary['category_balanced_index'])} | {_pct(b_summary['category_balanced_index']-a_summary['category_balanced_index'])} |",
        f"| Worst Category | {_pct(a_summary['worst_category_index'])} | {_pct(b_summary['worst_category_index'])} | {_pct((b_summary['worst_category_index'] or 0)-(a_summary['worst_category_index'] or 0))} |",
        f"| Invalid Output | {_pct(a_summary['invalid_output_rate'])} | {_pct(b_summary['invalid_output_rate'])} | {_pct(b_summary['invalid_output_rate']-a_summary['invalid_output_rate'])} |",
        f"| 成功耗时中位数(s) | {_fmt(a_summary['median_success_wall_seconds'],1)} | {_fmt(b_summary['median_success_wall_seconds'],1)} | {_fmt((b_summary['median_success_wall_seconds'] or 0)-(a_summary['median_success_wall_seconds'] or 0),1)} |",
        f"| 成功生成 Token 中位数 | {_fmt(a_summary['median_success_generated_tokens'],1)} | {_fmt(b_summary['median_success_generated_tokens'],1)} | {_fmt((b_summary['median_success_generated_tokens'] or 0)-(a_summary['median_success_generated_tokens'] or 0),1)} |",
        "",
        "## 六类差异",
        "",
        "| 分类 | A Index | B Index | B-A |",
        "|---|---:|---:|---:|",
    ]
    for item in category_rows:
        lines.append(
            f"| {item['category']} | {_pct(item['a_index'])} | {_pct(item['b_index'])} | {_pct(item['difference'])} |"
        )

    lines.extend(
        [
            "",
            "## 配对统计",
            "",
            f"- Hard Success 分层配对 Bootstrap 差值：{_pct(hard_bootstrap['observed_difference'])}",
            f"- Hard Success 95% CI：[{_pct(hard_bootstrap['ci95_low'])}, {_pct(hard_bootstrap['ci95_high'])}]",
            f"- P(B>A)：{_pct(hard_bootstrap['probability_positive'])}",
            f"- Partial Score 差值：{_pct(partial_bootstrap['observed_difference'])}，95% CI [{_pct(partial_bootstrap['ci95_low'])}, {_pct(partial_bootstrap['ci95_high'])}]",
            f"- McNemar：A-only={mcnemar['a_only_pass']}，B-only={mcnemar['b_only_pass']}，双侧精确 p={_fmt(mcnemar['p_value_two_sided'],4)}",
            "",
            "## 预声明决策门槛",
            "",
            "| 检查 | 通过 |",
            "|---|:---:|",
            f"| Hard Success 95% CI 下界 ≥ -3pp | {'是' if decisions['hard_success_noninferior_by_3pp'] else '否'} |",
            f"| Worst Category 回退 ≤ 8pp | {'是' if decisions['worst_category_within_8pp'] else '否'} |",
            f"| Invalid Output ≤ 8% 且相对 A 增幅 ≤ 3pp | {'是' if decisions['invalid_output_acceptable'] else '否'} |",
            f"| CBI 提升 ≥ 2pp | {'是' if decisions['cbi_improves_by_2pp'] else '否'} |",
            f"| 可声明 practical win | {'是' if decisions['eligible_to_claim_practical_win'] else '否'} |",
            "",
            "## 解释限制",
            "",
            "该判断只适用于当前基准版本、Lane、Suite、Seed、GGUF 与运行配置。统计显著性不能替代实际意义；效率提升也不能抵消质量门槛失败。",
        ]
    )
    Path(output_md).parent.mkdir(parents=True, exist_ok=True)
    Path(output_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    if output_json:
        dump_json(output_json, report)
    return report
