# Astra · 剩余方向独立复核回执

结论：**NO_QUALIFIED_CANDIDATE，本轮收口。** 不支持继续优先推进F02；F02保留`DEFERRED_NEW_EVIDENCE`，不外推全局`NO_GAIN`。完整报告在父目录`reports/FRONTIER-CLOSURE-ASTRA-20261031.md`。

用户要求Astra/xhigh。内置独立子代理`/root/astra_remaining_reassessment`按`gpt-6-astra`、`xhigh`、`fork_turns=none`配置派发并返回结果；没有外部CodexHost线程，也没有独立运行时模型/档位回读。

Reviewer只读检查P01B/F03、候选、donor、源码身份，并复算旧P11 SQLite；未SSH、修改文件、编译、测试、benchmark或运行GPU。root独立复算一致。

| 旧profile首末输出区间 | short | long |
|---|---:|---:|
| GU-SwiGLU全家族kernel并集占比 | 6.8911% | 6.5884% |
| 最大单格式TG21占比 | 2.2188% | 2.1287% |

[F02](../candidates/F02_EXACT_LOAD_LAYOUT.md)限制一个格式、一个内核。旧样本中最大格式条件成本不足4%，全家族需要消除约六成时间才可能达到4%；尚无对应load/layout新机制。共享解包、codebook staging与GU/SwiGLU/q8_1融合已存在。

这些是旧profile的区间并集，不是当前真实暖态的暴露成本或严格上界；不能合并五格式、把kernel时间当可省墙钟或声称实测回归。故取消原拟四小时F02审计，不改选另一卡续测。

F01/F04缺当前依赖与具体缺陷证据；F05–F07缺稳定暖态收益链；F08–F10受质量、数值或资产前提阻塞。[候选排序](../docs/03_CANDIDATE_DECISION.md)仅保留条件分支，不构成执行队列。

P01原短输出停止、P01B执行COMPLETE/资格INSUFFICIENT、[F03关闭](F03_REVIEW.md)、原六FAIL和P05 BLOCKED_EVIDENCE均保留。重开须有独立新机制、当前真实暖态命中与依赖证据、可信净省时至少4%依据，并明确后续执行范围。

文档收口时root仅经jssh只读核对29：2026-10-31 12:40:17北京时间生产inactive/dead/enabled，GPU1MiB/42°C、无compute。没有GPU追加、远端写入或生产恢复；该状态查询不是Reviewer自行执行。
