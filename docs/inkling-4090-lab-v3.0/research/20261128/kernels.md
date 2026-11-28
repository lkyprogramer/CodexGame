# Mirage / TileLang / Basalt × Astral(sm_89) 内核调研报告

日期：2026-11-28。只读研究：未编译、未安装、未跑 GPU；未修改 Astral fork 与 lab v3.0 目录。
证据标记：**[源码 path:line]** 为本次读到的源码事实；**[自报]** 为项目文档/提交里的自报数据（未复现）；**[推断]** 为我的计算或判断；**[待验证]** 为假设。

固定快照：Mirage \`mpk\` ed771bd（\`/root/github/inkling-research/repos/mirage\`）；TileLang 640fdca（v0.1.16，\`.../repos/tilelang\`）；Basalt fork losingle aa69624（\`.../repos/basalt\`）；Astral fork（scratchpad \`fork\`，\`crates/kernels-src/cu/\`、\`crates/model/src/inkling.rs\`）；lab v3.0 \`docs/\`。

---

## 0. 结论速览

1. 方案 §4–§6 的事实性陈述我抽查的部分基本成立（见各节"核对"表），但方案有两处**方向性遗漏**：
   - 它把 **FP8/INT8 KV、重新量化、路由剪枝**整体排除在主线外（方案 §6.6、line 720）。在"可有损、要极致"的新目标下，这些是 Basalt 里对 4090 **收益量级最大**的可借鉴项。
   - 它没有提到 Basalt 的 **bounded wait + sticky abort word**（\`include/basalt/kernels/wait_abort.hpp\`）。任何常驻/跨 CTA 等待实验都应先具备这一安全网。
2. **MTB-03（GU→SiTU→QAct 融合）真实剩余收益小**[推断]：
   - T=1 时 MoE 段已是 GU / SiTU+Q8 / Down / conv_residual 四个 kernel，中间张量只有几十 KiB。
   - 去掉 SiTU 这一个边界约省 1.5–2.5% decode，贴近 3% NO_BENEFIT 线。
   - 值得做的是更大的组合：GU 行配对 + epilogue，加 Down 的 ticket 收尾（吞掉 combine/conv/residual）。合计约 3–5%，per-visit 常驻上限也就 ~11% 的 kernel 间隙量级。
3. Mirage 在 sm_89 上**只能借协议，不能借 kernel**：
   - MoE 任务在 cc 89 直接 \`assert False\`；Inkling 任务全是 sm100 变体。
   - 可借的是：事件计数器带 iteration epoch（graph replay 无需清零）、静态队列的 Kahn 死锁检查，以及 data-as-flag / 定点确定性归约的思路。
4. TileLang 在 sm_89 可用作离线生成器：
   - 可用：mma.sync f16/bf16/fp8、cp.async、T.Pipelined、PersistentTileScheduler（纯索引）、\`T.sync_grid\`→cooperative launch。
   - 不可用：\`T.alloc_barrier\`、TMA、PDL、cluster。
   - 其 FP4 示例的解码**不只是 nibble 0 错**，见 §2.2。

---

## 1. Mirage MPK 在 Ada 上

### 1.1 动态 MPK：机制完整，sm_89 可编译，但模型任务不在 sm_89

| 方面 | 事实 | 出处 |
|---|---|---|
| 调度规模 | \`SCHEDULERS_PER_BLOCK = 4\`；\`MAX_NUM_WORKERS 160\`；TaskId = iteration(32) \| index(32) | [源码 mirage include/mirage/persistent_kernel/runtime_header.h:29-85] |
| shared 预算 | 保留 3 KiB 静态；cc≥86 动态上限 \`99*1024 − reserve\`（≈96 KiB），cc 80 为 163 KiB | 同上 |
| sm_89 走哪套头文件 | ampere 分支 | [源码 persistent_kernel.cuh:47-53] |
| worker / scheduler | worker 128 线程；\`execute_worker\` 961-1256；\`execute_scheduler\` 1258-1527；kernel 入口 1529-1548 | [源码 persistent_kernel.cuh:82, 961-1548] |
| 启动方式 | 普通 launch（非 cooperative），worker / scheduler 分两个 kernel、两个 stream | [源码 persistent_kernel.cuh:1959-2047] |
| 内存序 | 队列用 release/acquire 原子；部分 acquire/relaxed load 的 inline asm 没有 \`"memory"\` clobber | [源码 mpk_atoms.cuh:17-97] |
| 事件 | 计数器目标 = num_triggers × iteration，每轮无需清零 | [源码 persistent_kernel.cuh 事件路径；见 TaskId 编码] |
| 架构编译开关 | 按 cc 产生 flags | [源码 python/mirage/mpk/persistent_kernel.py:365-382] |
| MoE w13 | cc 89 → \`assert False\` | [源码 persistent_kernel.py:2071-2078] |
| MoE w2 | 只有 sm90/sm100 | [源码 persistent_kernel.py:2320-2325] |
| dense linear | 注册 cc 80–89 | [源码 persistent_kernel.py:2448] |
| Inkling 任务 | 注册的都是 sm100 变体 | [源码 src/kernel/graph.cc:556-575] |

判断：
- [推断] 协议部分（任务描述、事件、队列、epoch）与架构无关，可以照搬。
- [推断] **普通 launch + worker 与 scheduler 分两个 kernel** 依赖所有 CTA 同时驻留，启动本身并不保证这一点。
  - 在 4090 上，worker 约 96 KiB smem、一 SM 一 CTA，scheduler kernel 必须挤进剩余资源；挤不下就会 hang。
  - 这与 Basalt 默认关闭软件 grid barrier 的理由同源（§3.1）。
- [推断] mpk_atoms 缺 \`"memory"\` clobber 的 asm，在编译器重排普通访存时有理论风险。照搬时应补上 clobber 或改用 \`cuda::atomic_ref\`。

### 1.2 静态 megakernel 与死锁检查

- [源码 static_schedule.py:41-81] \`check_deadlock_free\` 在"数据依赖边 ∪ 同 SM 队列顺序边"上做 Kahn 拓扑排序，有环即拒绝。twoshot 规划在 84-155，生成启动代码在 377-398。
- [源码 static_megakernel.py:98-135] \`_add_node\` 的文档写明 hang 前提（107-108）。[源码 compiler.py:176-190, 219] 并发组必须落在不同 SM。
- [源码 include/mirage/static_megakernel/config.cuh:25-104] 包含：
  - TW、SMAX；
  - \`RING_BYTES\`（静态环 179200 B）；
  - EVICT hint、REARM、PDL。
- [源码 runtime.cuh:328-342] situ。
- [源码 runtime.cuh:376-500] 原语：
  - \`gq_div\`；
  - \`cnt_add/cnt_wait\`；
  - \`atom_inc_lane0\`；
  - \`red_add_fx\`（int64 定点确定性归约）；
  - \`poll16/rearm16\`（数据即旗标，0xFF 哨兵）。
- 静态路径的任务体用 tcgen05/TMA，**不能移植**。可移植的是规划器、Kahn 检查、计数器协议。

借鉴要点与边界：
- **Kahn 检查**：可作为 Astral 任何"每 SM 静态任务表"的 CPU 端准入器。它是无损工具，sm_89 无关。
- **data-as-flag 哨兵**：0xFF 字节在 F16/F32 中是 NaN，可作"未写入"标记，省去单独的 flag 与 fence。[推断] 但 Q8 码 0xFF = −1 是合法值，**不能用于 int8 平面**，只适用于 F32/F16 中间量。
- **定点归约 \`red_add_fx\`**：能把 split-K 工作区 + 顺序求和换成确定性 atomic，与 K11 相关。[推断] 但它是**数值变化**（定点量化），不是逐位等价，需单列有损/数值实验。

### 1.3 Inkling builder 与 Mini 的差距

- [源码 python/mirage/mpk/models/inkling/builder.py:1-80, 308-695] builder 面向大 Inkling：66 层、hidden 6144、top-6、BF16，任务为 sm100。
- Mini 的情况：
  - 24 物理层 / 48 visit，prelude 6 + core 12×3 + coda 6；
  - hidden 2304、F 1152、128 专家 top-8；
  - NVFP4 + Q8_0 混合权重，attention residual 块混合，跨遍 controller。
- [推断] 对 Mini 来说，builder 只是"如何把一层拆成任务"的参考。Mini 的 loop/bank/controller、NVFP4 解码、sm_89 任务体都要自己写。

### 1.4 能否只抽一个常驻 MoE 片段

[推断] 能，但只抽**协议**：
- 包括事件计数器 + epoch、per-expert 就绪计数、Kahn 检查，约 150–600 行。
- 任务体用 Astral 现有的 NVFP4 GEMV、SiTU+Q8、Down、combine。
- 启动必须 cooperative（Astral 目前没有 cooperative 启动路径，\`crates/kernels/src\`、\`inkling.rs\` 中无 \`cooperative\` 命中）。
- 等待必须有界（§3.1 wait_abort）。
- [待验证] cooperative kernel 能否作为 CUDA graph 节点捕获（CUDA 12.x 的 cooperative launch attribute），需在 12.8 上实测。

### 1.5 方案 §4 核对

| 方案陈述 | 结果 |
|---|---|
| Ada 动态 smem ≈96 KiB | 成立（runtime_header.h:29-85） |
| 静态环 179200 B | 成立（config.cuh） |
| check_deadlock_free 语义 | 成立（static_schedule.py:41-81） |
| Inkling builder 为大模型 | 成立（builder.py） |
| 补充 | moe_w13 在 cc 89 \`assert False\`；moe_w2 仅 sm90/100；Inkling 任务仅 sm100；动态 MPK 非 cooperative 启动 |

---

## 2. TileLang 在 sm_89

### 2.1 能力表

| 能力 | sm_89 | 出处 |
|---|---|---|
| mma.sync f16/bf16 | 可（AllowAmpereMMA） | [源码 src/cuda/op/gemm.cc:146-189, 410-438] |
| mma.sync fp8 (e4m3/e5m2) | 可，要求 sm89 | [源码 gemm.cc:146-189] |
| cp.async + \`T.Pipelined\` | 可（不依赖 mbarrier 的多级流水） | [源码 tilelang/cuda/pipeline.py] |
| \`T.alloc_barrier\` | **sm90 以下拒绝** | [源码 pipeline.py:182-195]；\`have_mbarrier\` 仅 sm90+ [源码 tilelang/contrib/nvcc.py:637-680] |
| TMA / PDL | 不可（\`have_tma\`、\`have_pdl\` 要求 major≥9） | [源码 nvcc.py:637-680；pipeline.py:244] |
| PersistentTileScheduler | 可，纯索引 grid-stride + L2 swizzle；\`cluster_size\` 在 sm_89 只能 1 | [源码 tilelang/language/tile_schedule.py:93-160] |
| \`T.sync_grid\` | 可，lowering 后改用 \`cudaLaunchCooperativeKernel\`，且断言不与 cluster 同用 | [源码 tilelang/language/builtin.py:1188-1190；src/cuda/transform/persist_threadblock.cc:19-49；tilelang/jit/adapter/wrapper.py:386-398] |
| AOT 导出 | \`export_sources\` 633、\`export_ptx\` 871、\`export_sass\` 933、\`export_library\` 800 | [源码 tilelang/jit/kernel.py] |

补充说明：
- [源码 kernel.py:668-669, 894-895, 956-957] 导出失败只 \`logger.error\`、不抛异常。方案 §5.4"要检查文件存在/非空/hash"成立。
- [推断] 对 Astral 而言，TileLang 的正确用法是：离线生成 sm_89 的 \`__global__\` CUDA 源，再纳入 \`crates/kernels-src\` 构建。cooperative 的需求要写进 manifest（方案已有）。

### 2.2 量化示例核对（方案 §5.5）

**fp4 hopper 示例** [源码 examples/dequantize_gemm/example_dequant_gemm_fp4_hopper.py:10-41]：
- \`_tir_u8_to_f4_to_f16\` 的做法：\`e_f16 = e_f4 + 14\`，\`m_f16 = m_f4\`，没有 e_f4 == 0 的特判（:28 那行被注释掉）。
- nibble 0 → 位型 \`14<<10\` = 0x3800 = **0.5**（标准 E2M1 为 0）。方案说法**成立**。
- [推断，按源码位运算] nibble 1 → 0x3800|0x200 = **0.75**（标准为 0.5）。nibble 8/9 对称地得到 −0.5/−0.75。即**两个次正规码都错**，方案只提了 0。
- 自测参考 \`torch_convert\`（:32-41）用的是**同一公式**，所以 \`test_fp4_fp16_convert_close\`（:77-92）总能通过，测不出这个错误。该示例的 GEMM 路径（:66, 162, 206）同样受影响。

**新版 \`quantize/nvfp4.py\`**：
- 显式 LUT 是正确的 E2M1 值表 [源码 :14-34, 159-176]。
- UE4M3 scale 解码 \`& 0x7F\` [源码 :61-76]。
- 布局工具是 **SM120 BlockScaledBasicChunk K-major** [源码 :8-12, 216-312]，不是 sm_89 布局。

**int4 GEMV 示例** [源码 example_dequant_gemv_fp16xint4.py:162-170, 217]：FP16 累加，\`atol=1e3, rtol=1e-1\`，unsigned 源格式。方案说法成立。

结论：TileLang 量化示例不能当数值参考。Astral 的真值仍是现有 loader 解码 + selftest 的 16 码表与 scale 编码全量测试。

### 2.3 方案 §5 核对

| 方案陈述 | 结果 |
|---|---|
| alloc_barrier pre-sm90 拒绝 | 成立 |
| fp4 nibble 0→0.5 | 成立 |
| int4 示例宽容差 | 成立 |
| 导出吞异常 | 成立 |
| sync_grid 需 cooperative | 成立（方案 line 240） |
| 补充 | nibble 1→0.75；自测参考同错 |

---

## 3. Basalt（losingle fork）

### 3.1 HIP 移植里的经验

| 主题 | 事实 | 出处 |
|---|---|---|
| CUDA 目标 | 仅 sm_120/121 | [源码 cmake/target_arch.cmake] |
| 小批分派 | \`BASALT_DECODE_SOA_DENSE_MAX_T=4\`，T=8 走 \`native_q80_mma\` | [自报 docs/rocm-gfx1201.md；源码 session.cpp:1004-1068 env 默认值] |
| GU + softcapped SwiGLU + q8_1 epilogue | 32 行/CTA：一个 CTA 同时算 gate 与 up 的同号行，激活与 q8_1 量化在 epilogue 完成 | [源码 src/models/inkling2/kernels/inkling2_nvfp4_hip.cu:1078-1235] |
| 激活函数 | "softcapped SwiGLU" = Astral/Mirage 的 SiTU：β·tanh(g/β)·σ(g)·lb·tanh(u/lb) | [源码 Mirage runtime.cuh:328-342；Astral inkling.cu:881-892] |
| DSpark PERSIST | 默认关 | [源码 dspark.cpp:147-153] |
| DSpark FUSE_STEP_FINAL | 默认关，注释："avoids non-cooperative software grid barrier + process-global g_ds_step_final_sync deadlock hazard" | [源码 dspark.cpp:163-170] |
| PERSIST 关掉后走什么 | 默认走"Wave B6"专用 kernel 组（128-CTA SoA top-64 等） | [源码 dspark.cpp:1771-1773] |
| 软件 grid barrier | \`grid_barrier_agent\` 在 64 CTA 上做非 cooperative 的软件栅栏 | [源码 dspark.cu:1816-1831, 2243, 2262, 2462]；\`g_ds_step_final_sync\` 为进程全局 [源码 dspark.cu:2699, 3998-4017] |
| 有界等待 | 跨 block 等待超过界限后写 sticky word 并放行（结果作废，context 保持可用），host 每个窗口后读 word，失败即停 | [源码 include/basalt/kernels/wait_abort.hpp:1-60]：\`kWaitPollNs\` 1 ms；code 编码 who/kind/line/block |
| buffer 生命周期 oracle | 符号化前向：每个 visit 输出一个不同符号，"每次复制"的参考与 8 个具名复用 buffer 的执行顺序逐步比对 hid / blocks / bank | [源码 walk.hpp:1-30；walk_test.cpp:1-60] |
| 长上下文 split | split span 只由行自身的 (n, window) 决定（与批内其他行和 launch 无关）：短 16/32，64 的倍数；SWA 最多 63 split，全局 64，≥32K 可到 256 | [源码 kernels/attn.cu:41-43, 127-147] |
| split 合并 | HIP 有 \`FUSE_COMBINE\`：自复位的 agent-scope 计数器，最后到达的 split 负责合并，不需要 memset，可 graph replay | [源码 attn.cu:681, 691-760, 2498] |
| split 合并（CUDA） | 用 cluster（\`kClusterSplits=8\`）做 DSMEM 合并，sm_90+ | [源码 attn.cu:2211-2215] |
| 有损路由 | \`moe_tail_tau\`：rank≥tail_rank 且权重 < τ·w0 的专家丢弃；singleton：仅批内 ≥2 行时，丢弃只被 1 行使用、且权重 < τ·w0 的尾部专家；之后重新归一化 | [源码 kernels/ops.cu:907-990]；默认 τ=0（关）、rank 5 [源码 session.cpp:5064-5068] |
| 有损路由收益 | flash verify 14.126→13.074 ms（+12.6%），singleton 0.35 + rank 6，KL +0.00279，30/30 eval | [自报 docs/rocm-gfx1201.md:129，RDNA4] |
| KV dtype | fp16 / int8（每 64 通道一个 FP16 scale，行 144 B）/ fp8（E4M3、单位 scale，行 128 B） | [源码 prep.cuh:145-148；自报 docs/precision/inkling2.md:58-66] |
| KV dtype 质量 | 5090，DQ8 pack，100×512：KLD fp16 0.00304 / fp8 0.00452 / int8 0.00343；top-1 97.81 / 97.04 / 97.47% | [自报 precision/inkling2.md:111-113] |
| INT8 KV 深层对比 | 131K × 8 段：TC reader 对 scalar 的 dNLL +0.0024±0.025 | [自报 precision/inkling2.md:84-100] |
| batch test 容差 | 非 STRICT 时 greedy 允许偏离，log-prob 差 ≤0.35 | [源码 kernels/batch_decode_test.cpp:98-101] |
| NVFP4 repack | \`& 0x7F\` 且 0x7F→0，非无条件可逆 | [源码 inkling2_nvfp4_hip.cu:189-190, 246-247, 270] |
| 嵌入表放主机 | token embedding（BF16 0.86 GiB）留在 page-locked RAM，卡上按行 gather | [自报 docs/models/inkling2.md:44-45] |
| 复制草稿 | 上下文中出现 ≥3 token 的重复时取复制草稿，与 DSpark 按期望 tok/ms 竞争；2,405 token 的复制 prompt decode 快 13% | [自报 docs/models/inkling2.md:186-193；策略在 include/basalt/spec/draft_policy.hpp，未读] |

关于 PERSIST 默认关的原因：代码只给 FUSE_STEP_FINAL 写了理由。[推断] PERSIST 用的是同一种非 cooperative 软件栅栏（dspark.cu:1816），并且已被 B6 专用 kernel 取代成为默认路径。理由应是"共驻风险 + B6 已更快"，但源码没有明说。

### 3.2 CUDA 主线（sm_120）逐项能否移到 sm_89

| 组件 | 用到的指令/特性 | sm_89 | 与 lab 重叠 |
|---|---|---|---|
| \`src/kernels/cuda/expert_tile.cuh\` | 配对 gate/up CTA + 激活 epilogue + f16 H；f16/bf16 mma、cp.async；NVFP4 解码用 \`cvt.rn.f16x2.e2m1x2\` | 除 e2m1 cvt（sm_100a/120a）外都可用；e2m1 改为 LUT/prmt 软件解码（Astral 已有 table16，gemv.cu:1162-1255） | MTB-03、K1、v3.0.14 后置"gate/up 与 SiTU epilogue 融合" |
| \`src/models/inkling2/kernels/experts.cu\` 的 ticket finish | 原子 ticket + threadfence，"最后完成的 block"做 Down 后的 combine/conv/residual，确定性；\`kSmallPairs=128\` | 可用（只用原子与 fence） | K9（verify 尾融合）；decode 的 conv_residual 边界 |
| 批次不变数值 | 一行的算术与批内其他行、launch 形状无关 | 设计原则，可用 | K5、T20/T25 |
| nvfp4_grouped_mma | s8 mma + mbarrier + \`cp.async.bulk\` | bulk 拷贝需 sm_90，**不可直接移植**；s8 mma 可用 | K6、K10 |
| native_mmvq | s8 mma m16n8k32、cp.async、ldmatrix | 全部 sm_80+，可用 | K2（Astral 已有 dp4a/MMA 双路） |
| attn_mma / attn_prompt | f16 mma、ldmatrix、cp.async | 可用 | K4、T17 |
| attn.cu cluster 合并 | cluster / DSMEM | 不可（sm_90+） | — |
| launch_pdl | griddepcontrol | 不可（Astral 的 PDL_WAIT 在 sm_89 是空操作 [源码 inkling.cu:17-22]） | — |
| dspark.cu | dp4a、s8 mma；2-bit 筛选 head | 可用 | T26（已判无收益） |
| FP8 KV 写入 | \`__nv_fp8_e4m3\`（\`cvt.rn.satfinite.e4m3x2.f32\`） | 可用（sm_89 起） | lab 06 §4（KV 压缩暂缓）、T17、T28 |
| iq_kernels.cu / gu2.cuh | IQ1_S…IQ4_XS 的 GU GEMV，用 funnelshift、prmt、__ldg | 可用，但形状写死 n_embd 2560/5120 [源码 gu2.cuh:1-3]，2304 需改 | T31（GSQ-RCO 低位） |

### 3.3 方案 §6 核对

| 方案陈述 | 结果 |
|---|---|
| CUDA 仅 sm120/121 | 成立 |
| DENSE_MAX_T=4 | 成立 |
| DSpark 两开关默认关、死锁注释 | 成立 |
| \`scale & 0x7f\` | 成立 |
| batch test 0.35 / STRICT | 成立 |
| walk_test oracle | 成立 |
| B22/B23 数字与 50/54 ctest | 成立 |
| Q8 SoA 额外 1.10 GiB | 本次**未复核** |
| **方向性问题** | §6.6 / line 720 把 FP8 KV、重新量化排除在外，不符合新的"可有损、极致"目标，应移入独立的有损轨道（§5 第 1、2 项）；有损路由剪枝、wait_abort、复制草稿、嵌入表放主机未被提及 |

---

## 4. Astral 对照：MTB-03 的真实剩余空间

### 4.1 现状（T=1 decode 每个 MoE visit）

[源码 crates/model/src/inkling.rs:1895-1998] 每个 visit 依次是：
1. \`launch_q\`（GU，NVFP4/Q8 GEMV，输出 gate‖up）
2. \`astral_ink_situ_q8\`（SiTU + Q8 量化，已融合）[源码 inkling.cu:881-892；启动 crates/kernels/src/inkling.rs:867-874；q8_store inkling.cu:582-590]
3. \`launch_q\`（Down）
4. \`conv_residual\`（combine + conv + residual，已融合）

所以每个 visit 是 **4 个 kernel**，每步共 48 个 visit。

中间张量（[源码 inkling.rs:590-668 Scratch；ops.rs:535-560 QAct]，T=1、8 个专家）：

| 张量 | 尺寸 | 计算 |
|---|---|---|
| gu（F32） | 72 KiB | 8×2304×4 B |
| SiTU 后的 Q8 q | 9 KiB | — |
| Q8 d | 1.1 KiB | — |
| f16 平面 h | 18 KiB | T=1 不读 |
| Down 输出 y（F32） | 72 KiB | 8×2304×4 B |

[[推断] 这些都远小于 L2（72 MiB）。融合**省不了 DRAM 流量**，只能省 kernel 边界（启动、ramp/tail、间隙）。]

### 4.2 量化估计

依据 [自报 lab 07_tasks.md:113，T16 第 1 轮，fork 9593eb4]：
- 1K decode 每步约 799 个 kernel，GPU 忙碌 7.16 ms；
- 专家 GEMV 占 26.5%（每步 88 次）；
- 其余小 kernel 约 22%，kernel 间隙约 11%。

各方案的估计，全部为 [推断]：
- **每个边界的平均代价**：11%×7.16 ms / 799 ≈ 1 µs 间隙，再加小 kernel 自身的 ramp/tail 约 1–2 µs，合计约 2–3 µs。
- **MTB-03 只去 SiTU 一个边界**：48 × 2–3 µs ≈ 0.1–0.15 ms，约 1.5–2.5%。另外 GU 要先做行配对才能在 epilogue 里拿到同号 gate/up，见下。
- **配对 + epilogue，再加 Down 的 ticket 收尾**（吞掉 conv_residual）：每 visit 4→2 个 kernel，省 96 个边界，约 3–5%。
  - verify（T=2–8）还额外合掉 \`moe_combine_t\` 与 \`conv_res_par\`，即 K9。
- **per-visit 常驻 MoE**（cooperative，GU→Down 用 per-expert 计数）：上限受 kernel 间隙与小 kernel 尾部份额约束，约 11–14%；现实约 3–6%。
  - 原因：grid barrier 本身就要约 2–4 µs，与 graph 内的 kernel 边界同量级；只有按专家粒度的数据流重叠才有净收益。
- 专家 GEMV 本身已到约 830 GB/s [自报 T16 带宽推断]，融合不会让权重读取变快。

### 4.3 GU 行配对是前置条件

- [推断] Astral 的 NVFP4 GEMV（[源码 gemv.cu:1162-1255] \`gemv_fp4_smem\`，带 no_allocate 流读与 table16 解码）按行独立计算。gate 行 j 与 up 行 j+1152 落在不同 warp/CTA。
- 要在 epilogue 里算 SiTU 并做 32 元素 Q8 块量化，需要在加载时把 gate/up 行**交错重排**，使一个 CTA 拿到连续 32 对。
- 这是**无损布局变换**：行置换，累加顺序不变，可做到逐位一致。

---

## 5. 排序清单（对 4090 上的 Astral，价值从高到低）

| # | 做什么 | 损失性 | sm_89 / 指令 | 与 lab 重叠 | 收益量级与依据 | 验证 |
|---|---|---|---|---|---|---|
| 1 | **全局层 KV 改 FP8（E4M3、单位 scale）或 INT8（64 通道一个 FP16 scale）**；可选 TC reader（INT8 码先转 f16，按组在累加后乘 scale） | 有损 | 可用：\`cvt.rn.satfinite.e4m3x2.f32\`、\`cvt.rn.f16x2.e4m3x2\`、可选 fp8 mma m16n8k32 | lab 06 §4（目前暂缓）、T17、T28（可叠加）、R4 | [推断] 全局层 KV 32→16 KiB/位置（INT8 为 18 KiB）。128K 时每 token 约 4 GiB KV 读，按约 900 GB/s 约 4.8 ms，砍半后 13.6→约 11.2 ms，即 **64K–128K decode 约 +15–25%**；KV 容量约 2×（132K→约 250K）。前提：Astral 的 K 已 L2 clip [源码 inkling.cu:75-77, 618]，V 已 per-head RMSNorm（lab 06 §4）。质量 [自报 Basalt 5090] KLD +0.0015（fp8）/ +0.0004（int8） | 先实测 K/V 存储后的分布与 E4M3 饱和率；W1 c512×8 KLD/top-1；T25 E 集 num-4L；131K/400K needle；T28 的 shadow 复用 |
| 2 | **有损专家剪枝**：尾部 τ（rank≥r 且 w<τ·w0）+ verify 批内 singleton 剪枝，剪后重新归一化 | 有损 | 可用，纯路由改动 | R3、R8、T35；DSpark 接受率（T21） | [推断] decode 平均少 1–2 个专家 → 26.5%×12.5–25% ≈ **+3–7%**；verify 的专家并集缩小更多，[自报 Basalt RDNA4] verify +12.6%，KL +0.0028 | 扫 τ/r/singleton；KLD、num-3、任务正确率；记录 DSpark 接受率变化；对照 R3 的 8/9 名 margin |
| 3 | **MoE 链融合**：GU 行交错 + SiTU/Q8 epilogue（即 MTB-03），再加 Basalt 式 ticket 收尾（Down 的最后一个 block 做 combine+conv+residual；verify 时吞掉 K9） | 无损（累加顺序不变时可逐位一致） | 可用：原子 ticket + threadfence；不需要 e2m1 cvt | MTB-03、K9、K3、v3.0.14 后置项 | [推断] 单 SiTU 边界 1.5–2.5%；两处合计 **3–5%**；数据量很小（§4.1） | 先 MTB-03 单项，过 3% 线再加 ticket；逐位比对 + G2 + T20/T25 |
| 4 | **常驻实验的安全底座**：cooperative 启动（driver API）+ Basalt 有界等待 / sticky abort word + Mirage Kahn 检查 + epoch 计数器（replay 无需清零） | 无损（基础设施） | 可用（cooperative launch 自 sm_60 起支持）；[待验证] graph 捕获 cooperative 节点 | MTB-06、T30、§1.4 | 自身无收益；第 3 项进阶（per-visit 常驻，上限约 11–14%，现实 3–6%）的前提 | 故意让一个 CTA 不驻留或缺一次 commit，应得到"窗口失败"而不是 hang；Kahn 检查用注入环的负例测试 |
| 5 | **split attention 的 combine 融合**（最后到达的 split 合并，自复位计数器）+ **按行决定的 split span** | 无损（合并顺序固定） | 可用：agent-scope 原子 | K4、K5、K11 | [推断] 每步省最多 48 个 combine 边界，短上下文约 1–2%；span 按行决定后 verify 行与 decode 行同算术，便于解释 K5/T20 差异 | 同 key 数下单行与 verify 窗口内的行逐位比对；graph replay 多次 |
| 6 | **复制草稿**：上下文 ≥3 token 重复时取复制草稿，与 DSpark 按期望 tok/ms 选择 | 无损（target 全验证） | 可用，平凡 | T21、R7（lab 中无 n-gram/lookup 条目） | [自报 Basalt] 复制型 prompt +13%；对新写散文约 0 | T21 协议加代码编辑 / RAG 类负载；输出与贪心一致 |
| 7 | **token embedding 移到 pinned host**，卡上 zero-copy gather | 无损 | 可用 | T17 容量 | [推断] A1 的 token_embd 为 Q8_0 [lab 01_model.md:87]，约 0.49 GB → FP16 KV 下多约 15K 位置，FP8 下多约 30K；每 token 的 PCIe 读 2.4 KB，延迟约 µs 级 | 容量记录；decode 时间 A/B |
| 8 | **TileLang 作离线生成器**，只用 mma.sync / cp.async / Pipelined / sync_grid | 无损 | 见 §2.1 | K1、K6、K10 | 工具价值；不能拿示例当数值参考 | 生成 CUDA + manifest，纳入 sm_89 构建，selftest 16 码全量 |
| 9 | **Mirage 定点确定性归约**替换 split 工作区 + memset | 有损（数值变化，确定性） | 可用：int64 原子 | K11 | [推断] 小，每个 split 点省一次 memset 与一次求和 kernel | 与现有 F32 顺序求和对比误差分布；重复运行逐位一致 |

不建议投入：
- Mirage 动态 MPK 整体搬运：模型任务不在 sm_89，且非 cooperative 启动。
- Basalt nvfp4_grouped_mma：依赖 \`cp.async.bulk\`。
- cluster 合并、PDL。
- Basalt Q8 SoA 双份权重：显存。
- IQ kernel 仅在 T31 判定低位 GGUF 值得做时才参考。

---

## 6. 未覆盖与风险

- 第 1、2、3、5 项的收益全部是按 T16 旧快照（fork 9593eb4，K2 撤回前）的份额推算的。当前 fork 的热点份额需要先用 nsys 重测。
- Basalt 的数据全部是 5090 / RDNA4 自报。质量数据大多是 512 短上下文，长上下文只有 INT8 reader 有深层对比。
- 本次未读：\`draft_policy.hpp\`、Basalt \`model.cpp\` 的 Q8 SoA 显存细节、Mirage OSDI 论文（以源码为准，未下载）。
- 未新增克隆或下载；只用已有的浅克隆。
