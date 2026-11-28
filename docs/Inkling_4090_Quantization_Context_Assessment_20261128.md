# Inkling 4090：权重量化、KV Cache 量化与长上下文扩展评估

**日期：2026-11-28（北京时间）**  
**性质：只读调研、源码审计与条件可行性评估；未实施引擎改造，未在用户的 RTX 4090 上运行新实验。**  
**配套文档：** `Inkling_4090_Quantization_Context_Implementation_Plan_20261128.md`

## 1. 结论与建议

这个方向可行，而且是当前项目扩大上下文最直接的路线；但应分开推进两个工程规模明显不同的项目：

1. **近期：保留 A1 权重，完成已有 T44 的八个全局 visit 的 FP8/INT8 KV。** 它直接降低随上下文线性增长的存储与读取量，且已有 CUDA attention、环形缓存、分块 prefill、推测验证可作为基础。保留当前 `K12 + T45 → T44 → K15 → K13` 的优先顺序。
2. **中期：以 T31 筛选新权重，只为通过质量门的一款资产补完整运行支持。** GSQ-RCO IQ3_S 是首个质量与体积候选；AP Q3_K_XL 是保留较多现有 NVFP4 路径的工程对照。它们都不是“换个 GGUF 文件即可”。
3. **远期：全局远历史 KV 4bit、按 visit 的混合精度，再组合原生低位权重。** 512K 有明确的显存可行性；1M 可作为条件研究目标。近期不以 2bit KV 或跨 pass KV 共享作为默认实现。

建议把容量目标划成四级，避免把预测写成已达成结果：

| 级别 | 推荐组合 | 当前判断 | 主要限制 |
|---|---|---|---|
| 128Ki 的速度与余量 | A1 + 全局 KV8 | 高优先级、工程可行 | attention 解码成本、merge、量化质量与草稿接受率 |
| 192–256Ki | A1 + 全局 KV8；plain 与单 DFlash2 分别验收 | plain 256Ki 有较强显存依据；带草稿不能直接承诺 | 固定缓冲与草稿常驻、真实 prefill 峰值、配置上限 |
| 512Ki | 全局远历史 KV4，必要时降低权重驻留量 | 条件可行 | 质量、额外元数据、prefill、草稿固定开销 |
| 1Mi | 原生低位权重 + KV4，优先仅 DFlash2 | 值得研究，不是近期交付承诺 | 新格式内核、长任务质量、真实 prefill 时间与完整状态验证 |

本文的 Ki/Mi 均指 token 数的二进制单位：128Ki = 131,072，256Ki = 262,144，512Ki = 524,288，1Mi = 1,048,576。GB = 10^9 bytes，GiB = 2^30 bytes。

## 2. 固定审计快照与证据等级

| 对象 | 本次固定版本 |
|---|---|
| `lkyprogramer/inkling-4090-engine` main | `d586fec31afd08526d0500ba815a33be18199c65` |
| `lkyprogramer/CodexGame` 的 `4090-report` | `495f110dfe4a1bb5e5ae743c9378ab9a9937e103`，实验室 v3.0.26 |
| 实验室目录 | `docs/inkling-4090-lab-v3.0` |
| A1 | `Inkling-2-Mini-UD-Q4_K_XL.gguf`，17,629,760,736 bytes |
| A1 SHA256 | `e64276656f072e9b2197a61723667cbdb71da66a716ffd966e572c21088f3cd3` |
| 既有 G2 对照 | llama.cpp b12751；DFlash2 Phase 0 单独用过 b12823，不替换 G2 基线 |
| 硬件范围 | 单 RTX 4090、24 GiB 级显存、64 GB RAM；仓库记录的链路为 PCIe Gen3 x16 |

证据分四类：**代码事实**、**仓库记录的既有 GPU 实测**、**上游作者自报**、**本文推导/建议**。本次只进行了源码阅读、模型元数据/文件头核查、CPU 数值计算和验证器反例复现，没有下载完整新模型并独立复测其成绩。[S01][S02][S03]

后续执行前重新记录 HEAD、dirty diff、二进制 SHA256、PTX/cubin、模型哈希与环境。若主线继续提交，应重建基线并重审接口；不能把本报告的固定快照当成未来 HEAD 的事实。

## 3. 项目已经走到哪里

### 3.1 当前 A1 已经使用 NVFP4/Q8_0

名字里的 `Q4_K_XL` 不是当前实际张量格式。A1 的记录是 NVFP4 ×40、Q8_0 ×154、F32 ×518、BF16 ×32。GGUF 路径保留 NVFP4/Q8_0 压缩值与 scale 的 GPU 表示，并非把一个普通 Q4_K 模型在加载时统一转换为 NVFP4。[S03][S04]

`Loader::mat` 实际接受 F32、BF16、Q8_0、NVFP4。枚举中出现某个格式名不等于完整支持：IQ3_S 连 layout 都缺，Q2_K 有 block layout，但缺 CPU decoder 与目标矩阵执行路径。F16/MXFP4 的通用枚举和部分底层能力也不意味着 Inkling matrix loader 接受它们。[S04][S05]

