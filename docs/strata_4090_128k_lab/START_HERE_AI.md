# Strata 当前执行入口

先读[下一步行动计划](plans/NEXT_ACTIONS.md)和[Astra复核与收口报告](reports/FRONTIER-CLOSURE-ASTRA-20261031.md)。当前冻结合同下NO_QUALIFIED_CANDIDATE，本轮已收口；撤回优先推进F02的建议，F02保留DEFERRED_NEW_EVIDENCE。P01/P01B/F03历史终态保留，P05 BLOCKED_EVIDENCE及六FAIL不变。生产随后按用户要求[恢复运行](reports/PRODUCTION-RESTORE-20261031.md)，GPU由生产占用；旧停机回执不代表当前空闲。

## 权威与读取顺序

1. [合并记录](reports/DOC-MERGE-20261030.md)：先区分当前现场复核、作者历史研究、未完成准备。
2. [frontier AI 合同](frontier/START_HERE_AI.md)：只读当前阶段与直接依赖，十二张方向卡是条件分支。
3. 原实验事实以 `reports/` 和对应 `workspace/` 原件为准；生产保护和运行资源规则沿用本目录 `AGENTS.md`。frontier/sources/LOCK.json 冻结后续 P6 研究身份；根 sources/LOCK.json 保留 A0 历史身份，两者角色不同。
4. 工具继续使用根目录 `lab/`、`tools/`。frontier/tools只含离线计算器；根tools/frontier已实现P01最小live adapter，实际本轮已停止，不能重复原run。只有明确授权执行对应阶段时，才进入工具开发或目标机负载。

## 当前停止点

- Astra复核：2026-10-31已完成；旧profile最大单格式条件成本2.22%/2.13%，无已证load/layout新机制。取消原拟四小时F02审计，不改选另一卡，不追加GPU；不外推全局NO_GAIN。
- frontier/P00：已完成；身份/来源/请求/离线接口和独立门见P00报告及PHASE_GATE。无需重建已匹配P6。
- frontier/P01：已执行，103183token prime输出941后按门停止，两append NOT_RUN，结果INSUFFICIENT。原件和执行源码保留；不自动重跑。
- frontier/P01B：2026-10-31独立新合同已执行COMPLETE；完整host窗口/原始IDs已采集，窄host间隙不足4%，其他GPU/CPU内部依赖未知，候选资格INSUFFICIENT。本批次关闭。
- F03 CPU审计：2026-10-31已完成；合法旧快照保留，同步零填原型三对CPU均慢6.08%–7.74%，无合格候选，不追加GPU。
- frontier/P02及以后：当前不进入候选开发。未来重开须有独立新机制、当前真实暖态命中与可闭合依赖、可信方案及新增成本账支持完整请求净省时≥4%，并明确后续执行范围；缺证据不自动触发新采集。
- frontier/P05：目前缺稳定 warm fixed2048 原件，BLOCKED_EVIDENCE；P24 的 5-token append 不能替代。诊断完成不会自动解除该门。
- 原六 FAIL 不变；性能研究通过不等于生产采用。

## 历史入口

原 [AI 执行说明](history/START_HERE_PRE_FRONTIER_20261030.md) 和 [HC 续测合同](history/CONTINUATION_20261029.md) 仅供追溯。旧自动续测 PAUSED、旧 reset 授权到期；不沿其候选顺序继续开跑。
