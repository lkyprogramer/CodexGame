# 独立审阅及修订记录

日期：2026-11-15（Asia/Shanghai）。范围：研究结论、后续执行规格、模板与静态结构。没有代码构建、模型、GPU或性能验证。

本包经历了候选机制反证审阅、独立技术终审、独立机械/结构核验。审核不是替代硬件证据，也不授予未来执行权限。

## 已纳入的主要修订

| 问题 | 修订与复核点 | 状态 |
|---|---|---|
| Lookup改名可能复活旧H1/H7 | D1拆planner/source、skip、width；保持同来源宇宙/同W；宽度不在本包 | 已修订 |
| “Target不变即sampled无损”不充分 | 实际q/residual、Target RNG、sample-and-match分开；未合格sampled退baseline | 已修订 |
| MTP skip隐含免除状态追平 | 要求真实执行witness与catch-up完整成本，不能证明则BLOCKED | 已修订 |
| B0被误称旧ring | B0统一为当前绑定baseline；旧H1只用H1_REF做历史/离线参照 | 已修订并静态复核 |
| source_lock_ref相对基准歧义 | LAB_ROOT基准、addenda固定前缀、source_lock_sha256；移动时显式重新冻结 | 已修订并静态复核 |
| R1缺当前成本但无合法取证出口 | 加R0-E0独立baseline-only申请，候选关闭、独立预算、只回填R1；未知catch-up不填0 | 已修订并独立复核 |
| R0/R1新增CLI可能被当只读权限 | 显式要求CPU/离线实现授权；未批准只交规格/BLOCKED | 已修订 |
| G2 CPU门与R3数值/状态混名 | 明确G2只CPU/build，R3内各资格独立 | 已修订并静态复核 |
| 配对聚合缺显式字段 | RunEvidence增加pair/block/treatment/case/order/manifest，不靠文件名推断 | 已修订 |
| 磁盘预算缺approved/used位置 | 补storage_bytes默认0，定义未压缩保留峰值语义，null cap阻断 | 已修订并静态复核 |
| M0范围泛化成通用race改造 | 仅Strata终止输入行/continuation；donor scratch经验沿旧A2参考 | 已修订 |
| H2只有低秩概念 | 加固定weight-only构建规格、同坐标hidden、原Q4 selected-row重算；全部仍为拟议 | 已审阅，维度/算术一致 |

## 没有被审核“补成通过”的项目

- 当前用户运行二进制、P3最终projection分派、实际模型/flags仍未绑定。
- D1真实任务机会、实际skip/catch-up、H2当前head-only成本与召回仍未实测。
- K-PAIR无GPU资格；M0未在用户部署回归。
- 旧H1/H3/K1及StrataDF2等关闭状态不变，P05/长检索质量缺口不解除。
- 新的引擎改造、CPU运行时validator、统计实现、GPU数值/状态/服务/性能均NOT_RUN。

独立技术结论：修订后可交付**研究与执行规格包**；不等于存在已证实的4090净收益。文件校验范围见[VERIFICATION](VERIFICATION.md)。