原生 safetensors 加载路径另有转换：部分 BF16 dense/embedding 转 Q8_0、NVFP4 专家重新打包、MXFP8 专家转 Q8_0。必须区分这个路径与直接 GGUF 加载。[S06]

### 3.2 KV 已按实际访问次数分离

正式 Mini 固定三遍：6 个 prelude 层 + 12 个 core 层 ×3 + 6 个 coda 层，共 48 次执行。共享的是 24 个物理层的权重；每个执行 visit 仍有独立 KV 与短卷积历史。全局物理层为 5、11、17、23，展开后是 **8 个全局 visit、40 个局部 visit**。[S04][S07]

目标 KV 当前是 FP16。局部层已使用 ring，默认 prefill chunk =2048，局部窗口 =1024，因此局部 KV 每个 visit 配置 3072 行，保留整个 chunk 所需的窗口余量。不能把“做局部 ring”再次列为新增收益，也不能仅保留 1024 行而破坏 chunk 内较早 query 的历史。[S04]

名字 `attn_merge_q8` 表示后续激活量化，不表示持久 KV 已量化。`crates/kvcache` 中的设计骨架也不是当前目标缓存的真实实现；活跃缓存主要在 `crates/model/src/inkling.rs`。[S04][S08]

### 3.3 最新速度必须使用同一协议

| 协议/模式 | plain | DSpark | DFlash2 | DFlash2 + DSpark |
|---|---:|---:|---:|---:|
| 最近 T14/G3 记录 | 141.8 | 206.1 | — | — |
| T43/T21 的 40-prompt 混合协议 | 139.4 | 222.5 | 251.4 | 257.6 |

单位为 tok/s，均为仓库既有记录。T21 是 32 个短 prompt 加 8 个 16K raw continuation，每个输出 512 token、重复两次。汇总是每个 prompt 的重复中位数，再对 prompt 求算术平均；不是总 token/总 wall time，也不是四个桶等权。混合草稿的同口径提升是 **257.6/222.5−1≈15.8%**，不能把 206.1→257.6 全部归因于同一次改造。[S09]

现有 `--draft-alt` 在请求开始时按上下文长度选一次草稿器；两个完整 Spec 都保持常驻。它没有逐轮自适应地卸载另一套草稿状态。量化改变 verify 与 draft 的相对成本后，原先的 4096 阈值需要重新评估，但不在本次文档交付中改动。[S04][S09]

### 3.4 现有任务不重新编号

| 现有项 | 快照状态 | 本报告如何衔接 |
|---|---|---|
| K12 + T45 | 待实施 | 保留在先；统一小批 Q8 算术和 decode/verify 行为 |
| T44 | NOT_RUN | 补全 FP8/INT8 KV 的设计、容量账与验收 |
| T31 | DEFERRED | 先在外部 runtime 筛选资产，再决定 native port |
| K15 | 待实施 | 接续 attention split/merge 优化；与新 KV 布局协调 |
| K13 | 待实施 | prefill 优化仍必要；先 controller GEMV→GEMM |
| T25 | RUNNING | 保留未完成项；E 子项 PASS 不代表全任务完成 |
| T41/T46 | PASS | 沿用已有评估闭环，补一项已实证的数据完整性检查 |
| T39 | NOT_RUN | 算术误差补偿，不能宣称恢复低位权重丢失的信息 |
| T26/T28/T34 | NO_BENEFIT | 不以新名称重开相同假设 |
| K16 | 已有候选 | embedding host 放置是既有方向，不另造任务 |

T42 的最新排序为：完成 T43 后，K12+T45 → T44 → K15 → K13 → K14 → T47。本文只提出补充阶段，未改动仓库计划。[S02]

## 4. 显存账：为什么 KV8 是直接路线

### 4.1 精确的目标 KV 公式

设容量为 C，每个 K/V 行有 8×128=1024 个元素，默认局部 ring 行数 L=3072，则：

\[
M_{KV,F16}=2\times1024\times2\times(8C+40L)
=32768C+503316480\quad\text{bytes}.
\]

即全局 KV **32 KiB/token**，局部 ring **固定 480 MiB**。128Ki 时全局 4 GiB；256Ki 时 8 GiB；1Mi 时 32 GiB。只降低全局 KV，就能改变容量增长斜率。[S04，公式为本文据代码计算]

若遍数为 R，则全局 visit 数为 2+2R，局部为 10+10R。表中数字仅适用于正式三遍。减少遍数会改变模型计算，不能当作无损省缓存方法。

### 4.2 加上 scale 后的真实预算

下表仅计算八个全局 visit 的持久 K/V，不含局部 ring、热尾、page padding、权重和草稿：

| 候选布局 | bytes/token | 128Ki | 256Ki | 512Ki | 1Mi |
|---|---:|---:|---:|---:|---:|
| FP16 | 32768 | 4.000 GiB | 8.000 | 16.000 | 32.000 |
| FP8，K/V 各每 head 一 FP16 scale | 16640 | 2.031 | 4.063 | 8.125 | 16.250 |
| INT8，每 64 通道一 FP16 scale | 16896 | 2.063 | 4.125 | 8.250 | 16.500 |
| INT4，每 64 通道一 FP16 scale | 8704 | 1.063 | 2.125 | 4.250 | 8.500 |
| INT4，每 32 通道一 FP16 scale | 9216 | 1.125 | 2.250 | 4.500 | 9.000 |

