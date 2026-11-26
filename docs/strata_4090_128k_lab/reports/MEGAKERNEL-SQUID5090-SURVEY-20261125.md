# 调研（第二版，深读）：megakernel-zoo、squid5090 与相关论文/项目对 Strata 4090 的借鉴和整合路线（2026-11-25）

> 本版替换同日的第一版。第一版只读了两个仓库的文档和 megakernel 长文，论文没有读原文；它的错误和遗漏列在 §0.3。
>
> 全程只读：没有在 4090 上运行任何东西（OCR 占用期间测试暂停），没有改引擎或生产配置。

标注：
- **【事实】**：本机日志、实测或 Strata 源码里直接可见。
- **【来源】**：外部项目或论文自己报告的数字，本机没有复现。
- **【推断】**：由事实或来源推算，没有实测。
- **【假设】**：有待验证的解释。

## 0. 结论

### 0.1 一句话

最便宜、也可能最大的新收益不在 megakernel，而在两组"已经写好、本机从未测过"的东西：
- 采样投机的三种 opt-in 模式（S 组）；
- 一批源码声明逐位一致的图 / 融合开关（K 组）。

megakernel 方向的价值主要在测量方法和关键路径视角。动代码之前，先用 Strata 自带的测量开关把每层关键路径拆清楚（M 组）。

### 0.2 主要结论

1. **采样投机（S 组，零代码，分布无损）。**
   - 【事实】Pi 的请求都是采样：thinking 档 temperature 1.0 / top_p 0.95 / top_k 20，off 档 0.7 / 0.8 / 20（B2 采样探针 PREREG）。Strata 在采样请求下默认用 MTP 头的 argmax 作草稿，再与目标的采样结果做 exact-match（`coupled_draft.hpp` 文件头）。
   - 【事实】v0.2.17 已带三种 opt-in，默认全关。实验室从未测过：DF01 系列明确排除了它们，NEXT_ACTIONS 也没有记录。
     - `STRATA_SPEC_COUPLED=1`：草稿用目标的采样链和同一个 uniform 抽取；验证仍是 exact-match，目标的采样过程不变。
     - `STRATA_SPEC_GUMBEL=1`：两侧都改用 Gumbel-max 抽样。分布相同，但同一 seed 下文本会变。
     - `STRATA_SPEC_PROB=1`：标准的投机拒绝采样（Leviathan / Chen）。生产有 `pcie_frac 0.34` 和自适应换入，在这种配置下默认的 pick 门会退回旧规则，而旧规则在门失败时分布有偏。要再加 `STRATA_SPEC_PROB_GATE=top` 才是精确的（v0.2.17 `generate.cpp:3471-3500`、Strata `docs/DETAILS.md:636-646`）。
   - 【来源】fngine（同一模型，RTX 5090）第 7 轮把采样下的草稿从"argmax 当固定 token 验"改成"按 q 抽、按 min(1, p/q) 验"。同一采样预设（1.0 / 0.95 / 20）下，每轮 token 从 1.89 涨到 2.54，decode 两轮分别 +24.7% / +29.6%（各 9 次配对）。
   - 【来源，反向】Strata 自己在 RTX 3060 上测过：COUPLED / GUMBEL 把草稿接受率从 62.1% 提到 66.9% / 68.0%，但 tok/s 在波动范围内；PROB 在温度 0.3 / 0.7 / 1.0 下都略慢（DETAILS.md:1643-1644）。
   - 【推断】我们的空间比 fngine 小。`--spec-min-p 0.5` 只在草稿头有把握时才出草稿，所以 ≥32K 采样回放每窗口已有 2.53 个 token（接受率 0.678），greedy 题集是 2.78（A0 + EXACT6 时期）。
     - 按"每窗口 token = 1 + 接受率 × 草稿数"估算：接受率相对提高 7.7%（3060 的幅度）时，每窗口 token +4.3%；追平 greedy 时 +9.9%。
     - 窗口宽度不变时，窗口耗时基本不变。扣掉草稿侧采样的开销，预期 decode +2～9%。
     - PROB 会把 CPU 专家的分组算术换成逐 token 算术，CPU 时间可能变长，这可能就是 3060 上 PROB 变慢的原因【假设】。
   - 这三种模式都不改变目标分布：COUPLED 的目标采样过程不变；PROB+top 有精确性单测（`spec_admission_test`、`spec_proposal_parity` 等）。所以只需要正确性检查和 loop 迹象检查，不需要质量非劣门。采用意味着改生产 env，需要用户确认。

2. **未测过的无损开关（K 组，零代码）。**
   - 【事实】v0.2.17 的 `verify.cpp` / `verify_kernels.cu` 里有 73 个 `STRATA_*` 开关。先去掉已测过或已默认开启的：
     - EXACT6 已在生产，其中包括 `SIDE_MIXER=2`；
     - `MMVQ_IL` 默认开，IL0 / IL89 已测，未采用；
     - `COMMIT_BATCH`、`ONE_TOKEN_COMMIT` 在 CUDA 上默认开。

     再去掉被禁用或不适用的，剩下 7 个：源码注释写明"same bytes / 逐位相同"、本机没测过——`L2_PF`、`FUSE_WAIT=2`、`QIL`、`QFUSE`、`VERIFY_DEVICE_PLAN`、`GRAPH_PRIO`、`SELECT_LONG`（只看 ≥64K）。
   - `STRATA_L2_PF` 正是第一版 E3 打算写的东西：CPU 专家等待期间，在低优先级侧流上把下一层的 dense 权重预取进 L2。
     - 【来源】fngine 用的是同一手法：宽度 1 时每步 9.47→8.92 ms；把分叉点挪到共享专家之后，宽度 3 时 12.48→11.95 ms。
     - 【来源】mkzoo 的反例：H100 上 `prefetch.global.L2` 根本不进 L2；大块权重预取在所有引擎上都亏，只有小块、临近使用的预取有收益。
   - 【推断】单项多在 0～2%，`L2_PF` 和 `VERIFY_DEVICE_PLAN` 可能更大。NEXT_ACTIONS 里"引擎参数和采样都已测完"的说法需要修正。

