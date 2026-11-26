# 04 · Astral fork 与 sm_89 移植

上游：`syntheticminds-lab/Astral-Inference-Server` @`49a0a2bee3270ad7518cebe7a059496b250180d1`（S10）。fork 后的工作分支为 `inkling-4090`。下文的文件和行号均指这个 commit。

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
| `crates/kernels-src/cu/inkling.cu` | `#define MAX_CTX 8192`；解码注意力把 `logit[MAX_CTX]`（32 KB）放在静态共享内存 | 上下文硬上限；4090 每 SM 100 KB，占用率低于 A100 |
| `crates/kernels/src/inkling.rs:408,912,1221` | 注意力启动器检查 capacity ≤ MAX_CTX、head_dim 128、`n_rel` 上限 | 同上 |
| `crates/model/src/inkling.rs` `Session::new` | 48 个 slot 的 K/V 都按完整 capacity 分配（f16） | 见 [01](01_model.md) §3 |
| `crates/loader/src/inkling_checkpoint.rs:282,473` | MXFP8 转 Q8_0；要求 `model_type == inkling2_loop` | varloop 原生 checkpoint 预计可直接加载（P5 前验证） |
| kernel 类型 | GEMV/GEMM 入口只有 f32 / bf16 / q8_0 / nvfp4（另有 Qwen 用的 mxfp4） | 只能用 A1 这类 NVFP4 + Q8_0 文件 |

推断：4090 上首次构建、selftest 和 `verify-model` 很可能不需要改代码就能通过；需要改的是性能和上下文长度。这是推断，由 T07/T09 验证。

## 3. 工作包

| WP | 内容 | 对应任务 | 完成判据 |
|---|---|---|---|
| A 上卡 | 构建 `ASTRAL_CUDA_ARCHS=89`；新增 `ArchProfile::Sm89`（family F80，`sm_target` "89"，`cp_async`、int8 TC、FP8 TC 为 true，fp4 为 None），更新第 249 行的测试 | T05、T07、T11 | selftest 全部 PASS；`astral hw` 输出 `sm89` |
| B 观测 | 新增 `ASTRAL_TRACE=<path>`。按 slot 输出 JSONL：pass、物理层、残差 RMS、controller gain/forget 统计、mix 权重、路由 top-8 id 与权重、注意力熵（抽样）、每遍结束时的 logit lens。只在 eager 模式（`ASTRAL_NO_GRAPH=1`）下生效 | T15 | trace 关闭时 logits 与关闭前逐位一致；trace 开启时 G2 不回退 |
| C 调优 | 用 CUDA event、`kbench`、nsys 时间线找热点；调整 GEMV 每块行数、`mma3` 的 tile 与 stage（适配 100 KB）、carveout（`ASTRAL_CARVEOUT`）、dp4a 与 mma 的切换（`ASTRAL_DECODE_DP4A`、`ASTRAL_SMALL_DP4A`）、注意力 split 数（`ASTRAL_ATT_SPLITS`）；之后评估 Ada 的 FP8 `mma.sync` 用于 Q8_0 部分 | T16 | G3 |
| D 长上下文 | SWA slot 改为长度 1024 + 草稿余量的环形缓冲；全局 slot 用分块 online softmax，logits 不放共享内存；长预填分块；可选全局 KV 用 q8 | T17 | G4 |
| E 循环控制 | 遍数可配置（`--passes`，或解析 varloop 配置）；跨遍 KV 策略开关；早停钩子 | T18 | 3 遍时与改前逐位一致；varloop 可在 1–6 遍下运行 |
| F 草稿器 | 4090 上的 DSpark（现有实现）；DFlash2 移植（5 层 qwen3 类结构，可复用 `qwen.rs` 的 kernel） | T13、T14、R7 | 投机解码与普通贪心等价（[05](05_validation.md) §3） |

## 4. 提交纪律

- 每个 WP 一个系列的 commit。commit message 写明动机，以及修改前后的 selftest、`verify-model` 结果。
- 新增的环境变量写入 `docs/configuration/environment_variables.md`；默认行为与上游保持一致，所有新行为都必须显式开启。
- 保留 SPDX 头和 Apache-2.0 NOTICE；新文件写 `Copyright (c) 2026 <本人>`，涉及 llama.cpp 的部分注明 MIT 来源。
- fork 只在本机 `$LAB/src/astral` 中，不推送到任何远端，除非用户要求。

## 5. 长上下文的语义风险

全局层的相对 bias 带对数缩放的位置，超过 `rel_extent` 1024 之后的距离处理必须与 llama.cpp 完全一致（#33053 的 indexed bias 与 dense fallback 两条路径）。验证方法：在 16K 和 32K 上用 llama.cpp b12751（`-ub 128`，控制 dense bias 的显存）生成 KLD 基准，Astral 对齐后才进入 64K / 128K。64K 以上 llama.cpp 的 dense 回退放不进显存，只能对照 Astral 自己在 32K 与 64K 之间的一致性、困惑度和 needle 类检索，结论标注为“无外部参考”。

## 6. 调试回退

`ASTRAL_NO_GRAPH=1`（eager 执行）→ 融合开关（`ASTRAL_NO_FUSE_MIX`、`ASTRAL_NO_FUSE_ROUTER`、`ASTRAL_NO_BATCH_CTRL`、`ASTRAL_SIDE_BF16`）→ `ASTRAL_CUDA_ARCHS=80` 构建（sm_80 SASS）→ `verify-model` 定位到具体算子 → 对该 kernel 写 selftest 用例。