以上是指定布局的数学值，不是现有功能或预测速度。非对称 zero point、保护通道、变换 codebook、FP16 热尾和对齐都需另加。精度分组越细，开销和质量可能更好也可能更慢，需实际比较。

### 4.3 目标 scratch 不会吃掉全部 KV 收益，但固定开销不可忽略

默认目标 scratch 由分配语句求和约 1078.21 MiB，短卷积状态约 3.66 MiB。另一个跨 visit 复用的 attention workspace 为：

\[
M_{attn}=12480\lceil C/64\rceil\approx195C\text{ bytes}.
\]

它在 128Ki/256Ki/512Ki/1Mi 分别约 24.375/48.75/97.5/195 MiB，**不能再乘 48**。这些是 buffer payload，不包含 CUDA context、module、graph、分配余量。[S04][S08]

使用旧 T17 plain 的 128Ki 峰值 23280 MiB 校准，扣除全局 KV 与 attention workspace，得到该配置的固定基项约 18.71057 GiB。将全局 KV 改为上述布局，得到以下**情景推算**：

| 假设配置 | 推算总量 | 含义 |
|---|---:|---|
| A1、FP8-head、256Ki、无草稿 | 22.821 GiB | 有 plain 256Ki 的可行性依据 |
| A1、INT8-g64、256Ki、无草稿 | 22.883 GiB | 接近上项，仍需覆盖 pack/真实 prefill 峰值 |
| A1、INT4-g64、512Ki、无草稿 | 23.056 GiB | 可探索，但保护区和安全余量可能改变结果 |
| A1、INT4-g32、512Ki、无草稿 | 23.306 GiB | 更细 scale 已明显压缩余量 |
| A1、INT4-g64、1Mi、无草稿 | 27.401 GiB | 仅 KV4 不足以让当前 A1 达到 1Mi |
| **假设实测权重驻留≤11 GiB**、INT4-g64、1Mi、无草稿 | 约 22.0 GiB | 说明低位权重+KV4 的组合空间；不是对某个文件的实测保证 |

表中未计新实现特有开销，基项来自历史二进制，不能直接当作分配承诺。建议工程验收预留至少 0.75 GiB 的可用显存余量；这是本方案的保守验收选择，不是硬件定律。实际总显存应读取设备值，不能硬写 24576 MiB。[S03]

### 4.4 草稿器对容量的影响不同

| 模式 | 除目标外，随 C 增长的草稿 KV | 固定项 |
|---|---:|---|
| 无草稿 | 0 | 无 draft |
| DSpark，默认 FP16 | 4096 C bytes | 权重、两层 local ring、features、verify/rollback、graphs |
| DFlash2 | 0 | 五层 local ring、权重与更丰富的草稿缓冲 |
| DSpark + DFlash2 同时常驻 | 4096 C bytes | 两者完整固定状态都存在 |

DSpark 只有一层全局 draft KV，其余两层为局部。DFlash2 的五层都是 window=2048；引擎实际分配 2056 行，因此纯 KV 约 40.156 MiB，而不是随 C 增长。配置与运行时代码已交叉核对。[S10][S11][S12]

不能把 DFlash2 的“无全局缓存”理解为没有额外显存：仓库最大成功分配点 122880 的峰值已是 24062 MiB。仅 target KV8 对双草稿容量的收益不能按 2×计算。建议先验收 plain 256Ki；带 DFlash2 从 192Ki 开始逐档上探，224/240/256Ki 由实际余量决定。达到更长上下文时优先单 DFlash2 profile，避免不使用的 DSpark 全局历史继续占用显存。

## 5. 速度收益：有空间，但不能承诺翻倍

T42 在 128K 的 plain profile 中，global attention split 占 GPU busy 的约 35.9%，merge 占 12.1%；短上下文则 Q8 小批算子更突出。这支持保留 K12 在先、T44 后接 K15 的原顺序。[S02][S13]

即使把这 35.9% 的 split 部分理想化为快一倍，而其他工作完全不变，按该口径得到：

\[
S\le\frac{1}{(1-0.359)+0.359/2}\approx1.219.
\]

这是特定“只缩短 split 一半”假设的 Amdahl 演算，不是 T44 的普适上限；融合可能节省其他成本，解码、同步和 scale 读取也可能反向增加成本。原计划中 73.7→95–105 tok/s 仍是预测。新一轮应分别记录 attention、merge、pack、verify、draft、accepted tokens/round 与完整请求时间。

4090 的 Ada/SM89 支持 FP8 能力，但不具备 Blackwell 的原生 NVFP4/MXFP8 路径。已有 A1 NVFP4 是通过 SM89 可执行内核消费它，不能据此声称 4090 使用 Blackwell FP4 Tensor Core。FP8 存储压缩与 FP8 attention 全矩阵计算也是两件事；近期优先在片上解码后沿用现有算术，是否改 FP8 QK/PV 是后续独立实验。[S14]

低位权重同样如此：专家文件更小，可能降低权重读取；复杂 IQ/codebook 解码、寄存器压力、grouped GEMM 排布、verify 专家并集会抵消部分收益。相同 token、相同上下文、相同草稿策略下的端到端 A/B 才有决策价值。[S04][S15]