3. **先测量（M 组）。**
   - 用 Strata 自带的开关：
     - `STRATA_VERIFY_PROFILE=1`：每层 34 个 GPU 打点；
     - `STRATA_DUMMY_NODES=k`：每层插 k 个空 kernel 节点，测真实窗口图里一个节点的成本；
     - `STRATA_COMMIT_TIMING=1`；
     - `STRATA_SPEC_DEPTH=1`：按草稿深度统计接受率。
   - 另加：
     - 一次带拷贝引擎行的 nsys；
     - 两个微基准：读带宽，以及 DDR 满载时 mapped flag 的往返时间；
     - 一个最小的延迟注入补丁：给某段加 10 µs，看窗口时间的变化斜率，判断这段在不在关键路径上。
   - 这些结果决定 C 组和 X 组做不做。
   - 【推断】按各来源的节点成本（H100 1.3 µs、B200 0.8 µs、5090 在用 PDL 之前约 1.9 µs、Strata 自测 gfx1201 约 2.4 µs）乘以每窗口 2,145 个 kernel，边界开销在 1.7～5 ms/窗口之间。范围太宽，必须在本机实测。

4. **无损代码（C 组）收敛到三处**，都以 M 组的结果为门：
   - doorbell 之前的串行链，以及超连接（hyper-connection，`gr_*`）kernel 的融合。后者在追踪下约 2.5 ms/窗口。
   - 按 T 特化。
   - 命中专家 kernel 的流式双缓冲。只有延迟注入证明 GPU 专家在关键路径上时才做。
     - 【来源】fngine 在 hot_down 末尾加 10 µs：高命中率时 decode −7～9%，命中率 79% 时没有影响。
     - 我们的命中率是 92～96%，介于两者之间。

5. **有损方向（Q 组）。**
   - 文献给 ECAP / DEFER 提供了直接的设计校准和风险点（§4.5）。
   - 质量门升级为五项：token forcing、KL + flips、自身噪声阈值、固定驻留、≥32K 长生成。
   - 文献里最大的有损杠杆是按驻留偏置路由（PSR / Cache-Prior）。它对应 `STRATA_ROUTE_RESIDENT`，按约定禁用，本文不提。

6. **降级或不做。**
   - 预测式预取（第一版 E4）：四个独立系统实测无益。
   - 整窗 megakernel（第一版 E5，改为条件立项的 X 组）：来源在 MoE 上实测只有 1.0～1.18×，而 sm_89 没有 PDL / TMA / cluster。
   - W12 / DFloat11、认证 head、verify tree、更大的换入预算、CPU cache 预热、单 kernel GDN 层。

7. **环境因素：GPU 时间片。**
   - 【来源】fngine 发现桌面合成器每秒约 300 次提交，让 CUDA 每步慢 28～30%。
   - 【推断】OCR 共置进程忙时同样会抢 4090 的时间片，可能是真实流量下 decode 波动最大的单一来源。
   - 可以先用现有的 prodlog 和监控数据做只读相关性分析，不占 GPU。

### 0.3 相对第一版的更正

| 第一版说法 | 更正 | 依据 |
|---|---|---|
| "没有一个项目是 Qwen3.8-Flash-Next + CPU offload" | satellitedown/fngine 就是：同一模型，RTX 5090 + AVX-512 CPU 专家层 + MTP，有逐轮实测记录。atomic-engine 也在同一个 GSQ-RCO IQ3_XXS 上做专家流式加载 | fngine `engineering-notes.md` |
| DFloat11 是"无损 12-bit" | DFloat11 只对 BF16 的指数位做 Huffman 编码，平均约 11 bit。定长 12-bit 的是 SpecPilot 的 W12 | arXiv 2504.11651 §2；2611.02501 §4.1 |
| R'x 是"跨层路由预测" | R'x 是同一层、提前一个 sublayer 的预测（层输入 × 本层 router）。它在 4 个 GPU build 上全部失败，因为预取流量挤占了关键路径 | mkzoo runs |
| E3（等待期间预取 L2）需要写代码 | v0.2.17 已有 `STRATA_L2_PF`（默认关），只需要测 | `verify.cpp:1665-1720` |
| E2 的融合候选包括 `copy_*_from_mapped` | 这些小 kernel 恰好是 fngine 推荐的做法：用 kernel 读 mapped 内存，替代会排在 DMA 后面的 memcpy 节点，不应合并掉。"把 wait 融进后续拷贝"已有 `FUSE_WAIT` 开关 | fngine 第 4 轮；`verify.cpp:444-503` |
| 每个 flag 由多少 CTA 轮询未知 | 单独的 wait kernel 都是 `<<<1,1>>>`，已满足"单一轮询者"。只有 `FUSE_WAIT=1` 会让每个行块各自轮询，在 Turing 上 −1.5%，不要开 | `verify_kernels.cu:1639`；`verify.cpp:491-500` |
| 生产没有设置图相关开关（第一版正文未写，但调研时的判断有误） | 生产 env 含 EXACT6，其中有 `SIDE_MIXER=2` | P0-T6、V0216-CONFIG-MIGRATION |
| E4 预测预取"有新证据，可做" | 负证据很强，降为离线研究，先验很低（§4.7） | fngine、atomic-engine、HOBBIT、mkzoo |
| 论文只按转述记录 | 本版读了原文（§1） | — |

### 0.4 对现有计划的影响

- NEXT_ACTIONS 处于维护模式，结论是"引擎参数和采样都已测完"。本调研找到两组未测项（S、K），都是零代码，而且无损或分布无损。建议在下一次 OCR 空闲、并获准停生产时一次筛查完（§4.8）。
- B2 approx 第二阶段，以及 ECAP / DEFER 的构建和门，继续暂停。恢复时先做 M 组，因为 M 组同时给出 ECAP / DEFER 可回收时间的上限（spin）。
- 门槛：对逐位一致的臂，改用 SpecPilot 的采用规则，从 A/A 噪声推出门槛，不再固定用 4%。已测 ABBA 噪声 0.6%，门槛 = 1% + 2 × 0.6% = 2.2%。这样 1～3% 量级的无损项才能被看见。

