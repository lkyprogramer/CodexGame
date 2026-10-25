> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# tqLLM 借鉴与 NInfer 后续融合：执行摘要

**结论：可行，但应吸收算法、算子与验证方法，不应把两个推理引擎直接合并。** 先交付现有MTP/Lookup/完整验证链路的收益，再以独立资格门槛推进27B DFlash2与全局草稿检索。这里的“可行”指设计和源码接入路径成立，不代表24GB显存与性能收益已经实测成立。

## 固定范围与入口

本扩展接在原包P0—P6之后；P7必须消费真实通过的P6-GATE与其提交，不能以U的SHA代替尚未完成的合并结果。原U=`5b99996bc7c1fe6ff27f271a205eb605302ec8bb`；tqLLM参考T=`4d27324a124f92b7b7dcc554e6406ab6dc645b49`。冻结参考版本可复现，不追随main漂移。具体源依据见[证据目录](09-source-evidence.md)。

用户目标仍为单RTX4090、64GB主机内存、Qwen3.8-27B、长上下文Java/Coding Agent；不换Target权重、不缩短既定上下文、不取消B0、计时、ReplaySSM、continuation cache或接口兼容。P4之后基线是新版`rk4v4`，不是附件末尾的`rk4v4-e8`。新格式保留原包隔离缓存的要求。

## 三类工作

| 类别 | 纳入内容 | 发布条件 |
|---|---|---|
| 低成本主线 | 精确观测、MTP K选择、Prompt Lookup链、已有完整KV验证优化 | P8/P9统一gate；相同Target质量与真实wall time成立 |
| 有条件高收益 | 原生27B DFlash2 companion、固定ring、受限draft词表；独立草稿archive与全局检索 | 默认启用须模型、显存、精确性、长上下文与增益均满足；研究阶段单独记录准入 |
| 不进入首轮 | Token tree、稀疏Target验证、Target TQ3/TQ4换权、TCQ新KV、训练专用长上下文drafter | 仅有触发条件及后续研究说明，不假冒本轮必交付 |

## 四个不能被跳过的结论

1. NInfer27B在U中`DFlashConfig::supported=false`、最大DFlash草稿数0；35B已有DFlash不是27B DFlash2绑定。需要新增companion artifact、特征与算子链，不是开启已有开关。[N01/N03]
2. tqLLM检索原型只选择最近4096个16-token远端chunk，启用时将ring置0，失去对应draft graph和批量fast path。借鉴的是分数/选择/RoPE思想，必须重构候选覆盖与内存生命周期。[T03—T06]
3. NInfer已有131072-row优化proposal head、small-T1—6、TargetVerifyFrameView与ReplaySSM；应在这些边界扩展，不建立第二套验证/提交权威。[N02/N05/N07]
4. 不能用Target KV或GDN状态伪装Draft KV；DFlash2从指定Target层hidden features投影生成自己的历史状态。已有Target L2恢复不会自动恢复这些特征。[T04]

## 收益假设与止损

不承诺250tok/s或固定倍数。tqLLM的3090、TQ量化Target、短推理文本结果不能移植为NInfer的4090、groupwise-int、128K—248K代码性能。[T01/T08]

候选收益至少同时报告：已提交tokens/执行时间、HTTP首token延迟、完整多轮Agent wall time、接受率、显存和主机内存峰值。P10/P11的建议默认采用门槛是128K decode中位数提升至少15%，并且不违反原包延迟/回退门槛；这是本计划的采用标准，不是已有测量。预算/正确性失败则高级阶段BLOCKED；只有收益不足则promotion=DECLINED且默认off。完成真实实验与不采用决定仍是有效交付，但不能声称新功能性能合格。

## 交付物性质

本扩展包含设计、32个实施task、6个统一gate、机器可读DAG/验收矩阵、CPU预算与覆盖oracle工具。所有NInfer开发、CUDA构建和GPU资格均待实施。工具自测只证明这些Python计算与门禁辅助工具的受测行为。
