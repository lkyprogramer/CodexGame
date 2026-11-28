# 论文与代码调研：Self-Rewriting / LoopTitan / QDA 对方案 13（T37–T40）的核对与借鉴

日期 2026-11-28 · 范围：方案 13（docs/13_inkling_loop_model_extreme_research_plan_20261128.md）第 4 章中三篇 arXiv 论文及两个代码仓库。只读研究，未编译、未安装、未运行任何训练或推理。

**标记约定**
- 【源码】可复查的仓库事实，带 文件:行号。LoopTitan 路径相对 repos/LoopTitan/src/moeloop/；QDA 路径相对 repos/qda/。
- 【自报】论文或仓库文档自报的实验数据，本次未复现。
- 【推断】我的计算或判断，给出前提。

**材料与固定版本**
- 论文 PDF 在 /root/github/inkling-research/papers/，共约 10 MB：looptitan_2611.34821v1.pdf、qda_2611.23388v1.pdf、selfrewriting_2611.21885v2.pdf。
- 仓库在 /root/github/inkling-research/repos/，均为 --depth 1 浅克隆：
  - LoopTitan HEAD a9f526a78469069e7ab3d628e4e7395254837f4e，22 MB。
  - qda HEAD dc39a02bfd87bb2790e34001708d54ce9131e076，17 MB。
  - 两者都与方案 13 §16 的 pin 一致。
- 方案 13 实际只引用了三个 arXiv 编号。AP 是 HF 模型库，Dlouapre 是 HF Space，均不是论文；§4.3 与 §4.5 不在本报告核对范围内。

---

## 0 结论

1. **方案 13 第 4 章关于这三篇论文的事实陈述基本准确，没有发现错误。**
   - 有两处偏保守或遗漏，会影响 T37 和 T38 的先验：
     - LoopTitan 在匹配预算下，非复访对照保留了**全部**收益；加算力时，更深的对照拿到 90.2%。方案写的是"大部分"。
     - LoopTitan 自己统一协议复现的 per-visit LoRA、EMA memory、学习型退出门、随机深度，**都比 LoopTitan-Base 差**（+8.14 / +21.68 / +43.47 / +14.89 mBPB）。
   - 方案还漏了 LoopTitan 附录 D.3 的各遍梯度余弦和信噪比数据。这正是 T38 的直接先验，而且偏负面。
2. **QDA 对 Astral 有用的部分是评估闭环，不是量化配方。**
   - 评估闭环指：top-128 加尾桶的 KL 缓存、gencheck 截断与复读检测、噪声带 σ、"存储网格不等于服务网格"的检查。
   - 量化配方用不上的原因：
     - A1 的专家本来就是官方 NVFP4 / MXFP8 原生格式，没有更高精度的 master 可恢复。
     - QDA 没有 Q8_0 或 FP8 专家库的 GGUF 搜索空间。【源码】docs/formats.md："QDA writes no FP8 expert bank"；GGUF 只有 gguf-q4km。
3. **K7（Q8_0 → FP8）在 sm_89 上的理由很弱。**【推断】
   - 精度：E4M3 相邻值的相对间距为 6.7–12.5%，比 Q8_0 粗约 14–17 dB SQNR。
   - 带宽：每权重只省约 6% 字节。Q8_0 在 decode GPU 时间中占 39%，所以端到端上限约 2.3%。
   - 计算：对算力受限的 prefill，直接用 Q8_0 的 int8 码走 INT8 mma 更合适，权重无损。
4. **T37–T40 的独立排序（§5）：**
   - T39 先做，并加一个更便宜的"每 (层, 专家, 遍) 标量"前置臂。
   - 然后搭 M1/M2，用 Muon 作基线，并加 LoopTitan 式对照。T38 和 T37-tiny 都在这里花几分钟 GPU 就能筛。
   - 再建"冻结量化 A4 的可微参考"。T37 全尺寸、T40、各种 per-visit 小适配器都依赖它。在 2K 上下文下估计峰值约 20–21 GiB，可行。
   - T38 全尺寸最后做，M1 无信号就不做。
5. **M1/M2 在 2M token 下只需几分钟 GPU，2M 太少。**【推断】
   - LoopTitan 自报：在大得多的模型上，0.625B token 时循环配方没有收益（Fig. B1）。
   - 建议把每机制 4 GPU 小时的停止预算换成 100M–1B token 级的筛选。

---

## 1 方案 13 第 4 章逐条核对

### 1.1 §4.1 Self-Rewriting（arXiv 2611.21885v2）

| 方案陈述 | 核对 | 依据 |
|---|---|---|
| 编辑者参数固定，编辑只作用于它请求的 target runs | 准确 | 【自报】论文方法部分：编辑者即模型自身，φ=θ 固定，编辑只施加在被请求的运行上 |
| 附录 E.9 的八个会话各自从 base weights 开始 | 准确 | 【自报】E.9 第二协议 |
| 最大变化：48 个线性注意力层 dt_bias 全部 +0.5，held-out 57.2% → 63.8%，截断率下降 | 准确 | 【自报】session 8：+6.6 点，95% CI [5.0, 8.1]，p<1e-5；截断率 33.6% → 26.1% |
| 修复实验由未损坏模型编辑损坏副本 | 准确 | 【自报】repair 实验 |
| 没有找到官方完整工程或编辑后权重 | 我也没找到 | 正文只有项目主页链接，没有代码链接 |