## 1. 实际读过的材料

| 类别 | 内容 | 深度 |
|---|---|---|
| 仓库 | megakernel-zoo `95e315c8`：README、`SKILL.md`、`playbook.md` 全文，各 run 的 notes / journal / findings（子代理逐 run 摘录） | 全读 |
| 仓库 | squid5090 `50b5bf40`：README、`LEARNINGS.md`、`PLAN.md`、`ledger.jsonl`，以及 `kernels_gemv.cu` 的 MoE 部分 | 文档全读，代码只读 MoE 部分 |
| 文章 | A Megakernel per Model（mkzoo 作者长文，含数据表） | 全读 |
| megakernel 谱系 | Hazy *Look Ma, No Bubbles!* 及三篇后续（70B、TK2、Retire the Abstractions）、ThunderMLA；MPK arXiv 2512.22219v2 全文（含图中数值）；Cohere North megakernel；Thinking Machines *Defeating Nondeterminism*；Hazy / MPK 仓库里的等待与信号代码 | 全读 |
| 同模型 / 近似引擎 | fngine `docs/engineering-notes.md` 全文（7 轮性能记录）；ingine 的验证器；atomic-engine 的 expert source、优化审计、预测预取记录 | fngine 全读；其余读相关部分 |
| 评测与质量 | SpecPilot 2611.02501；*Accuracy is Not All You Need* 2407.09141；KernelBench 2502.10517；KernelBench-Verified 2607.16241；robust-kbench 2509.14279；KernelGuard（摘要 + 规则代码）；DFloat11 2504.11651；LoopCD 2610.02185；Mooncake | 全读；KernelGuard 与 Mooncake 浅读 |
| MoE CPU/GPU offload | Fiddler、KTransformers（SOSP'25）、MoE-Lightning、HybriMoE、Ostinato 2611.11533、IsoMoE 2611.27604、Apto、Apex、RapidMoE、Eliseev & Mazur、Pre-gated MoE、ProMoE、AdapMoE、HOBBIT、DAOP、fMoE、MoE-Infinity、ExpertFlow、Cascade、EcoSpec、AcceptMoE 2608.02989、PSR 2610.34721、SP-MoE、Specter、MoE-SpAc、MoE-CORE | 核心论文读全文；BuddyMoE、SPICE、SliceMoE、Limits of Speculation、Expert Coactivation 只读摘要和数字 |
| Strata 源码 | v0.2.17 的 `verify.cpp`、`verify_kernels.cu`、`verify.hpp`、`generate.cpp`（scratchpad 副本）；本地 `/root/github/Strata`（HEAD `c6f6427d`，含 v0.2.17～v0.2.20 tag）的 `spec_prob.hpp`、`coupled_draft.hpp`、`docs/DETAILS.md`、`docs/SETTINGS.md` | 读相关部分 |

论文原文和摘录在 scratchpad 的 `agents/{megakernel,refs,moe-offload-lit}` 下。那是临时目录，可能被清理。

## 2. 我们的位置

### 2.1 窗口构成

【事实】B2 approx C0a，2026-11-23，固定历史回放中 ≥32K 的请求，Pi 采样。

| 项 | ms/窗口 | 每层 |
|---|---|---|
| 合计 | 18.22 | — |
| GPU-reach wait（host 等 GPU 到达下一层） | 9.29 | 约 194 µs |
| CPU 专家（1.56 条目/层） | 5.61 | 约 117 µs |
| draft | 1.57 | — |
| adapt wait + join | 0.29 | — |
| 其余（plan、stage、commit 等） | 约 1.45 | — |
| T / 每窗口 token / 接受率 / decode | 3.25 / 2.53 / 0.678 / 138.7 tok/s | — |

其他事实：
- decode 命中率稳定期 92～96%（10_NON_PR）。
- 每个 CPU miss 约 76 µs，用到 36 GB/s 上限的约 55%；其中同步开销约 2.5 µs，gate/up 受计算限制，还和 PCIe 争用内存（NP-3 trace）。
- 2 条 DIMM 只占了 6 个内存通道中的 2 个，读带宽上限 36 GB/s（P0-T7）。
- PCIe 3.0 实测 12.3 GB/s，`pcie_frac 0.34`。
- 显存频率 decode 时 10251 MHz，最大 10501 MHz。

### 2.2 GPU 时间线

【事实】v0.2.16，100K 上下文，nsys 节点级追踪，265 个窗口。追踪本身让耗时增加约 35%，只看比例。

| 每窗口 | 值 |
|---|---|
| kernel 数 | 2,145（其中 693 个平均不到 3 µs；记账类 533 个，合计 1.85 ms） |
| GPU 忙 / 空闲 | 14.95 / 5.35 ms |
| `wait_flag_ge_kernel`（GPU 自旋等 CPU） | 144 次，2.34 ms（平均 16.3 µs） |
| 命中专家 kernel：`b6_mmvq_rows`、`native_gu_swiglu`、`native_down_multi` 等 | 约 4.9 ms |
| 超连接 kernel：`gr_down_staged` 1193、`gr_up_multi` 599、`gr_up75` 487、`gr_norm_split` 268 µs | 约 2.5 ms |
| GDN commit（`gdn_step_commit_layers`） | 每窗口 0.6 次 × 205 µs |

### 2.3 关键路径模型与文献校准

【推断】每层的窗口时间 ≈ doorbell 之前的串行链（reach）+ max(0, CPU − GPU 命中专家)。

- **reach 每层约 194 µs。**
  - 【来源】mkzoo 测得 MoE 的骨架是字节时间的 2～5 倍：Flint B=1 时 1467 µs，字节下限 690 µs；North 每层 39.6 µs，字节时间 27.4 µs。
  - 我们 GPU 链约为字节时间的 4 倍【推断，10_NON_PR 第 5 节】，在这个区间内。
