# 14 · 运行记录字段参考

每个 `(task, seed)` 生成一行 JSONL。该行是最终统计的唯一事实来源；Markdown 报告是可再生视图。

## 1. 身份与完整性

| 字段 | 含义 |
|---|---|
| `schema_version` | 记录 Schema 版本 |
| `benchmark.name/version` | 基准身份 |
| `benchmark.manifest_sha256` | 运行时基准清单文件哈希；未生成时为 null |
| `run_id` | 唯一运行 ID，也是 artifact 子目录名 |
| `started_at/completed_at` | UTC ISO 时间 |
| `suite/lane/seed` | 实验分组 |
| `config.source/sha256` | 实际 TOML 路径和哈希 |

## 2. 模型与端点

`model` 保存 Config ID、家族、GGUF 路径、SHA、Hash 校验状态、Quant、Template ID 和备注。

`endpoint` 保存 base URL、endpoint model、timeout 和本任务实际 endpoint retry 次数；API key 不落盘。

模型文件为空时可用于假端点/开发测试，但正式 4090 横评必须填写可访问 GGUF 路径和 64 位 SHA-256。

## 3. 推理参数

`inference` 保存：temperature、top_p、top_k、min_p、max_tokens、context_size、reasoning_effort、MTP 标记、tool mode、tool budget、system prompt 路径/哈希。

`context_size` 是实验声明；实际 server context 仍由启动参数控制。两者不一致属于实验配置错误。

## 4. 任务身份

`task` 保存：ID、标题、类别、语言、难度、权重、任务类型，以及 prompt/task.json 的 SHA-256。

## 5. Outcome 与验证

常见 `outcome`：

- `completed`：产生工作区 diff 或审查 JSON；不等于隐藏测试通过；
- `invalid_output`：没有可用 diff/JSON；
- `patch_failed`：统一 diff 无法应用；
- `tool_budget_exhausted`：试图超过工具预算；
- `endpoint_error`：请求/服务异常。

最终正确性以 `verification.passed` 和 `verification.score` 为准。Verifier stdout/stderr 截断保存在记录和 artifact。

## 6. Usage 与 Endpoint metrics

`usage` 来自 OpenAI-compatible 响应：prompt、completion、total、reasoning token。Endpoint 不返回 reasoning 时为 `null`，不是 0。

`endpoint_metrics` 尝试读取 llama.cpp 常见 timings 与 speculative 字段：

- prompt/decode tok/s；
- reported prompt/decode ms；
- drafted/accepted tokens；
- MTP acceptance。

Runner 使用非流式响应，因此 TTFT 固定为 `null` 并附说明。需要 TTFT 时从 server telemetry 采集。

## 7. Agent 指标

| 字段 | 含义 |
|---|---|
| `tool_calls` | 实际执行的工具调用数 |
| `invalid_tool_calls` | 工具名/参数/路径非法 |
| `failed_tool_operations` | 调用有效但操作失败，如公开测试非零、patch 不能应用 |
| `public_test_runs/failures` | 公开测试调用和失败次数 |
| `public_test_final_pass` | 最后一次公开测试结果 |
| `recovered_after_public_test_failure` | 曾失败且最终公开测试通过 |
| `patch_bytes` | 最终 git diff 字节数 |

## 8. GPU 与 Artifact

`gpu` 是 `nvidia-smi` 0.5 秒采样的摘要：Peak VRAM、平均利用率、峰值功耗和温度。无 NVIDIA 环境时 `available=false`。

`artifacts` 指向：

```text
final-response.txt
final.patch
raw-responses.json
tool-trace.json
verification.json
patch-apply.log       # 若适用
gpu-samples.json      # 若可用
answer.json           # Review 题
```

正式归档应保留整个 artifacts 目录，不能只保存汇总 JSONL。
