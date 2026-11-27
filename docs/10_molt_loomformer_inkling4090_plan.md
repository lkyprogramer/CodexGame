# Inkling 4090 自有引擎底层定制方案

## MoLT、LoomFormer、mlx-serve #1331 / #1330 与最新 Astral fork 的统一方案

> **执行代理说明：**实施时按任务逐项推进，可采用 superpowers:subagent-driven-development 或 superpowers:executing-plans；每项使用下面的复选步骤，GPU 实验仍在同一张卡上串行。本次交付是方案和源码审查，未修改引擎、未推送仓库、未执行新的 4090 测量。

**Goal：**将自有 Rust + CUDA 引擎建设成专用于 Inkling 循环结构、RTX 4090 和单请求深度研究的工具，完成可归因的底层优化，并以小规模实验检验新的记忆架构。

**Architecture：**围绕 Inkling 的真实依赖建立静态 visit/slot 表、每遍不变的消息预计算和可提交的缓存状态；沿用现有计算路径与数值合同。MoLT 的严格前缀反馈和 LoomFormer 的头级矩阵记忆进入独立研究臂，训练与模型身份显式区分。

**Tech Stack：**Rust 1.100、CUDA 12.8.93、sm_89、单 RTX 4090；现有原生 CUDA Graph、手写 CUDA、Python 离线判定器。研究训练脚本不进入生产 Rust 依赖。

**Spec：**本文第 1–12 节是设计定义，第 13–16 节是实施与验收计划；原执行合同和唯一任务清单仍是 CodexGame 的 docs/inkling-4090-lab-v3.0/AGENTS.md 与 docs/inkling-4090-lab-v3.0/docs/07_tasks.md。新增依赖须同步到后者后再执行。

**版本与时间：**提案 1.0，2026-11-26，北京时间。审查期间引擎和实验室继续更新，已追到 22:16 的 v3.0.11；源码锁定如下，实施时先检查是否发生后续变更。

| 对象 | 本次固定身份 | 作用 |
|---|---|---|
| 自有引擎 | lkyprogramer/inkling-4090-engine，main，18bf3e338a08bd66223b0bc5aaa26f3896fb9446 | 代码事实基线 |
| 实验室 | lkyprogramer/CodexGame，4090-report，9f6d4b030ba26b51af2a41edfba2679febd104ee | v3.0.11，任务与执行证据 |
| MoLT | arXiv:2611.34923v1；hustvl/MoLT，1313b83adf05f666726bf009014f5f50ae345b23 | 严格前缀反馈与读写解耦 |
| LoomFormer | arXiv:2611.30634v2；Caiyun-AI/LoomFormer，e52e5761d36066ed62e061a044d8314437cb7b11 | 头级动态连接、矩阵状态与融合实现 |
| mlx-serve #1331 | head ad695002aa89fda7ac27b901d7474ddc84299af8，已合并 | 推测执行、候选状态、成本与 kernel |
| mlx-serve #1330 | head 6a22c34e558579a27a52fa4fb3a94a49d3a6c41c，开放 Draft | 部分整合、请求隔离、成本表、数值合同 |
| 目标模型 | A1：Inkling-2-Mini-UD-Q4_K_XL.gguf，SHA256 e64276656f072e9b2197a61723667cbdb71da66a716ffd966e572c21088f3cd3 | 同资产原模型对照 |
| 数值参考 | llama.cpp b12751，532d674；完整身份沿用 models.lock 与现有来源表 | 不自动升级参考 |

### Global Constraints

- 原模型基线固定 A1、三遍循环、同一量化权重；改变遍数、缓存来源或消息含义，单列推理策略或新模型实验。
- 只针对 Inkling 与 sm_89；不新增通用调度平台、存储服务、跨模型插件系统或专家 SSD 方案。
- 使用现有驱动与工具链；执行时继承现场驱动守卫、生产状态和已授权窗口，不由本方案改变现场权限。
- 每个改动一个可归因提交；关闭新功能时恢复原基线；GPU 测量串行。
- 保留 V4–V8 和 num-3 已批准合同。本文新增的候选筛选标准属于提案，不能反向改写历史 PASS/FAIL。
- 完整 logits、原始时间记录及权重不必进入 Git，但必须保存路径、SHA256、生成命令；统计摘要不能代替原始证据。
- 模型资产、缓存布局、遍数、精度、探针状态、graph key 和代码 SHA 一并进入 run.json。

### Review Focus

1. 同一物理层、逻辑 slot、执行 visit 三者错配，尤其 coda slot 与 DSpark feature tap。
2. SWA 批量写覆盖尚需读取的旧历史；推测拒绝后只回退位置而没有恢复内容。
3. CUDA Graph 捕获旧指针、旧布局或共享 split 工作区被两个 stream 同时使用。
4. “内存已分配”被当作“数据已有效”，尤其 QAct 的 FP16 平面和实验探针。
5. 从短序列、汇总比值或论文的小模型结果推出全上下文、逐位置或 4090 性能结论。

---

## 1. 结论与首轮执行顺序

最值得做的主线是：**先补非零输入的底层数值测试，承接最新 T20 的已测覆盖与长文失败记录，再实现每遍不变的消息计算，随后完成 SWA 的暂存与提交机制。**这些工作能够直接改变当前引擎的计算或存储成本，同时保留三遍模型的数学定义。

LoomFormer 值得纳入，但其主要贡献是提高信息传递的表达能力，不能当成给现有 Inkling 直接提速的 kernel。它最适合补充两个方向：头级因果探针；未来新模型中的内容矩阵与读写融合。MoLT 则指导我们寻找哪些同位置依赖可以通过训练迁移到历史记忆。

建议推进顺序：

1. T22：补 QAct/FP16 有效性与非零 MMA3 测试；校正 T17/T20 状态行，保留 T20 长文 num-3 FAIL，补真实 nv=3/5/7 与新状态专项。
2. T23：将实际的 48 次执行与状态映射显式化，支撑 T15/T17/T18。
3. T24：上一遍消息批量读取、共享源归一化、controller 的消息半支预计算。
4. T17：40 个 SWA slot 改为环形缓存，并完整处理 prefill 暂存和推测提交。
5. T16：按真实消费者省去激活平面写入，再选择短 prefill expert tile 或 attention split 调优。
6. T21：草稿缓存和轮次成本优化。
7. R11–R13：头级因果研究、严格前缀可替代性、小模型架构对照；有证据再训练大模型适配器。

这里的顺序允许 CPU 侧准备并行；实际卡上实验仍串行。T17 的设计准备不必等待 T24 得出性能结论。

## 2. 最新项目状态：哪些已经完成，哪些还缺

### 2.1 不能沿用早先 v3.0.4 的判断

| 项目 | 最新状态 | 证据范围 |
|---|---|---|
| 独立 Astral fork | 已建立并跟踪 main | 不再以三份 format-patch 作为当前源码 |
| sm_89 档案与构建 | 已完成 | c240d53；实际构建含 sm_89 |
| legacy stream 上传/清零竞态 | 已修复 | d17a519；不能为减少同步直接删掉 |
| prefill 两条浮点 split-K 不确定性 | 已修复 | 35de94a；固定分片工作区与定序求和 |
| V7 num-3 | C 集 PASS | 16 个新 prompt × 5 个长度，80 个位置 |
| G2 | T19 已解除有条件通过；适用范围不能外推 | v3.0.10 短序列复判；v3.0.11 的 D 长文 FAIL 另列 |
| G3 | 已有实测 PASS 记录 | T14：32 prompt × 5 次、512 token、ctx 8192 |
| T20 | 已执行，记录判交付 PASS；数值结果有 PASS 与 FAIL | v3.0.11：B 短序列各路径 PASS；D 长文 num-3 FAIL；密集 V4 通过 |
| T17 | 实现尚未完成；任务表误标 PASS | 最新引擎只增加诊断，没有 ring 或 8K 以上扩展 |
| T15、T16、T18、T21 | NOT_RUN | 探针、进一步调优、varloop、成本模型 |
| R1–R10 | 仍是研究任务 | 不能把方案文字当作机制实证 |

依据：[L01]、[L02]、[E01]、[E02]。

### 2.2 性能基线用正式 T14 口径

| 配置 | Decode tok/s | 备注 |
|---|---:|---|
| Astral，无草稿 | 143.1 | ITL p50/p95 7.01/7.05 ms；TTFT p50 90 ms |
| Astral，DSpark，自适应 k≤6 | 173.9 | 各 prompt 约 141–271 tok/s |
| llama.cpp，无草稿 | 74.7 | 同 A1、开启 Flash Attention |
| llama.cpp，DSpark k=3 | 90.5 | 同请求口径 |

配对几何平均：Astral 对 llama.cpp 无草稿 1.92×；Astral 的 DSpark 相对自身无草稿 1.20×。早期 T13 的约 183 tok/s 是另一轮记录，不用它替代正式 T14 数字。[E02][L02]

T14 的逐请求原始结果主要留在现场目录，Git 中能读到方法、脚本和结果记录。本次没有从 Git 重新算出 1.92×，也没有在 4090 上复跑。后续候选必须对固定的新基线重新做同机配对，不能只对一个历史均值报收益。

### 2.3 num-3 的真实含义

本次用仓库已有 JSONL 和当前判定器离线复算，A/B/C 的判定对象与提交 JSON 一致，C 的汇总判定可离线复算一致。判定用的是**同一位置集合上各汇总量的比值**：

- near_w 的 mean、p90；
- KL 的 mean、p90、max；
- 上述候选汇总量 / 参考形状噪声的同名汇总量 ≤ 2。

此外，候选 step/prefill 的 argmax 若变化，step 侧 top-2 margin 必须小于 0.5；候选和参考两套数据都须匹配预期位置集合，完整、唯一、无额外项且有限。任一硬条件不满足都不能判 PASS。T19 C 的执行身份是 f8c976e；本次源码审查从 fc5be35 追到 18bf3e3，不能把历史运行说成对任意未来 HEAD 的验证。

它不是要求每一个位置的误差比值都 ≤ 2。C 集出现个别位置比值较大并不违反合同，尤其参考误差接近零时。C 集实际前缀长度约 31–204，不能证明 1024 滑窗边界、8K 或多种 verify 批长已通过。[L03][L04][E10]

重复性记录分别为 step 0/208 个文件不同、prefill 0/208 个文件不同。将“两个路径各比较 208 个文件”写成“总共 208 个文件覆盖所有状态”会丢失范围。

### 2.4 新发现：新增 MMA3 测试可能被零 FP16 输入空测通过

本次静态调用链核实：

1. selftest.rs 的 split_k_cases 对两种矩阵创建 QAct::with_f16。
2. with_f16 将 h 平面分配并清零。
3. 测试仅调用 Gemv::quantize；当前接口写 q、d，不写 h。
4. launch_mma 默认在形状满足条件且未设 ASTRAL_MMA_INT8 时优先读 h。
5. 两个形状都满足该分支；重复比较和对 atomic 比较可能都在比较零输出。

这影响两组 GEMM 用例的四项比较的证明力，不等于 controller 测试也无效，更不等于真实模型推理为零。生产路径的 rms_q8、gate_q8、situ_q8 等会填写 h；T19 的真实模型重复性证据仍然存在。[E08][E09]

T22 要先补：非零输入、h 确实写入、输出非零、输入扰动可观察、匹配操作数舍入的 CPU 参考，再保留 deterministic 重复性与 atomic 路径对照。不能把“85/85”单独当作后续 kernel 改造的充分依据。

### 2.5 调研期间新增的 T20：已测覆盖、失败项与状态错行

22:15–22:16 北京时间的新提交增加了 prefill→decode 和 DSpark verify 行的导出；核心 CUDA、自测输入合同和 KV 布局未变。本方案已把它纳入最新基线。[E13][L02][L08]

| 新证据 | 结果与范围 |
|---|---|
| B 组 16 prompt，prefill 336 位置 | num-3 PASS |
| B 组 decode、verify nv=2/4/8，各 320 生成位置 | num-3 PASS；五个汇总比值总体在 0.59–1.09；有 1–3 个近平局 argmax 差异 |
| 三种 verify 批长 | 仓库记录对应位置逐位一致；与图化 decode 并非逐位一致 |
| B 组自由生成 16×160 token | 首次分歧 margin ≤0.27；严格一致前缀总计 895/2560，不能写成完整文本严格一致 |
| D 组 4 篇长文档，64 个边界位置 | num-3 FAIL；除 KL 超限，prefill 有 3 处、decode 有 1 处 argmax 翻转违反 margin≥0.5 硬门 |
| c4096×4，密集 8188 位置 | step 与 prefill→decode 满足现有 V4 公式；这是另一统计合同 |
| D 组重复性 | 184 个输出文件逐位一致 |

