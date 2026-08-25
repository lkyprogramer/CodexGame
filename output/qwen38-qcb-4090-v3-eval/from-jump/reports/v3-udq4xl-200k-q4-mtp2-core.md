# v3-udq4xl-200k-q4-mtp2 — QCB-4090 测试报告

## 1. 实验身份

| 项目 | 值 |
|---|---|
| 基准版本 | `1.0.0` |
| 模型 | `v3-udq4xl-200k-q4-mtp2` |
| 家族 | `Qwen3.8-27B` |
| 量化 | `UD-Q4_K_XL-Dynamic-V3` |
| Template | `official-jinja-medium` |
| 模型 SHA-256 | `3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e` |
| Hash 状态 | `match` |
| 赛道 | `optimized` |
| Suite | `core` |
| Context | `200000` |
| Reasoning effort | `medium` |
| MTP | `True` |
| Seeds | `[11, 29, 47]` |

## 2. 数据完整性

| 指标 | 结果 |
|---|---:|
| 运行数 | 96 |
| 唯一题目 | 32 |
| 重复 task/seed | 0 |
| API reasoning_tokens 覆盖率 | 0.0% |
| thinking chars 覆盖率 | 100.0% |
| GPU 采样覆盖率 | 100.0% |
| Endpoint timing 覆盖率 | 100.0% |
| 基础设施错误率 | 0.0% |

## 3. 质量结果

| 指标 | 结果 |
|---|---:|
| Hard Task Success Rate | 46.9% |
| Partial Test Pass Rate | 56.2% |
| Category Balanced Index | 48.3% |
| Worst Category Index | 8.7% |
| Invalid Output Rate | 0.0% |
| 不稳定题目率 | 56.2% |

## 4. 六类能力矩阵

| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |
|---|---:|---:|---:|---:|---:|---:|
| single_file | 6 | 18 | 55.6% | 69.8% | 58.4% | 86.2 |
| bug_fix | 6 | 18 | 50.0% | 51.1% | 50.2% | 98.1 |
| repo_engineering | 8 | 24 | 45.8% | 45.8% | 45.8% | 234.6 |
| agent_tool | 4 | 12 | 83.3% | 83.3% | 83.3% | 51.3 |
| long_context | 4 | 12 | 41.7% | 50.0% | 43.3% | 79.7 |
| code_review | 4 | 12 | 0.0% | 43.3% | 8.7% | N/A |

## 5. 成功任务效率

| 指标 | 结果 |
|---|---:|
| 成功任务耗时中位数 | 102.6 s |
| 成功任务耗时 P90 | 293.0 s |
| 成功任务 end-to-end completion token 中位数 | 9486.0 |
| 失败任务 end-to-end completion token 中位数 | 7412.0 |
| API reasoning_tokens 中位数 | N/A |
| 成功任务 thinking chars 中位数 | 16972.0 |
| 失败任务 thinking chars 中位数 | 16414.0 |
| 全部任务 thinking chars 中位数 | 16708.5 |
| 可见回答 chars 中位数 | 2476.0 |
| 成功任务/Wall-hour | 11.03 |
| Prompt tok/s 中位数 | 882.3 |
| Decode tok/s 中位数 | 77.4 |
| MTP acceptance | 62.9% |

## 6. Agent 与工具行为

| 指标 | 结果 |
|---|---:|
| Tool calls | 1666 |
| Invalid tool calls | 75 |
| Valid tool-call rate | 95.5% |
| Tool operation success | 56.4% |
| Public test runs | 31 |
| Public-test recovery candidates | 9 |
| Public-test recovery rate | 100.0% |

## 7. RTX 4090 运行指标

| 指标 | 结果 |
|---|---:|
| Peak VRAM | 23030 MB |
| Median average GPU utilization | 86.1% |
| Peak power | 446.0 W |
| Peak temperature | 89.0 °C |

## 8. 每题结果

| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |
|---|---|---:|---:|---:|---:|---:|
| AT001 | agent_tool | 3 | 100.0% | 100.0% | 43.9 | 3199.0 |
| AT002 | agent_tool | 3 | 100.0% | 100.0% | 42.3 | 3176.0 |
| AT003 | agent_tool | 3 | 100.0% | 100.0% | 104.8 | 8353.0 |
| AT005 | agent_tool | 3 | 33.3% | 33.3% | 290.4 | 22472.0 |
| BF001 | bug_fix | 3 | 66.7% | 66.7% | 90.2 | 7203.0 |
| BF004 | bug_fix | 3 | 100.0% | 100.0% | 102.6 | 8818.0 |
| BF005 | bug_fix | 3 | 0.0% | 0.0% | 394.0 | 29555.0 |
| BF006 | bug_fix | 3 | 33.3% | 40.0% | 98.1 | 9486.0 |
| BF008 | bug_fix | 3 | 66.7% | 66.7% | 107.8 | 9674.0 |
| BF009 | bug_fix | 3 | 33.3% | 33.3% | 96.2 | 8868.0 |
| CR001 | code_review | 3 | 0.0% | 46.7% | 48.8 | 3163.0 |
| CR002 | code_review | 3 | 0.0% | 60.0% | 58.5 | 3760.0 |
| CR003 | code_review | 3 | 0.0% | 26.7% | 66.2 | 4252.0 |
| CR004 | code_review | 3 | 0.0% | 40.0% | 60.6 | 3955.0 |
| LC001 | long_context | 3 | 33.3% | 33.3% | 110.3 | 10337.0 |
| LC002 | long_context | 3 | 66.7% | 66.7% | 73.2 | 5831.0 |
| LC003 | long_context | 3 | 33.3% | 33.3% | 58.7 | 4601.0 |
| LC004 | long_context | 3 | 33.3% | 66.7% | 100.9 | 8432.0 |
| RE001 | repo_engineering | 3 | 66.7% | 66.7% | 217.8 | 16506.0 |
| RE002 | repo_engineering | 3 | 0.0% | 0.0% | 47.8 | 3683.0 |
| RE003 | repo_engineering | 3 | 0.0% | 0.0% | 38.2 | 2793.0 |
| RE004 | repo_engineering | 3 | 66.7% | 66.7% | 79.4 | 8755.0 |
| RE005 | repo_engineering | 3 | 0.0% | 0.0% | 190.3 | 14822.0 |
| RE006 | repo_engineering | 3 | 100.0% | 100.0% | 272.3 | 20324.0 |
| RE007 | repo_engineering | 3 | 33.3% | 33.3% | 141.8 | 12210.0 |
| RE009 | repo_engineering | 3 | 100.0% | 100.0% | 234.6 | 18975.0 |
| SF001 | single_file | 3 | 33.3% | 33.3% | 370.1 | 24680.0 |
| SF002 | single_file | 3 | 66.7% | 88.9% | 145.3 | 12393.0 |
| SF003 | single_file | 3 | 33.3% | 33.3% | 312.1 | 35255.0 |
| SF006 | single_file | 3 | 66.7% | 86.7% | 32.1 | 2842.0 |
| SF008 | single_file | 3 | 66.7% | 93.3% | 88.1 | 8066.0 |
| SF012 | single_file | 3 | 66.7% | 83.3% | 164.9 | 13221.0 |

## 9. 失败与输出状态

| Outcome | 数量 |
|---|---:|
| `completed` | 83 |
| `tool_budget_exhausted` | 13 |

## 10. 解释约束

- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。
- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。
- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。
- `API reasoning_tokens` 只来自 usage / completion_tokens_details。llama.cpp 当前通常不填这个字段。
- thinking chars 来自 `message.reasoning_content` 或 `<think>` 标签，**不是** Reasoning Token，不能写成减少了 N% tokens。
- end-to-end completion token 含思考 + 工具参数 + 最终回答，是可比较的工程成本。
- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。
