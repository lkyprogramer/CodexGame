# salience-r5-q4km-optimized — QCB-4090 测试报告

## 1. 实验身份

| 项目 | 值 |
|---|---|
| 基准版本 | `1.0.0` |
| 模型 | `salience-r5-q4km-optimized` |
| 家族 | `Qwen3.8-27B` |
| 量化 | `Q4_K_M` |
| Template | `salience-native` |
| 模型 SHA-256 | `09283343875f15f318ba8ceab76a7d24972f1dca01c91b06f944784e098ec2a2` |
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
| 基础设施错误率 | 0.0% |

## 3. 质量结果

| 指标 | 结果 |
|---|---:|
| Hard Task Success Rate | 46.9% |
| Partial Test Pass Rate | 56.9% |
| Category Balanced Index | 49.1% |
| Worst Category Index | 15.7% |
| Invalid Output Rate | 0.0% |
| 不稳定题目率 | 59.4% |

## 4. 六类能力矩阵

| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |
|---|---:|---:|---:|---:|---:|---:|
| single_file | 6 | 18 | 77.8% | 84.7% | 79.2% | 115.1 |
| bug_fix | 6 | 18 | 44.4% | 48.1% | 45.2% | 104.9 |
| repo_engineering | 8 | 24 | 33.3% | 38.9% | 34.4% | 164.4 |
| agent_tool | 4 | 12 | 83.3% | 83.3% | 83.3% | 78.8 |
| long_context | 4 | 12 | 33.3% | 50.0% | 36.7% | 98.0 |
| code_review | 4 | 12 | 8.3% | 45.0% | 15.7% | 83.5 |

## 5. 成功任务效率

| 指标 | 结果 |
|---|---:|
| 成功任务耗时中位数 | 103.7 s |
| 成功任务耗时 P90 | 377.3 s |
| 成功任务 end-to-end completion token 中位数 | 8405.0 |
| 失败任务 end-to-end completion token 中位数 | 7189.0 |
| API reasoning_tokens 中位数 | N/A |
| 成功任务 thinking chars 中位数 | 18319.0 |
| 失败任务 thinking chars 中位数 | 18235.0 |
| 全部任务 thinking chars 中位数 | 18277.0 |
| 可见回答 chars 中位数 | 2304.0 |
| 成功任务/Wall-hour | 10.13 |
| Prompt tok/s 中位数 | 716.5 |
| Decode tok/s 中位数 | 75.6 |
| MTP acceptance | 61.7% |

## 6. Agent 与工具行为

| 指标 | 结果 |
|---|---:|
| Tool calls | 1672 |
| Invalid tool calls | 77 |
| Valid tool-call rate | 95.4% |
| Tool operation success | 57.5% |
| Public test runs | 25 |
| Public-test recovery candidates | 10 |
| Public-test recovery rate | 80.0% |

## 7. RTX 4090 运行指标

| 指标 | 结果 |
|---|---:|
| Peak VRAM | 22622 MB |
| Median average GPU utilization | 86.0% |
| Peak power | 445.8 W |
| Peak temperature | 90.0 °C |

## 8. 每题结果

| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |
|---|---|---:|---:|---:|---:|---:|
| AT001 | agent_tool | 3 | 66.7% | 66.7% | 23.5 | 1687.0 |
| AT002 | agent_tool | 3 | 100.0% | 100.0% | 94.6 | 6587.0 |
| AT003 | agent_tool | 3 | 100.0% | 100.0% | 126.3 | 11076.0 |
| AT005 | agent_tool | 3 | 66.7% | 66.7% | 82.0 | 6574.0 |
| BF001 | bug_fix | 3 | 33.3% | 33.3% | 122.8 | 8740.0 |
| BF004 | bug_fix | 3 | 66.7% | 66.7% | 92.7 | 7285.0 |
| BF005 | bug_fix | 3 | 0.0% | 0.0% | 391.0 | 29285.0 |
| BF006 | bug_fix | 3 | 66.7% | 66.7% | 106.0 | 8405.0 |
| BF008 | bug_fix | 3 | 66.7% | 88.9% | 589.4 | 40787.0 |
| BF009 | bug_fix | 3 | 33.3% | 33.3% | 244.4 | 19770.0 |
| CR001 | code_review | 3 | 0.0% | 60.0% | 53.4 | 3837.0 |
| CR002 | code_review | 3 | 33.3% | 66.7% | 59.0 | 3936.0 |
| CR003 | code_review | 3 | 0.0% | 26.7% | 44.3 | 2971.0 |
| CR004 | code_review | 3 | 0.0% | 26.7% | 84.2 | 5810.0 |
| LC001 | long_context | 3 | 33.3% | 33.3% | 131.7 | 11096.0 |
| LC002 | long_context | 3 | 33.3% | 66.7% | 78.6 | 7189.0 |
| LC003 | long_context | 3 | 66.7% | 66.7% | 64.2 | 5420.0 |
| LC004 | long_context | 3 | 0.0% | 33.3% | 65.9 | 4829.0 |
| RE001 | repo_engineering | 3 | 33.3% | 33.3% | 451.7 | 33882.0 |
| RE002 | repo_engineering | 3 | 33.3% | 33.3% | 57.8 | 4891.0 |
| RE003 | repo_engineering | 3 | 0.0% | 0.0% | 23.2 | 1675.0 |
| RE004 | repo_engineering | 3 | 33.3% | 55.6% | 121.3 | 11027.0 |
| RE005 | repo_engineering | 3 | 0.0% | 0.0% | 189.0 | 15481.0 |
| RE006 | repo_engineering | 3 | 100.0% | 100.0% | 95.4 | 7594.0 |
| RE007 | repo_engineering | 3 | 0.0% | 0.0% | 118.2 | 9219.0 |
| RE009 | repo_engineering | 3 | 66.7% | 88.9% | 181.8 | 15094.0 |
| SF001 | single_file | 3 | 100.0% | 100.0% | 119.1 | 10501.0 |
| SF002 | single_file | 3 | 66.7% | 83.3% | 118.3 | 10030.0 |
| SF003 | single_file | 3 | 66.7% | 66.7% | 157.4 | 13882.0 |
| SF006 | single_file | 3 | 66.7% | 66.7% | 33.0 | 2309.0 |
| SF008 | single_file | 3 | 100.0% | 100.0% | 100.5 | 9150.0 |
| SF012 | single_file | 3 | 66.7% | 91.7% | 184.7 | 16037.0 |

## 9. 失败与输出状态

| Outcome | 数量 |
|---|---:|
| `completed` | 86 |
| `tool_budget_exhausted` | 10 |

## 10. 解释约束

- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。
- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。
- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。
- `API reasoning_tokens` 只来自 usage / completion_tokens_details。llama.cpp 当前通常不填这个字段。
- thinking chars 来自 `message.reasoning_content` 或 `<think>` 标签，**不是** Reasoning Token，不能写成减少了 N% tokens。
- end-to-end completion token 含思考 + 工具参数 + 最终回答，是可比较的工程成本。
- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。