**最新 07 任务表有错行：T17 被改成 PASS，T20 仍是 NOT_RUN；同文件执行记录和 CHANGELOG 则写 T20 完成。**结合源码新增范围，可以确认 T20 已执行，不能因此认为 SWA ring 或 128K 已做完。实施前先校准表格，并保留长文失败项。

D 的 prefill/decode KL mean 比值约 2.8/2.5，KL max 约 6.9/5.2；prefill 三处硬门翻转的 margin 约 1.016、1.087、0.703，decode 一处约 1.087。因此不只是统计量被极小参考分母放大的问题，不能全部概括成近平局。

D 的少数位置存在明显分布分岔，参考自身也会分岔；这支持进一步诊断数值敏感性，但不证明超限与实现完全无关。密集 V4 使用 W1 的文档拼接 corpus，D 使用指定文档截取并加 chat 指令/模板；它们属于同一语料家族的另一序列/协议，**不是对 D 相同 token 前缀的加密采样**。密集 V4 PASS 不能自动改判已有 num-3 FAIL。

尤其不能在看到结果后只留下“不含分岔点”的位置：保留所有失败点作为固定回归，在相同 D token 前缀上补密集诊断，再在独立 E 集上验证预先定义的长文评价规则。本方案不替用户修改现行门槛。

B 之前已经参与 T19 诊断，D 这次已经用于 T20；它们适合回归，不再当作新方案的未见保留集。新增独立集合从 E 命名。T20 的长 KLD 脚本在比较后删除原始 .bin，仅留下 hash/摘要；后续需要保留可恢复的原始证据，hash 本身不能恢复数据。

还有一处复现身份需要补齐：T20 的 identity.txt 记录的是 fc5be35 加三个修改中的源文件及未跟踪 Cargo.lock；后续才归档为 18bf3e3。当前缺二进制 hash 和当时 working-tree patch hash，不能直接宣称该运行具有“干净 18bf3e3 构建”的完整证明。后续基准固定二进制及工作区差异身份即可，不必否定已有数值记录。

## 3. 两篇论文分别能提供什么

### 3.1 MoLT：重构跨遍依赖

MoLT-KV 将同位置的上一遍依赖改为严格前缀反馈。单遍递归对应其稳定解，通常不等于固定两遍或三遍；Hybrid 还有固定 prompt 记忆边界。U-MoLT 的读出省略依赖 decoder 的独立性。其 Qwen 变体的因果卷积仍需尾部窗口，正说明状态性不能忽略。论文的 token efficiency 也不等于 GPU 成本下降。[P01][P02]

其具体机制包括：严格前缀 memory KV 与当前 token 的 depth KV 在同一 attention 归一化中竞争；U-MoLT 将写 memory 的 encoder 与读取 memory 的 decoder 分离。decoder 不反馈 memory 时，可省去未请求的中间遍读出；省最后位置之外的计算，还要求没有相应跨位置状态。共享 memory 源不等于各 decoder 层共用同一组投影后 K/V。

对本项目的启发：画清每一条必须串行的边，先提取真正不依赖当前层输入的计算；若要删除同位置跨遍依赖，建立新的训练实验。

### 3.2 LoomFormer：细化垂直信息选择

LoomFormer 用向量流产生控制信号，用矩阵流保存内容，允许不同头的 Q/K/V/输出旁路选择早期头的信息。它的收益是训练后质量与计算预算的关系；同尺寸推理并未更快，A800 的 2.8B decode 例子为 171 对 198 tok/s。[P03][P04]

官方实现中 MShift 读取本层上一 token 的原始输入矩阵；它不是普通 attention 的 KV，也不是只在当前 token 内存在的全部临时状态。strict horizontal mask、输出旁路、矩阵写入和独立位置通道共同定义新模型，不能单独换掉 Inkling 的注意力后继续使用原权重。[F01][F02][F03]

Loom 的 depth reader 是可带符号的线性收缩 q·M；Inkling 的 bank mix 是对源做 softmax，MoLT 的 MoLA 使用自己的多来源 attention 定义。这些不是可互换的同一个算子。本文迁移的是依赖分析、融合和实验方法。

### 3.3 迁移判断表

| 思路 | 当前 Inkling 是否可直接保持语义 | 本方案处理 |
|---|---|---|
| 固定上一遍数据源，批量处理读取 | 可以；重排算术时另外验数值 | T24 |
| 减少中间张量写入、融合读/归一化/投影 | 满足消费者与状态顺序后可以 | T16、T24 |
| 区分长期历史与短命内容 | 可以 | T23、T17 |
| 跨 segment 的统一 softmax | 数学可等价，但须保留 sink、bias、mask、归约顺序 | T17 |
| 直接复用某一遍 KV，删除其余遍 | 改变模型语义 | 继续现有 R4，不冒充无损 |
| MoLT 式单遍递归 | 需要新反馈定义和训练 | R12、R13 |
| Loom 式 head-to-head 矩阵读写 | 需要新参数与训练 | R11 先观测，R13 再验证 |
| 直接移植 Loom 的 RoPE / self-exclusion | 不可直接套用 | 保留 Inkling 无 RoPE、相对 bias、sink 的定义 |
| 两槽 MShift 缓存直接用于 8-token verify | 不足以处理任意接受前缀 | 研究臂也使用暂存/提交机制 |

## 4. 当前执行图和必须保持的状态含义

下面是 A1 的实际形状，后续所有专用化均以此为前提。[E03][E05][L05]

| 项目 | 当前值 / 语义 |
|---|---|
| hidden | 2304 |
| Q / KV heads | 24 / 8，head_dim=128；Q width=3072，K/V width=1024 |
| 物理层与执行 | 24 层权重；6 prelude + 12 core×3 + 6 coda = 48 visits |
| attention 类型 | 8 个 Global slot、40 个 SWA slot；SWA=1024 |
| 位置与归一化 | 目标模型无 RoPE；learned relative bias，n_rel=16、extent=1024；global log-length scaling、sink、output gate |
| controller | Q/K/V/FFN 四 port，低秩 rank=64；gain/forget 为 tanh |
| MoE | 128 experts、top-8、intermediate=1152；SiTU 与原 router 定义 |
| 短卷积 | K、V、attention output、FFN output；kernel=4，历史=3；按 logical slot 独立 |
| 精度 | 混合 NVFP4/Q8/BF16/F32 权重；目标 KV 为 FP16；不是所有张量 4-bit |
| 原生草稿 | 3 层 bundled drafter、block=8、taps [5,23,41,48]；另有 Markov head |

### 4.1 visit 与 slot 不能共用一个编号

| 执行阶段 | physical_layer | pass | chronological visit | 现有 slot |
|---|---|---:|---|---|
| Prelude | 0–5 | 无 | 0–5 | 0–5 |
| Core 第 1 遍 | 6–17 | 0 | 6–17 | 6–17 |
| Core 第 2 遍 | 6–17 | 1 | 18–29 | 24–35 |
| Core 第 3 遍 | 6–17 | 2 | 30–41 | 36–47 |
| Coda | 18–23 | 无 | 42–47 | 18–23 |

当前 DSpark tap 依据 run 内递增的 visit，且在进入 layer 前 stash；最终 tap 是输出归一化表示。它们不是按物理层号直接索引。改变遍数后不能沿用 [5,23,41,48] 的数字并假定语义未变。[E03][E04]

### 4.2 状态分为三种寿命

| 对象 | 持久范围 | 能否跨遍别名 |
|---|---|---|
| 权重与量化布局 | 模型全生命周期 | 同物理层共享 |
| 8 个 Global slot 的 K/V | 已提交前缀 | 默认不共享 |
| 40 个 SWA slot 的 K/V | 各 slot 最近 1024 个位置 | 默认不共享 |
| 48 × 4 处 conv 输入历史 | 各 slot 已提交边界的 3 个输入 | 不共享 |
| bank、bank_out、prelude | 当前 forward/当前 token 批次 | 按读写依赖复用 scratch |
| msgs、controller 中间值 | 当前 pass/层/批次 | 允许预计算和复用，但不能跨前缀当历史 |
| DSpark 特征和候选 hist | 当前 prefill chunk 或 verify 轮次 | 需匹配接受前缀 |
| 未来 Loom MShift 状态 | 每个研究层的上一 token 原始输入矩阵 | 必须与位置、轮次共同提交 |

### 4.3 增加一个小的静态执行描述

建议新增私有模块 crates/model/src/inkling_plan.rs，不扩建通用图编译器。它只回答：执行哪个物理层、读写哪个 slot、是否全局、消息来自哪一遍、DSpark 在哪一个 visit 取特征。

拟议接口，尚未实现：

~~~rust
struct VisitSpec {
    visit: u16,
    slot: u16,
    physical_layer: u16,
    pass: Option<u8>,
    kind: AttentionKind, // Global 或 Swa { window }
}
struct InklingPlan {
    visits: Vec<VisitSpec>,
    slot_count: usize,
    fingerprint: [u8; 32],
}
impl InklingPlan {
    fn fixed_three_pass(cfg: &Config) -> Result<Self>;
}
~~~

先保持现有 slot 编号及执行顺序，逐项对照上表。T18 才新增按遍数构建计划。plan 指纹进入 graph key、trace 和状态快照，防止一种遍数的状态被另一种遍数误用。

## 5. 首选定制优化：每遍不变的消息计算

### 5.1 为什么当前代码存在机会

在第二、第三遍入口，forward 将上一遍留下的部分 blocks 作为 bank，将上一遍最终 cur 复制到 bank_out，再把 cur 恢复为 prelude。接下来的 12 个物理层反复读取同一组 bank/bank_out，各用本层 msg_query 产生 Q/K/V/FFN 四类消息。源数据在该遍内不随当前层推进而变化。[E03]

因此可以把“上一遍决定的工作”从 12 次逐层依赖中提前做完。仍然保留三遍，当前层的 hidden、路由、注意力和短卷积仍依赖前面的实际计算。

### 5.2 三级实现，逐级判收益

**M1：复用源归一化。**当前 mix 对每个 query 重算相同源状态的 RMS；先为固定源计算 FP32 逆 RMS。保持 source 顺序、eps=1e-6 和原 dot/softmax 归约定义。为争取逐位一致，还须沿用元素分组、线程归约树和 FMA 规则；改变归约组织时按数值变化验收。第一版只复用逆 RMS，不扩大中间矩阵。

**M2：批量读取 48 个消息。**一个 pass 的 12 层 × 4 reader 组成 query 表，输出按 (layer, token, port, dim) 存储；层执行时取得连续视图，保持每 token 四个 port 相邻、msg_stride=4D 的寻址约定。若选择其他布局，必须同步修改 controller stride。将 12 次 mix 启动改成一组固定形状计算；只先用于 decode 和 2–8 token verify，包含真实 k=2/4/6 对应的 3/5/7 行。

**M3：提前计算 controller 的消息半支。**当前定义为：

$$
c_{\ell,p}
= W^x_{\ell,p}\operatorname{RMS}(x_{\ell,p})
+ W^m_{\ell,p}\operatorname{RMS}(m_{\ell,p}).
$$

第二项在整遍开始时已经确定，可以和消息一起计算。当前输入项保持逐层执行，然后生成 gain、forget 并完成：

$$
x'=(x-\tanh(f)\odot x)+\tanh(g)\odot m.
$$

**不能只保留 64 维 c 的消息半支而丢弃 m**：最终合并仍直接使用 2304 维的消息。也不要将 tanh 门解释成概率。[E07]

### 5.3 明确显存和计算成本

一次缓存全部消息的 FP32 大小：

$$
12\times4\times T\times2304\times4
=442368T\text{ bytes}.
$$

| T | 全消息缓冲 | 64 维消息半投影缓冲 |
|---:|---:|---:|
| 1 | 432 KiB | 12 KiB |
| 8 | 3.375 MiB | 96 KiB |
| 2048 | 864 MiB | 24 MiB |

所以不在 2048-token prefill 中默认物化全部消息。prefill 先采用 M1，或按 token tile 做 M2/M3。一次性计算全部消息也可能增加写回成本；必须测源加载节省与新 buffer 成本的净值。

### 5.4 拟议改动点

| 文件 | 修改 |
|---|---|
| crates/model/src/inkling.rs | pass 入口建立 MessageBatch；layer 读取对应视图 |
| crates/kernels/src/inkling.rs | 新增消息批处理启动器；controller 增加消息半支输入模式 |
| crates/kernels-src/cu/inkling.cu | 共享源 RMS、批量 mix、固定顺序半投影合并 |
| crates/testing/src/selftest.rs | 旧 mix 对新 mix；旧 controller 对新 controller |
| docs/configuration/environment_variables.md | 新开关与 graph 失效条件 |

