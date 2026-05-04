#!/usr/bin/env python3
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def fmt(value) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-csv", required=True)
    parser.add_argument("--meta-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    rows = load_csv(Path(args.results_csv))
    meta = json.loads(Path(args.meta_json).read_text(encoding="utf-8"))

    success_rows = [r for r in rows if r["success"].lower() == "true"]
    refusal_rows = [r for r in rows if r["refusal_detected"].lower() == "true"]
    json_ok_rows = [r for r in rows if r["json_parse_success"].lower() == "true"]

    family_map: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        family_map.setdefault(row["family"], []).append(row)

    task_lines = []
    for row in rows:
        task_lines.append(
            f"| `{row['case_id']}` | {row['family']} | {row['http_status']} | {row['finish_reason'] or '-'} | "
            f"{row['content_length']} | {row['refusal_detected']} | {row['json_parse_success']} | {row['predicted_per_second'] or '-'} |"
        )

    preview_lines = []
    for row in rows:
        preview_lines.append(f"- `{row['case_id']}`: {row['content_preview'] or row['error_message'] or '-'}")

    report = f"""# 35B Uncensored Chat 专项评测报告

## 1. 概览

- 生成时间（UTC）：`{utc_now()}`
- 目标模型：`{meta.get('model', '-')}`
- 目标地址：`{meta.get('base_url', '-')}`
- 总用例数：`{len(rows)}`
- HTTP 200 数：`{len(success_rows)}`
- refusal 检测数：`{len(refusal_rows)}`
- JSON 严格通过数：`{len(json_ok_rows)}`
- 平均响应时延（ms）：`{fmt(mean([float(r['elapsed_ms']) for r in rows]))}`
- 平均生成速度（tok/s）：`{fmt(mean([float(r['predicted_per_second']) for r in rows if r['predicted_per_second'] not in ('', '-')]))}`

## 2. 按任务统计

| 用例 | family | http | finish | content_len | refusal | json_ok | tok/s |
| --- | --- | ---: | --- | ---: | --- | --- | ---: |
{chr(10).join(task_lines)}

## 3. 家族分布

{chr(10).join([f"- `{family}`: {sum(1 for r in family_rows if r['success'].lower() == 'true')}/{len(family_rows)} HTTP 200" for family, family_rows in family_map.items()])}

## 4. 输出预览

{chr(10).join(preview_lines)}

## 5. 说明

- `refusal_detected` 只是基于输出关键字的粗粒度统计，不等同于严格安全分类。
- 这份报告偏向观察：直接性、风格完成度、格式服从和长上下文表现。
- 最终主观评价应结合 `uncensored_chat_bench_results.json` 的完整输出逐题阅读。
"""

    Path(args.output_md).write_text(report, encoding="utf-8")
    print(f"Wrote report: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
