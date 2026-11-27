# 04 · Astral fork 与 sm_89 移植

上游：`syntheticminds-lab/Astral-Inference-Server` @`49a0a2bee3270ad7518cebe7a059496b250180d1`（S10）。fork 是独立公开仓库 `lkyprogramer/inkling-4090-engine` 的 `main`（S30；早期的分支名 `inkling-4090` 已不用）。§2 的文件和行号指上游这个 commit；v3.0.14 新增的几行指 fork 当前代码。

## 1. 代码地图（只列本项目会碰到的部分）

| crate | 关键文件 | 作用 |
|---|---|---|
| `core` | `src/arch.rs` | 架构档案表，只用于报告和测试 |
| `gpu` | `src/lib.rs`、`sys.rs` | 运行时 dlopen `libcuda.so.1`，不链接 CUDA 运行库；PDL 开关；动态共享内存属性 |
| `kernels-src` | `build.rs`、`cu/*.cu` | 逐个 `.cu` 编成 fatbin，对每个 `ASTRAL_CUDA_ARCHS` 目标使用 `-gencode arch=compute_X,code=sm_X`；可用 `NVCC`、`ASTRAL_NVCC_DEFINES` |
| `kernels` | `src/ops.rs`（GEMV/GEMM）、`src/inkling.rs`（注意力、mix、路由、conv、controller）、`src/dspark.rs`、`src/reference.rs` | 启动器与 CPU 参考实现 |
| `loader` | `src/lib.rs`（GGUF）、`src/inkling_checkpoint.rs`（原生 safetensors 转 GGUF 布局） | 模型加载 |
| `quant` | `src/lib.rs` | GGML 类型表与 NVFP4 重排；kernel 的“真值” |
| `model` | `src/inkling.rs`（`Config`、`Weights`、`Session`、`forward`、`layer`）、`src/dspark.rs` | 前向与投机解码；**循环研究主要改这里** |
| `testing` | `selftest.rs`、`golden.rs`、`kbench.rs` | 验证与基准 |
| `cli` | `src/main.rs` | `hw`、`selftest`、`gguf-info`、`verify-embd`、`verify-model`、`score`、`generate`、`spec-generate`、`cmp-prefill`、`serve`、`kbench`、`version` |

工具链要求：`rust-toolchain.toml` 固定 1.100.0；安装文档要求 nvcc ≥ 12.8；运行时只依赖驱动。

## 2. sm_89 现状（静态阅读结论）

