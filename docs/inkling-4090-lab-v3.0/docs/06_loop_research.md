# 06 · 循环研究

v3.0.7 按用户提交的研究评审（仓库 `docs/Inkling-4090-Lab-v3-Research-Review-2026-11-26.md`，下称“评审”）核实后重写：R1–R7 补全实验设计，新增 R8–R10。任务依赖以 [07](07_tasks.md) 为准。

前提：G2（T19 复核后）通过，T15（探针）完成；R1 另需 T18。所有实验在 Astral fork 上进行，数据按 [05](05_validation.md) §7 的格式写入 `$LAB/runs/<任务>/<UTC 时间戳>/`。分析在 4090 主机的 CPU 上做，不在本地开发机上做。

## 1. 语义约定（所有实验共用）

### 1.1 坐标

探针和结论统一使用 `(token_position, physical_layer, pass, logical_visit, stage)`。固定三遍时：prelude 物理层 0–5，core 6–17 跑 3 遍，coda 18–23，共 6 + 12 × 3 + 6 = 48 个 visit（HF `core_start: 6, core_end: 18`，开区间；S21）。物理层表示共享的参数，pass 表示遍次，visit 表示执行顺序，三者不能互相替代。

每遍 core 都从 prelude 的输出和本遍的块状态开始；第二遍起才通过 controller 读取上一遍的消息，不是把上一遍末尾的一个 residual 原样往下跑。每个 pass 的 KV 和 conv 历史分别存放（HF 实现对每个 pass 深拷贝一份 cache 层，S21 已核实）。

### 1.2 状态表

| 对象 | 参数跨遍共享 | 状态跨遍共享 | 实验时必须记录 |
|---|---|---|---|
| core 投影与专家权重 | 是（同一物理层） | 不适用 | 物理张量身份、量化格式 |
| core 注意力 KV | 不适用 | 默认按 pass 独立 | 读哪一遍的历史、当前 token 写进哪一遍 |
| K / V / 注意力输出 / FFN 输出的短卷积 | 是 | 按 visit 独立 | ring 指针、有效长度、回滚版本 |
| 注意力残差（块 mix） | 按定义使用 | 当前块与跨遍消息分别管理 | 块编号、归一化前后 |
| controller | 是 | 输入来自不同 pass | 输入、消息、gain、forget |
| DSpark 特征 | — | 按 feature stash 位置读取，不按物理层取 | slot 约定（`[5,23,41,48]` 要对照代码中的实际 stash 位置解释） |
| CUDA graph | 固定执行结构 | 依赖稳定的地址和形状 | 遍数、capacity、verify 长度 |

controller 的 gain 和 forget 都是 **tanh**（HF 实现，S21 已核实），不是概率：keep = 1 − forget 可以大于 1，gain 可以为负。不能把它们解释成“保留百分比”。

### 1.3 四类变化

| 类别 | 例子 | 评价方式 |
|---|---|---|
| 表示 / 状态的等价变换 | 无损打包、同值重排 | 逐位往返与状态不变量 |
| 同一数学的实现变化 | 融合、不同 reduction、不同 MMA | 数值误差（[05](05_validation.md) §6）与回归 |
| 推理策略变化 | 跨遍共享 KV、LoopCD、早停 | 新策略的质量 / 成本权衡 |
| 模型变化 | 换 checkpoint、微调 controller | 新模型对照，不算原模型的无损加速 |

同一专家在多遍被选中只说明参数被重用；输入变了，专家输出仍要重算。KV 历史相似也不等于可以直接别名共享。

### 1.4 三种读出

| 名称 | 定义 | 用途 |
|---|---|---|
| raw lens | 中间表示直接过 output norm + head | 便宜，快速定位变化 |
| coda lens | 对指定深度的完整块状态跑 coda（6 层、块 mix、norm、head、softcap），注明 coda 的历史从哪来 | 中间表示的可读出性 |
| native-r | 整个 prefill / decode 都执行 r 遍 | 真实的 r 遍模型 |

对一个 token 复用最终深度的 coda 缓存，与整个前缀都按浅深度重算，是两个不同的实验。coda lens 有真实成本（6 层 + 大词表 head），估算早停收益时必须计入。

## 2. 研究项

