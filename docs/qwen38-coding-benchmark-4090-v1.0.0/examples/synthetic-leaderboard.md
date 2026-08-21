# QCB-4090 多模型排行榜

- 赛道：`normalized`
- 测试集：`smoke`
- 生成时间：`2026-08-20T07:44:13.187Z`

> 排名先应用质量门槛，再按 Category Balanced Index、Hard Success、Worst Category、成功任务耗时和生成 Token 排序。Normalized 与 Optimized 赛道不得合榜。

| 排名 | 模型 | 合格 | Hard Success | CBI | Worst Category | Invalid | 成功耗时(s) | 生成 Token |
|---:|---|:---:|---:|---:|---:|---:|---:|---:|
| 1 | synthetic-candidate | 是 | 0.833 | 0.837 | 0.707 | 0.028 | 30.1 | 604.5 |
| 2 | synthetic-original | 是 | 0.806 | 0.817 | 0.700 | 0.000 | 30.2 | 604.5 |

## 质量门槛明细

| 模型 | 完整配对 | Hard 非劣 | 最差类别保护 | 无效输出门槛 |
|---|:---:|:---:|:---:|:---:|
| synthetic-candidate | ✓ | ✓ | ✓ | ✓ |
| synthetic-original | ✓ | ✓ | ✓ | ✓ |

## Pairwise 配对统计

| A | B | 完整配对 | Runs | Hard B-A | 95% CI | McNemar p | Holm p |
|---|---|:---:|---:|---:|---:|---:|---:|
| synthetic-candidate | synthetic-original | 是 | 36 | -0.019 | [-0.056, 0.000] | 1.0000 | 1.0000 |

## 使用限制

该榜只说明同一基准版本、相同 Lane、相同 Suite 和完整配对记录下的相对结果。效率只在质量门槛内参与排序；快速失败不会被当成性能优势。Pairwise p 值使用 Holm 校正，但仍必须结合效应量和置信区间解释。