沿用已有 QKV controller 批处理，不再重复实现“把三个 controller 合成一个 launch”。M1/M2/M3 分开提交与测量。

### 5.5 验收

- 关闭开关时，原图、数值和状态逐位一致。
- M1/M2 若仅改变数据存取，首先争取逐位一致；M3 归约重排归入同数学的数值变化，走现有 G2 与 T20。
- 随机源、真实 bank 抽样、近乎相同的源、极大异常坐标、正负门分别测试。
- 验证 source bank 在被消费前未被 scratch 复用覆盖。
- 对同一 bank/bank_out 和 query，逐一对齐第二、第三遍的 12 层 × 4 port × token 消息，再对齐半投影和 controller 输出；不能只依赖最终 logits。
- 测 1-token decode、2/3/4/5/7/8 行 verify、prefill 分开，覆盖 adaptive 切图与短尾；只有端到端收益才默认启用。两轮有依据的改进仍不足 3%，按 T16 规则记录 NO_BENEFIT。

### 5.6 更深一层的定制：两个消息源的代数化表示

当前标准 block_size=6、core=12 层时，每个后续 pass 的消息实际只混合两个固定源：上一遍第一个 core block 的输出和最终 core 输出。这允许一个更激进的 M4 候选，放在 M1–M3 之后单独评估。[E03][E07]

设两个源经当前 RMS 规则归一化为 z₀、z₁，每个 layer/port 的 softmax 权重为 a、b，则实数数学上：

$$
m=a z_0+b z_1,\qquad
G_{ij}=\frac{z_i^\top z_j}{D},\qquad
U_{j,i}=W^m_j z_i.
$$

于是：

$$
r_m=(a^2G_{00}+2abG_{01}+b^2G_{11}+\epsilon)^{-1/2},
\qquad
W^m_j\operatorname{RMS}(m)=r_m(aU_{j,0}+bU_{j,1}).
$$

可以只存两个高维 basis、每个 reader 的系数、Gram 和两个 64 维投影，在 controller combine 内按需重建 raw m，省去 48 个完整消息的物化。combine 注入的是 raw m，不能把 r_m m 当作残差消息。

**收益和代价都要算：**两个 basis 约 18 KiB/token、双投影约 24 KiB/token，再加系数；对比 M2 的 432 KiB/token。每个 Wm 各不相同，不能共享一次投影；两次 basis 投影替代原来一次消息投影，算术增加，虽可同一权重加载服务两个 RHS，仍未必更快。

它只在实数代数下与原算式等价。旧 mix 的 RMS、缩放折入系数和 FMA 顺序不同；Gram 在源近反向、a≈b 时有消去误差，G₀₀/G₁₁ 也不能假定为 1。必须有直接重建消息后计算 RMS 的稳定 fallback 或明确失败诊断，不能静默 clamp 后称无损。

M4 属于“同数学的数值变化”实验，需完整 G2/T20 和真实 source 抽样；不是无需验证的默认优化。若以后 block 布局改变导致源数增加，则自动回到通用消息路径，不把两源假设硬编码成所有模型的事实。

## 6. 最确定的容量改造：SWA ring 与候选暂存

### 6.1 当前实现与理想稳态容量

Session::new 目前为 48 个 slot 全部分配 capacity × 1024 个 FP16 K 和 V；typed kvcache crate 仍是占位实现。直接在 Inkling Session 内实现两类缓存即可，不必先实现上游的通用池/分层存储设计。[E03][E11]

每 slot-token 为 4096 bytes。三遍的容量公式：

$$
B_{\rm full}=48\times L\times4096,
\qquad
B_{\rm ring}=8\times L\times4096+
40\times1024\times4096.
$$

| 目标长度 | 全长布局理论 KV（现实现上限 8K） | 理想 ring 后目标 KV | 节省 |
|---:|---:|---:|---:|
| 8,192 | 1536 MiB | 416 MiB | 1120 MiB，72.9% |
| 32,768 | 6144 MiB | 1184 MiB | 4960 MiB |
| 65,536 | 12288 MiB | 2208 MiB | 10080 MiB |
| 131,072 | 24576 MiB | 4256 MiB | 20320 MiB |

这只是目标模型 KV 的稳态算术，不是 tok/s 提升，也不包括权重、草稿 KV、工作区和 graph。A1 文件约 16.42 GiB，实际驻留权重还应取加载统计。128K 是否放得下，要以完整峰值预算验收。[L05]

### 6.2 三个坐标分离

1. absolute_position：模型位置语义，用于相对距离与全局对数缩放。
2. committed_len：可被后续 token 作为正式前缀读取的长度。
3. physical_row：Global 线性行，SWA 为位置取模后的行。

绝不能把 ring 下标传给相对 bias 或位置缩放。Rust 和 CUDA 中多处 min(capacity, MAX_CTX) 都必须分类处理，而非只把 8192 改大。simple attention 的 logit[MAX_CTX] 保留为短参考路径，长上下文走已有 split/online-softmax 路径。[E05][E07]

### 6.3 推荐方案：只读已提交 ring，加当前批次 delta

当前代码先写整批 K/V，再做 attention。T 个新 query 的窗口联合范围最多 W+T−1；直接写 W 行 ring 会覆盖早期 query 仍需要的历史。

推荐使用两段逻辑视图：

- 已提交前缀：只读 ring，按绝对位置索引。
- 当前批次：独立 K/V delta，保存本批量化后将被 attention 真正读取的 FP16 值。

对 query p，严格读取逻辑位置 [max(0,p+1−W), p]；属于当前批次的行从 delta 读取，其余从 ring 读取。第一版保持原来的逻辑 key 顺序与归约分组，避免同时更改数学与存储。

prefill 没有拒绝，可在本 slot 的 attention 完成后提交本批最后 W 行，再复用共享 prefill delta。T=2048、KV width=1024 时，一个共享 K/V delta 为 8 MiB，而不是给 40 个 slot 各保留一个完整的 2048-token 副本。

verify 的接受长度要等完整目标前向后才确定，所以每个需要回滚的 slot 都保留小 delta。48 slots × 8 rows 的 FP16 K/V delta 上界是 1.5 MiB；仅 SWA 则是 1.25 MiB。Global 可以继续线性写入未来行。后继轮次读取正式历史时，以 committed_len 为边界；当前 verify 的 query p 则同时读取已提交前缀和本轮 start..=p 的候选输入，屏蔽 p 之后的行。未提交未来行在下一轮仍不可见。

### 6.4 推测轮次的提交语义

现有接受器验证 anchor 加 k 个 draft。若接受 j 个 draft：

- 提交的输入状态是 anchor + j 个 draft，共 j+1 行；
- 输出还包含一个 target 选出的新 token，它成为下一轮 anchor，其模型状态尚未计算；
- 因而新 committed_len = start + j + 1；不能把 bonus token 再算作已消费输入。

同一逻辑提交必须处理：目标 KV、四处 conv、DSpark context KV、下一轮 feature 来源、设备位置与 host 位置。当前 conv_commit 按 hist 的前 j+1 行更新，即包含 anchor 的 hist[0..=j]；新状态取旧历史与这些输入拼接后的最后 3 项，优先复用其语义。[E03][E04][E06]

拟议内部结构：

~~~rust
struct RoundState {
    epoch: u64,
    start: u32,
    proposed_inputs: u8,  // anchor + draft，至多 8
    committed_inputs: u8,
}
enum KvStorage {
    Global,
    SwaRing { window: u32 },
}
// 原位数据、候选 delta 与控制字段由一个 Session 持有；
// commit 在已有单 stream 图中的 accept 之后执行。
~~~

这不是新增服务事务框架，只是把当前分散的状态更新统一成可验证的内核执行顺序。

### 6.5 Attention 归一化

若后续为性能将旧 ring、delta、远近历史拆成多个 reduction 段，合并每段的 (m,l,o)，先统一最大值再合并指数缩放。Inkling 的 sink 只参与一次；不能每段各加一个 sink。还要保留 learned relative bias、global tau、qk clip、output gate。

LoomFormer 的严格 mask 和 RoPE 不进入此路径；多段历史使用标准 online-softmax 状态合并。对照必须使用同一组 K/V 和同一 mask，不能拿不同缓存内容解释 kernel 数值差异。

### 6.6 必测边界

- 长度 1023/1024/1025、2047/2048/2049、8191/8192，以及扩展后的 8193。
- chunk=1、7、511、512、1024、2048；重点测 T≥W 和跨环。
- verify 输入行数 2/3/4/5/7/8，接受 j=0、部分、全部；另测普通 1-token 路径。3/5/7 分别对应 k=2/4/6，必须覆盖 adaptive 连续切图，以及上一轮长候选到下一轮短候选的旧 tail 隔离。
- 拒绝发生在环尾；连续两轮拒绝；reset 后复用同地址；最后不足一轮的容量。
- query 处于 ring 最早有效位置；绝对距离恰好跨 1024；sink 占主导。
- 图模式与 eager，trace 开/关，prefill→decode→verify 的边界。

容量不足一轮时先保持现有停止合同；若实现降 k 继续，单列行为变更与测试，不能顺手改变。

先在 8K 内与原线性缓存做同前缀对照，再进入 16K/32K/64K/128K。保留外部参考不足时的证据范围，不以“大容量成功分配”替代正确性验证。

## 7. T16 的底层候选：只做仍有明确浪费的地方

### 7.1 QAct 按真实消费者输出平面

当前若干 QAct 同时保留 INT8 值、scale 与 FP16 值。某些小批路径只读 q/d，某些大 prefill 的 MMA3 只读 h，但上游融合生产者仍可能写两份。

新增固定的消费者表，按当前选择的 kernel 记录每个激活需要哪些平面。不能简单规定“所有 decode 都不要 FP16”，因为 projection、MoE、LM head 的选择不同，环境开关也会切换路径。

拟议类型：

~~~rust
enum ActPlanes { Q8, F16, Both }
// 写入端与消费端共用由固定执行配置产生的 ActPlanes；
// 数据有效性和已分配内存是不同状态。
~~~

只省去无人读取的写入，不改仍被消费的舍入方式。修改 ops.rs、inkling.rs、inkling.cu、dspark.cu 的平面传递；加入“请求了 F16 但未写入就拒绝/断言”的调试检查。T22 是此候选的前置任务。

### 7.2 短 prefill 的 MoE MMA tile

总 token 数超过 8 时，不能推断每个专家都拥有大批量。当前 MMA3 的 64-token tile 可能面对只有 1/2/4 行的 expert work item。

实验仅针对 T16 实测热点形状：NVFP4 gate_up、down 和少数 Q8 投影。记录每 expert 的真实 count，按 8/16/32/64 行进行 FP16 输入 tile 特化；第一轮保持权重表示和累加精度，不先换 INT8/FP8。

必须计入工作项分桶、padding、额外 launch、确定性 split 合并开销。路由选择不变不代表输出近似相同；使用同一 token/expert 映射核对输出。它属于现有 K1/K2 的具体化，不新建通用 GEMM 库。

### 7.3 确定性 workspace 的清零

当前 split workspace 路径先清零，再由每个 split 写部分和。如果能证明本次所有被 sum kernel 读取的元素都被唯一覆盖，可删除清零节点。

证明对象必须包括 MoE 的 yidx 覆盖、空 expert、尾行和 split 数变化。否则保留清零，或仅对活跃区求和。不要凭“kernel 看起来写满了”删 memset，更不能回到浮点 atomicAdd。

### 7.4 单 token 输入上传

Session::step 每次创建长度 s.tmax 的 token 数组，仅首项有效，再上传 token 与 position；当前同步还承担 d17a519 修复的先后关系。

候选是固定 pinned input packet 或只上传有效首项，并将上传明确排在执行图之前。按事件/stream 所有权控制复用，不直接删同步。先用现有 ASTRAL_STEP_TIMING 测 copy/launch/sync/read 的占比，收益很小时不抢占主线。

### 7.5 Loom 代码中可以借鉴但需要筛选的布局

Loom fast_inference 将若干矩阵内部转置、按对齐宽度补齐，并把上一层写入与下一层读取融合，目的是减少中间内存流量。[F03][F04]

Inkling head_dim=128 已对齐，不能重复套 padding 并期待同样收益。可试的窄方向是：

- T24 的消息源归一化、消息读取与下一步低秩投影融合；
- T17 在全局长历史上比较原 K 布局与固定 tile 转置 K，单独计入追加与尾块维护成本；
- 对 24 Q heads / 8 KV heads 的 GQA=3 研究每 CTA 复用 K/V 加载，但不要把 Loom 的 MHA kernel 当作已经验证的 GQA 实现。

这些均属于待测候选，不能列成已获得收益。优先测当前布局的带宽与 cache miss；没有瓶颈证据就不换格式。

