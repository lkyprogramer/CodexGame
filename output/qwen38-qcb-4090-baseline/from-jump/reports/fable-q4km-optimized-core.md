# fable-q4km-optimized — QCB-4090 测试报告

## 1. 实验身份

| 项目 | 值 |
|---|---|
| 基准版本 | `1.0.0` |
| 模型 | `fable-q4km-optimized` |
| 家族 | `Qwen3.8-27B` |
| 量化 | `Q4_K_M` |
| Template | `fable-native-medium-override` |
| 模型 SHA-256 | `f5eeeee69f5cf9dfea8412a01a1c2ef594b93c5683675e275b9c2936fab7623f` |
| Hash 状态 | `match` |
| 赛道 | `optimized` |
| Suite | `core` |
| Context | `112000` |
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
| 基础设施错误率 | 1.0% |

## 3. 质量结果

| 指标 | 结果 |
|---|---:|
| Hard Task Success Rate | 41.7% |
| Partial Test Pass Rate | 52.1% |
| Category Balanced Index | 45.8% |
| Worst Category Index | 16.7% |
| Invalid Output Rate | 0.0% |
| 不稳定题目率 | 46.9% |

## 4. 六类能力矩阵

| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |
|---|---:|---:|---:|---:|---:|---:|
| single_file | 6 | 18 | 33.3% | 50.4% | 36.7% | 184.5 |
| bug_fix | 6 | 18 | 44.4% | 48.1% | 45.2% | 67.1 |
| repo_engineering | 8 | 24 | 33.3% | 37.5% | 34.2% | 81.3 |
| agent_tool | 4 | 12 | 66.7% | 66.7% | 66.7% | 84.9 |
| long_context | 4 | 12 | 75.0% | 77.1% | 75.4% | 56.3 |
| code_review | 4 | 12 | 8.3% | 50.0% | 16.7% | 50.4 |

## 5. 成功任务效率

| 指标 | 结果 |
|---|---:|
| 成功任务耗时中位数 | 71.1 s |
| 成功任务耗时 P90 | 246.2 s |
| 成功任务 end-to-end completion token 中位数 | 6269.5 |
| 失败任务 end-to-end completion token 中位数 | 7744.5 |
| API reasoning_tokens 中位数 | N/A |
| 成功任务 thinking chars 中位数 | 10791.0 |
| 失败任务 thinking chars 中位数 | 16211.5 |
| 全部任务 thinking chars 中位数 | 12130.5 |
| 可见回答 chars 中位数 | 2034.5 |
| 成功任务/Wall-hour | 9.92 |
| Prompt tok/s 中位数 | 543.2 |
| Decode tok/s 中位数 | 74.7 |
| MTP acceptance | 59.6% |

## 6. Agent 与工具行为

| 指标 | 结果 |
|---|---:|
| Tool calls | 1772 |
| Invalid tool calls | 67 |
| Valid tool-call rate | 96.2% |
| Tool operation success | 49.4% |
| Public test runs | 18 |
| Public-test recovery candidates | 5 |
| Public-test recovery rate | 60.0% |

## 7. RTX 4090 运行指标

| 指标 | 结果 |
|---|---:|
| Peak VRAM | 22272 MB |
| Median average GPU utilization | 87.1% |
| Peak power | 446.2 W |
| Peak temperature | 90.0 °C |

## 8. 每题结果

| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |
|---|---|---:|---:|---:|---:|---:|
| AT001 | agent_tool | 3 | 100.0% | 100.0% | 106.3 | 7033.0 |
| AT002 | agent_tool | 3 | 100.0% | 100.0% | 149.3 | 10214.0 |
| AT003 | agent_tool | 3 | 66.7% | 66.7% | 63.5 | 5172.0 |
| AT005 | agent_tool | 3 | 0.0% | 0.0% | 347.7 | 25745.0 |
| BF001 | bug_fix | 3 | 33.3% | 33.3% | 92.9 | 7633.0 |
| BF004 | bug_fix | 3 | 100.0% | 100.0% | 38.9 | 2725.0 |
| BF005 | bug_fix | 3 | 0.0% | 0.0% | 419.8 | 29638.0 |
| BF006 | bug_fix | 3 | 66.7% | 66.7% | 47.4 | 3863.0 |
| BF008 | bug_fix | 3 | 66.7% | 88.9% | 79.5 | 7572.0 |
| BF009 | bug_fix | 3 | 0.0% | 0.0% | 259.5 | 19675.0 |
| CR001 | code_review | 3 | 0.0% | 53.3% | 28.6 | 1817.0 |
| CR002 | code_review | 3 | 0.0% | 73.3% | 30.1 | 1904.0 |
| CR003 | code_review | 3 | 0.0% | 26.7% | 38.4 | 2379.0 |
| CR004 | code_review | 3 | 33.3% | 46.7% | 43.3 | 2757.0 |
| LC001 | long_context | 3 | 100.0% | 100.0% | 70.9 | 6411.0 |
| LC002 | long_context | 3 | 100.0% | 100.0% | 56.3 | 5055.0 |
| LC003 | long_context | 3 | 33.3% | 33.3% | 87.9 | 6824.0 |
| LC004 | long_context | 3 | 66.7% | 75.0% | 31.3 | 2244.0 |
| RE001 | repo_engineering | 3 | 33.3% | 33.3% | 277.6 | 19878.0 |
| RE002 | repo_engineering | 3 | 0.0% | 0.0% | 93.6 | 7642.0 |
| RE003 | repo_engineering | 3 | 0.0% | 0.0% | 58.0 | 4097.0 |
| RE004 | repo_engineering | 3 | 100.0% | 100.0% | 72.3 | 7228.0 |
| RE005 | repo_engineering | 3 | 0.0% | 0.0% | 209.1 | 15775.0 |
| RE006 | repo_engineering | 3 | 66.7% | 77.8% | 38.9 | 3245.0 |
| RE007 | repo_engineering | 3 | 0.0% | 0.0% | 78.3 | 6749.0 |
| RE009 | repo_engineering | 3 | 66.7% | 88.9% | 87.0 | 6379.0 |
| SF001 | single_file | 3 | 66.7% | 66.7% | 243.7 | 20738.0 |
| SF002 | single_file | 3 | 33.3% | 38.9% | 242.5 | 18965.0 |
| SF003 | single_file | 3 | 0.0% | 0.0% | 345.5 | 32500.0 |
| SF006 | single_file | 3 | 33.3% | 53.3% | 33.1 | 2440.0 |
| SF008 | single_file | 3 | 33.3% | 60.0% | 126.7 | 13061.0 |
| SF012 | single_file | 3 | 33.3% | 83.3% | 106.0 | 9331.0 |

## 9. 失败与输出状态

| Outcome | 数量 |
|---|---:|
| `completed` | 80 |
| `endpoint_error` | 1 |
| `tool_budget_exhausted` | 15 |

## 10. 解释约束

- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。
- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。
- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。
- `API reasoning_tokens` 只来自 usage / completion_tokens_details。llama.cpp 当前通常不填这个字段。
- thinking chars 来自 `message.reasoning_content` 或 `<think>` 标签，**不是** Reasoning Token，不能写成减少了 N% tokens。
- end-to-end completion token 含思考 + 工具参数 + 最终回答，是可比较的工程成本。
- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。
