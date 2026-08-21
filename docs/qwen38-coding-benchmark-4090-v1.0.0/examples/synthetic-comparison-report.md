# QCB-4090 模型对比：synthetic-original vs synthetic-candidate

- 赛道：`normalized`
- Suite：`smoke`
- 完整配对运行数：36

## 总体对比

| 指标 | A | B | B-A |
|---|---:|---:|---:|
| Hard Success | 80.6% | 83.3% | 2.8% |
| Partial Pass | 90.3% | 93.3% | 3.1% |
| Balanced Index | 81.7% | 83.7% | 2.0% |
| Worst Category | 70.0% | 70.7% | 0.7% |
| Invalid Output | 0.0% | 2.8% | 2.8% |
| 成功耗时中位数(s) | 30.2 | 30.1 | -0.1 |
| 成功生成 Token 中位数 | 595.0 | 604.5 | 9.5 |

## 六类差异

| 分类 | A Index | B Index | B-A |
|---|---:|---:|---:|
| single_file | 85.0% | 85.3% | 0.3% |
| bug_fix | 85.0% | 85.3% | 0.3% |
| repo_engineering | 80.0% | 90.2% | 10.2% |
| agent_tool | 85.0% | 85.3% | 0.3% |
| long_context | 70.0% | 70.7% | 0.7% |
| code_review | 85.0% | 85.3% | 0.3% |

## 配对统计

- Hard Success 分层配对 Bootstrap 差值：1.9%
- Hard Success 95% CI：[0.0%, 5.6%]
- P(B>A)：65.7%
- Partial Score 差值：2.8%，95% CI [0.8%, 5.2%]
- McNemar：A-only=0，B-only=1，双侧精确 p=1.0000

## 预声明决策门槛

| 检查 | 通过 |
|---|:---:|
| Hard Success 95% CI 下界 ≥ -3pp | 是 |
| Worst Category 回退 ≤ 8pp | 是 |
| Invalid Output ≤ 8% 且相对 A 增幅 ≤ 3pp | 是 |
| CBI 提升 ≥ 2pp | 是 |
| 可声明 practical win | 是 |

## 解释限制

该判断只适用于当前基准版本、Lane、Suite、Seed、GGUF 与运行配置。统计显著性不能替代实际意义；效率提升也不能抵消质量门槛失败。