| 位置 | 事实 | 对 4090 的影响 |
|---|---|---|
| `crates/core/src/arch.rs:78` | `from_compute_capability` 不含 (8,9)；第 249–250 行的测试断言 (8,9) 返回 None | `astral hw` 会报 profile 为 null；**不阻塞运行** |
| `crates/hw/src/lib.rs:116` | profile 只用于填充报告字段 | 同上 |
| `crates/kernels/src/lib.rs:38-44` | fatbin 中没有当前 GPU 可用的 SASS 时，加载报 209，并提示重新设置 `ASTRAL_CUDA_ARCHS` | 构建 `89`（sm_80 的 SASS 也能在 8.9 上运行，可用于二分定位） |
| `crates/gpu/src/lib.rs:204` | PDL 只在 cc ≥ 9 启用 | 4090 上没有 PDL；依靠 CUDA graph 摊薄 launch 开销 |
| `crates/kernels/src/ops.rs:902` | wgmma 只在 cc = 9 且构建含 90a 时启用 | 4090 上 Inkling 的预填走 `Gemv::launch_mma`（`mma3` 系列，`mma.sync`）；`launch_mma5` 的 fragment 路径没有接入 Inkling 模型（2026-11-26 按评审核实源码后更正，原文误写为 `mma5`） |
| `crates/kernels/src/ops.rs:1131` | `launch_q` 的共享内存超过 48 KB 就报错 | sm_89 的静态共享内存上限同样是 48 KB，无变化 |
| `crates/kernels-src/cu/inkling.cu` | `#define MAX_CTX 8192`；`logit[MAX_CTX]`（32 KB 静态共享内存）只在 simple / reference 路径 `attn_decode` 里（`head_dim ≠ 128`、`n_rel > 32` 或设了 `ASTRAL_ATTN_SIMPLE` 时才走）。**Inkling 默认形状走 `attn_decode_split`**：split-K 分块 online softmax + merge（decode 每 split 一个 chunk；verify 小批限 split 数、每个 split 循环多个 chunk；大 prefill 走 `attn_prefill`）。另有多处 `min(capacity, MAX_CTX)` 钳位（第 365、952、1041、1125、1150、1445 行附近） | 8192 上限真实存在，但分散在四处：Rust 启动参数检查、CUDA 内的多处钳位、simple 路径的静态共享内存、Session 的缓存分配与位置管理。只删 Rust 检查会留下 CUDA 截断；只加大 `MAX_CTX` 会撑大 simple 路径的共享内存（v3.0.7 按评审核实后更正：原文把 simple 路径当成了解码主路径） |
| `crates/kernels/src/inkling.rs:408,912,1221` | 注意力启动器检查 capacity ≤ MAX_CTX、head_dim 128、`n_rel` 上限 | 同上 |
| `crates/model/src/inkling.rs` `Session::new`（第 519 行检查 capacity ≤ `MAX_CTX`） | 48 个 slot 的 K/V 都按完整 capacity 分配（f16） | 见 [01](01_model.md) §3 |
| `crates/model/src/inkling.rs` `layer` | `attn_prep` 先把本批 `ntok` 个 token 的 K/V 全部写进缓存，再调用注意力；V 的写入路径是 short conv → 不带可学习 gain 的 per-head RMSNorm → F16 | 做 SWA 环形缓冲时，同批早期 query 需要的行可能被同批后写的行覆盖（WP-D） |
| `crates/loader/src/inkling_checkpoint.rs:282,473` | MXFP8 转 Q8_0；要求 `model_type == inkling2_loop` | varloop 原生 checkpoint 预计可直接加载（P5 前验证） |
| kernel 类型 | GEMV/GEMM 入口只有 f32 / bf16 / q8_0 / nvfp4（另有 Qwen 用的 mxfp4） | 只能用 A1 这类 NVFP4 + Q8_0 文件 |
| fork `crates/model/src/inkling.rs` `forward`（v3.0.14 核实，方案 10 §4.1） | slot 编号：prelude、core 第 1 遍、coda 的 slot 等于物理层（0–5、6–17、18–23）；core 第 2、3 遍是 24–35、36–47。visit 是执行顺序，coda 是 visit 42–47 却用 slot 18–23。DSpark 的 taps `[5,23,41,48]` 按 visit 计数，在进入该 visit 前取，48 是最终 norm 之后 | slot、物理层、visit 三者不能混用；改遍数后 taps 的数字不能照搬（T23） |
| fork `crates/kernels/src/ops.rs` `QAct::with_f16` / `Gemv::quantize` / `launch_mma`（v3.0.14 核实） | FP16 平面分配时清零；`quantize` 只写 q / d；`launch_mma` 在 n、k 为 64 的倍数且未设 `ASTRAL_MMA_INT8` 时读 FP16 平面。生产路径的 `rms_q8`、`gate_q8`、`situ_q8` 会写 FP16 平面 | “内存已分配”不等于“数据有效”：只经过 `quantize` 的激活喂给 MMA3 会算出零（T22） |
| fork `crates/model/src/dspark.rs` `Spec::new` | 草稿 K/V 为 FP32，3 层（layer 0、2 为 local，窗口 1024；layer 1 为 global），每层按 capacity + block + 8 行全长分配：约 24 KiB / token | 128K 时约 3.0 GiB，是开 DSpark 跑 128K 能否放下的关键项（[01](01_model.md) §3，T17 / T21） |

推断：4090 上首次构建、selftest 和 `verify-model` 很可能不需要改代码就能通过；需要改的是性能和上下文长度。这是推断，由 T07/T09 验证。

## 3. 工作包