**长 prompt 的 prefill 是另一条上限。** 八个 global visit 仍执行稠密因果 attention；压缩 KV 并没有消除随真实输入长度 N 近似按 N² 增长的 attention 工作。输入从128Ki增到1Mi时，线性部分约增8倍，二次部分约增64倍；这只是工作量尺度，不是实际延迟预测。旧 T17 的128K prefill为31.849秒，可作为历史参照；新路径应在多个真实输入长度拟合 `T_prefill(N)=aN+bN²+c`，用实测决定是否继续扩大容量，而不是从 decode tok/s 推算首字延迟。[S04][S08][S33]

完整请求时间应同时报告 `T_request≈TTFT+生成token数/decode速度`、有效终答率与每个有效答案耗时。对只生成几百token的长文请求，decode提速可能远小于prefill增加的成本。K13仍然有价值；本方案没有因KV8而跳过既有prefill优化。

## 6. 哪些新量化模型值得接入

### 6.1 固定文件大小与初步排序

| 候选 | 文件大小（GiB） | 当前引擎新增格式种数 | 定位 |
|---|---:|---:|---|
| GSQ-RCO IQ3_S | 10.641 | 12 | 第一质量/容量候选，分配与评估资料透明 |
| GSQ-RCO Q2_K_XL | 9.120 | 12 | 更激进容量候选；不是首个默认替换 |
| AP Q3_K_XL | 12.696 | 9 | 保留 32 个 NVFP4 张量，适合作工程成本对照 |
| AP IQ2_XXS v1.2 | 7.903 | 10 | 极低位对照，质量和 native 内核成本需另判 |
| kaiPTQ Q2_K_XS | 7.449 | 独立 trellis 路径 | 研究候选，暂不并入首轮 native port |
| kaiPTQ Q3_K_S / Q3_K_M | 9.312 / 11.175 | 同上 | 可做外部质量对照 |

文件大小来自固定 HF revision 的 API 清单；不是用户 GPU 实测。GSQ 两款的 inventory 来自完整作者 allocation；AP 两款读取前 16 MiB 后解析完整 tensor directory，未下载全部权重、未独立重算整文件 hash。[S15][S16][S17]

**不能把上游不同评测的得分拼成一个“最好量化”排名。** GSQ 的 xhigh、多次采样、部分 BF16 解码评估，与 AP 的 KL/小规模 agent 任务、kaiPTQ 的 high/温度1 GPQA、EXLR8 的 low/固定输出预算均不同。它们支持各自的候选价值，不证明当前 4090 runtime 的综合胜负。

### 6.2 支持闭包远大于一个类型

GSQ `IQ3_S` 中不只有 IQ3_S；`Q2_K_XL` 甚至没有 Q2_K 张量。两款 GSQ 的新增格式并集为 13 种，再加两款 AP，共需 14 种。完整清单见附录 A。

工程含义是：parser、CPU 参考解码、GPU packed layout、单行 GEMV、2–8 行 verify、分组专家 GEMM、prefill、embedding/dense 非专家路径都要闭合。只给 enum 加名字，或仅写 decode kernel，无法构成可用支持。

草稿器也读取目标权重：DSpark 初始化用目标 output head 计算 `rank+1` 行的折叠 head（常见为65行）；DFlash2 用目标 embedding 构造 mask row，运行时再使用目标 head、top-16 与 selector。新格式必须覆盖这些行数与调用路径；切换目标资产后须重新构造派生表，不能复用旧A1的派生状态。草稿权重不改仍可能降低接受率。[S10][S11]

其中 Q2_0 是 id42、64 值/18 bytes；Q2_K 是不同的 256 值 block。Inkling expert-down 的 K=1152，可整除 64/32，不能整除 256，格式不能按文件名替换。AP Q3 的 32 个 NVFP4 张量还配有 32 个 `[128]` 外部专家 scale；当前 loader 已有 `.scale` 发现与上传路径，应复用并验证，不能遗漏，也不必把它虚构成全新模块。[S04][S18]

### 6.3 三条接入路径的真实差异

| 路线 | 优点 | 代价与边界 | 建议 |
|---|---|---|---|
| 外部 llama.cpp/kaiLLM 先测 | 不先付 native kernel 成本 | 外部速度不等于 Astral 速度 | T31 首选 |
| 源解码后重新量化为 NVFP4/Q8_0 | 可以复用当前算子、测试校准来源价值 | 引入二次量化；2–3bit 权重容量优势通常不再保留 | 独立质量实验，不作为低位容量交付 |
| 保持原始量化值的 packed native 执行 | 能兑现压缩驻留与相应读取优势 | 需要完整格式与算术路径 | 只为外部筛选过门的一款做 |

重新量化不一定抹掉所有上游校准价值，也绝不能宣称仍保留上游分数；它是一个新派生资产。精确重新排列字节与重新量化应分别命名。

GSQ 的 BF16 input embedding 有约 0.863 GiB。作者称其不占 VRAM，是针对其 llama.cpp 放置方式；本引擎把 embedding 上传 GPU。K16 可研究 host embedding，但不得在当前预算中默认已经省掉这部分。[S04][S15]