方案没写、但对筛选协议有用的细节：
- 第二协议的 8 个会话中 5 个主动撤回。显著的只有两个：session 8，以及 session 2（层 63 输出矩阵减去某测得方向的 5 倍投影，+4.0 点）。
- 第一协议的编辑只有 57.2% → 58.3%（p=0.038）。
- 摘要里"八个连续会话准确率只升不降"不是累积进化，方案 §4.1 的判断正确。

### 1.2 §4.2 LoopTitan（arXiv 2611.34821v1，代码 a9f526a7）

| 方案陈述 | 核对 | 依据 |
|---|---|---|
| 匹配参数、训练 FLOPs、logical KV；拆开复访、形状、残差尺度和优化器 | 准确 | 【自报】§3–§5 |
| 在所测设置中，循环配方的"大部分"优势可由这些因素解释 | **偏保守** | 【自报】匹配预算下非复访对照保留全部收益，复访本身 +0.7（AdamW）/ +0.6（Muon）mBPB，在噪声内。加一遍算力时，更深对照拿到 90.2%（10.4 vs 11.5 mBPB），复访剩下约 1.1 mBPB |
| 代码含物理 owner 与 logical visit 分离、visit 专属组件、EMA memory、每 visit KV、Muon | 准确 | 【源码】见 §2.1 |
| 优化器对共享 owner 先求和梯度再更新 | 准确 | 【源码】optim.py:5–6 原文："A shared owner's gradient is already the sum over its calls, so it receives one update per optimizer step." 这是 autograd 自然累加，不是专门写的求和步骤 |
| 残差尺度等价关系联动初始化、学习率、衰减和 epsilon | 准确 | 【自报】Proposition 1：(a; W0, η, λ) ⇔ (1; aW0, aη, λ/a)，AdamW 还要 ε/a。前提是不 clip，且 Muon 有范数下界；各遍尺度不同时不成立 |
| 主要用 8×H200，大设置 16×H200；17 个模型 seed 42 | 准确 | 【自报】MoE-12 在 5B token 下用 35.6 H200·h |

方案遗漏、而且会改变判断的内容：
- **统一协议下的已发表循环设计（Tab. B9，Muon，5B token，seed 42，相对 LoopTitan-Base 的 mBPB）【自报】**
  - 和 Inkling 拓扑最接近的"中段跑两遍（prelude + core×2 + coda）"：+0.51
  - 所有层跑两遍并加 per-visit LoRA（rank 160，只加在 attention 上）：**+8.14**
  - 短中段循环跑四遍：+8.09
  - 四层共享专家：+12.29
  - 随机深度（只反传最后 2 遍）：+14.89
  - 两个 EMA memory：**+21.68**
  - 学习型退出门：**+43.47**
  - 含义【推断】：在从零训练、匹配预算的条件下，"给循环加 per-visit 状态或适配器"没有一项胜出。T37 是 per-expert 账本，和 per-visit 状态同类，先验偏负。这不直接否定在冻结模型上改装（retrofit），但 T37 必须带 §6.6 已列出的"同容量匿名状态 / 普通 adapter"对照。
- **训练长度（Fig. B1）【自报】**："The looped recipe has no gain at 0.625B tokens"。直接影响 §11.1 的 2M token 筛选设计，见 §5.4。
- **读出（App. D.2）【自报】**
  - 第一遍后就读出，要多付 98.2–274.3 mBPB。
  - 收益最大的 20% token 占第二遍收益的 64–95%。
  - 第二遍残差更新的范数是第一遍的 1.76–2.61 倍。
  - 固定遍数模型在未训练的遍数上两边都退化：2 遍模型跑 1 遍 +121.2，跑 3 遍 +21.4。只有随机深度训练对遍数稳健，但它的最优值差 13.1。
- **各遍梯度（App. D.3）【自报】**
  - 复访专家的两遍梯度余弦始终为正，并随训练下降：AdamW 从 0.633 降到 0.317，Muon 从 0.495 降到 0.143。
  - 每遍独立 router 时，余弦只有 0.023–0.062。
  - 求和梯度的 SNR 只在 22/70 个组合里超过单遍，且从不超过 5%；求和与单遍 SNR 比的中位数是 0.993。
  - 这是 T38 的直接先验，见 §5.3。
- **作者列为开放问题的**：把已训练模型改装成循环、跨 visit 共享 KV、下游任务。所以对 R4 没有新证据。

### 1.3 §4.4 QDA（arXiv 2611.23388v1，代码 dc39a02b）

