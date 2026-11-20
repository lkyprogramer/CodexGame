# 外部项目结论：先测本机路径，不接收外部提速数字

截至 2026-11-20（北京时间）。本章是设计门禁，不是基准结果。
本地新基线尚未绑定，也没有进行 GPU 运行验证。历史实测资产是 Qwen3.8-Flash-Next GSQ-RCO IQ3_XXS 两分片、Xeon Silver 4216、PCIe Gen3 ×16；不要用 IQ3_S、旧 MTP spec4 或 donor 的配置冒充现在的运行状态。
正式 A/B 的模型与分片哈希、量化、KV、模板、采样、MTP、硬件与实际运行机制均由基线绑定。

## 哪些外部事实改变了行动

| 来源 | 从一手证据能确认什么 | 为什么不能直接搬到 4090 | 本轮处理 |
|---|---|---|---|
| [QuixiInfer `ce25391`](https://github.com/QuixiAI/QuixiInfer/tree/ce25391bff43ac9bb101e8d1f62e3705f8972494) | 强制长位置、按路径记账、冷暖分层；当前模型是 DeepSeek-V4.1-Flash，CPU/RAM/NVMe 明确受约束 | RTX 5090、128GB DDR5、不同模型/后端；其历史 Flash-Next 已借了 Strata 的工作区方案 | 借测量规程和反例；不重开工作区借用、专家分层或主机/PCIe 比例扫参 |
| [Kinetic `f3723b1`](https://github.com/Veloresearch/kinetic/tree/f3723b1e046cc7e1d013de160402f58d819ab423) | 多源 draft 和 rollback 可读；树在默认成本下关闭；Flywheel 真实有 host/PCIe 冷专家分派 | 4.5× 是小模型复写，普通生成约 1.02×；“hit”包括刚放进 cache 的专家 | 借来源歧义、宽度/提交成本和互斥等待定义；不移植树/Flywheel |
| [Speedy `7d500de`](https://github.com/DevDock-AI/Speedy/tree/7d500de0067f8fb31a9da1fbef16a303f790dacc) | 8-gram 辅索引会找回被短键桶覆盖的同会话旧位置；CPU 轻专家跨层加入改变输出 | 3080 + 八通道 RAM 的旧基准；上游已有同类小 scratch/routed/rewind-keep | **C01：只做固定 token 的离线碰撞反事实**；不能随方案一起改变 verifier、默认采样、tail skip 或工具行为 |
| [FlashInfer v0.7.5](https://github.com/flashinfer-ai/flashinfer/tree/9aa920602276537b27e017a762a71e3437fc7f0d) / [main `6fd1320`](https://github.com/flashinfer-ai/flashinfer/commit/6fd1320260a8224b8a0d69c8cca8235aed65b3b2) | 发布 tag 与 main 的 QSA sparse API 边界不同；QSA毕业提交为`1658f0b`，不是main HEAD；利用trace形状合同、候选tactic ID、实测覆盖/获胜差距 | API 存在不证明 Flash-Next 当前 QSA/KV 布局、比特或 Ada dispatch 可替换 | 借 shape/dispatch 清单、coverage、margin 和证据格式；不换库/注意力实现 |
| [Blink / 论文原文](https://arxiv.org/abs/2604.07609) | 论文结论受实验模型、硬件、布局、实现和指标定义约束 | 论文图表不是当前设备、当前 Flash-Next 合同的执行结果，不能替代本机归因 | 仅做证据和方法对照；不安排 Blink 移植、不据此重开旧 HC 或相关 kernel 优化 |
| [PolyStrata `3e16421`](https://github.com/simplexai-labs/PolyStrata/tree/3e1642161198c50ff1abed4046f4e4f476099dbb) | `strata-poly` 的 staged-expert 按大小分 MMQ launch 可减少逻辑填充；AMD 有预填收益；NVIDIA 出现输出分叉 | Flash-Next 用继承的 Strata 引擎；新实验在 Tiel/AMD 路径；Ada stream-k 归约重排 | **C02：只采实际启动形状和关键路径填充损失**；拒绝直接搬分组 launch |

### Strata 对照钉在当前上游，而非 fork 当年的起点

- [Strata `58ee322`](https://github.com/Niko1221/Strata/tree/58ee3227720629ff2e41d640165ebe89c880dfef) 是读取的 main；[发布 v0.2.16 的 annotated tag](https://api.github.com/repos/Niko1221/Strata/git/tags/acdcf162fd4af0e566b4d4bbc49f71c4c14e350a) 指向 `64524fb9fc82222ddce554c0643b64f056ec8366`。安装包实际 SHA 与路径仍以现场采集为准。
- Speedy 自报复制底座是 [v0.2.7.1，见 patch ledger](https://github.com/DevDock-AI/Speedy/blob/7d500de0067f8fb31a9da1fbef16a303f790dacc/SPEEDY.md#L1-L26)。旧基准只能解释旧变化，不能当“新版 Strata 没有”。
- [Poly 与主线 compare](https://api.github.com/repos/Niko1221/Strata/compare/58ee3227720629ff2e41d640165ebe89c880dfef...3e1642161198c50ff1abed4046f4e4f476099dbb) 确认共同祖先 `477ac13cbe8e582c20484871ce459d20d82df09d`、已分叉；结果不能按祖先版本的旧代码直接外推。
- 最新 Strata 的 [all-MMQ group scratch 与 HC region](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/src/prefill/prefill.cpp#L2131-L2174)、[routed prompt issuer](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/src/prefill/prefill.cpp#L4530-L4556)、[rewind keep](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/docs/DETAILS.md#L760-L778) 均有实现或入口。某个 upstream PR 未合不代表机制不存在；反过来，env 已配置也不证明此次 dispatch 命中。

## 同一个 Trace 需要回答哪些问题

| 关键问题 | 必要字段/事件 | 什么不能拿来顶替 |
|---|---|---|
| 同一位置的实际瓶颈是否变化？ | 请求与轮次 ID、pos、prompt 类别、cold/warm/restore、实际 kernel/路径、wall critical phase | 只对比 tok/s，或只用 CUDA kernel 活跃之和 |
| Draft 是否真正减少总工作？ | `source`、候选/命中长度、策略选择、实际 verify width、accepted/committed、reject/rollback/replay、轮时与每条有效提交时间 | acceptance 百分比、candidate K 或单条复写展示 |
| MoE 慢在排队、搬运还是计算？ | route 专家唯一数和有效行；resident-before-demand、new-admit、host/stage/transfer bytes、ready/late；CPU/DMA/GPU 的实际交叠与关键等待 | donor 自定义 hit rate，或相加重叠区间做百分比饼图 |
| 有效行填充真能值得更换 kernel？ | `phase`, `dispatch`, quant / shape / tile、实际 expert rows 与实际发射逻辑行、staging round、critical kernel 时间 | 局部 GPU 利用率或 padding 比例直接等同端到端提速 |
| warm start 改变的是哪一块？ | 服务端计算 ready/first-byte、客户端 first-byte、cache scope/有效 prefix/replay、启动到可用、稳态占用 | “after Enter”当纯 prefill，或把磁盘恢复当作免费缓存 |

只做有界采集：粗粒度长时间计数用于稳态，trace/detail 采样只用于定位，不把重观测开销带入候选收益统计。对齐工具版、记录 profiling time base，清楚区分互斥时间和重叠工作。
需要判断多个现象时先追问：它们能否在同一工作负载的短/长位置、copy-heavy/non-copy、冷启动/热续聊里复现？如果只在一个模型专门摆拍的 fixture 上出现，不算生产证据。

## 两条前置假说与淘汰规则

**C01：是否因有限 trigram 桶覆盖而错过同会话可验证的长后缀？**

1. 保存受授权的同会话已提交 token，不扩大数据边界；固定 prompts、position、policy 和实际轮时，回放当前 3-gram 与 3+8-gram。
2. 记录真正被挤出的旧位置、恢复长度、按已提交轨迹计算的 oracle 前缀、会被现行策略选择的比例，以及哈希、查找和 RAM 开销；oracle 不等于实际 GPU acceptance。
3. 如果不是频发，或换索引后仍没有可观端到端上界，就关闭，不做 engine patch。不能靠新 DFlash2、切采样或跨用户 corpus 把它救活。

**C02：真正进入当前 CUDA kernel 的 expert 组是否有可通过等价执行避免的填充？**

1. 优先复用128K总窗内合法长prefill原件（P0锁定输入长度，如约100K），记录运行pack形状、现行dispatch与staged/resident分布；warm tool suffix仅在既有轨迹或获批CASE支持时纳入，不试开关扫参。
2. 看实际 tile 的分母和排除重叠后的 kernel wall，保守定上界；不拿 AMD 43% occupancy 举例作为本机输入。
3. 如果填充不在关键路径、已被现行 fused/tile 选择吸收，或改变 NVIDIA 归约顺序，停止；否则只保留进一步等价设计的入口。

正式收益筛选按 [18_CANDIDATES_AND_STOP_RULES.md](18_CANDIDATES_AND_STOP_RULES.md)：至少 **4%，且超过 2× A/A 噪声**；筛选阶段是不可能过门即停止，过门的上界并非实测通过。低于门槛仍有容量/可维护性价值的观察另记，不当作当前性能胜利。
历史已关的动态 workspace/expert lending、专家 tier/去重、通用 prefill scheduling、CPU-gap、HC/细粒度 kernel 方向继续保持关闭；只有绑定后的新路径证据改变前提且出现足够 wall 上界，才单独重新提案。

## 如何避免滑回“先做再测”

- 第一个产物是能审计 A/A 和路径的 manifest/数据，不是 fork、补丁或运行命令的一组新默认。
- 不把同一请求跨样本复写、剪掉 prefill 的快数字、在 NVFP4/不同 pack 上跑得快，以及隐藏 output mismatch 计作成果。
- 保留失败：旧路径未激活、几何瓶颈不存在、copy-heavy 受益不覆现实、seed/cache 生命周期不等价，各自有独立终止理由。
- 若 C01/C02 的可行上界都过不了门，保留现配置，交付数据和明确 no-go；不用补造第三条优化路线。

## 给复核者的证据层级

1. **已读源码**：固定 SHA、实际函数、编译条件和参数默认值。只证明能力写在这个快照，不证明本机已进入。
2. **外部实测**：设备、包、位置、并发、缓存和指标必须与数字同列。只用于解释机制，不算本机结果。
3. **本机已验证**：必须有现场 manifest、原始采样、A/A 数据以及实际路径。此交付没有这一层性能结果。
4. **条件化推断**：每个候选必须给出最高可回收时间、测量开销与淘汰理由；不可观测的字段标为缺失，不填零。

跨项目只综合同口径事实，不求平均，也不造排行榜。同属“复写加速”的两个证据若依赖不同 input/cache，不能相加；同属“MoE 命中”的两个计数若定义不同，必须先重定义事件再用。

数据字段、A/A 执行和计时边界见 [05_DATA_MODEL_AND_MEASUREMENT.md](05_DATA_MODEL_AND_MEASUREMENT.md)。