- **骨架里是什么。**
  - 【来源】mkzoo 的 o20 / o120 有 45% 的 stall 停在 barrier / flag 自旋上。
  - 【来源】Hazy 在 B200 上每个依赖跳约 2 µs（两次 load + 两次 store，各约 500 ns），600 µs 的前向里有 250 µs 花在这里。
  - 因此**换成 megakernel 并不会让依赖延迟消失**，能省的只是 launch 间隙、尾部和 refill。
- **CPU 侧削减的上限。** tail skip、ECAP、DEFER、NP-3 类改动最多省下 GPU 的 spin：追踪下约 2.3 ms/窗口，不追踪时约 1.7 ms【推断】。MoE offload 文献的预算模型给出同样的上界：纯重叠类手段最多回收约 2 ms 的 spin，约占窗口的 11%。
- **CPU 层的性质与 fngine 不同。**
  - 【来源】fngine 的 Zen 5 CPU 层已在 DRAM 下限的约 20% 以内，所以作者认为只有减少要读的字节才有用。
  - 【事实】我们是 Xeon 4216，CPU miss 只用到 36 GB/s 的约 55%，gate/up 受计算限制（缺 VBMI 等指令，进不了 Strata 的 IQ512 编译单元）。
  - 所以 ISA 级的 CPU kernel 仍有空间。但 NP-3 已判调度类改动 NO_BENEFIT，Cascade Lake VNNI 实现需要另立项目，本调研不展开。

## 3. 迁移矩阵

只列对决策有影响的机制。"现状"指 Strata v0.2.17 在 4090 上的情况。

| # | 机制 | 来源与数字（【来源】） | 4090 / Strata 现状 | 去向 |
|---|---|---|---|---|
| 1 | 采样下按 q 抽草稿 + 拒绝采样或耦合抽样 | fngine：每轮 1.89→2.54 token，+25～30%；Strata 3060：接受率 +4.8～5.9 pt，速度持平 | 已实现（COUPLED / GUMBEL / PROB），默认关，本机未测 | **S 组** |
| 2 | 等 CPU 期间把下一层 dense 权重预取进 L2 | fngine −5.8%（宽度 1）；mkzoo：H100 上无效，大块预取全亏 | 已实现 `L2_PF`（sm_89 上逐 128 B 发 `prefetch.global.L2`），默认关 | **K 组** |
| 3 | 减少 kernel 边界：wait 融进拷贝、量化与交织合一、生产者直接写 q8_1 | mkzoo 交接优化 −1.1～10%；Strata 自测 Turing +0.5～1.4% | `FUSE_WAIT=2`、`QIL`、`QFUSE` 已实现，默认关 | **K 组** |
| 4 | 全命中的层在设备端做 plan，跳过 host 往返 | — | `VERIFY_DEVICE_PLAN` 已实现（源码注 "exact"），默认关 | **K 组** |
| 5 | 图节点优先级 | — | `GRAPH_PRIO` 已实现，默认关 | **K 组** |
| 6 | 长上下文 QSA select | Strata GP100：≤30K 时每窗口 +0.5 ms，300K 时 −4.0～4.7 ms | `SELECT_LONG` 已实现，默认关；我们的拐点未知 | **K 组**（只在 ≥64K 分段比较） |
| 7 | 单一轮询者；轮询前先发 load；强序读（`ld.relaxed.gpu` / `ld.acquire.sys`） | fngine：1 / 5 / 20 个 CTA 轮询的往返分别是 1.5 / 3.9 / 16.8 µs，DRAM 满载时 27 µs；mkzoo：先发 load −5.1%，弱读有 16～35% 读到旧值 | wait kernel 是 `<<<1,1>>>` + volatile 读，退出时 `__threadfence_system`，只满足了一半 | M6 测往返；C4 |
| 8 | 用 kernel 读写 mapped 内存，替代 memcpy 节点 | fngine：排在换入后面的拷贝从 33～50 µs 降到 2～3 µs；计数器拷贝曾等 486 µs | 窗口输入已走 `copy_*_from_mapped` kernel（满足）；`copy_` 流上的 H2D 拷贝（`verify.cpp:4033`，按代码推断是 PCIe 份额的 stage）会不会排在换入后面未知 | **M5** |
| 9 | 超连接读融合（norm + down 一个 kernel）；精确宽度特化 | fngine：融合 8.6→5.7 µs（用 cluster/DSMEM，sm_90+）；精确宽度 3.21→2.88 µs、4.51→3.93 µs（任何架构都可以） | `gr_*` 约 2.5 ms/窗口（追踪下） | **C2** |
| 10 | 命中专家 kernel 持久化 + cp.async 双缓冲 | fngine：hot_down 宽度 4 时 29.3→19.7 µs；gate/up 只跑到 1.0～1.29 TB/s | `b6_mmvq_rows` 等约 4.9 ms/窗口，是否在关键路径上不确定 | **C3**（以 M4 为门） |
| 11 | GDN 状态 fold / commit 挪出关键路径 | fngine：步尾 820→756 µs | Strata 有异步 commit（`STRATA_COMMIT_SYNC` 可关闭），在 CUDA 上是否与 draft 并行未核实 | **M2 → C5** |
| 12 | 每步换入规划、backed slots、elastic slots | fngine：宽度 1 +9～16%；换入预算 8 / 16 / 32 都无益 | Strata 有自适应层；B2 的 adapt 参数线已关闭；KVRES 已经腾出显存 | 不新开；只用来解释 M5 |
| 13 | 第 0 层按 token 查表、W12、DFloat11、认证 head | mkzoo / SpecPilot | 不适用：第 0 层是 GDN；专家已是 IQ3_XXS | 不做 |
| 14 | PDL、TMA、cluster、wgmma、graph SWITCH | squid：PDL 每个边界约省 0.5 µs | sm_89 / CUDA 12.3 都没有；12.3 有 IF / WHILE 条件节点 | 不做 |
| 15 | 预测式预取（同层 R'x、跨层 router 预览） | mkzoo：R'x 召回 82.6%（k=6），4 个 build 全失败；fngine：冷专家召回 67%、精度 44%；atomic-engine 慢 0.72%；HOBBIT 1.01～1.05× | — | 降级（§4.7） |
| 16 | 整窗或每层岛 megakernel | MPK：MoE 1.0～1.18×；Cohere：MoE 比 vLLM 快 1.58×；SpecPilot：单 kernel GDN 层 32.3 vs 17.3 µs/层，判关闭 | sm_89 可以用 grid sync / 计数器，但没有 PDL | **X 组**，条件立项 |
| 17 | verify tree、更多草稿 | fngine：tree 每轮 token +10%、步时 +36%，第 4 个草稿也被否决；EcoSpec：MTP 链只 +5% | Strata 有 DraftPolicy；CFG-SPEC-S 已测 | 不做 |
| 18 | 默认要求逐位一致、跨进程 flake soak、teacher-forced replay | mkzoo：t_replay 误差 0.2%；同一改动用生成文本测读到 −7%，真值是 0 | upgrade_gate 是自由生成的回放 | **M7 / E1** |
| 19 | 有损质量门：token forcing、KL + flips、自身噪声阈值、固定驻留 | SpecPilot；2407.09141（KL 与 flips 的 Spearman 相关 0.981，PPL 对噪声无感）；ingine；fngine / IsoMoE | 现有门：KL / top-1 + 任务集 | **G**（§4.5） |
| 20 | expert deferral（KTransformers） | DS-3 推迟 6 / 7 / 8 个专家：LiveBench −0.5 / −1.9 / −6.7% | DEFER 补丁已移植 | Q 组校准 |
| 21 | 自适应专家上限（AcceptMoE），保留每个位置的 top-1 | 固定数量上限 −9.1%，自适应 −0.27 pt；PSR：需要 top-1 救援 | ECAP 补丁是固定上限，只完整保留 token 0 | Q 组校准 |