### 6.4 kaiPTQ、EXLR8、TensorFold、Basalt 的取舍

kaiPTQ 的 `.gguf` 包含 trellis 编码，需要 kaiLLM；模型卡明确另有 llama.cpp 兼容版本，不能被页面自动生成的通用运行示例误导。EXLR8 也不是普通 EXL3 文件：其专用 codebook、side vector、变换与舍入顺序必须严格保持。两者可以借鉴校准与布局，但移植属于独立内核研究。[S17][S19]

MiaAI 的“RTX5090 TensorFold”仓库明确写尚未在 5090 实测，相关数据来自 RTX PRO6000。Basalt 的目标硬件也不同。可吸收按行数分派、量化布局、pass-aware 校准思路，不将名字或 Blackwell 数字折算成 4090 预期速度。[S20][S21]

## 7. 论文与相关研究：哪些能真正变成项目工作

| 来源 | 可借鉴的最小部分 | 在本项目的位置 | 不直接照搬的部分 |
|---|---|---|---|
| KIVI | K/V 分开分析；近端高精度；tile 内反量化 | KV4 候选与统计探针 | K 跨 token 分组会增加回滚事务复杂度；非 Inkling 质量保证 |
| KVQuant | outlier、分层敏感性、统计与存储分开 | T44 校准/误差诊断 | 目标模型没有 RoPE，不能机械移植 pre-RoPE 量化 |
| TurboQuant | 旋转/编码与内积误差的关系 | 低位远历史探索 | 不由压缩率推导单流端到端加速 |
| Inkling SRFT，2611.29092 | 有限 RPE 的远近拆分、GQA 复用、归一化 V 的低位编码 | KV4 以后的一条专项研究 | Metal 性能不转移；1M seeded-cache 不等于真实1M请求 |
| LoopKV | `(physical layer, pass, K/V)` 敏感性与成本联合分配 | T44 后的混合精度 | Ouro 的共享与阈值不能直接用于 Inkling |
| ResidualQuant | 最后 pass anchor + 残差的候选编码 | 仅在本项目相关性探针过门后 | 原 runner 对 chunked prefill/prefix 有限制；需解决未来 anchor 与提交时序 |
| LoopQuant/LoopTax | pass-aware 校准及对误差传播假设的反证 | 权重量化诊断 | 不预设误差必然按遍数线性或指数累积 |
| GSQ/RCO | 固定容量预算下，优化量化值与分配精度 | T31 与后续 in-house recipe | 不直接移植完整自动化平台 |
| Loop-PP/BRAID-MoE | 执行身份/依赖应显式表达 | 延续现有 visit/slot 正确性 | 多卡训练/通信收益不是当前单卡量化收益 |

这些资料分别对应 [S22]–[S32]。论文收益除特别说明外均是作者在其模型、硬件、负载上的结果。

直接相关的 SRFT 工作尤其值得保留，但要严格限制证据解释：其低位远历史方案报告了明显存储节省；256K–1M 的 decode 计时用直接构造的 cache，未完成相应长度真实 prefill；质量检查仅少量短语料窗口和 ≤32K 的三个 passkey。它提供了实现线索，不能证明你的引擎已经能在 1M 上可靠处理代码/多跳任务。[S25]

LoopKV 的重要启示是“精度按测得的 visit 敏感性分配”，而非“最后一遍必然最重要”。ResidualQuant 还要求当前 token 的最后一遍 anchor 完成后才能编码早期遍次；若与推测回滚、chunk 内因果顺序冲突，不能用提前读取未来 anchor 来换空间。[S26][S27]

## 8. Inkling 专属设计约束

### 8.1 不需要先做 RoPE 外推

官方模型声明原生上下文可达 1M。当前项目的 132096 是实现配置上限与显存限制，不是模型只训练了 128K。目标模型使用短卷积、有限相对位置 bias、query-dependent sink 与长度相关缩放，目标 attention 没有 RoPE。草稿器自身则有 RoPE；二者不能混为一谈。[S07][S10][S11]

### 8.2 必须保持的数值顺序

目标 K/V 的链路是：短卷积 → K 的 L2 clipping / V 的无 gamma RMS normalization → cache。Q/R 先应用 learned scale 与 clipping，全局 Q/R 再乘长度因子 tau。attention 为：

\[
s_{p,j}=Q_pK_j^T/\sqrt{128}+R_pB_{p-j}-sink_p.
\]

距离 ≥1024 时 RPE 项为零；softmax 分母还有一个零 logit、零 value 的 learned sink 表示。量化不得放到短卷积输入之前；也不能给每个 split 各加一次 sink。远近 attention 合并必须合并未归一化的 softmax 统计，sink 只计一次。[S08]

### 8.3 为什么短上下文通过还不够

对于同一个 key 量化误差 e，有 `|Δscore| ≤ ||Q||₂·||e||₂/√128`。当前 global Q 在 clipping 后还乘随位置增长的 tau，因此短上下文的量化损伤不能自动外推到 256K/1M。要直接测长位置的 score、attention 输出与任务质量；这也是只跑 4K PPL 不够的数学原因。