| ID | 问题 | 方法要点 | 指标 | 模型 |
|---|---|---|---|---|
| R1 | 额外的循环解决什么问题 | 主实验是 A4 在 1–5 遍（训练分布内：varloop 在中训练后段按 1:2:6:2:1 抽样 1–5 遍，之后以 3 遍做 post-training，S02 已核实）；A1 只测 3 遍和少量 1、2 遍作截断敏感性对照；6、10 遍单列为外推。每个深度从同一前缀**重建**自己的历史，不跨深度复用缓存。任务加三类小集：可生成的 N-hop 查找（按 hop 数和干扰分桶）、有确定答案的代码 / 数学题、多位置长依赖查找 | NLL / PPL、任务正确率、生成长度、截断率、整题用时、正确任务 / 秒。与三遍的 KL 变大不等于变差 | A4，A1 对照 |
| R2 | 每一遍在做什么 | 先落实 §1.4 的三种读出；看正确 token 的 log-prob 是否随遍次改善、哪些位置最后一遍才修正、块消息权重与异常激活是否提前预示修正；专门找“相邻遍余弦高但答案变了”的反例 | 每遍的正确 token log-prob、修正位置分布、反例 | A1、A4 |
| R3 | 跨遍的专家选择 | 记录 top-8 集合与选择分数、第 8 / 9 名的 margin、同一专家输入的变化、专家耗时与权重读取估计、同一物理专家的访问距离。A1 全驻显存，研究对象是 DRAM / L2 局部性和小批分组，不是 CPU offload。复用专家**输出**属于新的近似策略，要单独评估 | Jaccard、路由翻转率与 margin 的关系、访问距离 | A1 |
| R4 | 跨遍共享 KV | 三臂，在 8K 内做，不等 T17：**A** per-pass（基线）；**B** last-history，仿 PR51161：核心全局层的历史只由末遍写入，前面的 pass 只读末遍的历史、自己算出的当前 token K/V 不持久化，conv 按 pass 独立（S25 已核实；这是借鉴 PR 的新实验臂，不称为原样复现）；**C** first-pass，仿 prototux：后续 pass 的**全局层**直接读首遍存下的 K/V，自己不存，并跳过这些层的 K/V 投影和 K/V conv；SWA 层和 conv 状态仍按 pass 独立（S15 已核实）。prototux 仓库 README 报告 C 在 3000 token 贪心生成中出现复读，这不能直接否定 B；PR 的短样本一致也不能证明 B 普遍无损。每臂写明 `scope、history_source_pass、current_token_source、write_pass、conv_policy、prefill_chunk_policy` | 与 A 的 KL（[05](05_validation.md) §6 口径）、2K token 长生成的 n-gram 复读率、显存节省 | A1、A4 |
| R5 | controller 的因果作用 | 分开六种：原始；只去 gain 项；只去 forget 项；gain = forget = 0（恒等合并）；替换消息内容但保留 reader / gate；恢复某个 block 或 pass 的正确消息。先做单点干预（一个 token、一个 block、一个 pass），再考虑整遍消融；大范围置零会让表示离开训练分布，只能说明依赖性 | 正确答案概率、局部 winner-gap、后续路由、任务结果（不只看 PPL） | A1 |
| R6 | 早停是否值得做 | 三步：① 在完整深度的 trace 上做离线 oracle，得到乐观上界；② 计入 coda / head、探针、状态保存和补算的成本，上界都不够就停；③ 只选一种历史策略（整请求固定深度 / 提交前补齐 / 延后补齐 / 近似历史）。第一版只做“按请求固定 1–5 遍”的质量—延迟曲线；逐 token 动态深度放到后面。不能把 R2 的 raw-lens KL 阈值直接写成循环 break | oracle 上界、计入成本后的净收益 | A4 |
| R7 | 草稿器 | 先优化原生 DSpark（T21），再评估 DFlash2（A5）或 2DSD 的 loop-conditioned drafter。每个草稿器固定：目标权重与量化 hash、遍数与 cache 策略、feature tap 到 stash 位置的映射、embedding 归一化 / head / softcap / correction 顺序、词表范围与 mask、anchor 与 block 长度、接受 / 拒绝 / 状态恢复规则。有效吞吐 = 提交 token ÷ 真实轮次 wall time（重叠部分不重复相加）。平均接受长度提高不保证加速 | `draft_ms、verify_ms、rollback_ms、committed_tokens、accepted_prefix、bonus_tokens、expert_union_size` | A1 + A3 / A5 |
| R8 | 量化误差经循环是放大还是被修正 | A1 是 NVFP4、Q8_0、BF16、F32 混合，不是单一 4 位。分开研究：权重表示误差（同一原始资产转换前后，按物理层）、算术误差（固定权重，切换局部累加 / 舍入路径）、路由不连续（第 8 / 9 名 margin 附近的专家集合变化）、跨遍传播（只在一个 pass 的一个算子注入或恢复误差）、coda 敏感性。“只给第二遍升 Q8”需要第二份权重或运行时转换，先证明某阶段确实敏感再考虑 | 高 margin token、异常激活坐标、块选择与专家选择的变化（不只看平均 KL） | A1、A4 |
| R9 | 收益来自当前 token 的深度还是历史的深度 | 明确标为反事实的 2 × 2：历史浅 / 深 × 当前 token 浅 / 深。先定义浅 / 深历史的映射（首遍是否锚定、后续 pass 读哪个源缓存、conv 边界如何接续），不得把缺失的 cache 当零或复用最后一个 slot。先在固定 teacher-forced 前缀的少量位置离线做（参考 LoopBridge S14、Late Entry、Loop Behind；后两者不是 Inkling 实验，部分需要训练） | 正确 token 概率、coda 输出、路由；若“深历史 + 浅当前”接近 D，才继续 | A4、A1 |
| R10 | （可选）局部稳定性 | 固定输入、历史与路由策略，在一个消息或 block 状态上加若干方向、若干幅度的小扰动，比较下一遍和最终读出的变化；按路由是否改变分组。局部增益 `‖δout‖ / ‖δin‖` 只是局部量，不是全局收敛证明（状态不止一个向量，top-k 路由不连续） | 局部增益分布、放大位置 | A1 |