## 4. 整合路线

### 4.0 总览

| 组 | 内容 | 性质 | 预期（【推断】） | 成本 | 前置 |
|---|---|---|---|---|---|
| M | M1～M7 测量 | 测量 | 决定 C / X 是否立项；给出 ECAP / DEFER 的上界 | 停生产约 1 h；M4 要一个小补丁 | OCR 空闲 + 停机授权 |
| S | COUPLED / +GUMBEL / PROB+top | 零代码，分布无损 | decode +2～9%（不确定） | 每臂一次固定历史回放（约 12 min） | 同上；采用需用户确认 |
| K | 7 个开关 | 零代码，逐位一致（待验） | 单项 0～2%，个别可能更大 | 先逐位检查，再筛查 | 同上 |
| C | C1～C5 | 无损代码 | 合计 3～8%（强依赖 M） | 中，Strata 补丁 | M 组 |
| Q | B2 approx / ECAP / DEFER + 新质量门 | 有损 | ECAP / DEFER 上界约等于 spin（≤2 ms） | 已有计划 | 采用需用户确认 |
| X | 每层岛 megakernel | 无损代码 | 1～3 ms/窗口（按 MPK / Hazy 推算） | XL | M3 / M4 达到门槛 |

### 4.1 M 组：测量

| 编号 | 做法 | 回答的问题 | 门 / 用途 |
|---|---|---|---|
| M1 | `STRATA_VERIFY_PROFILE=1` 每层打点。它会关掉 `sh_fork`、side mixer、l2pf、df_branch、fuse_wait，所以只看结构和差值 | reach 每层 194 µs 里，GDN/QSA、router、plan+bell、waitA/B、HC 各占多少 | 给 C1 / C2 定靶子 |
| M2 | `STRATA_COMMIT_TIMING=1`；用 nsys 看 commit 图和 draft 是否重叠 | GDN commit 是否在关键路径上 | 决定 C5 做不做 |
| M3 | `STRATA_DUMMY_NODES=k`，k = 0 / 8 / 16，T 固定 | 4090 真实窗口图里一个节点的成本 | 节点成本 × 可消掉的边界数 ≥ 1.5 ms/窗口时，C1 立项；≥ 3 ms 时，X 进入候选 |
| M4 | 延迟注入：实验树上的小补丁，env 控制，默认关。分别在命中专家 kernel 末尾、doorbell 前的链上、CPU 层各加 10 µs | 每段落在关键路径上的比例（斜率） | 命中专家的斜率 ≥ 0.5 才做 C3；同时给出 ECAP / DEFER 可回收量的上界 |
| M5 | 带 CUDA memcpy 行的 nsys | PCIe 份额的 H2D stage 拷贝会不会排在自适应换入后面（每个专家 1.74 MB，PCIe3 上约 141 µs） | 若排队，就调优先级，或改用小 kernel 拷贝（fngine 的做法） |
| M6 | 两个微基准：1 GiB 流式读；单线程轮询 mapped flag 的往返时间，分别在 CPU 空闲和 4 线程扫 DDR 时测 | 真实读带宽；DDR 满载时 flag 往返会不会像 fngine 那样从 1.5 µs 涨到 27 µs | 决定 C4 做不做 |
| M7 | 由 A/A 噪声推出门槛 | 现有 ABBA 噪声 0.6%；SpecPilot 规则：增益的 95% 下界 > 1% + 2 × 噪声 | 无损臂的门槛定为 2.2%，不用 4% |

- 【事实】M1、M2、M3 用的都是现成开关；M5 只是 nsys 参数；M6 要两个小 CUDA 程序；M4 要几行补丁，放在实验树里，env 默认关。
- 【事实】M1 和 M3 会改变图的结构，结果不能当窗口的绝对时间，只看差值。

### 4.2 S 组：采样投机（零代码，分布无损）