V 的归一化在实现中含 epsilon 和 FP16 舍入，只能说近似单位 RMS。采用“无 scale V”前必须统计每个 global visit 的实际 norm，包括极小输入、不同 pass、换权重后的情况。不能从论文的理想化假设跳过这一步。

### 8.4 共享权重与共享缓存不是同一件事

首轮保持每个 visit 独立缓存。按 pass 改精度可使用同一物理权重，但独立 cache codec；跨 pass 共享 K/V 或 anchor 残差会改变状态依赖，另行验收。正式 Mini 不改三遍；varloop、动态循环与训练改造不作为本方案前置条件。

## 9. 现有证据门需要补齐什么

### 9.1 容量、真实输入、完成终答分开登记

| 已有证据 | 可以支持 | 不能单独支持 |
|---|---|---|
| DFlash2 C=122880，64-token prompt+8 output 成功 | 该容量配置能分配并执行短请求 | 122880-token 真实 prefill/质量 |
| T17 的约128K真实 prompt、PPL/抽样数值 | 现有模型的部分长上下文行为 | 全任务/多文档鲁棒性 |
| T25 E 的5.3K–9.4K六份 prompt | 该范围的数值比较 | 128K有损KV质量 |
| T17 9/9 passkey 出现在 content+reasoning | 能在生成某处取回 key | 9次均完成正确终答；其中6次 answer为空 |

T43 的执行记录另报告120K prompt 约94–95 tok/s，但已提交 P3 summary/fit 未含这一轮，应补原始证据后再用于新路线的严格 A/B。122880 是最大成功测试点，122881–131071 未扫描，不能称精确硬上限。[S09][S33]

### 9.2 本次实际复现的一个判定器缺口

使用仓库自己的 CPU fixture、原封不动的 `t25_judge.py`，把实际 NPZ position 全部加100000，仍返回 PASS；把每份 NPZ 缩成一行、JSON声明计数保持174，实际只评分2行，仍返回 PASS。这说明**实际数组的行数和精确位置集合尚未与输入 manifest 对齐**。它不证明历史 E 数据有问题。[S34]

建议作为 T41 追加一条定向修复：实际 position set、case ID、vocab width、行数、源输入哈希全部与冻结 manifest 核对；缺失/截断必须非零退出。无需因此重做整个评估系统。

### 9.3 有损量化采用两层判定

第一层检查“实现正确”：CPU codec 与 GPU reader 在同一组已解码量化值上对拍、状态不串、回滚可重现。第二层检查“近似是否值得”：相对冻结 A1/F16 的 PPL、KL、任务成功率、最终答案、草稿接受与性能。

量化不应假装逐位等价于原 F16 目标。推测解码的算法正确性应针对**同一个量化后的 target**检查；T45 的 batch invariance 也要覆盖该新 target。T46 的 top-2048+tail KL 仍仅用于筛选，正式候选需全词表抽样复核，不沿用其在旧分布上的0.43%差异作为新量化的保证。[S02]

## 10. 建议的验收与停止条件

以下是本报告提出的工程门，不是已经通过的结果。更详细的样本、命令与实现任务见配套方案。

| 维度 | 首轮8bit建议门 | 失败后的动作 |
|---|---|---|
| 数据完整性 | 所有预期case/position/hash实际存在；负控触发 | INVALID，不允许PASS |
| 算子与状态 | decoder一致；边界/拒绝/重置覆盖；关闭开关恢复原路径 | 修实现，不以宽松质量门掩盖 |
| 语言建模 | 留出集相对PPL增量≤0.5%；每域单列 | 细化K/V scale，保护敏感visit |
| 检索/代码/终答 | 配对95%单侧下界不低于基线−2个百分点；样本不足判INCONCLUSIVE | 扩足预先登记的样本或退回F16，不宣称无损 |
| 生成行为 | 截断/复读率增量的95%单侧上界≤1个百分点 | 查量化、停止条件或长上下文质量 |
| 内存 | 同C目标global KV实际payload≤原55%；整体峰值含所有stage/graphs，余量≥0.75GiB | 容量目标下调或单独研究固定项 |
| 速度型通过 | 64–128Ki端到端decode至少+10%，短桶回退≤3%，配对置信区间支持收益 | NO_BENEFIT或容量型profile |
| 容量型通过 | 新C真实prefill+生成+质量通过；共同C端到端回退≤5% | 若只分配成功，保留为capacity-smoke |

每种新权重先独立测试，组合时采用四臂：A1/F16、newW/F16、A1/newKV、newW/newKV。不能把组合误差简单假定为两个单项误差相加。

**停止规则：** 若8bit实现正确但共同上下文速度改善不足，容量有用则保留容量profile；若质量不过门则收回为研究模式。若外部T31质量与容量没有达到目标，不启动14格式大工程。若1M只有直接构造cache计时或分配成功，结论只能是容量/内核研究完成，不能标记1M任务支持。

## 11. 分阶段投资判断

