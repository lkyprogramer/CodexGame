# v3-udq4xl-200k-q4-dflash2-q2 — QCB-4090 测试报告

## 1. 实验身份

| 项目 | 值 |
|---|---|
| 基准版本 | `1.0.0` |
| 模型 | `v3-udq4xl-200k-q4-dflash2-q2` |
| 家族 | `Qwen3.8-27B` |
| 量化 | `UD-Q4_K_XL-Dynamic-V3` |
| Template | `official-jinja-medium` |
| 模型 SHA-256 | `3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e` |
| Hash 状态 | `match` |
| 赛道 | `optimized` |
| Suite | `smoke` |
| Context | `200000` |
| Reasoning effort | `medium` |
| MTP | `False` |
| Seeds | `[42]` |

## 2. 数据完整性

| 指标 | 结果 |
|---|---:|
| 运行数 | 12 |
| 唯一题目 | 12 |
| 重复 task/seed | 0 |
| API reasoning_tokens 覆盖率 | 0.0% |
| thinking chars 覆盖率 | 100.0% |
| GPU 采样覆盖率 | 100.0% |
| Endpoint timing 覆盖率 | 100.0% |
| 基础设施错误率 | 0.0% |

## 3. 质量结果

| 指标 | 结果 |
|---|---:|
| Hard Task Success Rate | 50.0% |
| Partial Test Pass Rate | 65.3% |
| Category Balanced Index | 61.2% |
| Worst Category Index | 2.2% |
| Invalid Output Rate | 0.0% |
| 不稳定题目率 | 0.0% |

## 4. 六类能力矩阵

| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |
|---|---:|---:|---:|---:|---:|---:|
| single_file | 2 | 2 | 50.0% | 75.0% | 55.0% | 143.0 |
| bug_fix | 2 | 2 | 100.0% | 100.0% | 100.0% | 235.6 |
| repo_engineering | 3 | 3 | 0.0% | 11.1% | 2.2% | N/A |
| agent_tool | 2 | 2 | 100.0% | 100.0% | 100.0% | 121.9 |
| long_context | 1 | 1 | 100.0% | 100.0% | 100.0% | 296.4 |
| code_review | 2 | 2 | 0.0% | 50.0% | 10.0% | N/A |

## 5. 成功任务效率

| 指标 | 结果 |
|---|---:|
| 成功任务耗时中位数 | 150.9 s |
| 成功任务耗时 P90 | 335.3 s |
| 成功任务 end-to-end completion token 中位数 | 6709.5 |
| 失败任务 end-to-end completion token 中位数 | 10463.0 |
| API reasoning_tokens 中位数 | N/A |
| 成功任务 thinking chars 中位数 | 14765.0 |
| 失败任务 thinking chars 中位数 | 15105.5 |
| 全部任务 thinking chars 中位数 | 15105.5 |
| 可见回答 chars 中位数 | 2405.0 |
| 成功任务/Wall-hour | 7.47 |
| Prompt tok/s 中位数 | 242.7 |
| Decode tok/s 中位数 | 40.3 |
| MTP acceptance | 66.1% |

## 6. Agent 与工具行为

| 指标 | 结果 |
|---|---:|
| Tool calls | 199 |
| Invalid tool calls | 7 |
| Valid tool-call rate | 96.5% |
| Tool operation success | 52.6% |
| Public test runs | 3 |
| Public-test recovery candidates | 1 |
| Public-test recovery rate | 100.0% |

## 7. RTX 4090 运行指标

| 指标 | 结果 |
|---|---:|
| Peak VRAM | 22924 MB |
| Median average GPU utilization | 44.1% |
| Peak power | 428.5 W |
| Peak temperature | 81.0 °C |

## 8. 每题结果

| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |
|---|---|---:|---:|---:|---:|---:|
| AT001 | agent_tool | 1 | 100.0% | 100.0% | 85.1 | 3408.0 |
| AT002 | agent_tool | 1 | 100.0% | 100.0% | 158.8 | 7399.0 |
| BF001 | bug_fix | 1 | 100.0% | 100.0% | 374.1 | 19039.0 |
| BF004 | bug_fix | 1 | 100.0% | 100.0% | 97.0 | 5059.0 |
| CR001 | code_review | 1 | 0.0% | 40.0% | 47.0 | 3067.0 |
| CR002 | code_review | 1 | 0.0% | 60.0% | 39.5 | 2613.0 |
| LC001 | long_context | 1 | 100.0% | 100.0% | 296.4 | 13435.0 |
| RE001 | repo_engineering | 1 | 0.0% | 0.0% | 706.5 | 26381.0 |
| RE004 | repo_engineering | 1 | 0.0% | 33.3% | 308.0 | 12220.0 |
| RE007 | repo_engineering | 1 | 0.0% | 0.0% | 417.5 | 11569.0 |
| SF001 | single_file | 1 | 100.0% | 100.0% | 143.0 | 6020.0 |
| SF002 | single_file | 1 | 0.0% | 50.0% | 219.9 | 9357.0 |

## 9. 失败与输出状态

| Outcome | 数量 |
|---|---:|
| `completed` | 11 |
| `tool_budget_exhausted` | 1 |

## 10. 解释约束

- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。
- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。
- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。
- `API reasoning_tokens` 只来自 usage / completion_tokens_details。llama.cpp 当前通常不填这个字段。
- thinking chars 来自 `message.reasoning_content` 或 `<think>` 标签，**不是** Reasoning Token，不能写成减少了 N% tokens。
- end-to-end completion token 含思考 + 工具参数 + 最终回答，是可比较的工程成本。
- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。