**臂**（所有臂都加 `STRATA_SPEC_DEPTH=1`，记录各深度的接受率）：
- S0：生产 env；
- S1：S0 + `STRATA_SPEC_COUPLED=1`；
- S2：S1 + `STRATA_SPEC_GUMBEL=1`；
- S3：S0 + `STRATA_SPEC_PROB=1` + `STRATA_SPEC_PROB_GATE=top`。

**负载**：用 B2 用过的 pisim 固定历史回放（多数请求 ≥32K，Pi 采样参数，固定 seed）。接受率只有在真实采样负载下才测得出来。

**主指标**：每窗口提交 token、ms/窗口，以及"总生成 token / 总 decode 时间"。

**正确性**：
1. 先跑上游单测：`coupled_draft_test`、`spec_prob_test`、`spec_admission_test`、`gated_proposal_test`、`spec_proposal_parity`、`native_arithmetic_parity`。这些测试需要先评估资源，或者在别的机器上跑。
2. 在固定驻留（`--adapt-every 100000`）下，S1 同一 seed 的文本应与 S0 相同。如果不同，说明有依赖窗口的算术。只记录，不阻断。
3. 各臂比较 loop 迹象和 `finish=length` 的数量。

**门**：
- S1 / S2 / S3 都不改变目标分布，所以不做质量非劣门。
- 速度门取 M7 推出的门槛和 3% 中的较大值。各臂的采样文本不同，噪声会比逐位一致的臂大，所以至少跑 ABBA。

**风险**：
- 抽出来的草稿可能更少通过 `spec-min-p 0.5` 门，T 会变小：每窗口更便宜，但 token 也更少，净效果只能实测。
- PROB 改用逐 token 的 CPU 算术，可能拖慢 CPU 层。
- 草稿链里多了采样 kernel，draft 1.57 ms/窗口会变。

**采用**：要改生产 env，必须用户确认。回滚就是删掉 env 后重启。

### 4.3 K 组：零代码无损开关

| 开关 | 源码说明（【事实】） | 风险 / 互斥 |
|---|---|---|
| `STRATA_L2_PF=1`（另有 `_MIB`、`_BLOCKS`，默认 8 块） | 等 CPU 专家时，在低优先级侧流上把下一层 dense 权重预取进 L2，"same bits" | 会和共享专家争 DRAM，fngine 因此把分叉点挪到共享专家之后；扫 16 / 32 / 64 MiB |
| `STRATA_FUSE_WAIT=2` | 把 plan 的 wait 融进后续拷贝，每层少一个节点；Turing 默认开，+0.6～1.4% | 不测 =1：行块各自跨 PCIe 轮询，Turing 上 −1.5% |
| `STRATA_QIL=1` | 量化与交织合成一次 launch，"same bytes"；Turing 默认开，+0.5～1%，每个 GDN / QSA 层少两次 launch | — |
| `STRATA_QFUSE=1` | GDN 输出 norm 直接写 q8_1 图像，"same bytes" | 会关掉一 token 窗口的自提交（`self_commit` 要求 `!g_qfuse()`） |
| `STRATA_VERIFY_DEVICE_PLAN=1` | 路由到的专家全部命中的层，在设备端做 plan，源码注 "exact" | 与 ECAP 补丁有交集（`v0217-ecap.patch` 第 27 行），组合时单独核对 |
| `STRATA_GRAPH_PRIO=1` | 节点保留各自流的优先级：侧流高，共享专家低 | 驱动可能读回全 0；启动日志里有直方图可核对 |
| `STRATA_SELECT_LONG=1` | 超过阈值的窗口改用多 CTA top-k，"same ids and score bits"；会多一套窗口图 | 多占显存；只在 ≥64K 的分段里比较 |

**排除**：
- `DF_BRANCH`：源码记录 NVML 查询会让图内分支卡住（#905），而我们的监控会调用 nvidia-smi。
- `VERIFY_QDEDUP`：与默认开启的共享专家分叉流互斥。
- `LFUSE`、`QSA_SPLIT_ATTN`：源码没有声明逐位一致。要测的话按有损处理，走质量门。

**做法**：
1. **逐位筛查**：固定驻留、同一 seed、一段短的固定回放，比较 S0 与每个单开关臂的输出 token 是否逐位相同。这是使用 M7 门槛的前提。`QFUSE` 可能因自提交的差异而不逐位，单独记录。
2. **速度筛查**：每臂跑一次，用 E1 的固定 T 读窗口计时，或者用固定历史回放里 ≥32K 的那段。
3. **ABBA**：过了筛查的项再做 ABBA，门槛 2.2%。
4. **组合**：最后测组合。mkzoo 的经验是单项收益不一定能叠加。

### 4.4 C 组：无损代码（都以 M 组为门）

**C1：doorbell 之前的链融合。**
- 候选：
  - router、topk、plan 合并；
  - `gr_norm_split` 融进 `gr_down_staged`；
  - 每层的记账 kernel（`rebase_ptrs`、`add_hits`、`doorbell_publish_res`）合成一个。
- 不要合并 `copy_*_from_mapped`（见 §0.3）。
- 门：M3 测得的节点成本 × 链上可消掉的边界数 ≥ 1.5 ms/窗口。
- 依据：mkzoo 减少阶段数 −1.1～2.9%、交接优化 −1.4～10%、把 norm 融进 epilogue −3.1%；Hazy 靠重算 RMSNorm 去掉一个边界。

**C2：超连接 kernel。**
- 精确宽度特化：T 作为编译期常量，只分配用到的列，任何架构都能做。
- 单 kernel 的 norm+down：fngine 用的是 cluster/DSMEM，sm_89 没有，需要改成每条流一个 CTA，或者用全局 partial 加计数器。
- 依据：fngine 1 token 3.21→2.88 µs、2 token 4.51→3.93 µs，输出逐字节相同。
- 门：M1 里 HC 的占比。

**C3：命中专家 kernel 流式化。**
- 做法：持久化 CTA + cp.async 双缓冲（sm_80+ 可用），每个专家的激活只量化一次。
- 门：M4 测得命中专家的斜率 ≥ 0.5。
- 依据：fngine 宽度 4 时 hot_down 29.3→19.7 µs，整条 MoE 管线 61.5→52.1 µs。

