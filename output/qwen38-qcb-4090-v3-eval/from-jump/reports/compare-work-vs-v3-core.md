# QCB-4090 模型对比：work-udq4xl-optimized-112k-mtp2 vs v3-udq4xl-200k-q4-mtp2

- 赛道：`optimized`
- Suite：`core`
- 完整配对运行数：96

## 总体对比

| 指标 | A | B | B-A |
|---|---:|---:|---:|
| Hard Success | 46.9% | 46.9% | 0.0% |
| Partial Pass | 55.4% | 56.2% | 0.8% |
| Balanced Index | 46.7% | 48.3% | 1.6% |
| Worst Category | 6.0% | 8.7% | 2.7% |
| Invalid Output | 0.0% | 0.0% | 0.0% |
| 成功耗时中位数(s) | 119.1 | 102.6 | -16.5 |
| 成功生成 Token 中位数 | 10790.0 | 9486.0 | -1304.0 |

## 六类差异

| 分类 | A Index | B Index | B-A |
|---|---:|---:|---:|
| single_file | 61.7% | 58.4% | -3.3% |
| bug_fix | 66.7% | 50.2% | -16.4% |
| repo_engineering | 44.2% | 45.8% | 1.7% |
| agent_tool | 58.3% | 83.3% | 25.0% |
| long_context | 43.3% | 43.3% | 0.0% |
| code_review | 6.0% | 8.7% | 2.7% |

## 配对统计

- Hard Success 分层配对 Bootstrap 差值：1.2%
- Hard Success 95% CI：[-10.4%, 12.7%]
- P(B>A)：57.6%
- Partial Score 差值：3.3%，95% CI [-6.7%, 13.4%]
- McNemar：A-only=16，B-only=16，双侧精确 p=1.0000

## 预声明决策门槛

| 检查 | 通过 |
|---|:---:|
| Hard Success 95% CI 下界 ≥ -3pp | 否 |
| Worst Category 回退 ≤ 8pp | 是 |
| Invalid Output ≤ 8% 且相对 A 增幅 ≤ 3pp | 是 |
| CBI 提升 ≥ 2pp | 否 |
| 可声明 practical win | 否 |

## 解释限制

该判断只适用于当前基准版本、Lane、Suite、Seed、GGUF 与运行配置。统计显著性不能替代实际意义；效率提升也不能抵消质量门槛失败。
