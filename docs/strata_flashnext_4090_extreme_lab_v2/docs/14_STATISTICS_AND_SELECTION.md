# 统计、排序与采用规则

## 1. 排名不是预期百分比

方向图谱的分数是工程排序：

`score = 6*potential + 5*fit + 4*evidence + 3*(5-effort) + 2*(5-risk)`

对应的可执行定义：

```python
def priority_score(potential, fit, evidence, effort, risk):
    values = (potential, fit, evidence, effort, risk)
    assert all(type(v) is int and 0 <= v <= 5 for v in values)
    return 6*potential + 5*fit + 4*evidence + 3*(5-effort) + 2*(5-risk)
```

potential为若瓶颈存在的影响范围；fit为当前机器/模型匹配；evidence为证据强度；effort/risk越高越差。分数不代表实测收益概率或百分比。**资格、依赖和已失败历史优先于分数**：不适用、已有无收益和Q/X轨道不与普通E/N主线直接混排。

## 2. 性能区间

时间类ratio=`candidate/base`，小于1更快。先在同一paired round或预注册宏块聚合相同case与场景，再对paired round/block进行配对bootstrap；按group/cache_state/scenario/context_bucket分层。禁止把不同场景的最好ratio拼成一个平均提速。

真实任务主指标为restricted time-to-success：按预定总预算B，成功记实际wall，未成功记B；联合报告完成率。需要全局目标时，使用调参前冻结的真实流量权重：`weighted_wall=sum(weight_s*mean_restricted_wall_s)`。没有流量权重就只给场景结果。throughput比值与latency比值方向不同，报告明确变换。

## 3. 缺失即不确定

期望round/arm/case来自campaign计划，不从实际观察到的数据反推。两臂都缺同一题也算缺失。重复、缺失、配置漂移、基础设施失效、未完成回执与无法验证身份阻止采用。模型oracle失败是有效质量观测，进入四格，不删除；任务预算耗尽计有效任务失败。OOM/引擎crash另设硬拒绝。N/Q产生不同但可评分的文本不属于无效输出。旧无计划日志只做描述统计，不产生PASS候选。

## 4. 建议正式门槛

这些是项目采用政策，不是项目作者实测结论，可在首次实验前由执行者冻结一次，不得看完候选结果再改：

- 主指标：95%配对区间上界≤0.97，即有证据支持至少3%的目标场景时间改善；或解决明确的正确性/缓存失效问题，且其主时间ratio的95%区间上界≤1.03、质量门通过。
- A/A噪声定义为预登记paired round ratio对1的绝对偏差的中位数；最小有意义改善m=max(3%,2×该值)。正式主门区间上界改为≤1−m；若噪声大先改善环境，不能事后换算法。
- 关键非目标场景：冻结的时间metric ratio的95%区间上界≤1.03；严重尾延迟、OOM、错误率单独审查。没有足够尾部数据就标INSUFFICIENT，不用均值代替。
- p99：需要足够实际请求。少于1000请求只作探索性描述，不能宣称p99门已过；正式比较按进程块/任务聚类区间。
- 质量：按`12_NUMERICS_AND_QUALITY.md`，E轨道无新确定性错误；N/Q任务级非劣需足够样本。
- 显存/RAM：记录peak和最小余量，不能以降低ctx、缩小安全余量或静默赶走更多expert来隐藏成本。
- 所有正式采用还必须通过包含candidate源码的组合回归和真实Pi留出。

## 5. 多重探索与winner's curse

64个方向不做64个同时“显著性竞赛”。先用机理与微基准淘汰，再固定少量候选；最终留出集不参与调参。若反复查看结果并修改参数，旧区间只是探索性，不再作为最终置信证据。

## 6. 状态机

`IDEA → ELIGIBLE → MICRO_PASS → NUMERIC_PASS → SCENARIO_PASS → HOLDOUT_PASS → COMBINATION_PASS → READY_FOR_DEPLOY`

旁路状态：`NOT_APPLICABLE / NO_GAIN / QUALITY_REGRESSION / BLOCKED / INSUFFICIENT / REJECTED`。部署回执与性能PASS分开；没有目标机运行不能到SCENARIO_PASS。

## 7. 实现覆盖边界

当前 `lab.cli stats` 采用paired log ratio bootstrap并按round聚合，输出严格smoke筛选；内置探索性候选阈值仍为点估计≥5%改善、区间支持正改善和off/base约±3%检查。它与本文正式采用政策不同，不能直接给正式PASS。正式性能分析器（restricted时间、失败类型、冻结权重、宏块可选、主/次CI门）是P00的明确开发任务。独立quality_gate已实现四格保守非劣；两者都不替代目标机引擎、Pi留出和组合回归。