**C4：host flag 协议的细节。**
- 轮询前先把后续要用的 load 发出去。mkzoo：−5.1%，以及 −190～−250 µs。
- 用 `ld.acquire.sys` 或 `ld.relaxed.sys` 代替 volatile。
- fence 只做必要的那一次。TK2：fence 过松会出错，过严代价 >10%。
- 每窗口用单调递增的 epoch 计数，不再清零（MPK）。
- 门：M6 显示 DDR 满载时往返明显变长。

**C5：GDN commit 与 draft 并行。**
- 门：M2 显示 commit 在关键路径上。
- 【推断】最多约 0.12 ms/窗口（0.6 次 × 205 µs）。

### 4.5 Q 组：有损方向的校准与质量门升级

**B2 approx（TAIL_SKIP / ROUTE_PRIOR）**：保持原计划，只升级质量门（见下文 G）。

**DEFER（KTransformers 的 expert deferral）**
- 【来源】DS-3 推迟 6 / 7 / 8 个专家时，LiveBench 分别 −0.5 / −1.9 / −6.7%。注意那是全 attention 模型、短上下文、没有测 KL，而且它的基线 CPU/GPU 重叠只有 5%。
- 【推断】我们能回收的上界是 spin，约 2 ms/窗口。
- 风险：被推迟的贡献晚一层才进入 GDN 递归状态，并跨 token 持续存在。没有文献测过这一点。必须做 ≥32K 的长生成，并逐层比较 GDN 状态的漂移。
- 内存序：DEFER 的 `h_pflag_` 交接按 mkzoo §5 检查：
  - 普通 store 不保证排在后续 atomic 之前；
  - 轮询必须用强读；
  - 跨进程做 flake soak。

**ECAP**
- 【来源】AcceptMoE：固定数量的上限 −9.1%；自适应上限只有 −0.27 pt，做法是按草稿深度加权（p̂^0.5）、上限取 exp(H)、并保留每个位置的 top-1。
- 【来源】PSR：块选择必须保留有把握位置的 top-1，否则 KL 约翻倍；36% 的已提交 token-层会因为哪些草稿被拒而换专家。
- 【推断】ECAP 现在是固定上限，只完整保留 token 0。可考虑：每个位置的 top-1 都不裁；上限随路由熵变化。ECAP 的输出依赖 T 和草稿，所以门要端到端测。

**G：质量门升级**（同时用于 B2 approx、ECAP、DEFER）
1. **固定驻留**：`--adapt-every 100000`。Strata 文档写明，默认自适应层下采样结果不可复现；fngine 同一 build 的 G1 在 79.3～85.0% 之间波动。
2. **teacher-forced KL / top-1 / flips**：报告 flips。2407.09141：KL 与 flips 的 Spearman 相关 0.981，PPL 对对称噪声完全无感。
3. **token forcing**（SpecPilot）：
   - 把候选的输出喂回精确路径打分；
   - 两条拒绝规则：错配率比"精确路径对自己"高出 0.5 pt 以上；或 margin > 2δ 的大分歧事件显著增多；
   - δ 用精确路径在不同 T 之间首次分歧时的最大 margin 来标定。
4. **阈值取自身噪声**（ingine）：用同一配置跑两次的 KL / top-1 差，不用固定常数。
5. **长度**：生成长度要超过开发时用的长度，并覆盖 ≥32K。KernelBench-Verified 的 HACK-6 说明，把递归状态清零在短序列上测不出来。

### 4.6 X 组：每层岛 megakernel（条件立项）

- **立项门**：M3 / M4 显示可消掉的边界与尾部 ≥ 3 ms/窗口，并且做完 C1 / C2 后仍 ≥ 2 ms。
- **形态**：
  - 从每层的 combine 到下一层 doorbell，做成一个持久化区域，每个 SM 一个 CTA；
  - 只有 combine 等 CPU flag，其余 SM 照常算共享专家、命中专家，并预取下一层与激活无关的权重（Cohere 的"先预取再等"）；
  - 使用单调计数器（MPK）；
  - 归约顺序照搬原 kernel（Thinking Machines），否则就不再逐位一致。
- **【来源】的上限与反例**：
  - MPK 的 MoE 层只有 1.07～1.18×；
  - SpecPilot 已经关闭了单 kernel GDN 层（32.3 vs 17.3 µs/层）和持久化跨 GEMM（196 vs 172 µs/层）；
  - Hazy 的作者报告了数月的竞态和死锁；
  - sm_89 每个 SM 的 smem 约 100 KB（未核实），没有 TMA / PDL / cluster。
- **【推断】**收益 1～3 ms/窗口（5～15%），工作量 XL，而且每次 Strata 升级都要重新移植。

### 4.7 降级或不做

| 方向 | 证据（【来源】） |
|---|---|
| 预测式预取（第一版 E4） | mkzoo 的 R'x 在 4 个 GPU build 上全部失败；fngine 冷专家召回 67%、精度 44%，再往后看一层几乎没有增益；atomic-engine 召回 45～47%，开启后慢 0.72%；HOBBIT 的 decode 预取只有 1.01～1.05×。没有一篇论文报告"对未命中专家"的预测精度。PCIe3 上一次错误预取浪费约 141 µs 链路时间 |
| 更大的换入预算、显存 LRU、CPU cache 预热 | fngine：命中率 0.949→0.955，但时间不变；预热即使完美预知也无益 |
| verify tree、第 4 个草稿、更大的草稿词表 | fngine：tree 每轮 token +10%、步时 +36%；其余几项都被否决 |
| W12、DFloat11、认证 head | 专家已经是 IQ3_XXS；DF11 在 batch 1 下是净开销；认证 head 只对 greedy 无损，在 RTX PRO 6000 上反而更慢 |
| 单 kernel GDN 层、持久化跨 GEMM | SpecPilot Table A7 已关闭 |
| 低权重的 miss 改用低比特副本（HOBBIT / SPICE） | 从 3-bit 降到 2-bit 比从 16-bit 降到 4-bit 风险大；全量副本要 28.8 GB 主机内存 |