| 阶段 | 产出 | 工程规模判断 | 进入条件 |
|---|---|---|---|
| CPU准备 | inventory、内存账、数据完整性回归、冻结数据 | 小 | 可与当前主线并行，不占4090 |
| T44 8bit | 完整global写入、decode/verify/prefill reader与回滚 | 中 | 当前K12/T45阶段完成或其契约冻结 |
| >132096容量 | 显式大context开关、真实长输入报告 | 中 | 8bit质量/状态门通过 |
| T31筛选 | 一款或零款通过的低位权重 | 小到中 | 独立GPU时隙；先外部runtime |
| 单资产native port | 选定格式闭包、SM89 kernel、完整回归 | 大 | 预计节省≥2GiB且质量可接受；不是仅文件更小 |
| 远历史KV4 | exact近端+packed远端与LSE合并 | 中到大 | KV8和长文基础稳固 |
| Loop-aware/SRFT/残差 | 更低bit或更高质量的专项codec | 研究性 | KV4仍不能达到目标，且探针显示可利用结构 |

不建议现在一起开展多种 trellis 格式、2bit KV、动态循环、专家裁剪和树推测。这里的约束来自可归因性与单卡验证成本：同一轮只改变一个因素，已有主线继续推进。

## 12. 最终判断

当前项目的下一段上限不只是 kernel 小修。**全局 KV8 是近期最确定的容量杠杆；原生低位权重是更大空间、更高接入成本的中期杠杆；KV4 与二者组合是512K–1M的合理研究路线。**

最值得避免的浪费是：在没有本地质量筛选前实现全部量化格式，或者把文件变小、cache构造成功、短PPL不变三件事合并成“超长上下文已可靠提速”。配套方案将它们分别设为可独立证伪的阶段。

## 附录 A：四款候选的完整格式闭包

计数为张量数，不是参数量、字节占比或工程工时。GSQ为作者allocation，AP为本次完整header解析。[S15][S16][S18]

| 类型 | ID | GSQ IQ3_S | GSQ Q2_K_XL | AP Q3_K_XL | AP IQ2_XXS |
|---|---:|---:|---:|---:|---:|
| F32 | 0 | 478 | 478 | 510 | 478 |
| BF16 | 30 | 57 | 57 | 32 | 32 |
| Q8_0 | 8 | 11 | 7 | 105 | 85 |
| NVFP4 | 40 | 0 | 0 | 32 | 7 |
| IQ1_S | 19 | 3 | 5 | 0 | 6 |
| IQ1_M | 29 | 0 | 2 | 0 | 0 |
| IQ2_XXS | 16 | 6 | 5 | 0 | 7 |
| IQ2_XS | 17 | 2 | 3 | 1 | 6 |
| IQ2_S | 22 | 3 | 8 | 3 | 5 |
| IQ3_XXS | 18 | 6 | 1 | 5 | 3 |
| IQ3_S | 21 | 4 | 0 | 2 | 0 |
| IQ4_NL | 20 | 21 | 13 | 4 | 0 |
| IQ4_XS | 23 | 10 | 45 | 0 | 2 |
| Q2_0 | 42 | 3 | 11 | 0 | 17 |
| Q3_K | 11 | 0 | 0 | 1 | 0 |
| Q4_K | 12 | 22 | 34 | 3 | 14 |
| Q5_K | 13 | 29 | 22 | 12 | 16 |
| Q6_K | 14 | 49 | 13 | 26 | 26 |
| 总数 | | 704 | 704 | 736 | 704 |

## 附录 B：资产快照

| 仓库 | revision |
|---|---|
| `ISTA-DASLab/Inkling-2-Mini-GSQ-RCO-GGUF` | `f0da1097633dd7c2f5733e4077cff861be122245` |
| `agentionai/Inkling-2-Mini-AP-GGUF` | `94a178b6dad70c9ecee7784cd4a9b9ebfa383f6c` |
| `kaitchup/Inkling-2-Mini-chimachima-kaiPTQ` | `47eb5bde4d681c4f2ac1b43f2f7338c0aaa017a0` |
| `thinkingmachines/Inkling-2-Mini` | `c9d028302cd0f035fdf8e7e91f089a4ce94d2195` |
| `kindlingai/inkling-2-mini-exlr8-k2-k3-k4` | `3037e66b3f01003ddf2c62b7e1d9469c59104609` |
| `aminems/inkling-1m-mlx` | `51e1653dc55aa4153e809d43f76ace45ea7e7769` |

新模型最终执行时下载到本地后必须独立计算完整文件SHA256。远端LFS hash与metadata记录不是本次已验证的完整payload哈希。

## 来源索引

来源访问日期均为2026-11-28。未提供完整commit的外部文档为当日快照，执行时需重新固定版本。