### 7.6 后置候选：expert gate/up 与 SITU epilogue

profile 确认独立 SITU 节点和 gu 往返值得处理后，让一个 CTA 计算对应 gate/up 行，保持 per-expert scale、SITU 与量化组顺序，直接输出 qa_ff。这有机会省掉每个 visit 的中间往返，但需要同 CTA 凑齐 32-channel 量化组，可能增加寄存器压力、降低并行度。它排在平面裁剪和 tile 实验之后；不把配对、量化分组、tile 三项同时改变后只测总吞吐。

### 7.7 A/B 必须证明候选实际参与

参考 #1330 的 engagement 记录：配置里开了开关，不等于模型走了该 kernel。每次 graph 捕获记录实际选择的 kernel、shape、ActPlanes、候选命中与 fallback 原因；基准汇总按 replay 的 graph 统计有效参与次数。记录可以放在 host 的捕获/调度处，不必给每个 GPU 节点加原子计数。

一个候选从未命中时，明确记录“候选未命中”及原因，任务状态仍使用现有词表；不能把两条相同路径的时间差当成优化收益。[X02]

## 8. DSpark：沿用原生草稿器，补状态与成本

### 8.1 当前已具备的能力

已有 adaptive policy、按 verify 长度捕获的 round graphs、四组 target feature、conv 输入 hist、GPU accept 与 conv_commit。不是从零接入投机解码。[E03][E04][E06]

当前 draft K/V 是 FP32，按所有层完整 capacity 分配；store_ctx 会处理本轮 verify 的多行结果，而有效历史由位置控制。现在线性布局中未提交未来行可被遮蔽，改成 ring 后这种写法不再自动安全。

### 8.2 三步候选

1. 按实际 draft config 区分 local/global 层，缩短 local 的持久历史；双向 draft block 另外暂存。
2. 将 context KV 与本轮 anchor/mask block KV 分开。两者分别使用 wkv_ctx/k_norm_ctx 与 wqkv/k_norm，不能把已接受 draft 的 block KV 直接提升为 context KV。提交的是目标验证 feature 的前 j+1 行重新投影生成的 context；下一轮 Markov feature 来源为第 j 行。保持 draft 的 block 内双向 mask。
3. 将 FP32 KV 改为 FP16/BF16 作为单独近似候选：目标模型验证仍控制最终接受，但草稿分布、接受率和成本可能变差。相对原 draft 的输出一致性与目标提交结果一致性分开报告。

草稿 local attention 的所有 block query 共同读取 [max(0,start−draft_window),start) 的 context 和整个 anchor/mask block；不能套用目标模型每个 query 各自计算的因果滑窗。实现中传入 window+block 正是为保留这一语义。[E04][E06]

目标 KV 的 8K→ring 节省不能代替草稿预算。draft 持久全长 KV 的一般公式为：

$$
2\,n_{\rm layer}^{draft}\,L\,n_{\rm kv}^{draft}\,d_{\rm head}^{draft}\,b.
$$

当前实现的 L 应取 dcap=target_capacity+block+8；compact 方案另列持久 context、双向 block 和 guard 余量。从 A3 config 取真实 heads/local/window，写入预算；不猜一个“约几百 MB”。在 128K 时，该项可能成为是否能装入 24GB 的决定因素。

### 8.3 按净提交收益选策略

每轮至少记录 draft_ms、verify_ms、commit_ms、rollback_ms、accepted_drafts、committed_inputs、emitted_tokens、bonus_tokens、expert_union、当前 context 和真实 wall_ms。拒绝通过“不提交 delta”处理时，记录 rollback_ms 为何为 0 或已计入哪个阶段。重叠计时不重复求和。

当前 draft transformer 仍执行 config 中完整 block；k 主要改变目标 verify 长度和 Markov head 步数，不能默认 draft 成本随 k 线性缩放。T21 中比较 k=2/4/6、plain，以及代码/中文/推理段等已冻结负载，至少包含短/长两个 context 桶；严格提交序列一致率与 V8 容差判定分开报告。按保留集得到开启区间，草稿接受率更高但 wall time 更差时，仍为 NO_BENEFIT。单流 4090 不优先追多请求吞吐。

## 9. R11：从头级信息流定位真正有价值的循环计算

### 9.1 研究问题与已有任务的关系

R5 已研究 controller 的整体干预，R2 已研究每遍读出。LoomFormer 提供的新观察粒度是：**上一遍的信息，通过哪个 port 改变了哪个头，随后影响哪个后续读取和最终选择？**

在原 Inkling 上先回答这件事，再决定是否值得训练新的矩阵记忆。不要把“消息权重大”直接解释为“因果重要”，也不要因为一个头常看 sink 就剪掉它。Loom 讨论的 sink-token 注意力与 Inkling 的显式 sink 归一化项不是同一种对象。

### 9.2 探针位置

基于现有 T15 增加固定 ProbeSpec，避免每个 kernel 都导出完整张量：

| 位置 | 默认记录的低成本摘要 | 需要时才导出的切片 |
|---|---|---|
| 每层 Q/K/V/FFN 消息 | 源权重、RMS、极值、跨遍差异 | 指定 token 的完整消息 |
| controller down / combine | x 半项、m 半项范数及夹角；gain/forget 分位数 | 64 维 latent、指定通道 gain/forget |
| Q/K/V 投影及短卷积前后 | 每头范数、变化量；conv 历史摘要 | 被干预头的完整向量 |
| attention 输出 | gate 前后头范数、sink 质量、时间位置桶质量 | W_O 前指定头输出 |
| W_O 后及 post conv | 当前注入变化、历史尾变化 | 被选 visit 的输入与输出 |
| router | top-8、8/9 margin、选中专家变化 | 对问题样本保留完整路由分数 |
| 最终输出 | gold log-prob、margin、KL、任务得分 | 选定位置完整 logits |

attention 的默认融合路径会隐藏 gate 前张量。探针模式可以使用专门的拆分参考图或在融合 kernel 中写摘要；探针图与计时图分别捕获，探针关闭后不得遗留 GPU→CPU 同步或额外全张量写入。[E03][E05][E07]

记录键沿用现有五元组，并补 port/head/intervention_id；实际 slot 和 plan fingerprint 同时记录。Q head 24、KV head 8，做 K/V 干预时明确其影响的三个 Q heads，不能假定一一对应。

### 9.3 三类干预，明确因果范围

1. **局部 port patch。**在固定前缀、固定本层输入下，替换一个消息 port 或其低秩半项，重跑本 token 的下游。它测局部敏感性，不证明可以长期删除某条路径。
2. **头输出 patch。**在 W_O 前替换指定头的输出：原值、零、同任务对照样本、另一遍匹配位置。继续执行 output projection、post conv、块残差与 coda，不能把这些后续步骤简化掉。
3. **持续干预。**从干预起点重建此策略自己的 KV/conv 历史，运行完整后续序列。与只改当前 token 的效果分开；必要时从相同前缀重新 prefill，不急于建设通用快照服务。

低成本候选筛选可用激活摘要、linear probe 或梯度近似；因果结论必须有真实 patch 对照。随机选同数量的头、同范数替换作为对照，避免把“扰动大”误当作“通道特殊”。

### 9.4 产物和退出条件

产出一张可复查的表：任务类型 × pass × layer × port/head × 持续干预代价 × 对答案的影响。优先寻找三种证据：

- 后一遍只在少量头/位置修正关键 token，适合后续受控计算策略。
- 消息与当前输入的作用可分离，适合把一部分生成过程移到历史预测器。
- 某些信息主要依赖长历史或短 conv，说明删除循环并不能靠一个简单的“历史向量”补回。

如果观测找不到稳定结构，保留否定结论；不以一张漂亮的 attention 图支持架构改动。R11 的首轮目标是识别可干预路径，不承诺马上产生速度收益。

## 10. R12：严格前缀是否足以替代同 token 消息

### 10.1 先定义允许的信息

为第 r 遍、第 ℓ 层、第 p 个 port 构造候选：

$$
\widehat m_{t,r,\ell,p}
=G_{\ell,p}\big(e_t,\;H_{<t},\;r\big).
$$

其中 e_t 只能使用当前 token 在既定前序计算中已经得到、且不依赖被删除同 token 循环的信息，例如 prelude 输出；H 包含已提交前缀，以及同一 forward/当前分支可因果使用的临时严格前缀。当前 token 的上一遍 bank、已经使用真实消息的后续 hidden、未来 token 或无关分支不能进入预测器输入；被拒绝的候选不得进入长期历史。这样 chunk/verify 与逐 token 路径仍表示同一递推。

原消息 m 作为监督目标可以导出，但不能混入特征。按文档/任务拆分训练、验证、保留集，再按长度和位置分层；同一长样本切片不能跨集合泄漏。输入可用性写入数据 schema 和特征生成代码，不只写在实验说明里。

### 10.2 两级难度

**第一层，预测低秩影响。**先预测 u=W_m RMS(m) 的 64 维输出，测相对误差、cosine、门变化和异常位置。这能以较小训练成本回答“影响是否可预测”，但仍然不能删除完整 m。

**第二层，预测实际合并内容。**只有第一层表现稳定，才训练消息重建或低秩重建基底，使预测器输出足以完成：

$$
x'=(x-\tanh(f)\odot x)+\tanh(g)\odot\widehat m.
$$

候选训练目标可组合消息误差、controller 输出误差和 teacher/student logits KL；权重在开发集选择、保留集冻结。中间 MSE 低而关键答案变坏时，以任务和输出损失为准。

可以先训练 ridge/小 MLP 作为可预测性下界，再试一个只读历史的轻量注意力 reader。不要一开始就把另一个大模型嵌入 decode，也不要把 64 维预测的成功叫作完整替代成功。

### 10.3 从诊断到真实递归

| 臂 | 历史来源 | 当前消息 | 能回答的问题 |
|---|---|---|---|
| Teacher | 原三遍模型历史 | 原消息 | 基准 |
| Oracle diagnostic | Teacher 历史 | 真消息或其可控压缩 | 通道容量和误差上界 |
| Prefix predictor | Teacher 历史 | 严格前缀预测 | 可预测性，仍有 teacher forcing |
| Free-run student | Student 自己的历史 | 严格前缀预测 | 误差是否随生成累积 |

只有最后一臂能支持真实部署判断。student 的 KV、conv、draft features 都由 student 自己的执行产生，不能一边省掉目标遍次、一边继续享用 teacher 的最终历史。Hybrid 另列：prompt 使用固定多遍，continuation 使用递归，其 prompt 边界和状态来源写进模型身份。

R12 接在 R9 的 history/current-depth 分离之后，不重复 R4 的 KV 直接别名实验。最初只在三遍模型里替换一个 port 或指定位置，逐步扩大覆盖；是否减少遍数由后续实证决定。

### 10.4 单 4090 的实际训练边界

第一阶段从冻结 A1 导出少量指定位置的激活，在独立的小预测器上训练，不保留 26B 主干反向图。磁盘只保留选中的监督切片与摘要，避免 48 visit × 全 token × 全向量的无边界导出。

若以后训练冻结大主干上的适配器，先做完整显存和反向可行性测量；“权重量化可推理”不意味着“24GB 自动可训练该结构”。原生 CUDA 推理引擎也没有因此自动获得 autograd。只有小实验验证了机制，才值得建设训练桥接和权重导出。

R12 的停止条件是：长生成误差持续放大，或预测器加上必要状态维护后的 wall time 无净收益。负结果也能明确哪些同 token 计算值得保留。

## 11. R13：小模型验证 MoLT × Loom 的新架构

### 11.1 要检验的两个独立因素

- 因素 A：跨遍反馈来自同 token，还是严格前缀。
- 因素 B：内容通过传统块/向量接口传递，还是可按头读取的矩阵接口。

先做四臂全因子对照，避免把两篇论文一次合在一起后无法归因：

| 实验臂 | 反馈 | 深度内容接口 | 目的 |
|---|---|---|---|
| A0B0 | 同 token 三遍 | 向量/块消息 | 项目内小基线 |
| A1B0 | 严格前缀 | 向量/块消息 | 测前缀反馈的代价与潜力 |
| A0B1 | 同 token 三遍 | Loom 启发的矩阵 | 测头级读写 |
| A1B1 | 严格前缀 | 矩阵 | 测二者是否互补 |

这是一组为本项目设计的新实验，不是论文官方复现。为控制因素，四臂共用 tokenizer、数据顺序、上下文、优化器与读出；匹配参数和训练预算时分别报告 token-matched、FLOP-matched 与真实 GPU-hour，不能用其中一种代替全部。

### 11.2 第一版有意做小