## 3. 探针设计（T15 的研究需求）

第一版只在选定 token 和块边界记录，不全层、全 token、全词表落盘：

| 探针 | 回答的问题 | 记录 |
|---|---|---|
| prelude / core block / coda 输出 | 信息在哪个阶段改变 | RMS、最大值、分位数、少数异常坐标的能量占比 |
| 注意力残差（块 mix） | 当前输入读取哪些块 | softmax 权重、reader score、来源块 |
| 跨遍消息 | 上一遍哪些信息传到下一遍 | 消息范数、reader 权重、输入与消息的相关性 |
| controller | 放大、抵消还是保留 | gain、forget、keep 的分布与输出贡献 |
| MoE 路由 | 是否走不同的专家路径 | top-8、选择分数、第 8 / 9 名差距、实际专家权重 |
| 注意力 | 近处还是远处取信息 | near / far / sink 概率质量，抽样熵 |
| 读出 | 中间信息能否用于预测 | raw / coda / native-r 分别标记 |

完整 logits 只为重算 KL、定位分歧或读出校准而保存；**top-k 日志不能代替完整归一化的 KL**。探针不能改变被研究的行为：按位置批量取回小数据，不在每个算子后同步；d17a519 加的同步不能在加探针时顺手删掉。

**Goodfire 的结果作为第一个复现目标**（S26 已核实）：他们在 Inkling-2-Mini 上发现少数巨大的异常激活决定跨遍读哪些块（坐标 2027 / 2304，RMS 归一化后约 +32.4，占平方范数 46%），并比较了 logit lens、tuned lens、coda lens。两步走：① 在 A1（量化后）和自己的输入上重新找异常坐标与块读取行为，2027 只作线索；② 单点干预（替换一个 token、一个 block、一个 pass 的消息或坐标），加同范数随机方向作对照。相关性消失时先查采样位置和量化影响；相关存在但干预无效，就记录为因果解释不成立。

## 4. KV 压缩的定位

KV 压缩不进主线，先等 T17 的 SWA ring 给出结构性的容量收益（[01](01_model.md) §3）。之后若仍需要，只做两个小实验：

- **无损编码**（参考 LoomKV / GAAC / SplitZip）：Astral 的 KV 是 **F16**，LoomKV 的 0.71 压缩比针对 BF16（FP8 为 0.85–0.87，S27 已核实），不能直接继承；先在实际写入点采样 K/V，按层 / pass / head / K、V 统计位模式和 XOR delta 的熵，计入 metadata 和工作区后再算净收益。
- **模型特定的有损量化**（参考 Inkling SRFT KV，S28）：在 Apple M6 / Metal 上做，SRFT + Lloyd–Max 量化是有损的（2.06 bit 时 ΔPPL +0.130）；质量只测了 WikiText-2 PPL 和 32K 以内的 passkey；256K–1M 的计时用的是合成 K/V（已核实 `bench_lm2_1m.py`）。可迁移的点：Astral 的 V 写入路径是 short conv → 无可学习 gain 的 per-head RMSNorm → F16 存储，支持研究不带 scale 的 V 量化，但先实测存储后的范数分布。量化误差与 kernel 误差分开测：量化后的 attention 先对“解码回同一组量化 K/V 的参考 attention”，再对原 F16。

停止条件：ring 已解决目标容量；含工作区后净节省很小；原始模式不受 KV 带宽限制；真实代码 / 中文 / 长依赖上质量损失不可接受；需要复制整套长缓存才能读出或回滚。

## 5. 规则

- 每项研究先写假设与判据，再看数据；结论分为“支持 / 不支持 / 不确定”，注明样本量。没有性能提升不算研究失败。
- 先做 16–32 个 case 的小实验再决定是否扩大；几千个 token 的细粒度测量用于定位机制，不能代替足够多独立题目的质量结论。
- 改变模型行为的实验（R1、R4、R5、R6、R9）必须带开关，关闭时与 G2 基线逐位一致。逐位比较只在 step 路径上做：prefill 路径两次运行本来就不逐位相同（[05](05_validation.md) §6.5），在 prefill 上用容差口径。
- 每次干预只改一个因素；独立改动都有证据之后才组合，组合先做最小的 2 × 2 检查交互。
- 发现值得做成功能的结果，另立任务，经过 G2 后才能默认开启。
- 外部论文和项目（LoopCD、ARLoop、LoopSpec、LoopCache、Late Entry、PackLoop、Loop Behind、2DSD 等）只作方法参考，各自的模型和硬件条件不同，峰值数字不能套到 A1 + 4090；按 R2 / R7 / R9 的小实验结果决定是否深入。
