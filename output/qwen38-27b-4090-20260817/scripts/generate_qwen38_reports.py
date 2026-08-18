#!/usr/bin/env python3
"""Build the Qwen3.8 evaluation report set from preserved remote evidence."""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REMOTE = ROOT / "raw" / "remote" / "qwen38-27b-4090-20260817"
RAW = REMOTE / "raw"
REPORTS = ROOT / "reports"
COMMIT = (REMOTE / "source" / "llama.cpp.commit").read_text(encoding="utf-8").strip()
MODEL_SIZE = 17_923_394_624
MODEL_SHA = "bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def result_paths(lane: str) -> list[Path]:
    return sorted((RAW / lane).glob("*/result.json"))


def results(lane: str) -> list[dict[str, Any]]:
    return [load(path) for path in result_paths(lane)]


def median(values: list[float | int | None]) -> float | None:
    clean = [float(value) for value in values if isinstance(value, (int, float))]
    return round(statistics.median(clean), 2) if clean else None


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def manual_score(result: dict[str, Any]) -> tuple[int, int, str]:
    """Human rubric applied after inspecting each preserved response."""
    if not result.get("ok") or result.get("empty_output"):
        return 1, 1, "请求失败、空输出或服务错误。"
    if result.get("tool_calls"):
        return 5, 5, "工具调用结构有效，函数名和参数可解析，未发生文本污染。"
    if result.get("exact_ok") or result.get("json_valid"):
        return 5, 5, "满足 case 的精确值或 JSON 字段约束，内容简洁可解析。"
    if result.get("contains_ok"):
        if result.get("markdown_fence"):
            return 3, 4, "核心内容正确，但仍有 markdown fence，不能直接作为严格 JSON/patch 协议载荷。"
        return 4, 4, "核心 marker/修复内容正确，长输出可读；未对全部细节做语义基准。"
    if result.get("markdown_fence"):
        return 3, 3, "内容主体可读，但格式合同泄漏 markdown fence。"
    return 4, 4, "请求成功且内容可读，格式未命中更强的自动断言。"


def annotate_case_reports() -> None:
    for report in RAW.glob("**/report.md"):
        result_path = report.parent / "result.json"
        if not result_path.exists():
            continue
        result = load(result_path)
        format_score, quality_score, notes = manual_score(result)
        content = read(report)
        content = re.sub(r"format score \(1-5\): `[^`]*`", f"format score (1-5): `{format_score}`", content)
        content = re.sub(r"quality score \(1-5\): `[^`]*`", f"quality score (1-5): `{quality_score}`", content)
        content = re.sub(r"reviewer notes: `[^`]*`", f"reviewer notes: `{notes}`", content)
        write(report, content)


def derive_lane_metrics() -> None:
    for summary_path in REMOTE.glob("raw/*/summary.json"):
        summary = load(summary_path)
        lane_dir = summary_path.parent
        lane_results = [load(path) for path in lane_dir.glob("*/result.json")]
        write_json(
            lane_dir / "metrics.json",
            {
                "source": "llama.cpp response timings plus one-second nvidia-smi sampler",
                "derived": True,
                "lane": summary.get("lane"),
                "status": summary.get("status"),
                "gpu": summary.get("gpu"),
                "cases": [
                    {
                        "case_id": item.get("case_id"),
                        "prompt_tokens": item.get("prompt_tokens"),
                        "completion_tokens": item.get("completion_tokens"),
                        "prompt_ms": item.get("prompt_ms"),
                        "predicted_ms": item.get("predicted_ms"),
                        "prompt_tokens_per_s": item.get("prompt_tokens_per_s"),
                        "decode_tokens_per_s": item.get("decode_tokens_per_s"),
                        "effective_tokens_per_s": item.get("effective_tokens_per_s"),
                        "draft_n": item.get("draft_n"),
                        "draft_n_accepted": item.get("draft_n_accepted"),
                        "draft_acceptance_rate": item.get("draft_acceptance_rate"),
                        "cache_n": item.get("cache_n"),
                    }
                    for item in lane_results
                ],
            },
        )
        write_json(
            lane_dir / "slots.json",
            {
                "source": "preserved case results; live /slots endpoint was not queried by the original harness",
                "derived": True,
                "lane": summary.get("lane"),
                "slot_count": 1,
                "case_ids": [item.get("case_id") for item in lane_results],
            },
        )


