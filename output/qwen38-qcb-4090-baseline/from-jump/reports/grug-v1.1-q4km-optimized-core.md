# grug-v1.1-q4km-optimized — QCB-4090 测试报告

## 1. 实验身份

| 项目 | 值 |
|---|---|
| 基准版本 | `1.0.0` |
| 模型 | `grug-v1.1-q4km-optimized` |
| 家族 | `Qwen3.8-27B` |
| 量化 | `Q4_K_M` |
| Template | `grug-native` |
| 模型 SHA-256 | `c158a0ffad48c3a0de56f502340dc9d588625212ca7175495132445c3825134d` |
| Hash 状态 | `match` |
| 赛道 | `optimized` |
| Suite | `core` |
| Context | `112000` |
| Reasoning effort | `medium` |
| MTP | `False` |
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
| Hard Task Success Rate | 15.6% |
| Partial Test Pass Rate | 25.3% |
| Category Balanced Index | 17.6% |
| Worst Category Index | 1.2% |
| Invalid Output Rate | 25.0% |
| 不稳定题目率 | 28.1% |

## 4. 六类能力矩阵

| 分类 | 题目 | 运行 | Hard | Partial | Category Index | 成功耗时(s) |
|---|---:|---:|---:|---:|---:|---:|
| single_file | 6 | 18 | 11.1% | 18.9% | 12.7% | 81.4 |
| bug_fix | 6 | 18 | 11.1% | 15.9% | 12.1% | 210.5 |
| repo_engineering | 8 | 24 | 20.8% | 29.2% | 22.5% | 74.6 |
| agent_tool | 4 | 12 | 8.3% | 13.9% | 9.4% | 160.5 |
| long_context | 4 | 12 | 0.0% | 6.2% | 1.2% | N/A |
| code_review | 4 | 12 | 41.7% | 71.7% | 47.7% | 17.2 |

## 5. 成功任务效率

| 指标 | 结果 |
|---|---:|
| 成功任务耗时中位数 | 60.2 s |
| 成功任务耗时 P90 | 303.2 s |
| 成功任务 end-to-end completion token 中位数 | 2635.0 |
| 失败任务 end-to-end completion token 中位数 | 6003.0 |
| API reasoning_tokens 中位数 | N/A |
| 成功任务 thinking chars 中位数 | 764.0 |
| 失败任务 thinking chars 中位数 | 3100.0 |
| 全部任务 thinking chars 中位数 | 2884.5 |
| 可见回答 chars 中位数 | 196.0 |
| 成功任务/Wall-hour | 3.40 |
| Prompt tok/s 中位数 | 275.2 |
| Decode tok/s 中位数 | 46.5 |
| MTP acceptance | N/A |

## 6. Agent 与工具行为

| 指标 | 结果 |
|---|---:|
| Tool calls | 2264 |
| Invalid tool calls | 51 |
| Valid tool-call rate | 97.7% |
| Tool operation success | 37.1% |
| Public test runs | 19 |
| Public-test recovery candidates | 7 |
| Public-test recovery rate | 0.0% |

## 7. RTX 4090 运行指标

| 指标 | 结果 |
|---|---:|
| Peak VRAM | 20196 MB |
| Median average GPU utilization | 92.5% |
| Peak power | 448.4 W |
| Peak temperature | 89.0 °C |

## 8. 每题结果