建议起点：physical 8 层，prelude 2/core 4/coda 2，core 三遍共 16 visits；D=384、6 个 Q heads、2 个 KV heads、head_dim=64、controller rank=32、短 conv=4。使用 dense FFN 先隔离反馈/记忆因素；后续再加 tiny MoE，不把专家路由变化混入第一轮。

这些是待资源测量的建议参数，不是经验证的最佳配置。若复用约 200K 词表，embedding 本身约 76.8M 参数；参数总量必须实际计算，不能仅凭“8层”称其极小。研究起步可用一致的较小 tokenizer，但四臂必须相同，且不能声称由此复现 Inkling 的语言质量。

先以几十个 step 校验数值、梯度、峰值显存与 tokens/s，随后冻结一个可完成的 token 预算。短合成任务测依赖结构，自然语言/代码保留集测非合成退化；每个主要比较至少多个随机种子，先完成一个小预算全因子实验，再扩大胜出方向。

### 11.3 更适合本项目的 Loom 简化

优先试 learned static write basis + dynamic gate + dynamic reader：

$$
\Delta M_\ell(t)
=\sum_h \sigma(a_{\ell,h}(t))\,
\overline k_{\ell,h}\otimes\operatorname{Norm}(o_{\ell,h}(t)).
$$

reader 的动态 query 从低秩控制流产生，内容从 M 读取。embedding、attention 与 FFN 的写入是否都保留，是配置的一部分，不能只写 attention 后仍称为完整 LoomFormer。

依据是 Loom 的 432M 消融中，静态 write key 配合保留动态 gate 留下了大部分相对 loss 收益；这是选择低成本起点的依据，不保证我们的小模型、更短训练或冻结主干仍复现结果。[P04]

MShift 放在下一步独立消融；去掉它有助于先把“同 token 深度路由”与“跨 token 递归状态”分开。静态写入与去 MShift 的两个独立消融不能直接相乘估算组合效果。

### 11.4 MShift 的真实状态合同

若加入 MShift，明确：

$$
\widetilde M_\ell(t)
=\operatorname{RMS}\left((1-z_\ell(t))\odot M_\ell(t)
+z_\ell(t)\odot M_\ell(t-1)\right),
$$

而后续写入继续更新原始 M：

$$
M_{\ell+1}(t)=M_\ell(t)+\Delta M^{attn}_\ell(t)+\Delta M^{ffn}_\ell(t).
$$

保存的是每层进入本层前的 raw M_\ell(t)，不能保存 shifted/normalized read view，也不能只保留整个模型最后的矩阵。对保留有限三遍的实验臂，状态按逻辑 visit 保存为 M_{r,ℓ}(t−1)；权重共享不授权不同 pass 共享状态。稳定递归臂采用更少状态槽时，另做完整递推证明和对照。[F01][F02][F03]

官方 fast path 的两槽保护单步读写；沿用 anchor 为候选行 0 的协议时，接受 j 个 draft 共处理 j+1 个输入，提交每个逻辑 visit 的候选行 j 对应的 raw input M；j=0 也提交 anchor。丢弃后续候选，不提前提交尚未处理的 bonus。

方案可选：

- 小矩阵、短 verify：每层保存每个候选边界的 M，按接受前缀选择。
- 较大矩阵：保存轮次前 checkpoint，接受后回放被接受输入。必须把回放成本算入总收益。

同时提交 KV、K-tail、位置；若保留 Inkling 短卷积，还要提交全部 logical slot 的 conv。不能把“两个槽够 decode”推广为“两个槽够任意推测回滚”。

### 11.5 MoLT 条件不能被矩阵接线悄悄破坏

同一个 forward 中，当前 token 的早层写 M、晚层读 M，是深度上的正常无环依赖。**把上一 loop 的同 token M 反馈给下一 loop，则重新引入同位置循环，不满足 MoLT 的严格前缀条件。**

A1B1 中，当前遍的 M 由本遍可用输入构造，跨遍反馈只读 j<t 的状态；MShift 也纳入完整递归状态。只有完整状态递推满足严格三角性，才讨论相应稳定解和单遍求值。固定有限三遍、稳定递归和冻结 prompt 的 Hybrid，分别验证，禁止混用“等价”一词。[P01][P02]

最有价值的 proof test 不是跑一段通顺文本，而是对很短 token 序列穷举足够 loop 次数，对比 stable unroll、token-ordered recurrence、chunked prefill 和逐 token decode。时间因果测试要求未来 token 扰动不改变过去输出；另设严格前缀依赖检查，故意接入跨遍同 token feedback 应使该结构检查或相应等价性条件失败。后者仍可能时间因果，不能混成一个测试。

### 11.6 进入生产引擎的条件

研究脚本独立放在 bench/research 下。新权重使用新的架构与缓存版本标识；旧 GGUF 不能在新增矩阵路径上“试着能不能跑”。先交付数学参考、短序列状态测试与可复查训练结果；确认质量/真实成本优势后，才为 sm_89 写该新模型专用 kernel 和 loader。

最终决策看正确任务/秒、长生成稳定性、完整显存峰值，以及相对原三遍路径的净成本。即使新模型训练 loss 更低，只要部署成本不合目标，也可以只保留其中的探针和训练方法。

## 12. mlx-serve #1331 / #1330：工程借鉴与整合边界

### 12.1 两个 PR 不能当作同一份成熟补丁

| 对象 | 本次固定身份 | 已核实状态 |
|---|---|---|
| #1331 | head ad695002aa89fda7ac27b901d7474ddc84299af8；base 808597663930095178b07731cee6921d26a651e1 | 已合并；merge 6ba6d34ea0bc265dc19b5b737fa21138b2a228e1 |
| #1330 | head 6a22c34e558579a27a52fa4fb3a94a49d3a6c41c；base 2d08bf86adae64290d0c36132771c8a1fc47dab4 | 开放 Draft；本次 API 返回 mergeable=false |

#1331 增加多请求的推测 round 合批、DFlash2 树候选、GPU verify/accept/commit、成本控制与多组 kernel。它保留目标模型的三遍执行，不是 MoLT 式减少遍数。[X01][X03][X04]

其 tree round 在接受后有一次小结果 host read，再由 host 构造 accepted-path commit；提交的数据操作仍在 GPU。不能将其描述成零 CPU 或一个 kernel 完成整轮。

#1330 是多条性能工作线的整合，选择 #1331 的部分实现为默认，保留一些替代 kernel 为 opt-in，并增加请求隔离、持久成本表、数值合同、末行输出合同和若干量化/模板修改。[X02][X07][X08]

**但 #1330 当前不是 #1331 最新 head 的超集。**提交图的共同点只到 #1331 早期 6bbaee0f；比较最新 #1331 与 #1330 是分叉状态，后者 ahead 31 / behind 6。后续修正是否逐项手工带入，需要按具体文件判断，不能依赖“合并了四个 PR”的标题。

验证也要分层：#1331 有作者在 Mac 上的模型和性能记录；#1330 当前 head 有通用 CI 通过，但其目标 M5 Max 的模型、kernel 数值与性能矩阵仍列 pending。转换字节一致、编译成功、数值测试与真实质量/速度是四类证据。两者都没有提供本项目 RTX 4090 的结果。

### 12.2 最值得直接吸收的四项

| 项目 | 原实现给出的具体启发 | 本项目落点 |
|---|---|---|
| Open verify | 正式历史与本轮 own KV 分开读，接受后按有效路径提交 | T17 的 ring+delta；T20 状态测试 |
| 小批 MoE 尾部 | 按 hidden 列归属融合专家求和、短卷积和 residual，候选历史独立保存 | T16，先限 nv≤8 |
| 轮次成本表 | 预先测成本，本请求估接受前缀，以期望输出/时间选择 plain 或 k | T21 |
| 请求与数值合同 | 草稿状态不跨 repeatable 请求继承；成本、shape、精度成为可重放身份 | T20/T23/T21 |

这些与前面两篇论文不同：论文主要给新结构与训练方法，这两个 PR 给同一 Inkling 家族里可参考的工程实现。仍然应按 CUDA 当前缺口迁移，不能整包翻译 Metal/Zig。

### 12.3 T16 新增一个优先候选：短 verify 的 MoE 尾部融合

现有 Astral 单 token 已融合专家合并、post conv 和 residual；多 token verify 仍有 moe_combine_t → conv_res_par 两步。#1331 的 few_tail 提供了一个可证明的所有权：每线程处理固定 hidden 列，按时间/祖先顺序完成该列的专家求和与卷积。[E03][E07][X05]

本项目的最小实现：

1. 复用现有 astral_ink_conv_residual 的按列结构，增加“只读旧 conv、输出每行 hist、禁止原位提交”的模式。
2. 仅用于 nv≤8；每列在寄存器中维护最近 3 个输入。
3. 保留原 top-8 求和、per-expert scale、conv 及 residual 算术顺序。
4. 接受判定后仍由既有 conv_commit 选择前 j+1 个输入的最终历史。
5. 分别比较 cur、hist、接受 0/部分/全部后的 next-token；不能只看本轮输出相近。

它与 T17 共用提交语义，但不需要先完成长上下文或树推测。大 prefill 仍保持 token 并行路径，不将按列串行循环扩到 2048 行。

此外，#1331 的 expert grouping 和权重复用，Astral 已经有相应机制。真实增量是 count 特化、gate/up epilogue、无效 lane 与中间写入；不再新建一套重复的分组器。

### 12.4 Attention：借共享加载和双源读取，不搬平台阈值

**双源读取。**参考 relsplit 的 committed/own 两段。未来 CUDA 还要处理 ring 的 tail/head 与候选 delta，统一按绝对位置进入 online softmax；sink 只计一次。本轮候选可见性与后续轮次已提交可见性分开。

**GQA 共享。**#1331 的非 NAX relsplit_lanes 让一个 KV tile 被同组 Q heads 和多个 query 使用。对 Astral 24Q/8KV，可以实验一个 CTA 覆盖同一个 KV head 的 3 个 Q heads 和少量 query，测 shared memory、寄存器、occupancy 与端到端收益。不要将这个具体共享加载结构归给所有 NAX 分支。

**全局远历史快循环。**当整个 query tile 对某些 key 都满足相对距离≥1024，这些远 key 的 learned relative bias 为零，但仍参与 global attention。可将该范围与近端分开，减少条件与相对状态寄存器；跨 1024、causal/window、split 边界的 tile 必须留完整路径。

Astral prefill 已有 Tensor Core flash，decode 已有 split/merge/gate 融合。NAX、Metal 的绑定数量、4KB fallback、63/64 行拐点、M4/M5 的 tile 和 command buffer 策略都不是 4090 的设计参数。[E05][E07][X06]

改变 P 的半精度舍入、tau 乘法位置或 QK/PV 路径属于数值变化；不因数学公式相同就宣称 bit-exact。PR 中 BF16 的绝对误差容差不能替代现有 G2。

### 12.5 T21：固定成本表与本请求接受模型

建议把当前自适应策略进一步写成可检查公式。若 A 为本轮接受的 draft 数，轮次输出含一个 target token：

$$
\mathbb E[N_{out}(k)]
=1+\sum_{j=1}^{k}\Pr(A\geq j),
\qquad
S(k)=\frac{\mathbb E[N_{out}(k)]}{C_{\rm round}(k,L)}.
$$

用本请求已观察的条件接受率估计生存概率，冷启动用冻结的开发集先验；成本取离线/加载阶段测得的表，包含 draft、verify、commit 和必要同步。plain 是显式候选，不能因为加载了 drafter 就强制每轮使用。接近最优时偏向较短 k 可以作为预先冻结的策略；不要逐轮用有噪声的墙钟反馈改变算法。[X04][X07]

移植时比 #1330 做得更严格：

- key 使用 engine/kernel build、GPU、driver/toolchain、目标和草稿资产内容 hash、kernel 开关、精度、cache layout、context 桶及 policy 版本；模型目录路径不足以代表权重。
- 持久化保留浮点 bit pattern，或固定量化后首轮也使用同一数值。#1330 文本表的舍入和首轮原始成本可能在选择边界造成差异，不能自动宣称跨重启完全一致。
- cost table 冻结不等于 k 固定：本请求接受率仍会更新。回放需要相同输入、相同状态、相同成本表、相同策略。
- 无效、缺项或身份不匹配时回退 plain 或重做校准，记录原因。
- offline 分析可以记真实阶段时间，但不要为了在线 chooser 在每轮引入额外 host 同步。

该项只扩充 T21 的表与 policy，不引入全局服务调度平台。

### 12.6 T20/T23：可重复请求的状态身份

#1330 把 greedy/seeded 请求从共享推测 round 中隔离，并限制继承其他已完成请求的 drafter 状态。这说明“随机种子相同”不足以定义可重复：cache、history、形状、kernel 选择和成本表都可能改变结果。[X07][X08]

