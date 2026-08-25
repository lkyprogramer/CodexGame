# coldfusion-v1.1-q4km-mtp-optimized — QCB-4090 测试报告

## 1. 实验身份

| 项目 | 值 |
|---|---|
| 基准版本 | `1.0.0` |
| 模型 | `coldfusion-v1.1-q4km-mtp-optimized` |
| 家族 | `Qwen3.8-27B` |
| 量化 | `Q4_K_M-MTP` |
| Template | `coldfusion-native-medium-override` |
| 模型 SHA-256 | `db466a9432a52b87a7b7560f432f0e1caafeb111dbe3d168acf74dfe143a637c` |
| Hash 状态 | `match` |
| 赛道 | `optimized` |
| Suite | `smoke` |
| Context | `112000` |
| Reasoning effort | `medium` |
| MTP | `True` |
| Seeds | `[42]` |

## 2. 数据完整性

| 指标 | 结果 |
|---|---:|
| 运行数 | 12 |
| 唯一题目 | 12 |
| 重复 task/seed | 0 |
| Reasoning Token 覆盖率 | 0.0% |
| GPU 采样覆盖率 | 100.0% |
| Endpoint timing 覆盖率 | 100.0% |
| 基础设施错误率 | 0.0% |

## 3. 质量结果

| 指标 | 结果 |
|---|---:|
| Hard Task Success Rate | 33.3% |
| Partial Test Pass Rate | 40.0% |
| Category Balanced Index | 31.9% |
| Worst Category Index | 0.0% |
| Invalid Output Rate | 0.0% |
| 不稳定题目率 | 0.0% |

## 4. 六类能力矩阵

| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |
|---|---:|---:|---:|---:|---:|---:|
| single_file | 2 | 2 | 0.0% | 0.0% | 0.0% | N/A |
| bug_fix | 2 | 2 | 50.0% | 50.0% | 50.0% | 58.4 |
| repo_engineering | 3 | 3 | 33.3% | 33.3% | 33.3% | 205.8 |
| agent_tool | 2 | 2 | 100.0% | 100.0% | 100.0% | 26.5 |
| long_context | 1 | 1 | 0.0% | 0.0% | 0.0% | N/A |
| code_review | 2 | 2 | 0.0% | 40.0% | 8.0% | N/A |

## 5. 成功任务效率

| 指标 | 结果 |
|---|---:|
| 成功任务耗时中位数 | 43.2 s |
| 成功任务耗时 P90 | 161.6 s |
| 成功任务生成 Token 中位数 | 3790.0 |
| Reasoning Token 中位数 | N/A |
| 成功任务/Wall-hour | 11.22 |
| Prompt tok/s 中位数 | 782.1 |
| Decode tok/s 中位数 | 68.0 |
| MTP acceptance | 64.1% |

## 6. Agent 与工具行为

| 指标 | 结果 |
|---|---:|
| Tool calls | 195 |
| Invalid tool calls | 7 |
| Valid tool-call rate | 96.4% |
| Tool operation success | 67.6% |
| Public test runs | 4 |
| Public-test recovery candidates | 1 |
| Public-test recovery rate | 100.0% |

## 7. RTX 4090 运行指标

| 指标 | 结果 |
|---|---:|
| Peak VRAM | 23290 MB |
| Median average GPU utilization | 86.7% |
| Peak power | 441.5 W |
| Peak temperature | 82.0 °C |

## 8. 每题结果

| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |
|---|---|---:|---:|---:|---:|---:|
| AT001 | agent_tool | 1 | 100.0% | 100.0% | 25.0 | 1669.0 |
| AT002 | agent_tool | 1 | 100.0% | 100.0% | 28.0 | 1968.0 |
| BF001 | bug_fix | 1 | 0.0% | 0.0% | 224.6 | 15898.0 |
| BF004 | bug_fix | 1 | 100.0% | 100.0% | 58.4 | 5612.0 |
| CR001 | code_review | 1 | 0.0% | 40.0% | 81.2 | 5200.0 |
| CR002 | code_review | 1 | 0.0% | 40.0% | 46.0 | 2636.0 |
| LC001 | long_context | 1 | 0.0% | 0.0% | 95.3 | 6306.0 |
| RE001 | repo_engineering | 1 | 100.0% | 100.0% | 205.8 | 15308.0 |
| RE004 | repo_engineering | 1 | 0.0% | 0.0% | 74.6 | 5904.0 |
| RE007 | repo_engineering | 1 | 0.0% | 0.0% | 225.6 | 17723.0 |
| SF001 | single_file | 1 | 0.0% | 0.0% | 116.4 | 9197.0 |
| SF002 | single_file | 1 | 0.0% | 0.0% | 102.7 | 7289.0 |

## 9. 失败与输出状态

| Outcome | 数量 |
|---|---:|
| `completed` | 11 |
| `tool_budget_exhausted` | 1 |

## 10. 解释约束

- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。
- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。
- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。
- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。