| 题目 | 分类 | Runs | Pass | Partial | 耗时(s) | Token |
|---|---|---:|---:|---:|---:|---:|
| AT001 | agent_tool | 3 | 0.0% | 0.0% | 66.2 | 2830.0 |
| AT002 | agent_tool | 3 | 33.3% | 55.6% | 157.7 | 6823.0 |
| AT003 | agent_tool | 3 | 0.0% | 0.0% | 140.8 | 6003.0 |
| AT005 | agent_tool | 3 | 0.0% | 0.0% | 351.8 | 15597.0 |
| BF001 | bug_fix | 3 | 0.0% | 0.0% | 32.4 | 1447.0 |
| BF004 | bug_fix | 3 | 0.0% | 0.0% | 166.3 | 7255.0 |
| BF005 | bug_fix | 3 | 0.0% | 0.0% | 62.5 | 2772.0 |
| BF006 | bug_fix | 3 | 33.3% | 40.0% | 400.2 | 17600.0 |
| BF008 | bug_fix | 3 | 33.3% | 55.6% | 28.5 | 1265.0 |
| BF009 | bug_fix | 3 | 0.0% | 0.0% | 294.8 | 13197.0 |
| CR001 | code_review | 3 | 33.3% | 73.3% | 13.5 | 553.0 |
| CR002 | code_review | 3 | 66.7% | 93.3% | 17.2 | 760.0 |
| CR003 | code_review | 3 | 0.0% | 46.7% | 28.9 | 1315.0 |
| CR004 | code_review | 3 | 66.7% | 73.3% | 18.1 | 807.0 |
| LC001 | long_context | 3 | 0.0% | 0.0% | 222.7 | 9833.0 |
| LC002 | long_context | 3 | 0.0% | 0.0% | 101.3 | 4612.0 |
| LC003 | long_context | 3 | 0.0% | 0.0% | 203.5 | 8875.0 |
| LC004 | long_context | 3 | 0.0% | 25.0% | 217.6 | 9429.0 |
| RE001 | repo_engineering | 3 | 0.0% | 0.0% | 224.8 | 9874.0 |
| RE002 | repo_engineering | 3 | 33.3% | 33.3% | 116.3 | 5186.0 |
| RE003 | repo_engineering | 3 | 0.0% | 0.0% | 36.4 | 1595.0 |
| RE004 | repo_engineering | 3 | 100.0% | 100.0% | 60.2 | 2635.0 |
| RE005 | repo_engineering | 3 | 0.0% | 0.0% | 239.6 | 10534.0 |
| RE006 | repo_engineering | 3 | 33.3% | 55.6% | 182.4 | 7956.0 |
| RE007 | repo_engineering | 3 | 0.0% | 0.0% | 293.9 | 12981.0 |
| RE009 | repo_engineering | 3 | 0.0% | 44.4% | 198.0 | 8887.0 |
| SF001 | single_file | 3 | 0.0% | 0.0% | 90.6 | 4213.0 |
| SF002 | single_file | 3 | 0.0% | 0.0% | 121.2 | 5465.0 |
| SF003 | single_file | 3 | 0.0% | 0.0% | 508.3 | 22245.0 |
| SF006 | single_file | 3 | 0.0% | 33.3% | 28.0 | 1224.0 |
| SF008 | single_file | 3 | 0.0% | 13.3% | 219.5 | 9613.0 |
| SF012 | single_file | 3 | 66.7% | 66.7% | 60.8 | 2748.0 |

## 9. 失败与输出状态

| Outcome | 数量 |
|---|---:|
| `completed` | 35 |
| `invalid_output` | 18 |
| `patch_failed` | 6 |
| `tool_budget_exhausted` | 37 |

## 10. 解释约束

- 本报告只对相同基准版本、相同题目、相同 Seed、相同赛道和相同执行器配置下的数据作直接比较。
- Normalized 与 Optimized 必须分榜；Template-only 变体不得描述为新权重模型。
- Endpoint 未返回 reasoning、timings 或 MTP 字段时，对应指标保持 N/A，不能解释成 0。
- `API reasoning_tokens` 只来自 usage / completion_tokens_details。llama.cpp 当前通常不填这个字段。
- thinking chars 来自 `message.reasoning_content` 或 `<think>` 标签，**不是** Reasoning Token，不能写成减少了 N% tokens。
- end-to-end completion token 含思考 + 工具参数 + 最终回答，是可比较的工程成本。
- 快速失败不是效率优势；效率排序应只在预先声明的质量门槛内进行。
