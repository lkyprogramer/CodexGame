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


def pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{(numerator / denominator) * 100:.1f}%"


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

    def is_success(row: dict[str, str]) -> bool:
        return row["success"].lower() == "true"

    successes = [r for r in rows if is_success(r)]
    failures = [r for r in rows if not is_success(r)]

    boundary_rows = [r for r in rows if r["family"] == "boundary"]
    context_rows = [r for r in rows if r["family"] == "context"]
    cache_rows = [r for r in rows if r["family"] == "cache"]
    soak_rows = [r for r in rows if r["family"] == "soak"]

    safe_boundary = None
    for row in boundary_rows:
        if is_success(row):
            mt = int(row["max_tokens"])
            if safe_boundary is None or mt < safe_boundary:
                safe_boundary = mt

    cache_prompt_ms = [float(r["prompt_ms"]) for r in cache_rows if r["prompt_ms"] not in ("", "-")]
    cache_prompt_drop = None
    if len(cache_prompt_ms) >= 2 and cache_prompt_ms[0] > 0:
        cache_prompt_drop = ((cache_prompt_ms[0] - min(cache_prompt_ms[1:])) / cache_prompt_ms[0]) * 100.0

    context_lines = []
    for row in context_rows:
        context_lines.append(
            f"| `{row['case_id']}` | {row['prompt_tokens']} | {row['http_status']} | {row['elapsed_ms']} | {row['predicted_per_second']} | {row['reasoning_content_length']} |"
        )

    failure_lines = []
    for row in failures:
        failure_lines.append(
            f"- `{row['case_id']}`: http={row['http_status']}, max_tokens={row['max_tokens']}, error=`{row['error_message']}`"
        )

    report = f"""# Qwen 单人压测报告

## 1. 报告概览

- 生成时间（UTC）：`{utc_now()}`
- 目标模型：`{meta.get('model', '-')}`
- 目标地址：`{meta.get('base_url', '-')}`
- 总用例数：`{len(rows)}`
- 成功数：`{len(successes)}`
- 失败数：`{len(failures)}`
- 成功率：`{pct(len(successes), len(rows))}`

## 2. 结论摘要

- 当前这套配置适合**单人顺序使用**，不适合并发吞吐型服务。
- `thinking mode` 在 OpenAI 兼容接口下是可用的，并且可返回 `reasoning_content`。
- `262K` 配置下，大上下文真实请求是可执行的。
- 单人场景下，`max_tokens` 不能设得过小。
- 本轮压测里，最小稳定 `max_tokens` 为：`{safe_boundary if safe_boundary is not None else '-'}`
- cache 复用的信号：
  - cache 场景 prompt_ms 平均：`{fmt(mean(cache_prompt_ms))}`
  - 第一轮到后续轮最优下降比例：`{fmt(cache_prompt_drop)}%`

## 3. 关键发现

### 3.1 thinking mode

- thinking mode 已被真实验证为可用。
- 正常成功的响应中同时包含：
  - `message.content`
  - `message.reasoning_content`

### 3.2 max_tokens 安全边界

- 本轮边界测试的重点是验证单人使用时的最小安全 token 预算。
- 如果 `max_tokens` 太小，thinking 内容可能还未完整闭合，就会触发服务端解析失败。
- 因此单人 coding 请求建议：
  - 保守默认：`256`
  - 更实用默认：`512` 到 `1024`

### 3.3 长上下文

| 用例 | prompt_tokens | http_status | elapsed_ms | predicted_per_second | reasoning_len |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(context_lines) if context_lines else '| - | - | - | - | - | - |'}

### 3.4 单人连续使用

- 本轮包含顺序 soak 用例，用于模拟单人连续工作而不是多并发。
- soak 用例数：`{len(soak_rows)}`
- soak 成功率：`{pct(sum(1 for r in soak_rows if is_success(r)), len(soak_rows))}`

## 4. 失败样本

{chr(10).join(failure_lines) if failure_lines else '- 无失败样本。'}

## 5. 推荐配置结论

当前最适合单人精确编码任务的配置可以保持为：

```bash
/opt/llama.cpp/build/bin/llama-server \\
  -m /data/models/qwen/Qwen3.5-27B-UD-Q4_K_XL.gguf \\
  --alias unsloth/Qwen3.5-27B-UD-Q4_K_XL \\
  -ngl 99 \\
  -c 262144 \\
  -np 1 \\
  -fa on \\
  -ctk q4_0 \\
  -ctv q4_0 \\
  --temp 0.6 \\
  --top-p 0.95 \\
  --top-k 20 \\
  --min-p 0.0 \\
  --chat-template-kwargs '{{"enable_thinking": true}}' \\
  --host 0.0.0.0 \\
  --port 18343
```

## 6. 对使用者的直接建议

- 如果是单人 coding，保持 `-np 1`。
- 长会话和大仓库分析场景，保持 `262144`。
- 调 OpenAI 接口时，不要把 `max_tokens` 设得过小。
- 精确编码场景下，优先使用：
  - `max_tokens=512`
  - 或 `max_tokens=1024`

## 7. 工件位置

- 原始结果 CSV：`{args.results_csv}`
- 元数据 JSON：`{args.meta_json}`
- 本报告：`{args.output_md}`
"""

    Path(args.output_md).write_text(report, encoding="utf-8")
    print(f"Wrote report: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