| WP | 内容 | 对应任务 | 完成判据 |
|---|---|---|---|
| A 上卡 | 构建 `ASTRAL_CUDA_ARCHS=89`；新增 `ArchProfile::Sm89`（family F80，`sm_target` "89"，`cp_async`、int8 TC、FP8 TC 为 true，fp4 为 None），更新第 249 行的测试 | T05、T07、T11 | selftest 全部 PASS；`astral hw` 输出 `sm89` |
| B 观测 | 新增 `ASTRAL_TRACE=<path>`。按 [06](06_loop_research.md) §3 的探针表，只在选定 token 与块边界记录 block / 块 mix / 跨遍消息 / controller / 路由 / 注意力质量 / 读出；坐标用 `(token_position, physical_layer, pass, logical_visit, stage)`；按位置批量取回，不在每个算子后同步，不删 d17a519 的同步 | T15 | 三项对照：探针关闭时与基线逐位一致；开 / 关的数值差异可解释；graph / eager 差异单独报告。性能数据只取关闭探针的正式模式 |
| C 调优 | 先做分阶段基线和热点表（T16 第一步），再按下面 K1–K7 的顺序每次只挑一个候选；工具用 CUDA event、`kbench`、nsys。性能计数器没有权限就记 N/A，**不为 profile 改驱动配置** | T16、T21 | G3；G2 不回退 |
| D 长上下文 | 四段，顺序不能换：① SWA 环形缓冲，在 8K 内验证绝对位置、窗口包含关系与回滚（只存写指针不足以恢复被覆盖的旧值，要按最大未提交长度留余量或保存撤销数据）；同批写入的覆盖问题见下；② 扩展**已有**的 split attention，把有效长度、物理 capacity、绝对 token 位置分开，逐处检查 `MAX_CTX` 钳位、索引类型、scratch 大小和 graph 捕获；③ 长 prefill 分块与参考对照（relative bias、全局位置缩放、sink、门控、短卷积）；④ 16K → 32K → 64K → 128K，每级记峰值显存与时间 | T17 | G4；§5 的边界用例全部通过 |
| E 循环控制 | 遍数可配置（`--passes`，或解析 varloop 配置）；跨遍 KV 策略开关（[06](06_loop_research.md) R4 的三臂签名）；早停钩子。R 变化时 visit 数、KV、conv、块消息、coda 都要随之重建，不跨深度复用缓存 | T18 | A1 默认 3 遍时与改前逐位一致；A4 有自己的三遍基线；A4 在 1–5 遍下可运行 |
| F 草稿器 | 4090 上的 DSpark（现有实现）；DFlash2 移植（5 层 qwen3 类结构，可复用 `qwen.rs` 的 kernel） | T13、T14、R7 | 投机解码与普通贪心等价（[05](05_validation.md) §3） |
| G 执行映射与消息预计算（v3.0.14，方案 10 §4–§5） | 私有 `inkling_plan.rs` 固定 visit / slot / tap 映射与 graph 身份；第二、三遍入口一次算完该遍 48 个消息（M1 共享源逆 RMS → M2 批量读取 → M3 controller 消息半支），各级独立开关 | T23、T24 | 关闭时逐位一致；中间张量逐项对齐；G2 不回退；端到端有收益 |

### 3.1 调优候选（T16 / T21，评审 §10.3）

| 顺序 | 候选 | 第一个实验 | 继续的条件 |
|---|---|---|---|
| K1 | NVFP4 GEMV 的软件解码与访存 | 真实热点形状上小范围扫描每块行数 / 展开参数 | 原算子通过且端到端有收益 |
| K2 | Q8_0 小形状路径 | T = 1 与 T = 2–8 分别比较 MMA 和 dp4a | 不靠改 dtype 换取隐藏的误差。T = 2–8（verify 与草稿）已采用（T16 第 2 轮，fork `aa837c7`）：sm_89 走 dp4a，DSpark 173.9 → 206.3 tok/s，G2 通过。T = 1（decode）在第 1 轮改成 dp4a（+9.4%），但 T20 B 组 decode 的 num-3 FAIL，已撤回，可用 `ASTRAL_DECODE_DP4A=1` 选用；要重新采用，需先让 decode 与 prefill 的差异回到限值内 |
| K3 | controller / mix / conv 融合 | 只融合时间线上仍独立且可以安全合并的操作（llama.cpp #33060 的五条融合链可作代码参考） | 状态更新顺序与数值门不回退 |
| K4 | 注意力 split 数 | 按有效长度与 capacity 测空 CTA、split / merge 成本 | 多个长度都没有明显退化 |
| K5 | verify 的数值一致性 | 相同 token 在不同小批形状下的结果 | 能解释并控制接受率变化 |
| K6 | 把 fragment / `mma5` 路径接到 Inkling | 一个真实 MoE 形状，显式计入新布局的权重表示、工作区和数值差异 | 值得扩到整个模型；这是新的布局与 kernel 实验，不是现成开关 |
| K7 | Q8_0 重编码为 FP8 | 只针对已证实受算力限制的局部 | 质量与时间同时有收益 |
| K8 | 按真实消费者裁剪激活平面（方案 10 §7.1） | 固定的消费者表：每个激活在当前 kernel 选择下要 Q8、FP16 还是两者；只省去没人读的写入 | 先完成 T22；“请求 FP16 却未写入”在调试模式下报错 |
| K9 | 短 verify 的 MoE 尾部融合（方案 10 §12.3，参考 mlx-serve #1331 的 few_tail，S35） | nv ≤ 8 时把 `moe_combine_t` → `conv_res_par` 合成按 hidden 列的一个 kernel：只读旧 conv、输出每行 hist，接受后仍由 `conv_commit` 提交 | cur、hist 与接受 0 / 部分 / 全部后的下一 token 都对齐 |
| K10 | 短 prefill 的 expert 行数特化 tile（方案 10 §7.2） | 记录每个 expert 的真实行数，按 8 / 16 / 32 / 64 行特化 NVFP4 gate_up / down | 计入分桶、padding、额外 launch 与确定性合并；同一 token / expert 映射核对输出 |
| K11 | split 工作区清零（方案 10 §7.3） | 证明每个被求和读取的元素都被唯一写入（含空 expert、尾行、split 数变化）后删 memset | 证明不了就保留清零；不回到浮点 atomicAdd |