当前项目单请求优先，可以用更简单的合同：

- Session 重用必须经过完整 reset；不得继承上一请求的 draft context、校准统计或残留的候选有效长度。
- 相同 token 前缀按不同 chunk 进入不同数值路径时，分别定义 strict repeatability 和 num-3 容差；不能把二者混成“无损”。
- 未来若做 prefix snapshot，身份至少含精确 token IDs/hash、模型与模板、plan/遍数、KV/conv/draft 全状态及 layout。只恢复 target KV 不等于恢复完整 Inkling 状态。
- 请求级重放测试覆盖新 Session 与复用 Session、两次启动、草稿开/关、同前缀不同 chunk；并发隔离只有将来正式支持并发时再做。

#1330 自己仍列出 drafter slot 淘汰、prefill chunk、plain batching 和跨请求 prefix restore 等残余问题。不要把它作为“状态隔离全部解决”的现成证明，更不把“重复同样输出”与“等于 plain 输出”画等号。

### 12.7 末行 head、数值类别和负控制

#1330 的 last-row 修复针对一个具体合同：请求最后一行的输出，应与同次 all-row 计算的最后一行一致；原来仅计算最后若干行会让 MLX 选择不同 matmul 路径。[X09]

对 Astral，应先补 T20 中三种输出模式在同 hidden 上的直接比较：normal last-token、all-logits、spec verify。当前普通输出明确只算最后一个 token，而 all-row/verify 可能选不同 kernel；现有数值合同允许范围内的舍入，不应为了仿照 MLX 就物化 2048×201024 的全词表 logits。仅该 FP32 矩阵约 1.53 GiB，还会增加计算。

更合适的实现是让模式的数值保证显式化，必要时固定相同 head kernel/操作数和归约；确实要全行参考时只在小规模诊断路径计算。MLX 的 lazy evaluation 可以消掉某些未使用结果，不能把这种“零服务代价”假设套进 eager CUDA Graph。

借鉴其数值分类，并映射本项目已有四类变化：

| 变化 | 本项目验收 |
|---|---|
| 同值布局、有效性、纯数据搬运 | 逐位与状态不变量 |
| reduction、MMA、融合舍入 | 同数学数值变化，G2/T20 |
| round/shape 调度 | 数学策略可相同，实际舍入路径仍要测 |
| 目标权重重编码、TRUNK_Q8 类改造 | 新权重身份，重做对应基线 |
| 草稿权重量化 | 目标与草稿保证分开，计接受率和净收益 |
| prompt 模板/thinking-off 强制尾部 | 输入 token 与语义变化，单独 API/模板实验 |

每个关键测试加一个有意义的负控制：错误 slot、错一行 bias、漏一个 expert、漏写 h、提前提交一行，测试必须失败。#1331 部分新 kernel 的 formal contract 尚欠，而 #1330 增补的 contract 尚不能当成 4090 实测；这种经验正好用于补强 T22 与 T20。

### 12.8 R7：DFlash2 与树推测放在原生 DSpark 之后

#1331 的 DFlash2 是另一份草稿资产，并带树构建、验证、采样与 accepted-path 提交。固定 PR 发布 fixture 是 5 层、block=8；当前 Astral 为 3 层 bundled drafter 加 Markov head。两份发布配置的 taps 恰好同为 [5,23,41,48]，但 loader、head、卷积和窗口语义不同；不能只换文件或复用 parser。这里的 DFlash2 配置来自固定 PR fixture，尚未再次下载核验最新发布权重。[X03]

先完成原生 DSpark 的 T21，再判断更好 drafter 的收益上界。新模型必须锁定资产、tokenizer、tap/hidden 规范、权重格式与显存，并记录真实启用的 drafter；不支持配置时的 fallback 不得算作新模型已运行。

树结构进入本引擎时至少新增：

- node_id、parent、depth、ancestor mask；token 绝对位置由 depth 决定，不能用平铺 node index。
- 每个 node 读取已提交前缀、本节点与祖先的 K/V；兄弟与后代不可见。4-tap conv 也沿 parent 取前 3 个输入，不能按相邻内存行卷积。
- 接受后 gather 一条路径，按逻辑时间提交到各 slot 的 cache/conv；同深度的兄弟节点不互相污染。
- 先证明单链树退化为现有 chain verify，再测非平衡树、不同分支长度、拒绝与 reset。

对于采样，只有 draft 实际抽样分布 q、target 分布 p 及 filter/temperature 一致地进入接受与残差算法，min(1,p/q) 才有相应保证。top-k/tree 裁剪还会改变 proposal 的条件分布；不能从一个固定候选列表的采样测试推导整个自适应 tree builder 也精确。

本次代码审查发现的待验证风险是：预算控制可能根据已抽到的候选分数决定保留哪些孩子，而接受器仍使用原无放回 q；需要把真实 builder→verify→accept 串起来，在可穷举小词表上核对输出分布。它是进入本项目前的必要验收项，不宣称已经在真实模型上复现了采样错误。

原生 greedy 优化仍先走最小链形改造。树推测、多请求合批、vision、thinking 模板与 TRUNK_Q8 都不挤占 T22/T24/T17 的第一轮。

### 12.9 最终取舍

| 采用层级 | 内容 |
|---|---|
| 首轮落实到现有任务 | open candidate view、短 verify 尾部融合、成本表身份、请求 reset/有效性、负控制 |
| profile 后选做 | GQA shared tile、远历史快循环、cnt 专化、gate/up epilogue |
| 研究阶段 | DFlash2/树推测、采样正确性与净收益、长期 prefix snapshot |
| 当前不迁移 | Apple 指令/阈值、整套多用户框架、其他权重转换、vision 与模板行为改动 |

## 13. 实施任务、验收与停止条件

### 13.1 任务总表

本表是待并入 docs/07_tasks.md 的增补，不覆盖原表的历史记录。新增 T22–T24、R11–R13 当前全部 NOT_RUN；其他条目是对既有任务的细化，T20 沿用已经完成的测量并补专项。

| 项目 | 前置 | 第一项可交付成果 | 完成判据 |
|---|---|---|---|
| T22，新增 | 固定基线 | 非零 FP16 MMA3 数据合同与用例 | 输入有效、非零、扰动敏感、参考与确定性检查通过 |
| T20，已有执行后的增补 | T19；新优化前先 T22 | 保留现有 B/D 结果，再补 nv=3/5/7 与新状态矩阵 | 不覆写 D 的 FAIL；新增数值与状态结果单列 |
| T23，新增 | T22；GPU 验收在 T20 基线后 | 私有 InklingPlan 与 graph 身份检查 | 三遍原行为一致，visit/slot/tap 映射和失效测试通过 |
| T24，新增 | T23、T20；T16 分阶段基线 | M1，再 M2，再 M3 的独立开关与证据 | 中间张量对齐，G2/T20 不回退，端到端收益 |
| T17，细化 | T23、T20 | 8K 内 SWA ring+delta | 所有接受边界正确，再逐级扩长；峰值预算通过 |
| T16，细化 | 原 T14、T20；平面修改加 T22 | 当前热点表和单个候选 | 配对净收益，G2/G3 不回退；不足规则则 NO_BENEFIT |
| T21，细化 | T16、T20；compact cache 加 T17 状态合同 | 成本分解、固定成本表与每请求策略 | 两类负载、两档 context；净收益和提交一致性 |
| T15，扩展 | 原 T20；新探针使用 T23 映射 | 稀疏探针，不带干预 | 关闭逐位一致；graph/eager、开/关差异分别说明 |
| R11，新增 | T15、T23；复用 R5 | 头/port 因果影响表 | 局部与持续干预分开，有随机对照和反例 |
| R12，新增 | R11、R9 | 严格前缀数据集与小预测器 | 无信息泄漏；teacher-forced 与 free-run 分开 |
| R13，新增 | R12 的可行性结论；可先写数学参考 | 四臂小模型及因果 proof test | 稳定解/有限遍/Hybrid 分开，质量与总成本有可复查结果 |

T23 不阻塞 T15 的早期 schema 和只读工具开发；它成为新状态布局和新探针正式接入前的统一映射。T18 仍先建立 A4 自己的三遍基线，不能借本方案把 A1 的任意循环次数默认合法化。

~~~mermaid
flowchart TD
  A["T22 非零数值测试"] --> B["T20 路径与状态覆盖"]
  B --> C["T23 固定执行映射"]
  C --> D["T24 消息预计算"]
  C --> E["T17 环形历史与提交"]
  B --> F["T16 热点与单项优化"]
  F --> G["T21 草稿成本与策略"]
  E --> G
  C --> H["T15 / R11 机制探针"]
  H --> I["R12 前缀替代"]
  I --> J["R13 小模型对照"]
~~~

### 13.2 T22：先修测试的输入合同

涉及现有 crates/kernels/src/ops.rs、crates/testing/src/selftest.rs；需要新 host-only 测试时在相应 crate 增加。

- [ ] 固定并打印所选 Gemv 路径、权重格式、QAct 平面有效性、split 数与 kernel 身份。
- [ ] 定义 Gemv::quantize 的合同：明确只写 Q8，或让“要求 Both”的接口实际填充 FP16。不能继续根据分配状态推断内容有效。
- [ ] 用非零、有正负及不同幅度的输入填 h；CPU 参考使用与目标路径一致的 FP16 操作数和实际量化权重解释。
- [ ] 先检查 h/输出非零及改变一个有效输入能改变输出，再比较 repeat/atomic/参考。构造“h 未填充”负例，必须失败。
- [ ] 分别覆盖 Q8 与 NVFP4 的两组真实形状；controller 的非零测试继续保留。
- [ ] GPU selftest 完成后，补一次短真实模型的 step/prefill 重复性与当前 num-3，不重新定义历史门槛。
- [ ] 将报告写为“新增用例验证范围”，保留旧 85/85 是历史事实，解释其局限。

### 13.3 T20：承接已完成覆盖，补新改动需要的部分

- [ ] 修正 T17/T20 的状态错行和 B 保留集身份；B/C/D 作为回归集保留。新规则/策略选择使用独立 E 集。
- [ ] 复用已完成的生成位置和 8/9、64/65、1024、2048、4096 附近边界；增加 nv=3/5/7、adaptive 连续切图、拒绝组合和新 ring 状态，不无理由重复整轮 T20。
- [ ] 对 D 的全部失败点做固定前缀、中间张量及路由 margin 定位；保留 num-3 FAIL，密集 V4 作为并列证据。新的长文统计合同先冻结，再用 E 验证。
- [ ] 区分 prefill 最后一行、逐 token step 和 verify 中相同行的计算路径；保持相同 token IDs、有效词表、softcap 与 logits 单位。
- [ ] 对所改算子的相关位置存完整 logits；长序列只挑选必要边界，其他位置保留数值摘要。
- [ ] 一个专项 wrapper 聚合所有硬条件并以非零退出码报告失败。现有 t19c.sh/t19c_judge.sh 和新增 t20 脚本以记录返回码为主，不能直接当成自动失败门。
- [ ] 同一 Session 的 A→reset→A、A→reset→B→reset→A，与新 Session 对照；打开草稿时增加相同流程。将请求状态泄漏与形状舍入区别报告。
- [ ] 同时记录严格 token 一致、允许的近 tie 变化及 winner-vs-chosen gap。日志缺失、不完整和非法值均为失败。

### 13.4 T23：把映射、状态、graph 身份变成显式检查

- [ ] 新增私有 inkling_plan.rs，将 §4 的完整映射做成 host 测试；固定三遍仍使用当前 slot 编号。
- [ ] plan 标记 slot attention 类型、window、卷积布局及 tap 意义；在模型加载时校验。
- [ ] graph key 限定在同一 Session 和 CUDA context，包含 plan 指纹、执行模式、本次实际 ntok/nv、layout、allocation generation、capacity/tmax、ActPlanes、kernel 配置、消息布局和改变图结构/指针的 probe、teacher-forcing 模式。
- [ ] tap 显式区分 visit 前与最终归一化后；消息源表明确上一 pass 的 bank 行与 bank_out，共同进入 plan 指纹。allocation generation 覆盖输入、cache、workspace 与诊断 buffer。
- [ ] 同 plan 但更换缓存地址/布局/精度时，旧 graph 不得复用；指针生命周期由 Session 持有。
- [ ] 将已提交位置与候选范围写入调试状态，reset 清除所有逻辑有效性和草稿轮次控制值。
- [ ] 新计划关闭或固定 R=3 时，运行结果与旧路径逐位一致；其他数值变更不得混入此提交。

不引入全局 scheduler、运行时插件或自动图优化器。该模块只服务当前模型的执行不变量。

### 13.5 T24：每一级独立交付