| 方案陈述 | 核对 | 依据 |
|---|---|---|
| 贡献是组合 PTQ 方法、快速 KL、teacher cache、长生成验证和受限搜索，不是新的量化 primitive | 准确 | 【自报】方法库含 21 种方法；【源码】packages/qda-agent/src/qda_agent/wiki/skill/quant-methods/references/methods/*.md 逐条注明了来源论文 |
| top-128 加 tail 是聚合 KL，是下界 | 准确 | 【源码】packages/qda-kl/src/qda_kl/topk.py:1–12（log-sum 不等式，KL_k ≤ KL）、:24（TOPK=128）、:67–85（kl_topk）。【自报】尾桶平均占 0.015–0.048% 概率，9 个检查点上估计值比全词表 KL 低 0–0.4% |
| 主实验每项 8×GH200×8h；GLM 6.5h 用 16×GB300；美元主要花在 agent token | 准确 | 【自报】 |
| GGUF 清单没有已验证的 Inkling 路径 | 准确，而且更窄 | 【源码】docs/formats.md：GGUF 只有 gguf-q4km（Q4_K_M 张量类型）。FP8 W8A8 只用于稠密层或 head，"QDA writes no FP8 expert bank"。W4A4 NVFP4 只支持 Blackwell（sm100/103/120），sm_89 级的 L40S 只标了 W4A16/W3A16 |
| 代码 Apache-2.0，recipe-inputs 为 CC-BY-NC-SA | 代码部分已核 | 【源码】LICENSE 头为 Apache 2.0；数据许可按论文与 README |

方案遗漏的点：
- **论文与发布代码的搜索空间不一致。**
  - 论文 Table 10 原文："Forbidden: other bit widths or per-module bits"。
  - 发布版 judge 允许在格式菜单内按层混合：
    - 【源码】packages/qda-agent/src/qda_agent/judge/checks/__init__.py:13–18："a per-layer mix of the menu's formats is admitted"
    - 【源码】packages/qda-agent/src/qda_agent/prompt/task.md:53："Bit width may differ per module within this menu and the budget"
  - 菜单仅为 bf16 / W8A16 / W4A16（加 W3A16），按 bpw 预算约束（docs/search.md:70–87）。
- **FP8 scale 不可微调**【自报】：W4A8 时 agent 放弃了蒸馏，因为"the smallest change to an FP8 scale rescales its whole group by at least 6%"。这对 NVFP4 的 E4M3 块尺度同样成立，见 §3.3。
- **一组 KL 的排序可靠度**【自报】：44 对检查点中，KL 有 82% 与准确率同序，层误差只有 73%。重建噪声 σ 为 0.5–1.6%。

---

## 2 LoopTitan 代码：per-visit 组件和优化器的位置，以及能否用作冻结 A4/A1 上的小模块

### 2.1 实现位置【源码】

| 组件 | 位置 | 要点 |
|---|---|---|
| 物理 owner 与 visit 选择 | model.py:247–249 per_visit；:401–403 | 构造时检查每个参数只有一个 canonical owner |
| 每 visit 的 attention / norm / router | model.py:252–295（Cell）；开关在 config.py:56–58 | 由 attention_per_visit / norm_per_visit / router_per_visit 决定是建 visits 份还是 1 份 ModuleList |
| per-visit LoRA | model.py:92–128（class LoRA）；:287–294（Cell 中挂载）；rank 在 config.py:60–61 | 只加在 attention q/k/v/out 和稠密或 always-on FFN 的 w1/w3/w2 上。**router 和 routed experts 不加 LoRA**（:255–258）。B 零初始化，起点与共享权重模型完全相同（:97–99、:113–115）。有 svd_init，用 W_l − W' 的截断 SVD 初始化（:117–128） |
| 每 visit 残差尺度 | config.py:64–65 visit_residual_scales；:200–206 校验；model.py:283 | 要求 core residual_scale = 1，且 state_update = residual |
| EMA memory（LOOM） | memory.py:11–44（EMACarry、ema_update，不 detach）；:47–60（residual_gain / reinjection_gain）；model.py:340–358 MemoryCell；:588–596 前向 | config.py:135–142：EMA 不能与 LoRA、norm_per_visit、input adapter 同用，MoE 时必须 router_per_visit |
| 每 visit 的 KV | cache.py:14–81 DecodeCache；model.py:446–452 cache_slots | slot = (region, cell, visit)；共享 attention 权重仍各占一个 slot；append 用 torch.cat，只是推理参考实现，不是性能实现 |
| 截断 BPTT | config.py:283、:308–310 grad_visits；model.py:591 | 前 depth−grad_visits 遍在 no_grad 下运行 |
| 退出门 | model.py:400、:613；halting.py:1–34 | halting.py:3–4 明确说明：退出概率只给每 token 的损失加权，不缩短执行路径 |
| Muon / AdamW 分组 | optim.py:9–17（分组）；:22–31（专家 LR 倍率、输出层 LR ×s 且 WD ÷s）；:37–43（DistMuon 需要 DTensor 与 FSDP，每个 Muon 参数每步都要有梯度）；:56（引用 TorchTitan 的 build_dist_muon）；:66–70（MUON_PATTERN）；:115–165（optimizer_config） | 每个 expert 矩阵单独正交化 |
| 解绑与转换 | untie.py:1–40；convert.py:1–30 | untie：完全共享的循环与展开后的深模型函数等价，但带 per-visit 尺度、EMA、input injection、visit_final_norm 或退出分布时不成立。convert：Ouro 与 Huginn 官方权重转换器，可作为两者语义的参考实现 |

### 2.2 哪些可作为冻结 Inkling 上的小模块训练【推断】

Inkling 的形状取自 lab docs/01_model.md：hidden 2304，Q 24 头 / KV 8 头，head_dim 128，128 专家 top-8。

| 小模块（LoopTitan 对应） | 在 Inkling core 12 层 × 3 遍上的规模 | decode 额外计算 | 改装可行性 | 风险或先验 |
|---|---|---|---|---|
| 每 visit 残差或输出增益（visit_residual_scales，再细到每 expert） | 每 (层, 遍) 标量：36 个；每 (层, 专家, 遍)：4,608 个 | 约 0，可并入 router combine 权重 | 高：可以前向闭式拟合，不需要反传 | 是 T39 的粗粒度版，见 §6 第 3 项 |
| 每 visit 的 RMSNorm gain（norm_per_visit） | 约 12×3×2×2304 ≈ 0.17M | 约 0，可融进现有 norm | 高 | 需要反传；与 R5 的 controller 干预不同 |
| 每 visit 的 attention LoRA，rank 16 | 16×(5376+3328+3328+5376) = 278,528 / (层, 遍) × 36 ≈ 10.0M；BF16 20 MiB，AdamW 状态约 160 MiB | 约 20M MAC/token，占前向约 4.45G MAC 的 0.45% | 中：需要冻结主干的可微参考（§5.2） | LoopTitan 从零训练时它比 Base 差 8.14（Tab. B9）。零初始化保证关闭时逐位等价 |
| 每 visit router | 每 (层, 遍) 2304×128 ≈ 0.29M | 0 | 中低 | 改变 top-8 选择，是离散跳变；会破坏 R3 的跨遍专家局部性。D.3 显示各遍 router 独立时梯度几乎正交 |
| EMA memory | — | — | 低 | 改的是残差状态更新律，不是小插件；代码约束与 LoRA、per-visit norm 互斥；从零训练也差 21.68 |
| 学习型退出门 | 2304 / 遍 | 每遍要先读出 | 低 | 最差的配方（+43.47）。Inkling 中间遍的读出还要过 coda 和 head（R2） |
| per-visit KV | Inkling 已有 | — | — | — |
| Muon | 只对二维矩阵有意义 | — | 小适配器用 AdamW 即可 | DistMuon 依赖 FSDP/DTensor（optim.py:37–43）；单卡需另写约 50 行 Newton–Schulz（系数 3.4445, −4.775, 2.0315，5 次迭代，【自报】）。**主要价值在 M1/M2 从零训练的基线**，见 §5.4 |

**24 GiB 能否放下（冻结 A4，2K 上下文，batch 1，R=3）**【推断】

| 项目 | 估计 | 依据 |
|---|---|---|
| 冻结的量化权重 | 16.4–17.5 GiB | A1 文件 16.42 GiB（01_model.md:29）。A4 加载时把 MXFP8 转成 Q8_0，未在 lab 文档中找到实测值，需用 T18 二进制实测 |
| CUDA context | 约 0.5 GiB | 01_model.md:28 |
| 遍边界检查点（BF16） | 约 1.7 GiB | 每 token 每 visit 取 cur 加 3 行 bank，即 4×2304×2 B = 18 KiB（按方案 §9.5 的 4d）；×48 visits×2048 token。只存每两遍可减半；用 grad_visits 式截断也可减少 |
| 单 visit 重算与反传工作集 | 0.6–1 GiB | 16,384 个 token-expert 行 × (2304 + 2304 + 1152 + 2304) × 2 B ≈ 0.26 GB，再乘约 2 倍梯度 |
| 专家反向的反量化 | 每个专家临时 15.9 MB BF16 | 一个专家 3×2304×1152 参数。**整层 BF16 展开需要 1.9 GiB，应避免**；方案 §9.6 中六层 11.39 GiB 的说法同理不必要 |
| loss 的 logits | 分块后约 0.2 GiB | 不分块时 2048×201,024×4 B = 1.53 GiB（FP32），必须分块计算 CE |
| 适配器与优化器 | T37 约 57 MB；LoRA r16 约 160 MB | — |
| 合计 | **约 20–21 GiB** | 低于方案 §11.5 的 22 GiB 门。4K 上下文时检查点翻倍，会越过门 |

**时间**【推断】
- 按 Inkling 每 token 前向约 9.4 GFLOP 计：48 visits 每个约 83M MAC，加 head 463M MAC，加注意力分数。
- 冻结主干训练每 token 约 3 倍前向（前向、重算、只对输入求梯度），2K token 一步约 58 TFLOP。
- 4090 BF16（FP32 累加）峰值约 165 TFLOPS；按有效 30–60 TFLOPS 加开销，每步约 1.5–4 s。
- 因此 2M token 约 0.5–1 小时，50M token 约 10–30 小时。
- 前提是存在 NVFP4 / Q8_0 的转置或反量化反向 GEMM；这类 kernel 现在没有，见 §5.2。

---

## 3 QDA 数值闭环对 Astral GGUF 资产的适用性

### 3.1 可以直接搬的（工具与方法，与格式无关）

1. **top-128 加尾桶的 teacher cache**
   - 【源码】topk.py:61–85（anchor_topk、kl_topk）、:88–99（kl_exact 参考）；refcache.py:1–25（按原模型指纹、prompt sha、读取设置、引擎版本作缓存键）。
   - Inkling 词表 201,024：每位置全量 FP32 logits 为 785 KiB；top-128 存 FP32 值加 int32 id 加尾项，约 1 KiB，约 780 倍压缩。
   - 10 万个位置约 98 MiB，而全量约 75 GiB。【推断】
   - 这对 R1、R4、R8、T35、T39 的开发集 KL 都直接有用；注意 lab 宿主盘也有限。
2. **gencheck**
   - 【源码】gencheck.py:1、:292–293：统计 cut（finish_reason == length）和 loops（is_loop）。
   - is_loop 定义在 :590–622：检查窗口 2048、最短 256 token、最大周期 512、至少重复 4 次，允许少量 token 不匹配。
   - 默认每个领域 4 个 prompt，答案上限 8192（:35–36、:59–62）。
   - R4 已经有"2K token 长生成 n-gram 复读率"，建议直接沿用 is_loop 的定义，便于对照。
3. **平局带 σ**
   - 【源码】prompt/__init__.py:166–223（kl_noise：相对差在该值内即判平局）。【自报】σ 取自不同校准子集重建的 ln KL 标准差，为 0.47–1.6%。
   - lab 的 T19 已有噪声对照；可以补一条：同一候选的不同构建或种子之间的 σ。
4. **两条现象检查**
   - "存储网格不等于服务网格"：比较加载器转换后的权重与生产者以为的权重，逐组比值应全为 1。【源码】wiki/.../phenomena/served-grid-differs-from-stored.md。
   - "路由翻转的地板"：先拿源模型对比不同 kernel 或 dtype 下的自己，测出翻转率，再看候选超出多少。【源码】wiki/.../phenomena/routing-and-mixer-sensitivity.md。
   - 这两条与 R3、R8 和 G2 的数值门直接对应。

### 3.2 方法搬得动、但对 A1 收益有限的（量化配方）

- **原因：A1 的专家本身就是官方原生格式。** 官方专家为 NVFP4 或 MXFP8；A1 有 40 个 NVFP4 张量，另有 8 个专家矩阵由 MXFP8 转成 Q8_0（01_model.md:16、:87）。没有 BF16 master 可以"恢复"。QDA 的 GPTQ、AWQ、scale-KD 都以 BF16 原模型为 teacher，**在 A1 上没有 teacher**。【推断】
- **唯一明确的 teacher 是"同一权重、更高精度的算术"**，也就是方案 13 的 T39-A。这与 QDA 的 scale-only distillation 结构相同：冻结码字，只调 scale。【源码】methods/lptq-e2e-scale-tune.md。区别在于 T39 按遍区分，而且不做反传。
- **MoE 专家的 Hessian 要按路由权重加权**（MoEQuant，【源码】methods/cond-moe-expert-hessian.md）。只有在以后做更低位资产时才用得上，例如 T31 的 IQ 或 K 系列，或自己把 NVFP4 降到 3 bit；那时 teacher 是 A1 本身。

### 3.3 按层或按遍选精度、尺度校准：能否覆盖"Q8_0 → FP8"和"NVFP4 专家重标定"

- **QDA 的搜索空间不覆盖格式转换。** 论文版固定格式和位宽；代码版只允许 bf16 / W8A16 / W4A16 / W3A16 菜单内按层混合，没有 FP8 专家库，也没有 Q8_0 或 NVFP4 的 GGUF 菜单。所以两个问题都只能借它的评估器，不能借它的搜索器。【源码】见 §1.3。
- **Q8_0 → FP8 E4M3（K7）【推断】**
  - 精度：
    - Q8_0 是 int8 加每 32 个一组的 FP16 scale，量化步长为组 absmax/127。按高斯权重估算 SQNR 约 46 dB。
    - E4M3 有 3 位尾数，二进制段内相邻值相对间距 6.7–12.5%，相对 RMS 误差约 2.5–3.6%，SQNR 约 29–32 dB。
    - 即每个权重的 RMS 误差大约是 Q8_0 的 5–7 倍。A1 的 Q8_0 张量主要是 attention、LM head 和 embedding，恰好是敏感部位。
  - 带宽：每权重从 8.5 bit 降到约 8 bit，省约 6%。T16 之后 Q8_0 投影与 head 约占 decode GPU 时间的 39%（01_model.md:93），端到端上限约 2.3%。
  - 算力：
    - 4090 的 FP8 mma（FP32 累加）峰值 330.3 TFLOPS，是 BF16 / FP16（FP32 累加，165 TFLOPS）的 2 倍。来源是 Ada 白皮书 v2.02，本次通过检索核到。
    - INT8 mma 峰值我记得是 660.6 TOPS，**本次没有检索到原文，需要核对**。
    - 若该值成立：对 prefill 等算力受限的部分，Q8_0 的 int8 码直接走 INT8 mma（m16n8k32，每个 k 块乘一次组 scale，与 llama.cpp MMQ 同思路），权重无损，峰值是 FP8 路径的 2 倍。激活量化成 int8 是有损的，但比 E4M3 细。
  - 结论：K7 应降级，并改写成"Q8_0 → INT8 mma"。前提是先核对 Astral 的 prefill Q8 MMA 现在用的是 FP16 还是 INT8 指令（T22 记录的 launch_mma 读 FP16 平面，提示现在是 FP16 MMA）。
- **NVFP4 专家重标定**
  - 有两层尺度：
    - 每张量的 F32 \`.scale[128]\`，每专家一个，连续可调。40 个张量 × 128 = 5,120 个标量。
    - E4M3 块尺度，每 16 个元素一个，离散，相邻可取值的相对间距 6.7–12.5%。【推断】这与 QDA 自报"≥6%"一致。
  - 前者可以做 scale-only 校准，零运行成本。但 A1 上缺 teacher（§3.2），只能对 F32 算术 teacher 拟合；这就是 T39-A 的"common"项，在每专家粒度上。
  - 后者只能做离散网格搜索（QDA 的 fp4hmse 在 E4M3 网格上带 Hessian 搜索；【源码】docs/formats.md:63），不能走梯度。
  - 两者都只在以后有低位或新资产时才有大收益。
- **按遍选精度**
  - 权重精度按遍不同，需要第二份权重或运行时转换（R8 已写）。
  - 只改激活或算术精度时，T=1 decode 主要受带宽限制，算术精度对速度影响很小，所以价值低。【推断】

---

## 4 方案 13 漏掉的有用点

| # | 来源 | 内容 | 对 Astral@4090 的意义 | 对应条目 |
|---|---|---|---|---|
| a | LT D.2【自报】 | 第一遍后读出多付 98–274 mBPB；20% 的 token 占第二遍收益的 64–95% | 逐 token 早停的上界存在，但集中在少数 token。LT 的学习型退出门最差，而且不缩短执行（halting.py:3–4）。支持 R6 的"先做离线 oracle 上界"，不支持直接训练退出门 | R6、T35 |
| b | LT D.2【自报】 | 固定遍数的模型在未训练遍数上两边都退化；随机深度训练稳健，但最优值差 13.1 | A1（固定 3 遍）不宜做"少遍"档位；降档要用 A4（varloop 训练过 1–5 遍）。证实 T33 应以 A4 为主体 | T33、R1 |
| c | LT D.3【自报】 | 各遍梯度余弦为正且逐渐变小，Muon 下降到 0.14；求和 SNR 中位比 0.993 | T38 在训练后期能"去相关"的空间小；Muon 的 Newton–Schulz 正交化本身也会改写更新方向 | T38 |
| d | LT Tab. B9【自报】 | per-visit LoRA 与 EMA memory 在统一协议下都比 Base 差 | T37 及同类"加状态"机制先验偏负，对照必须齐全 | T37 |
| e | LT Fig. B1【自报】 | 0.625B token 时循环配方无收益 | M1/M2 的 2M token 筛选测不出循环相关效应；要么换成能早出信号的合成算法任务，要么提高 token 数 | §11.1 |
| f | LT 代码【源码】 | LoRA 的 B 零初始化（model.py:97–99）；svd_init（:117–128）；grad_visits 截断 BPTT（model.py:591） | 零初始化直接满足 Astral"关闭时逐位一致"的合同；grad_visits 可在冻结 A4 训练时用来压显存 | T37、T40、小适配器 |
| g | QDA【源码】 | 发布版 judge 允许按层混合位宽（与论文不同） | 如果以后做低位资产对照（T31、AP），可以用其 bpw 预算记账口径 | T31 |
| h | QDA【自报】+【源码】 | 长生成的截断和复读与短上下文 KL 可能不一致（wiki 中的 long-generation-drift.md）；GLM 的例子是 12/191 截断 vs 原模型 3 | 所有有损候选（T35、T39、K7、R4 臂 B/C）都要加 gencheck，不能只看 teacher-forced KL | 05 验证口径 |
| i | SR【自报】 | 前向标量编辑（dt_bias +0.5）就让 held-out 提高 6.6 点、截断率下降 7.5 点；协议含编辑者看不到的验证集、撤回、置换检验 | 在 Inkling 上对应的是 controller gain / forget、输出门 bias、router bias、相对位置 bias τ 这些标量旋钮。**截断率下降意味着每个正确任务用的 token 更少**，可以算吞吐杠杆（R1 的"正确任务 / 秒"） | R5、R10、R1 |
| j | LT 开放问题【自报】 | 跨 visit 共享 KV 未研究 | 对 R4 没有新证据，维持现计划 | R4 |
| k | 合成【推断】 | 用小适配器恢复少遍质量：用 R=3 当 teacher，把每遍增益、norm 或 attention LoRA 蒸馏到 R=2 | A4 R=2 时 visits 从 48 降到 36，decode 上限约快 1.25–1.3 倍；有损。先测 A4 原生 R=2 的 KL 与任务差距，差距大时才训适配器 | T33、T35 |

---

## 5 T37–T40 的独立可行性与优先级

### 5.1 T39（按遍补偿 expert-down 输出）：第一

- **可行性高。** 只需前向，闭式 ridge 拟合，现有 A1 就能跑。F32 down bank 一层 1.27 GiB，在 2K 下分时可以放下（方案 §8.2）。
- **预期收益小。** G2 已经在噪声地板附近通过（T12、T19），NVFP4 GEMV 的算术误差可能低于重复测量噪声；方案自带的 NO_BENEFIT 门是合理的。【推断】
- **建议加一个更便宜的前置臂 T39-0**：每 (层, 专家, 遍) 一个标量（4,608 参数），直接乘进 router combine 权重 w_e，几乎零 kernel 改动。
  - 先看这一粒度能否把 KL 降到噪声之上，再上 group64（165,888 参数）。
  - 两臂共用一次采样与 KL 缓存。
- **验证**：top-128 KL 对 F32 算术 teacher 和对原 A1，各 3 次重复；gencheck 看 cut 和 loops。

### 5.2 先建"冻结量化 A4 的可微参考"：T37、T40 和所有小适配器共用

- 方案 §11.5 已把它列为 T37/T40 全尺寸的前置。我的显存账（§2.2）表明，在 2K、BF16 检查点、分块 CE、每专家临时反量化的条件下，峰值约 20–21 GiB，**可行**。
  - 方案 §9.6 设想"coda 全展开 BF16，11.39 GiB"，这不必要。coda 权重已经在推理常驻的约 3.2 GiB NVFP4 之内，反向时只需临时反量化单个专家。
- 关键缺口是转置或反量化方向的反向 GEMM，需要新 kernel：
  - NVFP4 以 16 个元素为块沿输入维分组，转置后要按输出维读尺度。
  - sm_89 上用 mma.sync BF16/FP16 m16n8k16 加 cp.async，把块反量化到共享内存。没有 FP4 tensor core，所以无法以 FP4 直接计算。
- 时间估计：2M token 约 0.5–1 h，50M token 约 10–30 h（§2.2，推断）。

### 5.3 T38（各遍梯度几何）：最低

- 先验偏负（§4 c）：
  - 后期各遍梯度已接近正交，Muon 下约 0.14。
  - 求和不降低也不提高 SNR。
  - Muon 的输出是动量的极分解因子，T38 的范数匹配在 Muon 下没有作用。T38 白化后的方向在 NS 之后还剩多少差异，需要实测。【推断】
- 在冻结 A4 上，T38 只作用于新增参数（例如 T37 的 P/B 也是三遍共享的），规模很小。
- **建议**：只在 M1 上做，基线必须是 Muon（每专家单独正交化，同 optim.py:9–17），并对照 AdamW。M1 一次运行只要几分钟，便宜；没有信号就停，不上全尺寸。

### 5.4 M1/M2 的 GPU 小时（2M token）与预算建议【推断】

| | M1（D256，8 层 2/4/2，E32 top-2，FFN128，Q6/KV2/head64，字节词表 260） | M2（D256，24 层 6/12/6，同上，Inkling 词表 201,024） |
|---|---|---|
| 参数量 | 每层：attention 262K + 专家 3.15M + router 8K ≈ 3.42M；8 层约 27.4M | 24 层约 82M；embedding 51.5M 加 head 51.5M（不绑定时），合计约 185M |
| visits | 2 + 4×3 + 2 = 16 | 6 + 12×3 + 6 = 48 |
| 每 token 训练 FLOP | 约 45M（线性层）+ 约 24M（注意力分数，ctx 1024，8 个 global visit）≈ 70 MFLOP | 线性层约 134M + head 约 309M + 注意力约 43M ≈ 490 MFLOP |
| 2M token 的理论计算 | 140 TFLOP | 约 1 PFLOP |
| 2M token 的实际估计（有效 10–40 TFLOPS，计入开销） | **约 1–5 分钟，0.02–0.1 GPU·h** | **约 2–5 分钟，0.05–0.1 GPU·h** |
| 50M token | 约 0.1–0.5 GPU·h | 约 0.4–1.5 GPU·h |
| 显存要点 | 很小 | 词表 20 万：8K token 的 FP32 logits 约 6.4 GB，**必须分块计算 CE** |

- 换算基准：LoopTitan MoE-12 在 H200 上约 3.9 万 token/s，按 3.14e9 FLOP/token 计约 12% MFU（【自报】时间，【推断】MFU）。手写的 MoE 参考（Python 层面 dispatch）可能比 FLOP 估算慢 5–20 倍；方案"先测 100 步再预测"的做法正确。
- **结论**：每机制 4 GPU·h 的停止预算，在 M1 上约可训练 1–3B token，在 M2 上约 0.3–1B token。2M token 只用掉预算的零头，而且在 LoopTitan 的证据下多半测不出循环效应。
- **建议**：
  - 筛选用 100M token 起步，每臂 3 个 seed，M1 共约 1–3 GPU·h。
  - 或者改用合成算法任务，在少量 token 内就出现分化：N-hop、Dlouapre 式图任务，R1 已有生成器。
  - 每个机制都带 LoopTitan 的三类对照：非复访、同参数更深、同 KV / FLOPs。

### 5.5 T37（专家消息账本）

- **可行性中。** 全尺寸需要 §5.2 的参考。decode 额外约 31.85M MAC/token，约占 0.7%；账本只存在于同一 token 的三遍之间，不跨 token 持久化，所以显存小。
- **先验偏负**（§4 d）。M1 上用 Muon 并带"同容量匿名状态 / per-visit LoRA / 每遍增益"对照，先证伪，成本几分钟到 1 GPU·h。只有 M1/M2 显示超过对照，才投入全尺寸 10–30 h。
- 能力研究，不是速度项。

### 5.6 T40（只读 prompt 加可改写潜在工作区）

- 新颖性最高，工程最重：需要 coda 反传、特征缓存 I/O、跨答案状态。
- 显存按 §5.2 的方式可放下，方案的 11.39 GiB 不需要。只反传 coda 的减负成立（方案 §9.5）。
- 收益是能力，不是吞吐；先在 tiny 或 M1 上证明拓扑。
- 排在 T37 之后或与之并行（两者共用可微参考），列为第三。

**综合排序**：
1. E0 评估闭环（§6 第 1 项）
2. T39-0 / T39-A
3. M1 上的 Muon 基线加对照，并在其中筛 T38 与 T37-tiny
4. 冻结 A4 可微参考
5. T37 全尺寸与少遍适配器（§4 k）
6. T40
7. T38 全尺寸（视 M1 结果，多半不做）

---

## 6 可借鉴项排序（对 Astral@4090 的价值）

| 排名 | 做什么 | 有损 / 无损 | sm_89 可行性与所需指令 | 与 K / R / T 的重叠 | 收益量级与依据 | 怎么验证 |
|---|---|---|---|---|---|---|
| 1 | E0：top-128 加尾桶 teacher cache，gencheck（cut + is_loop），平局带 σ | 对模型无损；KL 估计是下界，【自报】偏低 0–0.4% | 纯工具；不涉及 kernel | T19/T20 计算器、R1、R4 的长生成指标、R8 | 不提速。存储约 780 倍压缩（每位置 785 KiB → 约 1 KiB，【推断】）；【自报】比完整评估便宜 350–990 倍，同序率 82% vs 73%。是所有有损候选的前提 | 16 个 prompt 上把 kl_topk 与 T19 全词表 KL 并列，要求 ≤ 且差 <0.5% |
| 2 | A4 按请求降到 R=2；必要时加零初始化的每遍增益、norm 或 LoRA 小适配器，以 R=3 为 teacher 蒸馏 | 有损 | 适配器是标量折叠或小 GEMV；BF16 mma.sync 即可 | T33、T35、R1、R6 | decode 上限约快 1.25–1.3 倍（visits 48 → 36，【推断】）；LT D.2 说明少遍的损失不小，且固定遍数模型不能降档 | top-128 KL vs R=3、任务正确率、gencheck、T14 协议下的 tok/s |
| 3 | T39-0：每 (层, 专家, 遍) 标量乘进 combine 权重；再做 group64 的 T39-A | 有损（目标是消除算术误差） | 无新指令；group64 版需要在 epilogue 加 FMA | R8、T39 | 不提速；KL 可能只在噪声附近（G2 已过）。价值在于几小时内给出明确的可证伪结论 | 方案 §8 流程，加 E0 |
| 4 | SR 式前向标量编辑：controller gain / forget、输出门 bias、router bias、τ；配隐藏验证集、撤回和置换检验 | 有损（改函数） | 零运行成本 | R5、R10、R1 | 【自报】Qwen 27B 上 dt_bias 编辑 +6.6 点、截断率 −7.5 点；迁移到 Inkling 的幅度未知。截断减少即每个正确任务用的 token 更少 | 配对 held-out、p 值、gencheck 的截断率；不显著就撤回 |
| 5 | M1/M2 用 Muon 作基线，加 LT 三类对照；token 数提到 ≥100M | — | BF16 训练 | T37、T38、T40 的科学部分，R13 | 防止假阳性：【自报】仅换 Muon 就有 23.6 mBPB，是循环配方收益的 3.7 倍 | 3 个 seed；匹配 token / FLOP / GPU·h 分别报告 |
| 6 | K7 改写为"Q8_0 → INT8 mma"，取代"Q8_0 → FP8" | 权重无损；激活 int8 有损 | mma.sync m16n8k32 s8；INT8 峰值待核（我记得 660.6 TOPS）| K7、K2、K6 | 只对 prefill 和较长 verify 有意义；decode 受带宽限制，FP8 最多约 2.3%（【推断】） | 先核对 Astral prefill 的 MMA dtype，再按 T16 流程 profile |
| 7 | NVFP4 per-expert F32 \`.scale\` 校准（5,120 个标量）；E4M3 块尺度只做网格搜索 | 有损函数，格式和速度无损 | 零成本，折叠进现有 scale | T39、T31 | A1 上没有更高精度 teacher，收益小；以后做低位资产时价值上升 | E0 |

---

## 7 未核实项与风险

- 方案 §4.3（AP）与 §4.5（Dlouapre）不在本报告范围，我未核对。
- 4090 的 INT8 tensor 峰值未检索到原文；FP8（FP32 累加）330.3 TFLOPS 已核。
- A4 在 Astral 中的常驻显存在 lab 文档中没有找到实测；§2.2 的 16.4–17.5 GiB 是推断。
- Inkling 的 gate/up 形状按 down 的 GGML[1152,2304,128] 推断为各 2304→1152；是否有 shared 或 always-on 专家，本次没有核对，可能让 FLOP 账偏小。
- M1/M2 的 GPU 时间是 FLOP 估算；手写 MoE 参考实际可能慢 5–20 倍。
- 冻结 A4 训练的显存账没有算进 graph、allocator 碎片和 conv / bank 的反传细节；方案"2K 实测峰值"的门仍然必须执行。
- LoopTitan 的所有结论都来自从零训练（0.2B active 级），不能直接外推到对 26B 已训练模型的改装；作者本人也把"改装"列为开放问题。

## 附：本次落盘与清理

- 论文：/root/github/inkling-research/papers/，约 10 MB。
- 仓库：/root/github/inkling-research/repos/LoopTitan（22 MB）、/root/github/inkling-research/repos/qda（17 MB）。均为浅克隆，未安装依赖。
- 临时 HTML 和文本抽取放在 scratchpad 中，写完本报告后已删除。