### 4.8 建议执行顺序

1. **现在就能做，不占 GPU：**
   - 用 prodlog 和监控做只读分析，看 OCR 忙闲与 decode tok/s 的相关性（§0.2 第 7 条）；
   - 写 S / K / M 三组的预登记：臂、指标、门、no-repeat 条目；
   - 写 M4 补丁和 M6 微基准，只写不编译（本机资源约束）；
   - 修正 NEXT_ACTIONS 里"都已测完"的说法。
2. **第一次停机窗口**（需要 OCR 空闲 + 用户授权，约 2.5～3 h）：
   1. M1 / M2 / M3 / M5，约 45 min；
   2. K 组的逐位筛查和速度筛查，约 1 h；
   3. S 组四个臂各跑一次，约 50 min。
   
   之后按结果预登记 ABBA。
3. **第二次停机窗口：**
   - S / K 中过了筛查的项做 ABBA；
   - 恢复 B2 approx 第二阶段和 ECAP / DEFER 的门，质量门改用 G；
   - ECAP / DEFER 先用 M4 的斜率估算上界，上界低于门槛的不跑速度对照。
4. **之后**：C 组按 M 组结果逐项立项；X 组只在达到门槛后才讨论。

## 5. ECAP / DEFER 验证补充（与 §4.5 一起执行）

- **逐位部分**：ECAP 不触发的层，以及 DEFER 关闭时，输出必须与基线逐位一致。补丁的 `ecap_parity` 和 PORT_NOTES 列出的测试要先通过。
- **flake soak**：每个补丁跨进程重复至少 20 次，比较 token 流，抓偶发的内存序问题（mkzoo 遇到过 1/357 这种量级的偶发）。
- **两种驻留**：KL 在固定驻留下测；速度对照在自适应驻留下测，与生产形态一致。
- **长生成**：做 ≥32K 的长生成，并逐层比较 GDN 状态。这是 DEFER 特有的风险。
- **上界**：M4 测得的 CPU 斜率 × 被削减的 CPU 时间。

## 6. 未验证事项与风险

- **S 组收益方向不确定。** fngine（+25～30%）和 Strata 3060（持平）的结论相反，而我们的 `spec-min-p` 门会让空间更小（§0.2）。
- **K 组的"same bytes"只是源码注释。** 大多在别的架构上验证过（Turing、gfx12、GP100），sm_89 上要逐位核对。
- **Ada 上没有任何来源的实测。** 4090 的图节点成本、mapped flag 往返、L2 预取能否真正进 L2，都没有人在 Ada 上测过。
- **关键路径模型是推断。** "reach + max(0, CPU − GPU)" 尚未直接验证，M4 是第一次验证。
- **源码版本。**
  - `verify*` 和 `generate.cpp` 读的是 v0.2.17 副本；
  - `spec_prob.hpp` / `coupled_draft.hpp` 读的是 `/root/github/Strata` 的 HEAD（v0.2.20 之后），已用 `git show v0.2.17:` 核对：两个文件在 v0.2.17 都存在，GATE / MIN_TEMP 开关也在。
- **GPU 时间片的影响是按 fngine 类比推断的。** OCR 的 GPU 提交频率没有测过。
- **部分来源只是浅读。** BuddyMoE、SPICE、SliceMoE、Limits of Speculation、Expert Coactivation 只读了摘要和数字；KernelGuard 只读了摘要和规则代码；Mooncake 浅读。

## 7. 来源

- **仓库：**
  - [dangxingyu/megakernel-zoo](https://github.com/dangxingyu/megakernel-zoo) `95e315c8`；
  - [tensorfish/squid5090](https://github.com/tensorfish/squid5090) `50b5bf40`；
  - satellitedown/fngine；
  - satellitedown/inkling-2-mini-abliterated-ingine；
  - AtomicBot-ai/atomic-engine（`engine-development` 分支）。
- **文章：**
  - [A Megakernel per Model](https://dangxingyu.github.io/megakernel/)；
  - Hazy Research *Look Ma, No Bubbles!*（2025-05-27）及后续；
  - Cohere North megakernel；
  - Thinking Machines *Defeating Nondeterminism in LLM Inference*。
- **论文（arXiv）：**
  - megakernel 与评测：2512.22219（MPK）、2611.02501（SpecPilot）、2407.09141、2504.11651（DFloat11）、2607.16241、2502.10517、2509.14279、2610.02185；
  - CPU 计算与调度：2402.07033（Fiddler）、KTransformers（SOSP'25，doi 10.1145/3731569.3764843）、2411.11217、2504.05897、2611.11533、2611.27604、2611.01859、2610.23006、2610.01265；
  - 预测与预取：2312.17238、2308.12066、2410.22134、2408.10284、2411.01433、2501.10375、2502.05370、2401.14361、2410.17954；
  - 投机解码与 MoE：2506.20675、2607.12696、2609.22156、2608.02989、2610.34721、2510.10302、2511.14102、2603.09983、2610.01950、2609.22471、2608.21240、2511.10054、2512.12990。
- **Strata 本地：** `/root/github/Strata/docs/DETAILS.md`（采样投机、PROB 门）、`docs/SETTINGS.md`，以及 v0.2.17 源码副本。
- **本仓库：**
  - reports：`P0-T6-CFG-20261025.md`、`P0-T7-NP0-20261025.md`、`P2-NP3-TRACE-20261026.md`、`V0216-DECODE100K-NSYS-QUALITY-20261120.md`、`V0216-CONFIG-MIGRATION-20261120.md`；
  - plans：`B2_APPROX_20261124.md`、`NEXT_ACTIONS.md`、`NP3_CPU_POOL.md`、`SPEC_LOOKUP.md`；
  - docs：`10_NON_PR_DIRECTIONS.md`；
  - patches：`v0217-*.PORT_NOTES.md`。