- [ ] 缓存指定第二/第三遍 bank 与 query，得到旧 48-message 输出和 controller 中间量。
- [ ] M1 共享源逆 RMS，测 launch/读写变化和中间误差。
- [ ] M2 stack 模型加载时的 query，固定 (layer,token,port,dim) 布局，先运行 T≤8。
- [ ] M3 优先保存原始 dot(Wm,m) 与逆 RMS，在在线侧保留原合成顺序；若改算术顺序，明确按数值变化验收。
- [ ] graph 捕获使用稳定 buffer；任何潜在并行不得共享 split workspace。
- [ ] 测第二/三遍分别耗时、完整 forward 耗时、L2/DRAM 指标（可取得时）和峰值显存。
- [ ] 保留未启用时的基线；收益不足时只保留必要的测量工具，关闭候选。

### 13.6 T17：分四个提交阶段做缓存

| 阶段 | 代码范围 | 此阶段必须证明的事 |
|---|---|---|
| A：视图与 delta | model::Session、kernels::AttnPrep/AttnShape | 相同线性存储中先引入两段 view，数值和 mask 正确 |
| B：SWA ring | inkling.cu 的 prep、decode/split/prefill reader | 8K 内所有窗口/批次/拒绝边界与线性基线一致 |
| C：长位置 | Rust/CUDA 所有 MAX_CTX、split 数、relative distance | 位置语义与物理行分离，长路径不越界、不静默截断 |
| D：长上下文与草稿 | model inkling/dspark、API 容量验证 | 逐级 16K→128K，完整峰值、参考与长生成检查 |

- [ ] CPU 模型用整数绝对位置记录 ring 的逻辑内容；对随机 chunk/接受长度序列与线性记录比对。
- [ ] GPU 比较存入的 FP16 K/V 原值、每个 query 可见的绝对位置集合、attention 输出和最终 logits。
- [ ] 暂存区或未使用 tail 填不同的哨兵值，输出不得依赖无效区域；与真实 reset/reuse 一起测。
- [ ] 接受 0 个 draft 时仍提交 anchor；接受全部时只提交验证过的输入，不提前提交 bonus。
- [ ] 每次扩长先输出分项预算和实际峰值，失败时保留最后通过长度；不要把 128K 定为无论代价都必须实现的默认值。

### 13.7 T16 / T21：一轮一个原因

T16 先按照当前 07 的阶段矩阵采样：prefill 512/2K/8K，plain 历史 1K/4K/约 7K，verify 1–8，完整 DSpark。候选选择看阶段占比，不按论文热度。

每轮至少比较 baseline → candidate → baseline，沿用 T14 的正式配对重复协议得到端到端结论。profile 可少量采样，最终计时关闭 trace、调试与高开销 profiler。报告 kernel 时间、launch 数、峰值、TTFT/ITL 和 wall time，避免“kernel 快了但整体更慢”。

候选优先顺序由实测决定，但建议在相近收益预期下依次考虑：ActPlanes/dead store → 小批 MoE 尾部融合 → expert count tile → split workspace → gate/up epilogue → 更大布局变化。每次保留相同模型权重；权重转换或草稿量化另列实验臂。

T21 不把策略学习变成另一个复杂控制系统：固定测得的成本表，本请求更新接受统计，再按期望净速度选 plain/k。每轮选择、成本表 hash、收益估计和实际输出记入摘要；没有测到的形状不插值假装已校准。

### 13.8 数据合同

每次 run 使用现有目录规范，并至少有：

| 文件 | 内容 |
|---|---|
| run.json | 完整代码/模型/参考/工具链/机器身份；plan、cache、graph、精度、开关、数据与策略身份 |
| manifest.tsv 或现有等价清单 | prompt ID、token hash、指定位置、路径模式、预期输出文件 |
| phases.jsonl | 阶段成本；采样方式；每轮输入/接受/输出计数和 context |
| numerics.jsonl | 每位置误差、margin、argmax、词表和单位信息 |
| verdict.json | 完整性、状态不变量、V门、结论和退出原因 |
| evidence.sha256 | 本轮原始数据与摘要的 hash 索引 |

这是补齐现有证据合同，不是另建数据库。大 logits 可留现场，Git 保留清单、hash 与可重算的摘要。历史结果不覆写。

## 14. 如何补入两个仓库

### 14.1 CodexGame 的文件级改动

所有路径均相对 docs/inkling-4090-lab-v3.0。

| 文件 | 应补内容 |
|---|---|
| docs/10_molt_loomformer_inkling4090_plan.md | 放入本方案，作为两篇论文和两个 PR 的统一专题 |
| README.md | 保留 v3.0.11 已补齐的提交表；链接专题与最新判定范围 |
| docs/00_plan.md | 新增阶段与任务关系，保持 07 为状态真源 |
| docs/04_astral_fork.md | 更新真实 upstream/fork 基线；将 T24、ring/delta、ActPlanes、MoE 尾部融合落到 WP |
| docs/05_validation.md | 更新历史 V7 标题、num-3 当前定义、当前覆盖与 T20 待补范围；增加状态与负控制 |
| docs/06_loop_research.md | 原 R1–R10 保留；新增 R11–R13，引用本方案相应节 |
| docs/07_tasks.md | 先修 T17/T20 状态错行；新增 T22–T24/R11–R13；同步前置；所有新项 NOT_RUN |
| docs/08_runbooks.md | 只加入已实现的命令；未来接口保持“拟议”，不写成可运行指令 |
| docs/09_sources.md | 增加论文、代码 SHA、PR head 与合并状态；区分来源结论与本地推导 |
| VALIDATION.md | 历史初版验证保留，新增当前状态导航，防止旧标题盖过 v3.0.11 |
| CHANGELOG.md | 新方案与新任务登记；未跑 GPU 的内容不标性能/模型 PASS |
| tools/check_package.py | TOPICS 从 10 更新为 11；R 范围从 R1–R10 扩为 R1–R13；任务引用检测继续保留 |
| PACKAGE_MANIFEST.sha256 | 在文档与脚本改动完成后重新生成；不能直接复制旧 hash |

AGENTS.md 里若仍指旧分支或旧 patch 工作流，仅更新与当前 fork/main 不一致的事实；保留现场执行合同和用户已经给定的权限边界。

### 14.2 引擎的文件级改动

| 文件/目录 | 用途 |
|---|---|
| crates/model/src/inkling_plan.rs，拟新增 | 固定执行映射、slot 与 tap 身份 |
| crates/model/src/inkling.rs | pass 入口 MessageBatch；KV view/delta；graph key；probe 插点 |
| crates/model/src/dspark.rs | context/block KV 分离；实际成本记录；候选提交 |
| crates/kernels/src/ops.rs | QAct 有效平面和 GEMM 分派合同 |
| crates/kernels/src/inkling.rs | 新 launch 参数、cache view、消息批处理、融合启动器 |
| crates/kernels-src/cu/inkling.cu | message/controller、SWA view、attention 和小批融合 |
| crates/kernels-src/cu/gemv.cu | 仅在热点证据成立后修改 expert tile/epilogue/split |
| crates/kernels-src/cu/dspark.cu | accept/commit 与 compact 草稿视图；采样扩展单列 |
| crates/testing/src/selftest.rs | 非零算子、索引/stride、尾部、split 与负控制 |
| crates/testing/src/golden.rs | 需要时扩充同前缀、中间状态和有效位置对照 |
| crates/cli/src/main.rs | 仅增加实现后的专项诊断入口；不把实验接口泄漏到普通聊天流 |
| docs/design/inkling_execution_state.md，拟新增 | 当前状态合同、shape/精度矩阵与候选提交语义 |
| docs/benchmarks/inkling2_mini_rtx4090.md | 新实测完成后追加，不用预测数字改历史表 |
| bench/research/，拟新增局部目录 | R11 导出/分析、R12 小预测器、R13 数学参考与训练 |

本次交付没有向上述仓库写入这些改动。文件级表用于实施和评审，不是“已经实现”的清单。

### 14.3 建议提交切分

1. docs：当前状态与来源校准、新方案和任务编号。
2. test/kernels：QAct 非零输入合同，T22。
3. validation：T20 覆盖与返回码。
4. model：InklingPlan，保持固定三遍行为。
5. perf：M1；随后 M2；随后 M3，各自独立。
6. cache：线性 view/delta；SWA ring；长位置；草稿 compact，分开。
7. perf：每个经 profile 选中的算子一个提交。
8. research：R11/R12/R13 分别维护，不混入默认运行开关。

测试修复和性能候选不要捆成一个无法单独回退的大补丁。新功能关闭恢复基线；改变权重或训练出的模型以新资产身份进入比较。

## 15. 可运行入口与本次验证范围

### 15.1 已存在的入口

以下变量是执行者按当前 checkout 和现场 env 设置的路径，代码块展示现有接口，不表示本次已执行 GPU 命令。

~~~bash
python3 -m unittest discover -s "$INKLING_LAB_PKG/tests" -p 'test_*.py'
python3 "$INKLING_LAB_PKG/tools/check_package.py" --package "$INKLING_LAB_PKG"
python3 -m unittest discover -s "$INKLING_ENGINE/bench/llamacpp_compare" -p 'test_*.py'
~~~

GPU 窗口内按原 runbook 构建与守卫，已有命令包括：

~~~bash
"$INKLING_ENGINE/target/release/astral" version
"$INKLING_ENGINE/target/release/astral" selftest
"$INKLING_ENGINE/target/release/astral" verify-model "$INKLING_A1" "$INKLING_EVAL_LOG"
"$INKLING_ENGINE/target/release/astral" dump-final-logits "$INKLING_A1" "$INKLING_MANIFEST" "$INKLING_OUT"
ASTRAL_SPEC_FIXED=1 "$INKLING_ENGINE/target/release/astral" dump-verify-logits \
  "$INKLING_A1" "$INKLING_NATIVE" 3 "$INKLING_MANIFEST" "$INKLING_VERIFY_OUT"
~~~

18bf3e3 中的 dump-final-logits 已增加 decode 类型；dump-verify-logits 的参数 3 是 draft k，实际 verify 为 4 行。spec_force 将接受比较对象换成 manifest 序列，草稿仍可能被拒，conv_commit 仍实际执行；工具导出输入属于正确前缀的有效 row。它是有价值的真实 round 数值覆盖，但没有逐类拒绝/bonus 状态快照，不能代替自由生成、事务边界、不同图切换和 reset 的专项测试。

spec_round_logits 当前按配置的 sp.k+1 返回行数；adaptive 实际 kv 更小时，尾行不保证属于当前轮。现有 CLI 要求 ASTRAL_SPEC_FIXED，故其使用成立。新增诊断若覆盖 adaptive，须同时返回实际 nv 和有效范围，不能直接把整个 accessor 结果当当前轮证据。

数值判定接口已核实：

~~~bash
python3 "$INKLING_ENGINE/bench/llamacpp_compare/logit_compare.py" judge-paired \
  "$INKLING_JUDGE_MANIFEST" "$INKLING_CAND_JSONL" "$INKLING_REF_JSONL" \
  "$INKLING_LAB_PKG/tools/t19/rule_num3.json"
~~~

上述判定 manifest、参考与候选 JSONL 必须来自同一冻结位置集合，不能只换文件名复用旧参考。decode/verify 只导出原 manifest 首个 prompt 长度之后的位置，判定必须使用去掉该首项的生成位置 manifest，正如现有 *_gen.tsv；完整 prefill 则使用完整位置集合。新 ring/trace/message 模式尚无已实现的命令行接口，实施时再文档化；本文不虚构能直接运行的开关。

### 15.2 本次实际做过什么

- 固定读取引擎 main 和实验分支的最新可见 SHA，检查关键 model、CUDA、调度、缓存、测试、判定和实验记录。
- 对初始 v3.0.10 缓存的 81 条 manifest 文件记录校验 hash，全部一致；检查 82 个相关文件。随后对新增 T20 已下载的 56 个 manifest 文件记录校验，全部一致。
- 运行现有实验室 17 项 CPU 单测与引擎 logits 计算器 18 项离线单测，全部通过。
- 用实际计算器重算 A/B/C 的 num-3 汇总判定，对提交 JSON 逐字段一致；C 80 个预期位置独立重建。
- 对最新 T20 的 7 个公开判定重新计算：B 的五条路径 PASS、D 的两条路径 FAIL，与提交摘要一致；dense V4 仅按公开摘要复核既有公式，未从已删除的 .bin 重算。
- 阅读两篇论文与官方实现，检查两个 mlx-serve PR 的固定 head、实现、差异与公开验证状态。
- 对本方案进行独立源码与证据复核，修正 message stride、anchor 提交、Global 当前轮可见性和真实 verify 行数等实现风险。