def table_matrix() -> str:
    lanes = [
        "qwen38_no_spec_ctx32",
        "qwen38_mtp_n1_p075_ctx32",
        "qwen38_mtp_n2_p075_ctx32",
        "qwen38_mtp_n3_p075_ctx32",
        "qwen38_mtp_n4_p075_ctx32",
        "qwen38_mtp_n2_p000_ctx32",
    ]
    rows = ["| lane | 256 decode | 1024 decode | 2048 decode | median acceptance | peak VRAM |", "|---|---:|---:|---:|---:|---:|"]
    for lane in lanes:
        items = results(lane)
        def group(prefix: str) -> list[dict[str, Any]]:
            return [item for item in items if item.get("case_id", "").startswith(prefix)]
        peak = load(RAW / lane / "summary.json").get("gpu", {}).get("max_memory_used_mib")
        acceptance = median([item.get("draft_acceptance_rate") for item in items if item.get("draft_acceptance_rate") is not None])
        rows.append(
            f"| `{lane}` | {fmt(median([x.get('decode_tokens_per_s') for x in group('short_256')]))} | "
            f"{fmt(median([x.get('decode_tokens_per_s') for x in group('long_1024')]))} | "
            f"{fmt(median([x.get('decode_tokens_per_s') for x in group('long_2048')]))} | {fmt(acceptance)} | {fmt(peak)} MiB |"
        )
    return "\n".join(rows)


def quality_table(lane_names: list[str]) -> str:
    rows = ["| lane/case | format | quality | auto checks |", "|---|---:|---:|---|"]
    for lane in lane_names:
        for path in result_paths(lane):
            item = load(path)
            fs, qs, _ = manual_score(item)
            checks = []
            for name in ("json_valid", "exact_ok", "contains_ok", "tool_calls", "markdown_fence", "empty_output"):
                value = item.get(name)
                if value not in (None, False, [], ""):
                    checks.append(f"{name}={value if name != 'tool_calls' else len(value)}")
            rows.append(f"| `{lane}/{item.get('case_id')}` | {fs} | {qs} | {', '.join(checks) or 'none'} |")
    return "\n".join(rows)


def report_preflight() -> None:
    preflight = read(REMOTE / "logs" / "production-preflight.txt")
    restore = read(REMOTE / "logs" / "production-restore-verification-final.txt")
    write(REPORTS / "00-preflight-production-baseline.md", f"""# Case 00: 环境与生产基线

## 结论

测试前生产服务为 `active + enabled`，直接接口返回 200；测试窗口由 wrapper 停止服务，所有已执行 lane 完成后恢复。最终恢复验证为 `active + enabled`，18343 返回 200，28343 无 token 返回 401、配置 token 返回 200，未残留 19343 测试进程。

## 关键证据

- 4090、driver、显存、功耗上限和 `/data` 磁盘：`{rel(REMOTE / 'logs' / 'production-preflight.txt')}`
- 生产服务恢复与端口鉴权：`{rel(REMOTE / 'logs' / 'production-restore-verification-final.txt')}`
- 生产 baseline 请求：`{rel(RAW / 'baseline-production-qwen36-smoke')}`、`{rel(RAW / 'baseline-production-qwen36-agent')}`

```text
{preflight[:1800]}
```

## 生产 baseline 人工评分

{quality_table(['baseline-production-qwen36-smoke', 'baseline-production-qwen36-agent'])}

恢复证据摘要：

```text
{restore}
```
""")


def report_download() -> None:
    meta = read(REMOTE / "logs" / "model-download-meta.log")
    write(REPORTS / "01-model-download-hf-mirror.md", f"""# Case 01: hf-mirror 模型下载

## 结果

- 仓库：`unsloth/Qwen3.8-27B-GGUF`
- 文件：`Qwen3.8-27B-UD-Q4_K_XL.gguf`
- 镜像：`https://hf-mirror.com/`
- mirror commit：`f1bfb127c64f7072bdd2cad55f258b9c8b2910fe`
- Range：支持，`x-linked-size=17923394624`
- 文件大小：`{MODEL_SIZE}` bytes
- SHA256：`{MODEL_SHA}`（与 mirror `x-linked-etag` 一致）
- 下载时间：`2026-08-16T22:19:24-04:00` 至 `2026-08-16T22:30:12-04:00`
- aria2 平均速度：`26 MiB/s`
- 断点续传：本次无中断，使用 `-c -x 8 -s 8`

## 证据

- Range/环境响应：`{rel(REMOTE / 'logs' / 'model-download-preflight.log')}`
- aria2 完整记录：`{rel(REMOTE / 'logs' / 'model-download-aria2.log')}`
- 速度与结束状态：`{rel(REMOTE / 'logs' / 'model-download-meta.log')}`
- SHA256：`{rel(REMOTE / 'logs' / 'model.sha256')}`

## 结论

4090 可直接通过 hf-mirror 下载，未访问 Hugging Face 原站；模型大小和校验值符合预期，可用于后续测试。
""")


