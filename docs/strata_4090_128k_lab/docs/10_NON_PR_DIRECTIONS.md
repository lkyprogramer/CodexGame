# 非 PR 方向：29 号机的性能空间

本文件记录不依赖任何上游 PR 的优化方向，来源是 2026-10-23 对 29 生产日志、`/proc`、sysfs 和上游源码（冻结 main `5c8dd322` 与部署树 0.1.43.1）的只读调研。它和 PR 实验项并列，但**不进入 `config/experiments.json`**：配置类方向按 `CFG-*` 对照执行（规则同 [测试协议](04_TEST_PROTOCOL.md)“配置与诊断对照”），代码类方向按 `NP-*` 独立立项，流程沿用 PR 项的 Phase A～E 与 Gate。

所有数字标明性质：**事实**＝日志或源码直接可见；**估算**＝由事实推算，未实测；**假设**＝待验证的解释。

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
- **CFG-LOOKUP**：suffix drafter（前缀查表）默认开启，`--lookup-chain K` 可选。Pi 的 codemode 与 edit 工具调用会大段照抄上下文，适合查表 draft。**未确认**：main 注释写的是 “Greedy verification keeps the output”，需先统计采样请求下 lookup 窗口是否真正发生，再测 `--lookup-chain`。
- **NP-8 · 跨请求后缀树 draft（研究级）**：agent 循环反复出现的工具调用 JSON 框架和样板代码，不在当前上下文里也能预测（SuffixDecoding 类思路）。需要独立的接受率离线评估。

## 7. Prefill（占引擎时间约 20～25%）

- **NP-9 · 直接在量化权重上做 MMQ**：dequant 单独一遍占 9.7%。先确认 main 的 fused prompt-expert 路径在 sm_89 上是否被选中（#3779、#3277 只覆盖 sm_80 / sm_75），再考虑 int8 tensor core / dp4a 版 IQ3_XXS MMQ。
- **NP-10 · 分组搬到 GPU**：host grouping 占 6.6%，改为 GPU 侧排序与直方图。
- **wait copy 24%**：PCIe 是平台上限，只能靠更大 chunk 摊薄，见 #3307 / #3281。
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

## 8. 执行顺序

1. MIG 之后，NP-0 测量。
2. 配置对照（只改启动参数或环境；在 MIG 之后于 A0 上测，不在 0.1.43.1 上重复）：CFG-PROFILE、CFG-MTPQ4 / CFG-DVOCAB、CFG-LOOKUP、CFG-THP 的验证步骤；CFG-CSTATE、CFG-UNLOCK 需用户单独批准（CFG-UNLOCK 排在 MIG、CFG-IL0、#2253 之后）。与 CFG-IL0、CFG-EXACT、CFG-MMAP 一样，在 PR A/B 之前定论，通过的才进入公共基线。
3. 中等代码：NP-1、NP-2、NP-3。
4. 较大代码：NP-4、NP-5、NP-9、NP-10。
5. 远期：NP-8、persistent megakernel。

**不在范围**：任何硬件更换或 BIOS 改动（CFG-UNLOCK 不换硬件、不刷 VBIOS，作为需单独批准的整机配置列入）；`STRATA_STAGE_PIN`、`STRATA_ROUTE_RESIDENT`；改变数值语义的近似计算（如 #2690、#3545 一类）。thinking 用 `xhigh` 是很大的 decode 杠杆，但影响回答质量，属于产品决策，不作为性能实验项。

## 9. 交付

每个 NP 项在 `workspace/state/np-N/` 交付 `PORT_AUDIT.md`（或设计说明）、`IMPLEMENTATION_PLAN.md`、`REVIEW.md`、`DECISION.md`；每个 CFG 项交付两份配置的 sha256、原始日志与对照结论。生产配置的任何改动只以“候选”形式写进 `DECISION.md`，由用户审批。