没有运行新的 RTX 4090 基准、CUDA selftest、模型训练或长上下文实验；没有据此产生新的 tok/s、质量、接受率或实际显存结果。所有未来性能结论仍为待测假设。

### 15.3 数字的来源分级

| 数字/结论 | 性质 |
|---|---|
| 143.1/173.9 tok/s、G3 PASS | 用户仓库已有 4090 实测记录 |
| num-3 A/B/C 汇总复判 | 本次可离线独立复算 |
| T20 B 五臂 PASS、D 两臂 FAIL | 本次使用公开 JSONL 离线复算；D 硬门翻转保留 |
| T20 密集 V4 | 从公开汇总量复核公式；不是相同 D token 前缀的加密测量 |
| 8K 目标 KV 1536→416 MiB | 根据已核实模型形状推导，未实施实测 |
| 消息缓冲 432 KiB/token | 按拟议 FP32 layout 推导 |
| 论文质量与速度、MLX PR 的 Mac 成绩 | 作者在各自实验范围的报告，非本项目成绩 |
| M1/M2/M3、ring、epilogue、策略、新模型收益 | 未测；不提供虚假的累计加速倍数 |

## 16. 固定来源与定位

以下链接以固定 SHA 为主。正文中的 E 为引擎，L 为实验室，P 为论文/官方方法，F 为 Loom 实现，X 为两个 PR 的实现与状态。来源只支持所列事实；设计、优先级与验收建议是本报告的推导。

### 16.1 项目与实验记录

| 编号 | 固定来源 | 主要定位 |
|---|---|---|
| E01 | [引擎 README][E01] | fork 身份与当前复现说明 |
| E02 | [4090 基准][E02] | T14 性能与适用范围 |
| E03 | [Inkling model runtime][E03] | Config；Session；forward；layer；48 visit/slot；spec round |
| E04 | [DSpark runtime][E04] | Config；草稿 cache；store_ctx；draft block |
| E05 | [Inkling kernel wrapper][E05] | MAX_CTX；AttnShape/Prep；分派与 split |
| E06 | [DSpark CUDA][E06] | 接受长度、commit_conv、草稿双向 mask |
| E07 | [Inkling CUDA][E07] | mix、controller、conv、attention、MoE combine |
| E08 | [selftest][E08] | split_k_cases 的有效输入缺口 |
| E09 | [QAct / GEMM 分派][E09] | with_f16、quantize、launch_mma |
| E10 | [数值计算器][E10] | near_w、judge_paired、完整性与 margin |
| E11 | [KV 设计文档][E11] | 上游设计与当前 Session 实现区别 |
| E12 | [GEMV / GEMM CUDA][E12] | 量化读取、MMA tile 与 split workspace |
| E13 | [CLI][E13] | 已存在的诊断与 selftest 入口 |
| L01 | [实验室 README][L01] | v3.0.11 |
| L02 | [唯一任务表和执行记录][L02] | T14/T19；待执行 T15–T21 |
| L03 | [验证合同][L03] | num-3、V门、数据与证据要求 |
| L04 | [T19 C 结果][L04] | C/A/B JSONL 与 verdict |
| L05 | [模型资产与结构][L05] | A1/A3/A4 身份和结构 |
| L06 | [已有 R1–R10][L06] | 防止重复研究和错误语义 |
| L07 | [fork 工作包][L07] | T16/T17 的现行路线 |
| L08 | [T20 证据与脚本][L08] | B 各路径、D 失败、密集 V4 与执行范围 |

### 16.2 论文和官方代码

| 编号 | 来源 | 重点 |
|---|---|---|
| P01 | [MoLT v1][P01] | Appendix B：严格前缀递推、稳定解、Hybrid 边界 |
| P02 | [MoLT 官方固定代码][P02] | 已发布 U-MoLT 范围与方法定义 |
| P03 | [LoomFormer v2][P03] | 双流、头级读写与 MShift |
| P04 | [Loom 消融与性能表][P04] | Tables 3/9/10；不能外推 4090 成绩 |
| F01 | [HF LoomFormer][F01] | 每层 raw M 的缓存位置与读写顺序 |
| F02 | [Loom cache][F02] | M 状态和 KV 的独立生命周期 |
| F03 | [Loom fast engine][F03] | ping-pong、布局、融合、实际 dispatch |
| F04 | [Loom decode attention][F04] | 转置 K、尾块与 attention 实现范围 |

### 16.3 两个 PR 的固定实现

| 编号 | 来源 | 重点 |
|---|---|---|
| X01 | [mlx-serve #1331][X01] | 合并状态、作者验证和最终修正 |
| X02 | [mlx-serve #1330][X02] | 开放 Draft、整合范围、pending 与已知限制 |
| X03 | [DFlash2 实现][X03] | 独立草稿配置、候选 lattice/tree |
| X04 | [轮次控制器][X04] | 条件接受率、期望输出/成本、近最优选短轮 |
| X05 | [few_tail][X05] | 按列融合、候选 conv history、parent |
| X06 | [relsplit_lanes][X06] | 双源 KV、GQA/shared tile、mask |
| X07 | [持久 ladder][X07] | 成本表身份、编码与恢复 |
| X08 | [repeatable round 隔离][X08] | 单独执行、分组与请求状态边界 |
| X09 | [last-row head 合同][X09] | 完整行计算与 slice 的一致性 |
| X10 | [两 head 的比较][X10] | 分叉关系，不是最新全集 |
| X11 | [tree builder][X11] | 预算、抽样候选、父链与 proposal |
| X12 | [tree sampler][X12] | 接受/残差、随机寻址与有效分布 |

[E01]: https://github.com/lkyprogramer/inkling-4090-engine/blob/18bf3e338a08bd66223b0bc5aaa26f3896fb9446/README.md
[E02]: https://github.com/lkyprogramer/inkling-4090-engine/blob/18bf3e338a08bd66223b0bc5aaa26f3896fb9446/docs/benchmarks/inkling2_mini_rtx4090.md
[E03]: https://github.com/lkyprogramer/inkling-4090-engine/blob/18bf3e338a08bd66223b0bc5aaa26f3896fb9446/crates/model/src/inkling.rs
[E04]: https://github.com/lkyprogramer/inkling-4090-engine/blob/18bf3e338a08bd66223b0bc5aaa26f3896fb9446/crates/model/src/dspark.rs
[E05]: https://github.com/lkyprogramer/inkling-4090-engine/blob/18bf3e338a08bd66223b0bc5aaa26f3896fb9446/crates/kernels/src/inkling.rs
[E06]: https://github.com/lkyprogramer/inkling-4090-engine/blob/18bf3e338a08bd66223b0bc5aaa26f3896fb9446/crates/kernels-src/cu/dspark.cu
[E07]: https://github.com/lkyprogramer/inkling-4090-engine/blob/18bf3e338a08bd66223b0bc5aaa26f3896fb9446/crates/kernels-src/cu/inkling.cu
[E08]: https://github.com/lkyprogramer/inkling-4090-engine/blob/18bf3e338a08bd66223b0bc5aaa26f3896fb9446/crates/testing/src/selftest.rs
[E09]: https://github.com/lkyprogramer/inkling-4090-engine/blob/18bf3e338a08bd66223b0bc5aaa26f3896fb9446/crates/kernels/src/ops.rs
[E10]: https://github.com/lkyprogramer/inkling-4090-engine/blob/18bf3e338a08bd66223b0bc5aaa26f3896fb9446/bench/llamacpp_compare/logit_compare.py
[E11]: https://github.com/lkyprogramer/inkling-4090-engine/blob/18bf3e338a08bd66223b0bc5aaa26f3896fb9446/docs/design/spec/04-kv-and-memory.md
[E12]: https://github.com/lkyprogramer/inkling-4090-engine/blob/18bf3e338a08bd66223b0bc5aaa26f3896fb9446/crates/kernels-src/cu/gemv.cu
[E13]: https://github.com/lkyprogramer/inkling-4090-engine/blob/18bf3e338a08bd66223b0bc5aaa26f3896fb9446/crates/cli/src/main.rs
[L01]: https://github.com/lkyprogramer/CodexGame/blob/9f6d4b030ba26b51af2a41edfba2679febd104ee/docs/inkling-4090-lab-v3.0/README.md
[L02]: https://github.com/lkyprogramer/CodexGame/blob/9f6d4b030ba26b51af2a41edfba2679febd104ee/docs/inkling-4090-lab-v3.0/docs/07_tasks.md
[L03]: https://github.com/lkyprogramer/CodexGame/blob/9f6d4b030ba26b51af2a41edfba2679febd104ee/docs/inkling-4090-lab-v3.0/docs/05_validation.md
[L04]: https://github.com/lkyprogramer/CodexGame/tree/9f6d4b030ba26b51af2a41edfba2679febd104ee/docs/inkling-4090-lab-v3.0/tools/t19/results_c
[L05]: https://github.com/lkyprogramer/CodexGame/blob/9f6d4b030ba26b51af2a41edfba2679febd104ee/docs/inkling-4090-lab-v3.0/docs/01_model.md
[L06]: https://github.com/lkyprogramer/CodexGame/blob/9f6d4b030ba26b51af2a41edfba2679febd104ee/docs/inkling-4090-lab-v3.0/docs/06_loop_research.md
[L07]: https://github.com/lkyprogramer/CodexGame/blob/9f6d4b030ba26b51af2a41edfba2679febd104ee/docs/inkling-4090-lab-v3.0/docs/04_astral_fork.md
[L08]: https://github.com/lkyprogramer/CodexGame/tree/9f6d4b030ba26b51af2a41edfba2679febd104ee/docs/inkling-4090-lab-v3.0/tools/t20
[P01]: https://arxiv.org/pdf/2611.34923v1
[P02]: https://github.com/hustvl/MoLT/blob/1313b83adf05f666726bf009014f5f50ae345b23/language_tasks/BlaGPT/bla_gpt/u_molt.py
[P03]: https://arxiv.org/pdf/2611.30634v2
[P04]: https://arxiv.org/pdf/2611.30634v2#page=21
[F01]: https://github.com/Caiyun-AI/LoomFormer/blob/e52e5761d36066ed62e061a044d8314437cb7b11/pytorch/loomformer/modeling_loomformer.py
[F02]: https://github.com/Caiyun-AI/LoomFormer/blob/e52e5761d36066ed62e061a044d8314437cb7b11/pytorch/fast_inference/cache.py
[F03]: https://github.com/Caiyun-AI/LoomFormer/blob/e52e5761d36066ed62e061a044d8314437cb7b11/pytorch/fast_inference/engine.py
[F04]: https://github.com/Caiyun-AI/LoomFormer/blob/e52e5761d36066ed62e061a044d8314437cb7b11/pytorch/fast_inference/decode_attention.py
[X01]: https://github.com/ddalcu/mlx-serve/pull/1331
[X02]: https://github.com/ddalcu/mlx-serve/pull/1330
[X03]: https://github.com/ddalcu/mlx-serve/blob/ad695002aa89fda7ac27b901d7474ddc84299af8/src/plugins/inkling2/dflash2.zig
[X04]: https://github.com/ddalcu/mlx-serve/blob/ad695002aa89fda7ac27b901d7474ddc84299af8/src/sdk/spec/rounds.zig
[X05]: https://github.com/ddalcu/mlx-serve/blob/ad695002aa89fda7ac27b901d7474ddc84299af8/src/plugins/inkling2/kernels/few_tail.metal
[X06]: https://github.com/ddalcu/mlx-serve/blob/ad695002aa89fda7ac27b901d7474ddc84299af8/src/plugins/inkling2/kernels/relsplit_lanes.metal
[X07]: https://github.com/davidtai/mlx-serve/blob/6a22c34e558579a27a52fa4fb3a94a49d3a6c41c/src/engines/mlx/spec/ladder_store.zig
[X08]: https://github.com/davidtai/mlx-serve/blob/6a22c34e558579a27a52fa4fb3a94a49d3a6c41c/src/engines/mlx/spec/native_group.zig
[X09]: https://github.com/davidtai/mlx-serve/blob/6a22c34e558579a27a52fa4fb3a94a49d3a6c41c/src/sdk/bases/run.zig
[X10]: https://github.com/ddalcu/mlx-serve/compare/ad695002aa89fda7ac27b901d7474ddc84299af8...6a22c34e558579a27a52fa4fb3a94a49d3a6c41c
[X11]: https://github.com/ddalcu/mlx-serve/blob/ad695002aa89fda7ac27b901d7474ddc84299af8/src/plugins/inkling2/kernels/dflash_tree.metal
[X12]: https://github.com/ddalcu/mlx-serve/blob/ad695002aa89fda7ac27b901d7474ddc84299af8/src/plugins/inkling2/kernels/sample_tree_draw.metal