v3.0.14 补充（方案 10 §7.4–§7.6、§12.4）：后置候选有 expert gate / up 与 SiTU 的 epilogue 融合、单 token 输入用固定 pinned packet 上传（先用 `ASTRAL_STEP_TIMING` 看占比，且不删 d17a519 的同步）；K4 注意力可试一个 CTA 覆盖同一 KV head 的 3 个 Q head（GQA = 3）、以及全局层远端（距离 ≥ 1024、bias 为零）的快循环，跨 1024、window 和 split 边界的 tile 走完整路径。Loom 的转置 / 补齐布局与 Metal 的阈值不是 4090 的参数，没有带宽或 cache miss 证据就不换格式。

Ada 有 FP16 / BF16 / INT8 / FP8 Tensor Core，没有 TMA、wgmma、TMEM 和原生 block-scaled FP4。NVFP4 在 4090 上只能软件解码，“Ada 支持 FP8”不代表 Q8_0 可以直接喂给 FP8 MMA；把所有专家常驻展开成 BF16 会超出 24 GB 预算。每次调优之后：同一输入的 graph / eager 对照、G2 回归。固定遍数 R = 1–5 可以各有自己的执行图；逐 token 动态深度要等 R6 / R9 的数据支持。

v3.0.17 补充（方案 11，[09](09_sources.md) S37；任务见 [07](07_tasks.md) T26–T31）：
- T26（草稿 head 的完整分数筛选）只改草稿提案。
- T27（末层 coda 的 prefill 裁剪）只用于不开草稿的 prefill，属于数学等价改动，但小行数可能走不同的 kernel，舍入要单独测。
- T28（全局远块稀疏）是目标模型的近似，只用于单 token decode，先做 dense shadow。
- T29、T30 暂缓。
- 平台约束：PDL 只在 CC ≥ 9.0 可用，fork 已按此判断，4090 上没有；CUDA 条件图在本机的可用性没有验证（T30 暂缓，暂时不需要）。
- 不采用：全模型 megakernel、自制 Python → SASS 编译器、把 5090 的 EXLR8 数字当本机目标。

### 3.2 SWA 环形缓冲的同批覆盖问题（评审 §11.3，已核实代码顺序）

当前 `layer` 先为整批写入 K/V 再做注意力。C 个连续 query、窗口 W 时，同一批需要可见的行最多是 W + C − 1 行；只有 W 行的取模环形缓冲会覆盖同批早期 query 仍要读的行，**即使 C ≤ W 也不安全**。方案二选一并写入设计：给 ring 额外的 staging / 容量（W = 1024、C = 512 时，40 个 SWA visit 合计约多 79.8 MiB，未含投机回滚余量），或者按依赖交错写读的 tile 方案。无论哪种，都用逐 token 的完整缓存作对照。

**T17 的选择（v3.0.14；fork `9593eb4`，v3.0.15 在 4090 上验证，[07](07_tasks.md) T17）**：采用“额外容量”。SWA slot 的物理行数为 W + max(tmax, 8)，向上取整到 64（默认 tmax 2048 时为 3072 行），位置 j 存在第 j mod rows 行；全局 slot 行数等于 capacity。三个坐标分开：绝对位置（相对 bias、全局层的对数缩放都只用它）、有效长度（session 的 pos，决定哪些位置可读）、物理行（只用于寻址）。这样一批 prefill 写入的行不会覆盖本批最早 query 仍要读的行；verify 被拒绝的行只覆盖已经出窗的位置，之后真正走到这些位置时会重写，所以不需要撤销数据；草稿 KV 仍按全长线性分配，它写入未提交行的做法继续安全。代价是显存：默认分块下 40 个 SWA slot 共 480 MiB（理想的 1024 行为 160 MiB），`ASTRAL_TMAX=512` 时 240 MiB。方案 10 §6.3 的“只读 ring + 本批 delta”能把 SWA 压到 160 MiB 加一份 8 MiB 的共享 prefill delta（verify 另需每个 SWA slot 8 行的小 delta，合计约 1.25 MiB），但所有注意力 kernel 都要改成双段读取，并引入显式的 commit；列为显存不够时的后续候选。

