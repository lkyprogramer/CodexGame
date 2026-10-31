> 历史实验规范与记录。后续探索的当前阶段见 [NEXT_ACTIONS](../plans/NEXT_ACTIONS.md)；本文原口径用于解释原报告，不覆盖 frontier 新阶段合同。

# 非 PR 方向：29 号机的性能空间

本文件记录不依赖任何上游 PR 的优化方向，来源是 2026-10-23 对 29 生产日志、`/proc`、sysfs 和上游源码（冻结 main `5c8dd322` 与部署树 0.1.43.1）的只读调研。它和 PR 实验项并列，但**不进入 `config/experiments.json`**：配置类方向按 `CFG-*` 对照执行（规则同 [测试协议](04_TEST_PROTOCOL.md)“配置与诊断对照”），代码类方向按 `NP-*` 独立立项，流程沿用 PR 项的 Phase A～E 与 Gate。

所有数字标明性质：**事实**＝日志或源码直接可见；**估算**＝由事实推算，未实测；**假设**＝待验证的解释。

> **2026-10-26 状态**：第 1～7 节是 10-23 的调研原文（基于 0.1.43.1 日志），保留作依据。各项的实测结论、按单会话用法重排后的执行次序，以及与 v2 包 64 方向图谱的对应，见第 8 节和第 10 节；两者冲突时以第 8、10 节为准。

## 1. 基线画像

**事实**（`strata-iq3_xxs.log`，0.1.43.1，2577 个窗口的一条 decode 计时）：

```
17.49 ms/window，平均 T 3.24，2.33 token/window（约 133 tok/s）
= verify 15.34 [GPU-reach wait 9.93 + per-layer host 4.77（其中 CPU experts 4.24）+ stage 0.01]
  + commit/emit 0.02 + draft 1.88
每层每窗口：CPU experts 1.16 个，VRAM hits 29.72，PCIe 0.13
```

- CPU 处理一个未命中专家 76～87 µs（20.2～22.9 GB/s），PCIe 实测 12.3 GB/s（`PCIe share` 日志行）；专家约 1.74 MB（15.29 GiB / 9434 slots）。
- decode 命中率稳定期 92～96%，重启后首批请求低至 85.5%。
- 108K prompt prefill 36.4 s（约 2980 tok/s）：wait copy 24.1%、dequant 9.7%、gemm gate/up 10.5%、gemm down 5.1%、hc read 6.7%、gdn 6.6%、host grouping 6.6%、combine 5.5%、gdn recurrence 4.9%、qsa attn 4.6%。
- **估算**：约 48 层（由 profile 的 24576 个 (层, 专家) 对和每次未命中耗时反推）。

吞吐 = token/window ÷ ms/window。可动的只有：缩短 verify、缩短 draft、提高每窗口接受的 token。

**最大的未知数**：计时把“等 GPU”和“CPU 专家”相加，但同一层内 CPU 未命中专家与 GPU 命中专家是否并行，日志看不出来。若 CPU 慢于同层 GPU 专家，CPU 在关键路径上，第 3 节的收益是线性的；否则只有超出 GPU 的那部分能省。**第 3 节任何方向开始前必须先完成 NP-0。**

下面各方向削减的是同一段时间，收益不能相加。

## 2. NP-0 · 先测量（必做，零风险）

| 步骤 | 内容 | 产出 |
|---|---|---|
| 诊断构建 | 即 START_HERE P0-T5 的 DIAG（冻结 main + #1864 + #3631） | 每窗口 adapt wait / verify / commit / draft / join / other 与专家读取构成 |
| GPU 时间线 | 对 DIAG 跑一次 `nsys`，覆盖约 20 个 decode 窗口 | 每层 GPU 空闲间隙、每窗口 kernel 数、CPU 结果回传等待 |
| CPU 采样 | 对 pool worker 线程 `perf record`/`perf stat`（cycles、dTLB miss、指令数） | CPU 专家耗时中计算、等待、同步、TLB 各占多少 |
| 内存带宽 | 一次 STREAM 类读带宽测试（只读，不改配置） | CPU 路径的带宽上限，判断 20 GB/s 离上限多远 |

**Gate NP-0**：给出“CPU 是否在关键路径上”和“GPU 部分离带宽上限多远”的结论，再决定第 3、5 节投入哪项。

## 3. CPU 专家路径（4.24 ms，占窗口约 24%）

### NP-1 · 不依赖 VBMI 的 AVX512-VNNI IQ3_XXS 内核（代码）