- [S01] [引擎固定提交](https://github.com/lkyprogramer/inkling-4090-engine/commit/d586fec31afd08526d0500ba815a33be18199c65)。
- [S02] [实验室07_tasks，含T42–T46执行记录](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/docs/07_tasks.md)。
- [S03] [4090硬件与长上下文记录](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/docs/hardware/rtx4090.md)；[A1资产](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/docs/01_model.md)。
- [S04] [Inkling Config/Loader/Session/Spec实现](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/model/src/inkling.rs)。
- [S05] [格式枚举与CPU解码](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/quant/src/lib.rs)；[GGUF loader](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/loader/src/lib.rs)。
- [S06] [原生checkpoint转换](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/loader/src/inkling_checkpoint.rs)。
- [S07] [官方模型卡](https://huggingface.co/thinkingmachines/Inkling-2-Mini)；[官方发布说明](https://thinkingmachines.ai/news/inkling-2-mini/)。
- [S08] [CUDA目标attention及prep](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/kernels-src/cu/inkling.cu)；[kernel接口与workspace](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/kernels/src/inkling.rs)。
- [S09] [T43混合结果](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/tools/t43/results/p1/sw_report.txt)；[P3原始摘要](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/tools/t43/results/p3/summary.txt)；[fit.tsv](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/tools/t43/results/p3/fit.tsv)。
- [S10] [DSpark缓存与Spec](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/model/src/dspark.rs)。
- [S11] [DFlash2 runtime](https://github.com/lkyprogramer/inkling-4090-engine/blob/d586fec31afd08526d0500ba815a33be18199c65/crates/model/src/dflash2.rs)。
- [S12] [DFlash2固定配置](https://huggingface.co/incoai/Inkling-2-Mini-DFlash2/raw/4f9088ea/config.json)。
- [S13] [128K kernel profile](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/tools/t42/results/dec130944.kernels.txt)。
- [S14] [NVIDIA Ada tuning](https://docs.nvidia.com/cuda/ada-tuning-guide/)；[Transformer Engine格式支持矩阵](https://docs.nvidia.com/deeplearning/transformer-engine/support_matrix.html)。
- [S15] [GSQ-RCO模型卡](https://huggingface.co/ISTA-DASLab/Inkling-2-Mini-GSQ-RCO-GGUF)；[固定tensor allocation目录](https://huggingface.co/ISTA-DASLab/Inkling-2-Mini-GSQ-RCO-GGUF/tree/f0da1097633dd7c2f5733e4077cff861be122245/tensor-allocation)；[评估代码](https://github.com/IST-DASLab/GSQ-RCO-eval)。
- [S16] [AP模型卡](https://huggingface.co/agentionai/Inkling-2-Mini-AP-GGUF)；[固定文件清单](https://huggingface.co/api/models/agentionai/Inkling-2-Mini-AP-GGUF/tree/94a178b6dad70c9ecee7784cd4a9b9ebfa383f6c?recursive=true&expand=false)。
- [S17] [kaiPTQ模型卡](https://huggingface.co/kaitchup/Inkling-2-Mini-chimachima-kaiPTQ)；[kaiLLM](https://github.com/the-kaitchup/kaiLLM)。
- [S18] [ggml格式结构定义](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-common.h)。
- [S19] [EXLR8模型与格式](https://huggingface.co/kindlingai/inkling-2-mini-exlr8-k2-k3-k4)；[FORMAT.md](https://github.com/kindlingai/exlr8/blob/main/FORMAT.md)；[5090 recipe](https://github.com/kindlingai/recipes/tree/main/inkling-2-mini/rtx-5090/1x/exlr8-gr8)。
- [S20] [MiaAI TensorFold recipe](https://github.com/MiaAI-Lab/Inkling-2-Mini-RTX-5090-TensorFold)。
- [S21] [用户指定Basalt fork](https://github.com/losingle/basalt)。
- [S22] [KIVI，2402.02750](https://arxiv.org/abs/2402.02750)。
- [S23] [KVQuant，2401.18079](https://arxiv.org/abs/2401.18079)。
- [S24] [TurboQuant，2504.19874](https://arxiv.org/abs/2504.19874)。
- [S25] [Inkling SRFT，2611.29092](https://arxiv.org/html/2611.29092v1)；[作者实现](https://github.com/aminems/inkling-1m-mlx/tree/51e1653dc55aa4153e809d43f76ace45ea7e7769)。
- [S26] [LoopKV，2611.04137](https://arxiv.org/abs/2611.04137)。
- [S27] [ResidualQuant，2610.10381](https://arxiv.org/abs/2610.10381)；[作者代码及prefill限制](https://github.com/heejunkim00/ResidualQuant)。
- [S28] [LoopQuant，2610.16368](https://arxiv.org/abs/2610.16368)；[LoopTax实验](https://github.com/shubhambaid/loop-tax)。
- [S29] [GSQ，2604.18556](https://arxiv.org/abs/2604.18556)；[RCO，2605.00649](https://arxiv.org/abs/2605.00649)。
- [S30] [Loop-PP，2611.30581](https://arxiv.org/abs/2611.30581)。
- [S31] [BRAID-MoE，2611.32572](https://arxiv.org/abs/2611.32572)。
- [S32] [vLLM量化KV与跳过指定层的官方文档](https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache/)。
- [S33] [T17性能报告](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/tools/t17/results/b/report.txt)；[T17 needle原始输出](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/tools/t17/results/b/needle.jsonl)；[T25 E构造脚本](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/tools/t25/t25_e.sh)。
- [S34] [T25判定器](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/tools/t25/t25_judge.py)；[原始测试fixture](https://github.com/lkyprogramer/CodexGame/blob/495f110dfe4a1bb5e5ae743c9378ab9a9937e103/docs/inkling-4090-lab-v3.0/tests/test_t25_judge.py)。本文反例在该版本副本上CPU复现，未修改用户仓库。