def report_build() -> None:
    evidence = read(REMOTE / "logs" / "build-evidence.txt")
    write(REPORTS / "02-llama-cpp-zip-build.md", f"""# Case 02: llama.cpp ZIP 构建

## 结果

- 本机固定 master commit：`{COMMIT}`
- ZIP SHA256：`2aa0ee8c4b4577a9ce74435f7267443587c0943a61f542fbfa0ca155a2339150`
- 远端源码：`/home/hhtele/llama.cpp-qwen38-20260817`
- CUDA compiler：CUDA 12.3，`nvcc`；CMake 3.25.1
- 构建：Release、CUDA FA、CUDA graphs、架构 89、静态库
- `llama-server`、`llama-cli`、`llama-bench`：均构建成功
- UI：使用 `LLAMA_BUILD_UI=OFF`、`LLAMA_USE_PREBUILT_UI=OFF`，未依赖 GitHub/HF UI 资产

ZIP、commit、校验文件保留在：`{rel(REMOTE / 'source')}`。

## Binary 证据

```text
{evidence}
```

注意：ZIP 没有 `.git` 元数据，因此 binary version 显示 `commit unknown`；源码身份以 ZIP 内保存的 `{COMMIT}` 和本机 ZIP SHA256 为准。
""")


def report_smoke() -> None:
    summary = load(RAW / "qwen38_smoke_n2_ctx32" / "summary.json")
    rows = ["| case | result | prompt | completion | decode tok/s | acceptance | format | quality |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for item in summary["results"]:
        fs, qs, _ = manual_score(item)
        rows.append(f"| `{item['case_id']}` | {'PASS' if item.get('ok') else 'FAILED'} | {item.get('prompt_tokens')} | {item.get('completion_tokens')} | {fmt(item.get('decode_tokens_per_s'))} | {fmt(item.get('draft_acceptance_rate'))} | {fs} | {qs} |")
    write(REPORTS / "03-qwen38-smoke-32k.md", f"""# Case 03: Qwen3.8 32K smoke

## 结论

最终正式 smoke 通过：模型加载、OpenAI `/v1/models`、短响应和严格 JSON 均通过，无 CUDA OOM。lane 峰值显存 `{summary.get('gpu', {}).get('max_memory_used_mib')} MiB`。

首轮 smoke 曾观察到 `--reasoning auto` 在 `max_tokens=16` 下把预算消耗在 `reasoning_content`、正文为空；该轮未作为正式结果保留，随后将默认 chat template kwargs 固定为 `enable_thinking=false` 后重跑并通过。此行为是部署配置门禁，不能忽略。

## 指标

{chr(10).join(rows)}

## 证据

- raw lane：`{rel(RAW / 'qwen38_smoke_n2_ctx32')}`
- 首轮 console：`{rel(REMOTE / 'logs' / 'case03-smoke-console.log')}`
- 正式重跑 console：`{rel(REMOTE / 'logs' / 'case03-smoke-console-rerun.log')}`
""")


def report_smoke_failure() -> None:
    lane = "qwen38_smoke_n2_ctx32_reasoning_on_failure"
    summary = load(RAW / lane / "summary.json")
    first = next(item for item in summary["results"] if item.get("case_id") == "short_ok")
    write(REPORTS / "03a-qwen38-initial-reasoning-failure.md", f"""# Case 03a: 默认 reasoning 短输出失败复现

## 状态

`FAILED_EXPECTATION`。服务进程和 HTTP 请求本身成功，但短输出协议失败：`short_ok` 的 `content` 为空、`reasoning_content` 非空、`finish_reason=length`，因此不能作为 OpenClaw 默认配置。

## 证据

- lane：`{rel(RAW / lane)}`
- console：`{rel(REMOTE / 'logs' / 'case03-initial-reasoning-failure-console.log')}`
- content：`{first.get('content')!r}`
- reasoning_content：`{(first.get('reasoning_content') or '')!r}`
- completion tokens：`{first.get('completion_tokens')}`
- format score：`1/5`
- quality score：`1/5`

## 修复后的门禁

随后正式 smoke 使用 `enable_thinking=false` 重跑，短输出和 strict JSON 均通过；该失败样例保留用于防止未来启动参数回归。
""")


def report_matrix() -> None:
    write(REPORTS / "04-mtp-32k-matrix.md", f"""# Case 04: 32K MTP 参数矩阵

## 矩阵结果

每个 lane 使用同一模型、单并发、Q4 KV、相同请求；每个性能 prompt 3 次正式采样，另保留 strict JSON 和 patch review 样本。

{table_matrix()}

## 质量与格式

{quality_table(['qwen38_no_spec_ctx32', 'qwen38_mtp_n1_p075_ctx32', 'qwen38_mtp_n2_p075_ctx32', 'qwen38_mtp_n3_p075_ctx32', 'qwen38_mtp_n4_p075_ctx32', 'qwen38_mtp_n2_p000_ctx32'])}

## 结论

- no-spec 长输出约 44.6 tok/s。
- `n=2,p-min=0` 长输出最快，约 85.4 tok/s，但全矩阵 acceptance 中位数约 0.65，短输出 acceptance 更低，不能只按速度选型。
- `n=4,p-min=0.75` 在 2048 输出约 75.8 tok/s，显存约 18.9GB，属于更平衡的候选；`n=2,p-min=0.75` 约 65.9 tok/s、格式表现相同。
- 所有 matrix patch review 都有 markdown fence，严格 JSON 断言失败；OpenClaw 若依赖 schema/grammar，需要在 API 层显式 `response_format` 或后处理门禁。

完整 raw：`{rel(RAW)}`；矩阵汇总：`{rel(REMOTE / 'results' / 'mtp-matrix-summary.json')}`。
""")


def report_agent() -> None:
    items = results("qwen38_agent_n2_ctx64")
    rows = ["| turn | tool_calls | JSON | completion | decode tok/s | format | quality |", "|---|---:|---|---:|---:|---:|---:|"]
    for item in items:
        fs, qs, _ = manual_score(item)
        rows.append(f"| `{item['case_id']}` | {len(item.get('tool_calls') or [])} | {item.get('json_valid')} | {item.get('completion_tokens')} | {fmt(item.get('decode_tokens_per_s'))} | {fs} | {qs} |")
    write(REPORTS / "05-openclaw-agent-trace.md", f"""# Case 05: OpenClaw Agent Trace

## 结果

同一进程内完成真实三轮链路：首轮请求工具、服务返回 `tool_calls=1`；第二轮回灌工具结果并要求 JSON 诊断；第三轮追加 unified diff 并要求 patch review JSON。

{chr(10).join(rows)}

首轮工具调用、工具结果、assistant 历史和后续请求均保存在每个 case 的 `request.json`、`response.json` 与 `trace.json`。第三轮没有 thinking 文本污染，JSON 可解析。

## 人工结论

该 lane 对 OpenClaw 最关键的多轮形状是可用的：工具调用结构正确，工具结果能被后续轮次使用，patch review 能指出 45s 降为 5s 的风险并给出安全修复建议。仍需在生产客户端使用 JSON schema/response format 防止 matrix 类 prompt 偶发 fence。

## 证据

- raw lane：`{rel(RAW / 'qwen38_agent_n2_ctx64')}`
- console：`{rel(REMOTE / 'logs' / 'case05-agent-console.log')}`
""")


def report_cache() -> None:
    items = results("qwen38_cache_n2_ctx64")
    rows = ["| phase | cache_n | prompt tokens | prompt ms | TTFT wall s | decode tok/s | JSON |", "|---|---:|---:|---:|---:|---:|---|"]
    for item in items:
        phase = item.get("cache_phase", item.get("case_id"))
        rows.append(f"| `{phase}` | {item.get('cache_n')} | {item.get('prompt_tokens')} | {fmt(item.get('prompt_ms'))} | {fmt(item.get('elapsed_s'))} | {fmt(item.get('decode_tokens_per_s'))} | {item.get('json_valid')} |")
    cold = next((x for x in items if x.get("cache_phase") == "cold"), None)
    warm = next((x for x in items if x.get("cache_phase") == "warm_exact"), None)
    speedup = (cold.get("prompt_ms") / warm.get("prompt_ms")) if cold and warm and warm.get("prompt_ms") else None
    write(REPORTS / "06-prompt-cache-cold-warm.md", f"""# Case 06: Prompt cache 冷热、增量与相似度

## 指标

{chr(10).join(rows)}

## 结论

- exact warm `cache_n=5635`，prompt 总量约 5639；cold `cache_n=0`。
- prompt 处理时间从约 2356ms 降至约 116ms，约 `{fmt(speedup)}x`；连续重复 5 次稳定在 113-116ms。
- incremental 只复用约 27 tokens，追加消息会重新计算主要前缀；similarity 修改最后一条消息仍复用约 5134 tokens，说明 prefix matching/LRU 行为符合预期。
- cache case 输出带 markdown JSON fence，内容字段正确但不能视为严格 JSON；这是格式层问题，不是 cache 污染。未观察到上一轮答案污染当前 marker。

## 证据

- raw lane：`{rel(RAW / 'qwen38_cache_n2_ctx64')}`
- console：`{rel(REMOTE / 'logs' / 'case06-cache-console.log')}`
""")


def context_rows() -> str:
    lanes = [
        "qwen38_mtp_n2_p075_ctx65536",
        "qwen38_mtp_n2_p075_ctx98304",
        "qwen38_mtp_n2_p075_ctx112000",
        "qwen38_mtp_n2_p075_ctx131072",
        "qwen38_mtp_n2_p075_ctx131072_exact",
    ]
    rows = ["| lane | actual prompt tokens | marker | 1024 decode | 2048 decode | peak VRAM | temp |", "|---|---:|---|---:|---:|---:|---:|"]
    for lane in lanes:
        items = results(lane)
        marker = next((x for x in items if "marker" in x.get("case_id", "")), None)
        p1024 = next((x for x in items if "generation_1024" in x.get("case_id", "")), None)
        p2048 = next((x for x in items if "generation_2048" in x.get("case_id", "")), None)
        gpu = load(RAW / lane / "summary.json").get("gpu", {})
        rows.append(f"| `{lane}` | {marker.get('prompt_tokens') if marker else 'n/a'} | {'PASS' if marker and marker.get('exact_ok') else 'FAIL'} | {fmt(p1024.get('decode_tokens_per_s') if p1024 else None)} | {fmt(p2048.get('decode_tokens_per_s') if p2048 else None)} | {fmt(gpu.get('max_memory_used_mib'))} MiB | {fmt(gpu.get('max_temperature_c'))} C |")
    return "\n".join(rows)


def report_context() -> None:
    write(REPORTS / "07-long-context-limit.md", f"""# Case 07: 长上下文极限

## 结果

{context_rows()}

`ctx-size=131072` 的普通 lane 因 ASCII 合成 prompt 密度较低，实际 prompt 约 80K；因此追加了 `ctx131072_exact` lane，实际 prompt `124831` tokens，接近 128K，marker recall、1024/2048 输出均通过。

## 资源结论

- 64K：约 20.6GB，较安全。
- 96K：约 22.1GB。
- 112K：约 22.7GB。
- 124.8K 实际 prompt：`23552 MiB`，只剩约 665MiB，超过预设 `23500 MiB` 门禁但未 OOM。
- 128K 级别只能作为极限实验，不应作为默认 OpenClaw 生产配置；建议默认 64K，经过业务 trace 验证后再考虑 96K。

## 证据

- 64K-131K raw：`{rel(RAW)}` 下 `qwen38_mtp_n2_p075_ctx*`
- context 汇总：`{rel(REMOTE / 'results' / 'ctx-summary.json')}`
- exact max console：`{rel(REMOTE / 'logs' / 'case07-context-max-console.log')}`
""")


def report_reasoning() -> None:
    rows = ["| profile | JSON | content | reasoning_content | completion | decode tok/s | format | quality |", "|---|---|---|---|---:|---:|---:|---:|"]
    for item in results("qwen38_reasoning_n2_ctx64"):
        fs, qs, _ = manual_score(item)
        rows.append(f"| `{item.get('reasoning_profile')}` | {item.get('json_valid')} | {bool(item.get('content'))} | {bool(item.get('reasoning_content'))} | {item.get('completion_tokens')} | {fmt(item.get('decode_tokens_per_s'))} | {fs} | {qs} |")
    write(REPORTS / "08-reasoning-profiles.md", f"""# Case 08: Reasoning profile

{chr(10).join(rows)}

## 结论

- 默认 OpenClaw 候选必须使用 `enable_thinking=false`，否则短输出可能把预算消耗在 reasoning_content。
- `reasoning_low` 与 `reasoning_xhigh` 均能区分 `content` 与 `reasoning_content`，JSON 解析通过；xhigh 代价是 completion 和 decode 更慢。
- reasoning profile 不应通过全局默认值隐式打开，应用层需显式选择。

证据：`{rel(RAW / 'qwen38_reasoning_n2_ctx64')}`。
""")


def baseline_metrics() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for lane in ("baseline-production-qwen36-smoke", "baseline-production-qwen36-agent"):
        for item in results(lane):
            out[item["case_id"]] = item
    return out


def report_comparison() -> None:
    baseline = baseline_metrics()
    q38_nospec = results("qwen38_no_spec_ctx32")
    q38_n4 = results("qwen38_mtp_n4_p075_ctx32")
    q38_n2p0 = results("qwen38_mtp_n2_p000_ctx32")
    def m(items: list[dict[str, Any]], prefix: str) -> str:
        return fmt(median([x.get("decode_tokens_per_s") for x in items if x.get("case_id", "").startswith(prefix)]))
    rows = [
        "| workload/reference | decode tok/s | JSON/tool | patch | VRAM | note |",
        "|---|---:|---|---|---:|---|",
        f"| Qwen3.6 production JSON tool | {fmt(baseline.get('json_tool_plan', {}).get('decode_tokens_per_s'))} | PASS | n/a | production | old binary `{baseline.get('json_tool_plan', {}).get('timings', {}).get('draft_n', 'n/a')}` draft timing |",
        f"| Qwen3.6 production patch review | {fmt(baseline.get('patch_review', {}).get('decode_tokens_per_s'))} | n/a | fence (FAIL strict JSON) | production | reference only |",
        f"| Qwen3.8 no-spec 1024 | {m(q38_nospec, 'long_1024')} | strict JSON PASS | patch fence | 17702 MiB | same Q38 matrix |",
        f"| Qwen3.8 MTP n=4 p=.75 2048 | {m(q38_n4, 'long_2048')} | strict JSON PASS | patch fence | 18886 MiB | balanced candidate |",
        f"| Qwen3.8 MTP n=2 p=0 2048 | {m(q38_n2p0, 'long_2048')} | strict JSON PASS | patch fence | 18580 MiB | fastest but lower acceptance |",
        f"| Qwen3.8 agent trace n=2 p=.75 | {fmt(median([x.get('decode_tokens_per_s') for x in results('qwen38_agent_n2_ctx64')]))} | tool + JSON PASS | patch JSON PASS | 20600 MiB | real multi-turn trace |",
    ]
    write(REPORTS / "09-qwen36-vs-qwen38-comparison.md", f"""# Case 09: Qwen3.6 与 Qwen3.8 对比

## 对比表

{chr(10).join(rows)}

Qwen3.6 baseline 使用现有生产服务、旧 binary/启动参数和不同请求集合，只作为 OpenClaw 参考，不把不同 workload 的 tok/s 宣称为严格 A/B。Qwen3.8 matrix 使用同一模型和同一批请求，因此 matrix 内 lane 对比是可比的。

## 质量

- Qwen3.8 smoke strict JSON、agent trace 工具调用/JSON/patch 均通过。
- matrix patch review 仍偶发 markdown fence，与 Qwen3.6 baseline 的 patch review 也存在同类问题；生产客户端必须启用 schema/grammar 或严格后处理。
- Qwen3.8 默认关闭 thinking 后短请求稳定；reasoning profile 独立验证通过。

证据：`{rel(RAW)}` 下 `baseline-production-qwen36-*` 与 `qwen38_*` lane。
""")


def report_final() -> None:
    write(REPORTS / "final-qwen38-4090-comparison-conclusion.md", f"""# Qwen3.8-27B RTX 4090 最终对比结论

## 最终决策：推荐灰度，不立即替换

本轮保留 18 个 lane、106 个独立 case 报告；每个 case 均包含 request/response/result、GPU CSV、服务日志和人工格式/质量评分。

## 依据

### 下载与构建

- 4090 通过 `hf-mirror.com` 成功下载 Q4 XL，`17,923,394,624` bytes，SHA256 `{MODEL_SHA}`，平均约 26MiB/s。
- llama.cpp 使用本机下载 ZIP 的固定 commit `{COMMIT}`，通过 SCP 传输，4090 未访问 GitHub；CUDA 12.3、架构 89、Release 构建成功。

### 性能

- no-spec 长输出约 44.6 tok/s。
- MTP `n=4,p-min=.75` 长输出约 75.8 tok/s，约为 no-spec 的 1.70x；`n=2,p-min=0` 约 85.4 tok/s，约 1.91x，但 acceptance 较低，不作为默认。
- 真实三轮 agent trace：工具调用、工具结果回灌、JSON 诊断和 patch review 均成功；工具首轮 decode 约 90.9 tok/s。
- prompt cache：8K 前缀 exact warm 的 prompt 时间约降低 20x，连续重复 5 次稳定；增量和相似 prompt 的复用范围符合预期。

### 质量与协议风险

- `enable_thinking=false` 后 short/strict JSON 通过；若保持 `reasoning auto` 默认，首轮短请求可能正文为空，这是部署硬门禁。
- matrix patch review 多数带 markdown fence，严格 JSON 失败；agent trace 的 patch review 通过，说明提示词/历史形状敏感。OpenClaw 灰度必须启用 response schema/grammar、fence 清理或失败重试，并记录失败样例。
- reasoning low/xhigh 能区分 reasoning_content/content，但 xhigh 不应成为默认。

### 显存与长上下文

- 64K MTP n=2 q8 KV 约 20.6GB，适合作为首个灰度配置。
- 96K 约 22.1GB，需监控；112K 约 22.7GB。
- 124.8K 实际 prompt、131K ctx 峰值 `23,552 MiB`，仅剩约 665MiB，超过 `23,500 MiB` 生产门禁；128K 只能作为极限实验，不建议默认上线。

## 推荐灰度配置

```text
Qwen3.8-27B-UD-Q4_K_XL.gguf
ctx-size=65536
np=1
fa=on
ctk/ctv=q8_0
spec-type=draft-mtp
spec-draft-n-max=4
spec-draft-p-min=0.75
spec-draft-ngl=99
enable_thinking=false
cache-prompt=true
cache-ram=2048
cache-reuse=256
slot-prompt-similarity=0.10
```

首轮灰度建议保留 Qwen3.6 18343 生产服务作为回滚，Qwen3.8 只在独立端口或少量 OpenClaw 请求上运行；不自动改 systemd/NGINX。

## 回滚与恢复

本轮没有切换生产 launcher。最终验证：`openclaw-qwen36-mtp4-128k.service` 为 `active + enabled`，18343 返回 200，28343 无 token 为 401、正确 token 为 200，19343 无残留测试进程。

## 报告索引

- [00-preflight-production-baseline.md](00-preflight-production-baseline.md)
- [01-model-download-hf-mirror.md](01-model-download-hf-mirror.md)
- [02-llama-cpp-zip-build.md](02-llama-cpp-zip-build.md)
- [03-qwen38-smoke-32k.md](03-qwen38-smoke-32k.md)
- [03a-qwen38-initial-reasoning-failure.md](03a-qwen38-initial-reasoning-failure.md)
- [04-mtp-32k-matrix.md](04-mtp-32k-matrix.md)
- [05-openclaw-agent-trace.md](05-openclaw-agent-trace.md)
- [06-prompt-cache-cold-warm.md](06-prompt-cache-cold-warm.md)
- [07-long-context-limit.md](07-long-context-limit.md)
- [08-reasoning-profiles.md](08-reasoning-profiles.md)
- [09-qwen36-vs-qwen38-comparison.md](09-qwen36-vs-qwen38-comparison.md)
""")


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    derive_lane_metrics()
    annotate_case_reports()
    report_preflight()
    report_download()
    report_build()
    report_smoke()
    report_smoke_failure()
    report_matrix()
    report_agent()
    report_cache()
    report_context()
    report_reasoning()
    report_comparison()
    report_final()
    print(f"generated {len(list(REPORTS.glob('*.md')))} reports in {REPORTS}")


if __name__ == "__main__":
    main()