- **事实**：29 的 CPU（Xeon Silver 4216，Cascade Lake）支持 `avx512f/bw/dq/vl/vnni`，引擎却打印 `this CPU has no AVX-512: the expert kernels run on AVX-2`。原因是 `include/strata/kernels/cpu/expert.hpp:101` 的 `usable()` 要求 `avx512_vbmi`，Cascade Lake 没有 VBMI。
- **方向**：新增一条“VNNI、无 VBMI”路径：256 位 `vpdpbusd`（AVX512-VL）替代 AVX2 的 `maddubs + madd + add`；**不用 512 位寄存器**（Silver 只有一个 512 位单元，宽度不增吞吐，还会触发降频）；IQ3_XXS 网格查表用 `vpermi2d` 或 gather。
- **假设**：16 线程合计约 20 GB/s、单线程约 1.4 GB/s，远低于内存带宽，瓶颈在计算或调度。先用 `src/kernels/cpu` 下现有的 parity/bench 工具拆开。
- **2026-10-26 实测（[#3871 修正后的 bench](../reports/P2-PR3871-20261026.md)）**：单核确实计算受限（nt=1 每核 2.1～2.7 GB/s）。但 16 线程 nt=1 时，本机全部 10 种 GU/down 组合都已达到 36 GB/s 的 81～98%。decode 每个 miss 平均约 1.2 个 token，所以更快的内核基本没有空间，**维持暂缓**。引擎与吞吐下限之间的差距属于 NP-3。
- **验收**：与 AVX2 路径逐位一致（同一累加顺序）；单专家微基准与每层 host 时间同时下降。开关 `STRATA_LAB_NP1=0/1`。
- **停止条件**：NP-0 显示 CPU 不在关键路径上，或微基准显示瓶颈是同步而非计算。

### CFG-CSTATE · C6 唤醒延迟（系统配置，需用户批准）

- **事实**：调频策略 `schedutil`；C6 已启用，退出延迟 133 µs，cpu1（pool worker）进入 C6 约 334 万次。
- **假设**：每层 CPU 任务约 90 µs，一次 C6 唤醒就比任务长；48 层中部分层命中即是毫秒级。
- **对照**：A0 vs A0 + `performance` 调频 + 禁用 C6（或由进程持有 `/dev/cpu_dma_latency`），比较每层 host 时间与 ms/window。
- **限制**：这是 29 整机的 root 级配置，会影响同机其他实验。只在用户批准的维护窗口内执行，记录原值，结束后恢复。本包 runner 不会代为修改。

### CFG-THP / NP-2 · 专家 arena 的大页覆盖

- **事实**：THP `enabled=always`、`defrag=madvise`；引擎检测到 `always` 后不调用 `MADV_HUGEPAGE`（`src/core/pinned.cu:263`）；`vm.nr_hugepages=0`。
- **假设**：内存紧张、碎片多时，40 GiB arena 的缺页拿不到 2 MB 页而退回 4K 页，读 1.74 MB 专家时 TLB 未命中增多，L2 硬件预取在 4K 边界中断。
- **先验证**：下次启动后读引擎进程 `/proc/<pid>/smaps_rollup` 的 `AnonHugePages`，接近 40 GiB 则本项关闭。
- **修法**：NP-2 在 `always` 下也强制 `MADV_HUGEPAGE`（约一行代码，开关 `STRATA_LAB_NP2`）；或 hugetlbfs 预留 20464 个 2 MB 页（锁定 40 GiB，内存紧张时有风险，需用户批准）。

### NP-3 · CPU pool 的任务切分（代码）

每层只有约 1.16 个专家、3 行，却拆给 16 个线程，48 层各做一次分发与汇合。方向：按输出行切分、把 gate/up 与 down 合并成一个任务、去掉中间栅栏。以 NP-0 的 `perf` 同步占比决定是否投入。

**2026-10-26**：NP-0 已证明 CPU 专家在关键路径上，NP-3 是第一个代码方向。详细执行计划收编自 v2 包 P01，见 [plans/NP3_CPU_POOL.md](../plans/NP3_CPU_POOL.md)（先做 #3871 微基准修正与 perf 分解，再做并行中间量化、成本加权分行）。

### CFG-PROFILE · 用学习后的 expert profile 启动（配置）

- **事实**：`data/expert-profile-iq3xxs-learned.bin`（2026-10-16）存在，生产启动仍用 10-13 的静态 `expert-profile-iq3xxs.bin`。
- **对照**：A0 两份配置分别用两个 profile，比较重启后前 N 个请求的命中率与稳定期命中率。实验配置必须复制 profile 到 arm 目录，不读写生产 `data/`。

### NP-4 · 跨层路由预测 + PCIe 预取（研究级）

- **思路**：用第 L 层的残差流套第 L+1 层的 router，预测下一层哪些专家会未命中，提前经 PCIe 搬进显存；计算仍用真实路由，结果精确。
- **估算**：GPU 每层约 200 µs，按 12.3 GB/s 可搬约 2.4 MB ≈ 1.4 个专家，刚好覆盖每层约 1.16 个未命中；PCIe 平时几乎闲置（share 0.007）。
- **风险**：与 adaptive tier、overlap 的显存槽位交互；预测错误时浪费带宽和槽位。先离线评估预测准确率：v0.2.3 引擎命令行运行有 `--dump-routing PATH`（每层每位置的路由专家与权重）和 `--dump-layers PATH`（每层残差），可直接作为训练/评估数据；低于约 60% 不立项。

## 4. draft（1.88 ms，占窗口约 11%）

### CFG-MTPQ4 / CFG-DVOCAB · 现有开关（0.1.43.1 与 main 都有）

- **事实**：draft head 已裁剪到 106,299 个 token（178.4 MiB）；MTP 层占 950 MiB 显存（专家 675、dense 111）。源码中有 `--mtp-q4 all|proj|head`（draft 层 4 位副本）和 `--mtp-draft-vocab FILE`（自定义 draft 词表）。
- **方向**：用 Pi 实际输出的 token 频率生成更小的 draft 词表（例如覆盖 99.x% 输出的约 32K），再配合 `--mtp-q4 head` 或 `all`。目标分布不变（由验证决定），代价是接受率可能略降。
- **估算**：每窗口省 0.3～0.8 ms（2～5%）。
- **对照**：A0 vs A0+开关，主指标 ms/window、token/window、接受率；需同时跑 greedy 与 Pi 采样参数两组。

## 5. GPU 部分（等 GPU 9.93 ms，占窗口约 57%）

- **估算**：每窗口命中专家约 29.7 × 48 层 × 1.74 MB ≈ 2.5 GB，加 dense 约 2～3 GB，按约 850 GB/s 下限约 5～6.5 ms，GPU 部分约在带宽上限的 55～65%。具体损失在哪由 NP-0 的 nsys 决定。
- 已在实验包内的项：#3453（Ada MMVQ 表）、B6 跨行复用、CFG-EXACT、CFG-IL0（`STRATA_MMVQ_IL=0`，依据 Issue #1842 的 4090 共享表失配，见测试协议）。
- **NP-5 · 小 kernel 融合**：4090（sm_89）没有 PDL，小 kernel 的发射间隙更值得消除。候选：router + topk + 共享专家、hc read、norm + 激活量化。以 nsys 的每窗口 kernel 数和间隙为依据。
- **NP-6 · L2 持久化**：4090 有 72 MB L2，给 router、norm、hc 等小而热的张量设 `cudaAccessPolicyWindow`。
- **NP-7 · 窗口长度考虑专家并集成本**：验证窗口每多一行，要读的专家并集就变大。把实测的每个 T 的窗口成本喂给 draft policy，让窗口长度决策包含这部分成本。
- 远期：整层 decode 的 persistent megakernel，工作量很大，不在本轮。

## 6. 每窗口 token 数（当前 2.33）

- **事实**：Pi 请求是采样的（`temperature 1.0 / top_p 0.95 / top_k 20`），thinking 为 `xhigh`，接受率天然低于 greedy。
- **CFG-LOOKUP**：suffix drafter（前缀查表）默认开启，`--lookup-chain K` 可选。Pi 的 codemode 与 edit 工具调用会大段照抄上下文，适合查表 draft。**2026-10-26 已确认**：采样请求下 lookup 窗口确实发生，但被接受的 lookup 草稿只占生成 token 的 3.6～5.6%（thinking 是新文本）；CFG-LOOKUP2 在 greedy 题集也无收益。#4040（lookup 长窗口）因此只在改文件类会话评估。
- **NP-8 · 跨请求后缀树 draft（研究级）**：agent 循环反复出现的工具调用 JSON 框架和样板代码，不在当前上下文里也能预测（SuffixDecoding 类思路）。需要独立的接受率离线评估。

## 7. Prefill（占引擎时间约 20～25%）

- **NP-9 · 直接在量化权重上做 MMQ**：dequant 单独一遍占 9.7%。先确认 main 的 fused prompt-expert 路径在 sm_89 上是否被选中（#3779、#3277 只覆盖 sm_80 / sm_75），再考虑 int8 tensor core / dp4a 版 IQ3_XXS MMQ。
- **NP-10 · 分组搬到 GPU**：host grouping 占 6.6%，改为 GPU 侧排序与直方图。
- **wait copy 24%**：PCIe 是平台上限，只能靠更大 chunk 摊薄。**2026-10-26 已解决主要部分**：chunk 停在 8192 是 `--prefill auto` 的默认上限，`STRATA_PREFILL_AUTO_MAX=16384`（CFG-AUTOMAX）使 40K 冷读 −19%、超过 8192 的追问读入 −27%，wait copy 占比 31.8% → 17.9%；#3307 / #3281 不再需要（[报告](../reports/P2-PR3307-20261026.md)）。
- **追问的短读入（2026-10-26 实测，[P2-CFG-CPUSHARE-S](../reports/P2-CFG-CPUSHARE-S-20261026.md)）**：
  - 门槛以下的 chunk 只搬路由到的专家，CPU 分担一部分，耗时随 token 数增长。达到门槛的 chunk 流式搬全部非驻留专家，3K～7.3K 都是约 2.4～2.65 s。两者约在 4.4K 相交。
  - `STRATA_PREFILL_CPU_SHARE_MAX=4096` 让 3.1～3.2K 读入快 12.2%，其余不变，是采用候选。8192 / 16384 让 7～8K 单 chunk 慢 15～20%，拒绝。
  - 7～13K 读入：≤8192 的单 chunk 读入没有零代码空间；超过 8192 的由 CFG-AUTOMAX 变成单 chunk，TTFT 省 1.0～2.2 s。
- **追问 TTFT 中 prefill 以外的 0.6～0.8 s（2026-10-26 trace 实测）**：
  - park 上一个分支：0.15～0.5 s，PT=0 时每个用户轮都会发生 → CFG-PARKGAIN，只在选 PT=0 后测。
  - 专家缓存槽同步回填：0.2～0.35 s，每次 >1K 的读入都会发生 → 可改为与首个 decode 窗口重叠（代码，排在 NP-3 之后）。
  - checkpoint 保存：约 0.06 s。
- **GDN 递推 4.9%**：chunked tensor-core scan（#3779 的 `STRATA_GDN_TC`）有舍入级数值差，必须过质量门。
- **冷启动**：67 个请求中 6 个冷启动约占 prompt 时间一半，主要来自 park 被拒（#2253）和重启。**NP-11**：把 Pi 约 12.3K 的公共前缀持久化为会话文件，重启后免重读。

### CFG-UNLOCK · 解除 4090 的 FP32 累加 tensor 限速（整机固件阶段配置，需用户单独批准）

- **来源**：[JustAResearcher/gpu-unlock-ada](https://github.com/JustAResearcher/gpu-unlock-ada)（v1.1.1；检索时 main 为 `4e7fefcc4923f9e083d5324dc75a7d2f906af77f`）。它是一个 initramfs 内核模块，在 NVIDIA 驱动接管前运行已签名的 SEC2 Booter，利用其漏洞链写入 SS0=`0x88888888`、SS1=`0x8`，再做 FLR 交给原版驱动。不改驱动、不刷 VBIOS；去掉内核参数并断电一次即恢复。
- **来源报告（不是本包实测）**：
  - 4090 配对测试（450 W，驱动 615.78.08，内核 7.2.11）：FP16/FP32 累加指令吞吐 160.4 → 320.4 TF/s，BF16/FP32 159.7 → 320.2，TF32 约 2 倍；INT8、`dp4a`、FP16 累加、FP32 FMA 不变。
  - cuBLAS GEMM 只有 1.12～1.34 倍（FP16）、1.16～1.20 倍（BF16），4096³ BF16 不变；只有 1～2 张 4090 的样本。
  - Strata 在 3080 上的 A/B（[Zagitta/gpu-unlock#15](https://github.com/Zagitta/gpu-unlock/issues/15)）：cuBLAS +50%，Strata prefill 8K 不变、32K/128K +12～13%，decode 在噪声内。
- **29 上可能受益的部分（事实）**：Strata prefill 的专家 GEMM 先反量化成 FP16，再用 `mma … f32.f16.f16.f32` 和 `cublasGemmEx` + `CUBLAS_COMPUTE_32F` 计算。108K 冷 prefill 中走 FP16/BF16/TF32 tensor 的项合计约 45%（专家 gate/up + down 约 15%、hc read 6.7%、gdn 投影约 9%、qsa attn 4.6%、qsa proj 3.9%、qsa select 3.3%、共享专家约 1%）。wait copy 24%、dequant 约 10%、host grouping、combine 不受影响。decode 的 dense 投影走 MMVQ（`dp4a`/INT8），等 GPU 的时间主要受显存带宽限制，CPU 专家在主机上。
- **估算（推断）**：32K～120K 冷 prefill / TTFT −4～10%（108K 约省 1.5～3.6 s）；≤12K 约 0；decode 0；按真实流量（decode 占 75～80%）折算，引擎总耗时约 −1～2.5%，低于 A/A 噪声。NP-9 若把同一批 GEMM 改走 INT8 tensor（4090 上本来就不限速），本项剩余收益会更小。
- **29 前提（2026-10-25 只读核对）**：GPU `10de:2684`（项目支持的非 D 版 4090），PCI 地址 `0000:65:00.0`；显示由 ASPEED 板载显卡负责，4090 不接显示；Secure Boot disabled；Debian 12，内核 `6.1.0-17-amd64`，dkms 3.4.1、initramfs-tools 0.142，`CONFIG_CRYPTO_LIB_SHA256=y`；驱动 610.57.04；功率上限 450 W（默认 450、最大 500）；有 BMC（`/dev/ipmi0`），BMC 网络是否可达未验证。
- **未验证 / 风险**：4090 只在 Arch 7.2.11 + 615.78.08 上验证过；Debian 6.1 内核能否编译、610.57.04 能否正常接管，没有证据。机制依赖固件漏洞链和 GPU 复位；失败时模块会保留 DMA 缓冲，要求断电重来。29 只能经 `jssh 29` 远程访问，首次尝试必须完全断电冷启动，需要 BMC 可用或有人在现场。会打断同机其他实验。需要 sudo、DKMS、initramfs 和 GRUB 改动，超出本包常规权限。
- **执行（只在用户批准的维护窗口，排在 MIG、CFG-IL0、#2253 之后）**：
  1. 先确认 BMC 能远程断电和开机；记录原 `/proc/cmdline`、GRUB 配置和 initramfs 的哈希。
  2. 基线：项目自带的 `diagnostics/bench/mma_bench` 与 `validate_gemm`；Strata 的 decode 组和 cold-prefill 组（32K/64K/120K），各 5 轮，与当前公共基线同一配置。
  3. 在 29 上本地构建 deb 包（固件输入在本机下载生成，不使用他人构建的固件）。默认启动项不加参数，只新增一个单次 GRUB 启动项，带 `gpu_unlock.targets=0000:65:00.0`；保留原启动项为默认。
  4. 经 BMC 完全断电后用该启动项冷启动。核对 `journalctl -k -b | grep gpu_unlock` 出现 `unlocked`、post-FLR 检查通过、RM getter 报 `fmla32=0`、没有 `NVRM: Xid`。
  5. 用同一组负载复测，并加跑质量/工具/协议组和至少 1 小时持续负载。
- **门槛**：≥32K 冷 prefill 提升 ≥5% 且超过 A/A 噪声；decode、质量、工具硬门不退步；持续负载期间没有 Xid 或掉卡。否则判 NO_BENEFIT 并回退。
- **回退**：用默认启动项（不带参数）完全断电重启；卸载包会同时移除模块和 initramfs 集成。不 force-unload 处于 DMA 保留状态的模块。
- **交付**：`workspace/state/cfg-unlock/` 下的 `DECISION.md`、启动日志节选、寄存器读回、两组原始数据。是否常驻由用户决定；常驻还要做一次普通热重启验证，内核升级后需重建 initramfs 再验证。

## 8. 执行顺序（2026-10-26 按单会话用法与实测重排）

已完成（报告在 `reports/`）：NP-0；CFG-IL0 / CFG-IL89 / CFG-EXACT（EXACT6 进公共基线）/ CFG-THP / POOL8 / CFG-PROFILE / CFG-LOOKUP2 / CFG-MTPQ4（边缘）/ NP-1a（证伪）；CFG-CSTATE（已上线）；CFG-MMAP（不推荐）；CFG-PT（新增开关，推荐 PT=0）。

剩余次序（与 PR 交错，完整表见 README）：

1. **CFG-SPEC-S**（零代码，decode；**已完成，保持 `--spec 4`**，见 [P2-CFG-SPEC-S](../reports/P2-CFG-SPEC-S-20261026.md)：每窗口耗时随提交 token 近似同比例增长，宽度只能在 ±1% 内调，NP-3 降低 CPU 专家单价后再测 spec 5/6）：`--spec 3 / 4 / 5` 在 Pi 采样 + thinking 下对照。依据：采样下每窗口只提交 2.05～2.44 token，greedy 为 2.78。主指标引擎 ms/窗口与“总生成 token / 总 decode 时间”。细则见 [plans/SPEC_LOOKUP.md](../plans/SPEC_LOOKUP.md)。
2. **CFG-CPUSHARE-S**（零代码，追问 TTFT；**已完成，4096 为采用候选**，见 [P2-CFG-CPUSHARE-S](../reports/P2-CFG-CPUSHARE-S-20261026.md)：3.2K 读入 −12.2%，7～13K 持平；真实流量中约 4% 的追问落在受益区间）：`STRATA_PREFILL_CPU_SHARE_MAX` 3072 / 8192 / 16384，补测 4096。
3. **NP-3**（代码，decode）：#3871 已完成（[报告](../reports/P2-PR3871-20261026.md)：引擎 74～82 µs/miss，吞吐下限约 57 µs，上限约为窗口时间的 6～11%）。**已完成，pool 代码方向 NO_BENEFIT**（[perf](../reports/P2-NP3-PERF-20261026.md)、[trace](../reports/P2-NP3-TRACE-20261026.md)）：每个 CPU miss 约 76 µs，同步约 2.5 µs、尾部约 5 µs，其余在任务内（gate/up 受计算限制，PCIe 读与 CPU 争用内存）；P01-04 / 05 / 06 / 07 都不实施，trace 工具保留。
4. **NP-RES（v2 O07 / O08 / O09）**：**已完成，NO_BENEFIT**（[报告](../reports/P2-NPRES-PCIEFRAC-20261026.md)）：固定 `--pcie-frac 0.30` 对 PcieAuto +0.3～4.2%，`STRATA_PCIE_BALANCE=1` 0～+2.1%，都低于 3% 门；O07 / O08 按分析判断不立项，O09 未测。原计划：先做零代码的 **CFG-PCIEFRAC**：NP-3 trace 显示 CPU miss 单价随 PCIe 分担 0.10 / 0.20 / 0.34 / 0.50 为 69 / 71 / 80 / 85 µs，因为 PCIe 读与 CPU 共用 2 通道 DDR；serve 的 PcieAuto 按 `link / (link + 1.85 × pool 速度)` 调整（实测停在 0.20～0.30，不是此前写的固定 0.20，系数取自别的机器。再按“省下的关键路径时间 / 字节”选驻留专家、adaptive tier 成本治理。v2 包 `plans/P03_RESIDENCY_AND_SCHEDULING.md` 为设计参考。
5. NP-1（VNNI 无 VBMI 内核）：**#3871 已完成，维持低优先级**。nt≈1.2 时 10 种格式组合按整 expert 已达带宽的 81～98%；但 NP-3 trace 显示引擎里 gate/up 阶段单独受计算限制（25～27.5 GB/s，down 为 33.5），更快的 i-quant gate/up 内核理论上可省 CPU 专家时间的 10～13%。工作量大，排在 NP-RES、#3307、#4040 之后。
6. NP-4（跨层预取）、NP-5（kernel 融合）、NP-7（窗口成本含专家并集，与 O33 合并）：研究级，排在上面之后。
7. 低优先级（本用法）：NP-11（公共前缀持久化，只影响重启后首请求）、NP-9 / NP-10（冷 prefill）、NP-2（THP 已覆盖 85%，关闭）。
8. 需用户单独批准：CFG-UNLOCK（只影响冷长 prefill，本用法下更低）。

**不在范围**：任何硬件更换或 BIOS 改动（CFG-UNLOCK 不换硬件、不刷 VBIOS，作为需单独批准的整机配置列入）；`STRATA_STAGE_PIN`、`STRATA_ROUTE_RESIDENT`；改变数值语义的近似计算（如 #2690、#3545 一类）。thinking 用 `xhigh` 是很大的 decode 杠杆，但影响回答质量，属于产品决策，不作为性能实验项。

## 9. 交付

每个 NP 项在 `workspace/state/np-N/` 交付 `PORT_AUDIT.md`（或设计说明）、`IMPLEMENTATION_PLAN.md`、`REVIEW.md`、`DECISION.md`；每个 CFG 项交付两份配置的 sha256、原始日志与对照结论。生产配置的任何改动只以“候选”形式写进 `DECISION.md`，由用户审批。

## 10. 与 v2 包方向图谱的对应（2026-10-26）

v2 包（`../strata_flashnext_4090_extreme_lab_v2/`，GPT Pro，2026-10-25，未连目标机）把空间拆成 64 个方向 O01～O64 和 6 个前置 F01～F06。它不知道用户的单会话用法，也没有 #2253 / #1536 / PT 的实测。下表只列与本包相关的部分；分数是 v2 的工程分，**状态列以本包实测为准**。

| v2 ID | 方向 | v2 分 | 本包对应 | 本包状态 / 去向 |
|---|---|---:|---|---|
| O39 | RAM 准入释放与无效逐出 | 86 | #2253 | 已测：不推荐（本用法） |
| O40 / O13 / O41～O43 / O59 | slot 淘汰、拷贝配额、增量快照、SSD 快照、并发调度 | 58～71 | — | 多会话 / 并发才有收益，降为低优先级 |
| O01 / O02 / O03 / O05 | CPU pool 切分、阶段流水、亲和性、多 token 解包 | 70～83 | NP-3 | 第一个代码方向，[plans/NP3_CPU_POOL.md](../plans/NP3_CPU_POOL.md) |
| O04 / O06 | 4216 专用 VNNI 内核、预打包布局 | 60～68 | NP-1 | #3871 已测：nt≈1.2 时已近带宽上限，暂缓 |
| O07 / O08 / O09 | 按收益选驻留专家、三路成本调度、overlap / async 治理 | 74～77 | NP-RES、CFG-ADAPT | O07 / O08 已完成：CFG-PCIEFRAC、`STRATA_PCIE_BALANCE`（上游逐层版 O08）都低于门；O07 每 MB 成本均匀，分析判断 <1%。**O09 2026-10-26 补测完成：NO_BENEFIT**。lag2nw（overlap 关 + LAG=2 + NOWAIT，上游 sm_86 / sm_60 默认）略慢；async（`--adapt-async 1` + LAG=2）持平。overlap 下自适应层在关键路径上只剩约 0.24 ms / 窗口，见 [P2-CFG-ADAPT](../reports/P2-CFG-ADAPT-20261026.md) |
| O10 | PCIe 搬入专家直接晋升 | 50 | #2964 | 不适用（overlap 冲突） |
| O11 / O12 | 预取改进、同窗 expert 去重 | 59～62 | NP-4 | 研究级 |
| O15 / O16 / O17 / O18 | prefill scratch、chunk / CPU share 规划、事件稀疏化、跨 subchunk 复用 | 54～77 | #4039、CFG-CPUSHARE-S、#4005 | CFG-CPUSHARE-S 已完成（4096 采用候选）；#4039 低；#4005（HIP 平台数据）不收 |
| O19 / O20 | GDN chunk、QSA prefill | 57～78 | NP-9 一带 | 冷 prefill，本用法低。2026-10-26 数据：37K 冷读的 GPU 时间线里 GDN 递推只占 4.5%（等专家拷贝占 27.3%），`STRATA_GDN_CHUNKED=1` 就算减半也只省约 2% prefill，不测 |
| O21～O32 | GPU kernel、head / sampler、graph、int8 KV 向量化、split-KV、GDN decode 融合 | 43～69 | NP-5 / NP-6 | O22（MMVQ 表）已测无收益；其余等 NP-3 后重新 profile 再定 |
| O33 / O34 / O35 | spec 成本策略、lookup 长窗、suffix 索引 | 65～75 | CFG-SPECCOST、#4040 | **O33 原先误对应到 CFG-SPEC-S**：O33 指的是上游现成的 `STRATA_SPEC_COST=1`（按实测每行成本选 MTP 窗口长度，代替“草稿概率 ≥ spec-min-p”），CFG-SPEC-S 只测了 `--spec` 宽度。2026-10-26 补测 CFG-SPECCOST：NO_BENEFIT（窗口变短，每窗口 token 同比下降）。#4040 Gate A NO_BENEFIT（可加速部分占 decode 0.8%） |
| O23 / O36 / O38 | draft head 量化、新 draft、树验证 | 44～60 | CFG-MTPQ4、#3322 | MTPQ4 边缘；新 draft 需权重与批准 |
| O37 / O51 | 完整 state checkpoint、多级循环状态检查点 | 63 | #3584 | 单会话主要重读已由 #1536 / PT 解决，低 |
| O44 / O49 / O50 | 统一显存预算、host KV stage、分页 KV | 52～63 | CFG-KVRES、CFG-KVGROW；#3307 / #3281 | **原先只按 prefill 判断（#3307 NOT_APPLICABLE），漏了 decode 侧**：v2 P08-01 / 02 / 05 要求先验证现成的 `--kv-resident`（KV 流式，只留 N cell 在显存，其余放 pinned RAM，腾出的显存给专家缓存）和 `--kv-grow`（KV 按实际用到的 cell 占显存，其余给专家缓存，上下文增长时交还）。生产 KV 全驻显存约 1.55 GiB，约合 900 个专家槽（现 9420 个）。2026-10-26 补测：CFG-KVRES（20480）decode 四组 +2.8%～+4.4% 过门，7～12K 追问每次 +0.26～0.43 s，冷读慢 8～13%，质量（含 4K～123K 检索）与 base 相同，采用，10-26 21:38 写入生产配置并冒烟通过；CFG-KVGROW 未过门（≥65K 无收益） |
| O46～O48 / O52～O57 | 低比特 KV、替代权重、专家裁剪 / 延后、激活稀疏、QSA 裁剪 | 42～72 | — | Q / N 轨道，改变数值或语义；不在默认路线（#2690、#4068、#4046 同理）。O54 里的 route tail skip 在 29 上**默认已开**（rank 7：窗口内每个 token 都排第 8～10 名的未命中专家不搬也不算）；`STRATA_ROUTE_TAIL_SKIP=6` 是直接减少 CPU 专家计算的零代码开关，但会改变输出，要用户先接受“质量换速度”并过质量门才测 |
| O58 | Pi 上下文组织 / 压缩 | 64 | **CFG-PT** | 已测：推荐 PT=0（轮数约 2 倍），待真实 Pi 复核 |
| O60 | API / tokenize / SSE 固定开销 | 66 | #1536 | 已测：重读根因在 tokenize；#1536 候选 |
| O61 / O62 / O63 | allocator / NUMA / pin、LTO / PGO、功耗频率 | 51～65 | CFG-MMAP、CFG-CSTATE | MMAP 不推荐；CSTATE 已上线；LTO / PGO 先看 host 份额（per-layer host 里非 CPU 专家部分约 0.3 ms / 窗口，空间小）。O63：decode 时 SM 已在出厂最高 2745 MHz，无降频原因，无空间 |
| O64 | Ada tensor 限速解锁 | 51 | CFG-UNLOCK | 需批准；本用法收益更低 |

**2026-10-26 复查（用户要求再看一次 v2 包）：** 64 个方向按本机 decode 窗口的实测构成重新过了一遍（GPU 约 60%，分散在每窗口约 2,360 个 kernel 上，最大单项占 GPU 时间不到 9%；CPU 专家约 36%；见 [累计收益汇总](../reports/SUMMARY-GAINS-20261026.md)）。有两处原先对应错了，结论见上表 O33、O44 / O49 两行。按“零代码、不改数值、作用于 decode”筛出来、还没测过的只有 4 个，2026-10-26 停生产补测：CFG-ADAPT（O09 两臂）、CFG-KVRES、CFG-KVGROW、CFG-SPECCOST。其余方向维持原判：GPU kernel 方向（O20～O32）单项上限约 1～2%、工作量 XL；CPU ISA / 解包（O04～O06）在 nt≈1.2 时受带宽限制；多会话 / 并发方向在单会话用法下没有触发条件；Q 轨道（含 tail skip 加深）需要用户先决定是否接受质量换速度。

v2 前置 F01～F06 里本包已具备的：生产 / 资产身份冻结（P0-T1/T2）、MIG、DIAG 窗口分解、perf 可用。仍缺的：正式任务适配器（restricted time-to-success）、park/restore live adapter、allocator env 受控接口、window trace 常驻插桩（见 [测试协议](04_TEST_PROTOCOL.md)）。v2 新增 PR 中不收进本包的：#4031（多会话 slot 自动收缩）、#4002（多卡 staged copy）、#4005（HIP Windows 数据）、#4010（多卡）、#4068（KV 格式，Q 轨道）、#2690（专家延后，Q 轨道）、#4046（格式与本机不符）。