## 4. 提交纪律

- 每个 WP 一个系列的 commit。commit message 写明动机，以及修改前后的 selftest、`verify-model` 结果。
- 新增的环境变量写入 `docs/configuration/environment_variables.md`；默认行为与上游保持一致，所有新行为都必须显式开启。
- 保留 SPDX 头和 Apache-2.0 NOTICE；新文件写 `Copyright (c) 2026 <本人>`，涉及 llama.cpp 的部分注明 MIT 来源。
- fork 已按用户要求公开为 [lkyprogramer/inkling-4090-engine](https://github.com/lkyprogramer/inkling-4090-engine)（v3.0.6）；4090 上的 `$LAB/src/astral` 跟踪它的 `main`。新的推送、向上游提 PR 仍需用户逐次同意。

## 5. 长上下文的语义风险

全局层的相对 bias 带对数缩放的位置，超过 `rel_extent` 1024 之后的距离处理必须与 llama.cpp 完全一致（#33053 的 indexed bias 与 dense fallback 两条路径）。验证方法：在 16K 和 32K 上用 llama.cpp b12751（`-ub 128`，控制 dense bias 的显存）生成 KLD 基准，Astral 对齐后才进入 64K / 128K。64K 以上 llama.cpp 的 dense 回退放不进显存，只能对照 Astral 自己在 32K 与 64K 之间的一致性、困惑度和 needle 类检索，结论标注为“无外部参考”；“能分配”不等于“已验证”。llama.cpp #33063（CUDA / HIP 的 indexed-bias Flash Attention，未合并）可能补上参考路径，需按具体 commit 另行验证，不自动升级 S20。

边界用例（序列长度；trace 另存零基 `token_position`，不要把长度和下一个写入下标混用）：

- 窗口边界 1023 / 1024 / 1025，以及真正绕环前后；
- prefill 分块大小 1、一个不整齐的值、常规值；同批先写后读时，最早 query 的历史没有被覆盖；
- verify 接受 0、部分、全部；绕环覆盖发生之后的拒绝与回滚；
- 相同前缀 reset 后重算；相同前缀但有效长度不同，检查旧状态没有泄漏；
- 全局层拆成 near / far 两段时，sink 只参与一次归一化；
- 当前 capacity 8191 / 8192（生成与投机要预留剩余容量），扩展后加 8193。
- v3.0.14 补充（方案 10 §6.6）：分块 1 / 7 / 511 / 512 / 1024 / 2048，重点是分块 ≥ W 与跨环；verify 输入 2 / 3 / 4 / 5 / 7 / 8 行（3 / 5 / 7 对应自适应 k = 2 / 4 / 6），接受 0 个 draft 时仍提交 anchor，接受全部时不提前提交 bonus；拒绝发生在环尾、连续两轮拒绝、上一轮长候选到下一轮短候选的旧尾行隔离；reset 后复用同一地址；最后不足一轮的容量；query 位于 ring 最早的有效行；sink 占主导的头；graph 与 eager、trace 开 / 关、prefill → decode → verify 的交界。未写入的行和暂存区填不同的哨兵值，输出不得依赖它们。每个关键测试配一个负控制（错 slot、错一行 bias、提前提交一行），测试必须能失败。

新注意力实现与**同一份 KV** 上的参考计算比较；不同内容的 KV 或不同 cache 策略，不能用同一个“实现一致性”测试掩盖。

## 6. 调试回退

`ASTRAL_NO_GRAPH=1`（eager 执行）→ 融合开关（`ASTRAL_NO_FUSE_MIX`、`ASTRAL_NO_FUSE_ROUTER`、`ASTRAL_NO_BATCH_CTRL`、`ASTRAL_SIDE_BF16`）→ `ASTRAL_CUDA_ARCHS=80` 构建（sm_80 SASS）→ `verify-model` 定位到具体算子 → 对该 kernel 写 selftest 用例。
