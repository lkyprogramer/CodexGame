# NInfer V3统一实施计划

> For agentic workers：按依赖逐Task实施，Phase串行，独立Task可并行；每Phase合到同一commit后统一Review/测试/4090验证。代码与产品测试均未在本次文档交付执行。

**Goal:** 不丢现有NInfer定制与长上下文能力，先取得MTP/Lookup/词表/条件宽验证的真实净收益，再接DFlash2与全局检索。

**Architecture:** 保留P0—P6；新H0—H8替换旧P7—P12。一个Target/ReplaySSM/continuation权威，提案来源与神经backend、验证形状分离。

**Tech Stack:** C++20、CUDA sm89、CMake/CTest、Python reference；RTX4090单卡/64GBhost。

**Spec:** [架构](../design/00-architecture-and-contracts.md)、[吸收账本](../research/03-donor-adoption-map.md)、[验收](../design/09-test-and-evidence-contract.md)。

## Global Constraints

不改变Target权重/模板/默认KV/原已合格context；旧生产状态以P0/H0核实，不继承历史测量。P6之后使用合格rk4v4而非附件旧E8描述。新代码默认OFF、先base/text；greedy/deterministic只为proposal，Target保留生产sampling，组合经design/11及各shape资格前回原合格sampling；Target-greedy独立诊断。只借鉴donor算法/算子，不合并独立Git历史。缺GPU/资产不标PASS；发布与研究分离。

## Review Focus

Lookup stale history；不一致head接tail；accepted与committed/bonus混淆；W16只扩Attention未扩alignment；pinnedbuffer晚到跨epoch；改变宽度浮点分叉；中文bytefragment被词表过滤；短实际prompt冒充262K资格。各项均有具名Task断言。

## 原P0—P6保持

继续执行 [原总计划](../previous-v2/plans/00-master-plan.md)的P0—P6，共35个实施Task与7个gate。原43文件差异、冲突策略、上游34提交与B0/G1保留方案仍在。旧总计划有关P7之后的链接只作参考，新权威是本页。原命令所需脚本/数据按 [恢复指南](../support/REHYDRATE.md)还原，不能在生产源码目录reset。

## 后半程重新排序

| Phase | 目标 | 实施Task数 | 出口 |
|---|---|---:|---|
| [H0](phases/H0.md) | P6基线、语料、观测、资源与证据 | 6 | source/shape manifest；真实基线；指标/预算/证据checker可用 |
| [H1](phases/H1.md) | 现有W≤6的MTP＋Lookup与delta-q采样资格 | 7 | 复用既有sampler，生产Target分布/状态合同合格；E1 candidate非生产 |
| [H2](phases/H2.md) | 中文/Java草稿词表与head companion | 5 | 四profile覆盖与映射资格；不合格则维持131072 |
| [H3](phases/H3.md) | W8完整链与Graph资格 | 6 | W8全shape/资源/数值通过；未达收益不默认启用 |
| [H4](phases/H4.md) | W16、每lane策略与proposal-skip | 6 | 首版C1复制profile；真拒绝退出、对齐不省略；W16可不采用 |
| [H5](phases/H5.md) | 低成本路线独立发布/回滚 | 4 | 低成本优化可单独投入使用；DFlash2并非前置 |
| [H6](phases/H6.md) | 原生27B DFlash2 bounded ring | 7 | 真实companion+逐层参考+ring正确；可研究通过但promotion拒绝 |
| [H7](phases/H7.md) | 独立archive与全局selective drafting | 7 | 早期页可候选，辅助缓存独立，完整上下文E2E有净收益才采用 |
| [H8](phases/H8.md) | 最终组合资格和受控发布 | 5 | 全部声明范围的资格与真实回滚证据；未执行不填完成 |

默认完整DAG：`P0→P1→P2→P3→P4→P5→P6→H0→H1→H2→H3→H4→H5→H6→H7→H8`。

完整Task DAG见 [注册表](02-task-registry.md)；新53Task替换旧32Task（H1新增T07 sampling资格，不增phase），完整有效实施任务88个，统一阶段门禁16个。不是把所有研究都当必定有收益；不合格/取消的范围按design/09记录，不能宣称原范围完成。

## 工作区与命令变量

```bash
export DOCS=/path/to/ninfer-hyperqwen-v3-md-20261019
export PACK=/path/to/rehydrated-v2-support
export REPO=/path/to/ninfer-integration-worktree
export BUILD=/path/to/ninfer-build-sm89
export OUT=/path/outside-repository/hybrid-evidence
export TASK_OUT="$OUT/H1/H1-T02"
```

编译基准沿用 [原命令手册](../previous-v2/docs/08-command-runbook.md)。本包不新增假装可用的NInfer CLI；`--hybrid-policy`、`--proposal-head`和新testtargets由相应task实现后才能运行。H0的driver/checker也是待实施，不把本次文档一致性检查当作它们的测试。

每Task结束只做最小定向验证与自审；每Phase统一Reviewer审查与受影响硬合同/≤240相关A/B筛选；H5/H8集中正式发布资格，不逐Phase展开全部672。无subagent时按同DAG串行，但不得标注虚构独立review。每个CPUworker可独立worktree；一个公共文件/一个GPU都只有一个写入或执行owner。

## 窄范围发布前置

本页依赖是默认完整方案；W8/W16退出时仅可依据[发布范围契约](../design/10-release-scope.md)的`e1_w6/e1_w8`派生DAG进入H5。范围外任务保留真实状态，不能伪造H3/H4-GATE通过。

## 2026-10-20 当前先执行B29 baseline

执行入口改为 [plans/05](05-baseline-29-execution.md)。本轮只允许方案修订、必要采集/计量/监控工具、已有27B各上下文与Pi session baseline；优化实施暂不启动。B29是E8/schema20/生产sampling，BO/P6尚未认证；原P0的PROD/O/C及codec独立验收照常执行。生产Target sampling为收益目标，Target-greedy仅诊断；greedy proposal可经delta-q保留sampling输出。完整672只作声明目录，初始278/阶段≤240/发布26任务variant及formal metric资格按plans/06、design/07。

phase级默认DAG与三个feature scope保持，H1内新增T07共同sampling资格前置。B29测量前置可以先执行，不代表H0依赖已满足；P6/H5的实际发布/回滚仍阻断后续H0/H6资格。当前只完成baseline而没有BO构建、P6迁移和生产gate时如实列未完成，不沿用“文档已修订”推断PASS。长任务由ROOT唯一GPU owner、脚本监控和已授权定时唤醒处理，先证实监督/进度可恢复再让出回合。

## 2026-10-21已采用范围

当前仍BASELINE_ONLY；新授权是文档/采集工具+精简B29 baseline。先看plans/06、design/11；旧672全展开/Pi五遍/20×3通用下限撤回，未测不填PASS。H1新增T07（8具名采样断言）接现有accept/kernel/processor/RNG/state，T06性能依赖T07，所有新sampling组合OFF至资格完成；当前不做任何引擎优化。原P0—P6/生产门、三feature release范围保持，测量安排不是新feature release。
