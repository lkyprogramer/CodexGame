# Kern（SM89 / W4A16）路线评估与 `kern-sm89-w4a16-64k-poc-v1.0.0` 核实报告

日期：2026-09-09  
对象：RTX 4090（192.168.10.29）上的 Qwen3.8-27B 推理  
现网基线：NInfer `tensorninja/ninfer-4090@44a2c6c`，`docs/openclaw-qwen38-ninfer.md`，`output/qwen38-27b-4090-ninfer/reports/01–12`  
候选路线：`pegainfer-project/kern@5188aaf8`（本地 `/Users/luo/Documents/github/kern`，master + 7 个远端分支）+ GPT Pro 给出的 `docs/kern-sm89-w4a16-64k-poc-v1.0.0`

证据等级标记：**[实测]** 本次在 4090 / 本机实际执行并观察；**[源码]** 读取 kern / ninfer / POC 源码或本地文件；**[报告]** 引用现有 ninfer 测试报告；**[公开]** 公开仓库 / 模型卡；**[推断]** 由上述证据推算，未直接运行。

---

## 0. 结论

**1. 在 4090 上用 kern 继续"极致优化" Qwen3.8-27B，不是比现网 NInfer 更好的方案。不建议按 POC 启动。**

理由压缩成四点：

- **物理上限已经被 NInfer 吃掉大半。** 4090 显存带宽 1008 GB/s。W4A16 权重（~12.5 GB）+ BF16 `lm_head`（2.5 GB）每 decode step 至少读 ~15 GB，无投机解码时 roofline 上限 ≈ 57–67 tok/s；64K 上下文再加 4.3 GB BF16 KV，上限 ≈ 45–52 tok/s **[推断]**。NInfer 自己的 no-spec 实测就是 50.5 tok/s **[公开]**。现网 NInfer 靠 MTP n=3 + E8 4-bit KV 做到 4k 127 / 64k 111 / 184k 87–98 tok/s **[报告]**。POC P0 的门禁"短 ≥50 tok/s、64K ≥20 tok/s、无投机、BF16 KV"，**做到满分也只是"NInfer 关掉 MTP"的水平**，与现网差 2 倍，而且窗口从 262K 退到 64K。
- **kern 在 4090 上没有任何可复用的 GPU 内核。** kern 全部 cubin 目标是 `sm_103a`（GB300），attention 用 TensorRT-LLM 预编 `fmhaSm100f/Sm103a` cubin，GEMM 走 `extern:cublaslt_bf16_tn`（cuBLASLt BF16），无任何 int4/W4A16/Marlin 路径 **[源码]**。POC 计划的 T04–T10 实际上是"在 kern 里从零写一套 Ada 版 W4A16 GEMM + GDN + 分页 attention + 生成器"，这和 NInfer 三个 fork 花数月做出来的东西是同一件事。
- **kern 的差异化不在速度。** 它的卖点是"model as verified program"（manifest 声明式、哈希锁定、可证明复现）。在其原生硬件 GB300 上对比 vLLM 0.28 也只快 ~10%（plain 105 vs 95 tok/s，DFlash2 181 vs 171）**[源码 docs]**。项目 27 star / 0 fork / 单一主要作者 / 唯一 tag v0.1.0，schema 与分支 9 月 8 日仍在大改 **[公开][源码]**。押注它承载生产推理，维护风险高于 NInfer（多 fork、sm_89 原生、本地 12 份报告验证）。
- **要追平现网，P0 之后的 P1a/P1b/P1c/P2（采样、MTP/DFlash2、低比特 KV、200K）加起来就是把 NInfer 在 kern 里重写一遍。** 收益是"另一个实现"，不是"更快"。

**2. POC 文档本身质量不差（自检 63 项通过、隔离规则合理、承认自己不是引擎），但与真实条件有 20 余处出入，其中 6 处会直接改变计划**（详见第 6 节）：W4A16 权重其实已经在机器上但被原地改写；Pi 不在 4090 上；GitHub 当前可直连；宿主 nvcc 12.3 / 无 cargo；POC 的 Java 夹具与现网所有对照用的夹具不同；性能门禁与"是否值得替代 NInfer"无关。

**3. 如果目标是"比现在更极致"，成本更低、命中率更高的路径按顺序是：**
  1. NInfer 配置层：`rk8v4` 200K 档（4k 145 / 64k 129 / 120k 117 / 184k 104 tok/s，针全中、Java 3/3，代价窗口 200192）**[报告 12-D]**；这是零工程量的 +15–30% decode。
  2. NInfer 源码层（已识别、未做）：draft-head Ada MMA、UDP `e8_root_codec` bfi/redux、`--auto-long-anchors` 设计移植 **[报告 09]**。
  3. 一次有界实验：本机已存在的 vLLM recipe `CTX=fast SPEC=dflash2`（64K，声称 4090 greedy 130–163 tok/s）**[源码 README, 未测]**——本地只测过 `SPEC=mtp CTX=huge`（53–64 tok/s）。它能回答"DFlash2 在 4090 上到底多快"，成本半天，不需要写任何内核。
  4. 关注 NInfer 上游是否吸收 DFlash2 draft（目前 44a2c6c 的 loader 契约不接受 HF main 的 19G DFlash2 artifact）**[报告 01]**。
  
  kern 只在一种情形下值得投入：你想要的是**可审计、可证明复现的推理制品**（manifest + 哈希锁定 + attest），而不是 tok/s。那也应该做成"把 NInfer 已验证的 sm_89 内核搬进 kern 的 manifest"，而不是 POC 现在的"在 kern 里重新造 sm_89 内核"。

---

## 1. 调研范围与方法

| 来源 | 做了什么 |
|---|---|
| 4090 实机 **[实测]** | SSH 采集驱动 / CUDA / nvcc / cargo / docker 镜像 / 容器 / systemd / 端口 / RAM / 磁盘 / PCIe / 模型目录 / 权重 header / vLLM recipe / lucebox 目录；在 `/tmp` 运行 POC 的 `self_check.sh` 与只读 `preflight.sh`，跑完即删 |
| 现网报告 **[报告]** | `output/qwen38-27b-4090-ninfer/reports/01-qualify`、`07-fusion-best`、`09-fusion-final`、`10-pi-prefix-prod`、`11-vs-work-vllm`、`12-rewrite-checkpoint`，及 `scripts/`、`results/` |
| kern 源码 **[源码]** | 本地 master `5188aaf8`；远端分支 `trtllm-base`、`merge/trtllm-base`、`fuse/qwen38-decode`、`deploy/performance-atlas-20260905`、`feat/manifest-constants`、`k5-span`、`agent-opt/claude-fable-trtllm-1`；`crates/kern-{manifest,runtime,run,serve}`、`tools/`、`docs/`、`examples/qwen3.8-27b.json` |
| POC 全集 **[源码]** | `README`、`AGENT_START`、`docs/00–18`、`tasks/T00–T23`、`configs/`、`references/`、`validation/`、`poc_tools/`、`scripts/` |
| 公开资料 **[公开]** | `github.com/pegainfer-project/kern`、`pegainfer-project/pegainfer`、`open-infer.org`、`huggingface.co/dbirks/Qwen3.8-27B-W4A16-AutoRound`、`tensorninja/ninfer-4090`、`sergiuszm/ninfer-4090`、`UDPSendToFailed/ninfer-4090`、`pyros-projects/ninfer-4090`、`kernel-sanders/qwen38-27b-rtx4090-vision`、`syv-ai/qwen38-27b-rtx3090` |

本次**没有**做的事：没有在 4090 上停生产、没有占用 GPU、没有编译 kern、没有下载任何权重、没有改动任何现网文件。

---

## 2. 4090 机器实际条件 **[实测 2026-09-08 21:45–21:52 机器本地时间]**

| 项 | 实测 | POC 文档陈述 | 判定 |
|---|---|---|---|
| GPU | NVIDIA GeForce RTX 4090，24564 MiB，UUID `GPU-381cb85f-…` | RTX 4090 24GB | 一致 |
| 驱动 / UMD | KMD 610.57.04，CUDA UMD 13.3 | 610.57.04 / 13.3 | 一致 |
| `libcuda.so` | `libcuda.so.610.57.04`（2026-07-28） | — | — |
| 宿主 nvcc | **PATH 上没有**；`/usr/local/cuda-12.3/bin/nvcc` = 12.3.107（`cuda` → `cuda-12.3` alternatives） | "不假定 nvcc=13.3"、"宿主 nvcc 12.3 hold" | 一致（POC 01 正确） |
| Rust | **无 cargo / rustc** | 需 cargo（`cargo build --locked --offline`） | 需安装，POC 未给安装步骤 |
| Python | 系统 3.11.2，**无 numpy / torch**；另有 `~/anaconda3`（未检查其包） | 工具需 numpy 2.2.6 | `self_check.sh` 在系统 python 下 **FAIL**（`test_extended` 缺 numpy） |
| Docker | 25.0.2；NVIDIA CTK 1.14.4；runtime `nvidia` 可用 | — | 一致 |
| 本地 CUDA 镜像 | `nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04`（含 nvcc 13.2）、`13.2.0-cudnn-runtime`、`13.0.1-base`（**无 nvcc**）、均有 daocloud 镜像副本 | 偏好 `13.0.1` userspace | 13.0.1 只有 base；**13.2 devel 是现成的编译环境**（NInfer 镜像即用它） |
| RAM | 62.5 GiB（MemTotal 67.06 GB），可用 ~47 GiB，Swap 1 GB | 64GB | 一致 |
| 磁盘 | NVMe 915 GiB 总 / 557 GiB 可用（`/` 单分区） | "600GB SSD" | POC 把**剩余空间**写成了盘容量 |
| CPU | Xeon Silver 4216，16C/32T，单路 | — | — |
| **PCIe** | **Gen3 x16**（`pcie.link.gen.max=3`，Cascade Lake 平台） | 未量化 | 主机↔GPU ≤ ~12 GB/s；147 MiB GDN slot 搬一次 ≈ 12 ms，4 GiB KV ≈ 350 ms **[推断]** |
| OS / 内核 | Debian 12，6.1.0-17，glibc 2.36 | Debian 12 | 一致 |
| 生产服务 | `openclaw-qwen38-ninfer.service` **active**；容器 `ninfer-4090-prod`（`ninfer-4090:44a2c6c`）；进程 `ninfer-serve` 占 **22590 MiB**，空闲 **1511 MiB** | 一致 | 任何 GPU 开发都必须停生产 |
| 端口 | 18343 / 28343 / 18030(loopback) / 18080 在听；**18041、18042 空闲** | 18041 候选、18042 oracle | 可用 |
| 其他 GPU 相关 unit | `openclaw-qwen38-work-64k`（llama.cpp WORK）、`openclaw-qwen36-mtp4-128k`、`openclaw-qwen38-text` 均 inactive | — | 回滚路径存在 |
| Java / Pi / Node | OpenJDK 17.0.20；**`pi` 不存在**；node 18.19 | POC `java_runner` 假定本机有 Pi | **Pi 实际跑在 Mac 控制端**（`~/.pi/bin`），经 `log_proxy.py` 打隧道到 4090 |
| 网络 | `curl https://github.com` → **200**；`hf-mirror.com` → 200；`huggingface.co` → 不通 | "该机默认不能直连 GitHub" | 当前可直连（可能受代理/时段影响），离线 bundle 可降级为后备 |
| **W4A16 权重** | **已存在** `/home/hhtele/qwen38-vllm/models/Qwen3.8-27B-W4A16-AutoRound`（22 GB，root 所有，HF revision `1f05c441c4e64ae0549de44fa9ea5a6d43610314`）；**已被 recipe `prepare` 原地改写**：`config.json` 增加 lm_head / embed_tokens / mtp 三组 INT8 量化配置，shard 6/7 被替换（原件仅存为 `.bak_embed` / `.bak`），新增 `model_extra_tensors.safetensors`（draft/MTP）；另有 `-fast` 变体（int4-GPTQ lm_head） | "选同一量化源、本机 revision 冻结、原始文件只读" | **POC 不知道权重已在本机，也不知道它不再是 pristine** |
| `.ninfer` 制品 | `/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer` 18,210,531,328 B（16.96 GiB） | 一致 | — |
| 其他 Qwen3.8 权重 | GGUF：UD-Q4_K_XL(-dv3)、IQ4_XS、HauhauCS、ColdFusion、DFlash2 Q2/Q4/f16/q8；`qwen38-dflash2-src`（safetensors 3.6 GB） | — | 无 BF16 全量 safetensors（~50 GiB），kern 原生 BF16 路线在本机连权重都没有 |
| 其他引擎残留 | `~/qwen38-vllm`（recipe pinned `36317835…`，与 POC S04 一致）、`~/lucebox-qwen38-4090`（Luce-Org/lucebox，megakernel）、`~/ninfer-4090`（源码树，`PINNED_COMMIT 44a2c6c…`，`VERSION 0.6.1-rtx3090`） | — | 机器上已经有三套替代引擎的实验痕迹 |

模型结构（从本机 `config.json` 与 shard 1 header 读出）**[实测]**：`model_type=qwen3_5_text`，64 层 = 48 `linear_attention` + 16 `full_attention`；`hidden 5120`；attention `24 q / 4 kv heads × 256`；GDN `16 k / 48 v heads × 128`，conv kernel 4；MLP 17408；vocab 248320；`max_position_embeddings 262144`；`mtp_num_hidden_layers 1`。量化：`pack-quantized`，`Linear` 统一 W4 g128 symmetric，`weight_packed I32 [N, K/8]`，`weight_scale F16 [N, K/128]`（**scale 是 F16 不是 BF16**），`weight_shape I64[2]`；`in_proj_a/b` BF16 `[48, 5120]`。与 POC 04/06 描述一致。

---

## 3. 现网 NInfer 基线（不重复报告，只列决策相关数字）**[报告]**

| 指标 | 数值 | 出处 |
|---|---|---|
| 配置 | `--max-context 262144 --kv-capacity 262144 --kv-dtype rk4v4-e8 --spec mtp --draft-tokens 3 --lm-head-draft --prefill-chunk 1024 --continuation-cache l1-l2 (L1 6144 / L2 8192) --prefix-checkpoint-policy rolling-tool --preserve-thinking`，单并发 | 09 |
| 驻留显存 | 22594 / 24564 MiB | 09 |
| decode（thinking=medium） | 4k 127.1 / 64k 110.6 / 120k 115.4 / 184k 98.5 tok/s | 11 |
| decode（thinking=off，262k 档） | 4k 112 / 64k 111 / 120k 110 / 184k 87.2 tok/s | 09 |
| 184k TTFT / prefill | 94 s / ~1974 tok/s（vLLM 66 s / 2802；WORK 134 s / 1383） | 11 |
| Pi Java 三题（medium，现网） | 3/3，25 / 13 / 19 s | 10 |
| Agent 追加历史 prefix 命中 | ~85%（154961 命中 / 26845 实算），`stable_prefix_restores +20` | 10 |
| 60k 会话只改最新 user | `restore_user_turn_anchor` 100%，TTFT 0.90 s | 12 |
| 备选档 `rk8v4` 200192 | 4k 145 / 64k 129 / 120k 117 / 184k 103.7 tok/s，针全中，Java 3/3；未当默认（窗口） | 12-D |
| 已否决 | draft 4/5、rk2v4-e8（Java 题3 失败）、L3（本 harness 无收益） | 09 |
| 公开上游数字 | MTP3 code 148.6 tok/s；**no-spec 50.5 tok/s**；128K no-spec 39.6；115K prefill 2409 tok/s | tensorninja README |

---

## 4. kern 是什么 **[源码][公开]**

- 定位："A model-agnostic GPU runtime for shipping models as verified programs"。二进制不含模型；模型 = **manifest（schema v4 JSON）+ 一组按 sha256 锁定的 cubin + 权重 bind**；运行前 `Verified::from_json` 做静态校验，加载时按 `cuFuncGetParamInfo` 对 ABI。crates：`kern-manifest`（校验）、`kern-runtime`（分页 KV / state slot / prefix 表 / checkpoint / park-wake / VMM 池）、`kern-run`（CLI：run / test / bench / attest）、`kern-serve`（独立 workspace，拉 `pegainfer-frontend` git 依赖，OpenAI 兼容，连续批处理）。
- 目标硬件：**全部 cubin 为 `sm_103a`（GB300）**。`tools/handwritten.py` / `build_kernels.sh` / `flash-kda/build.sh` / `build_k3_mega.sh` 默认 `KERN_SM=sm_103a`；快速开始明确"需要 GB300"。master 的 `examples/qwen3.8-27b.json` 引用 22 个模块：attention 是 TensorRT-LLM 预编 `fmhaSm100fKernel_…P64…` 与 `fmhaSm103aKernel_…P64…`（Blackwell 专属），GDN 是手写 `chunk_h / chunk_o / kkt / solve_tril / cumsum / conv_fwd / post_conv / gdn_decode`，其余 `gemm16 / embedding / layer_norm / gemma_rms_norm / silu_mul / sigmoid_mul / argmax / copy_rows / line_copy / attn_prep / weight_prep / recompute`。**所有 dense GEMM 走 `extern:cublaslt_bf16_tn`（cuBLASLt BF16，`compile.rs:121`）**。
- 量化：**没有任何权重 int4 / W4A16 / Marlin / GPTQ / AWQ 路径**。仓库里"fp4/fp8"只出现在 Kimi-K2 MoE 的 `sm100_fp8_fp4_mega_moe`（Blackwell）。Qwen3.8 目标是 **BF16 全量权重（~50 GiB）**，24 GB 卡装不下。
- Qwen3.8 现状：`kern.toml` 有 `qwen3.8-27b` 与 `qwen3.8-27b-dflash2` 两个 target；master `c5848cd` 已把 decode_batch 换到 TRTLLM-GEN attention + `gemm16` + **PDL**，`KV_BLOCK_SIZE=64`，`KV_BYTES_PER_TOKEN=65536`，`GDN_BYTES_PER_SEQ=154,140,672`（= 48 × 3,211,264）。decode 程序一步 **646 个 call**（graph 捕获后才可接受）。
- kern-serve：只 greedy（`scheduler.rs:46`，非 greedy 参数只 `warn!` 一次仍 argmax，`:594–602`）；`--max-seqs` 默认 256（`lib.rs:87`）；`--prefill-budget` 2048；有 `checkpoint / retire / lease_from / park / wake` 基元（`pages.rs`、`tray.rs`、`host.rs`）。
- 性能（原生硬件，全部 GB300，**无任何 4090 / Ada 数字**）：
  - 网站快速开始：单序列 plain **105** / DFlash2 **261** tok/s——**claim**，仓库内找不到对应 raw JSON 或测量日期。
  - `docs/qwen38-bringup.md`（2026-08-31，bs=1，graph，融合前）：plain **80.8** vs vLLM 0.28 **95.0**；DFlash2 **177.9** vs **175.6**。
  - `fuse/qwen38-decode` 分支 tray14（2026-09-01，同 5 条 prompt）：plain **105.1 vs 95.1**，DFlash2 **181.4 vs 171.4**。
  - `docs/serve.md`（2026-09-03，kern-serve 门禁）：qwen3.8-27b-dflash2 conc1 **114 tok/s**，conc32 1709 tok/s。
  - `deploy/performance-atlas`：单卡 GB300 program 级 GPU 时间（decode B1 KV2048 p50 11.67 ms ≈ 86 步/s），不是 serving tok/s。
  - 读法：kern 对 vLLM 在原生硬件上的优势是 plain +6–10%、spec +1–6%；不同页面的数字来自不同树，不能混引。
- kern-serve 能力边界（源码 grep，`crates/kern-serve/src`）：OpenAI `tools` / `tool_calls` **not found**；`reasoning_effort` **not found**；greedy only；无 logprobs / echo。thinking 开关只是 chat template 的 `enable_thinking`，reasoning 走 `reasoning` delta。
- 带状态模型的前缀缓存语义（`docs/serve.md` L115–160）：Qwen3.8 的 GDN state 154 MB/序列，**只在请求结束 `retire`**；只有"续上一轮完整上下文"才命中，同一 prompt 重发不命中，部分命中对带状态模型"在算力上没有意义"（state 之后必须整段重算）。
- 运行时**不检查 SM**：cubin 能 `cuModuleLoad` 就跑，兼容性完全由工件 arch 决定。TRTLLM-GEN prefill 工件文档写明"SM103-specific; other GPUs … not validated"。
- 构建事实：编 Rust 不需要 CUDA toolkit（`cudarc cuda-13000`），但运行需 driver r580+ 与 `libcublas.so.13` / `libcublasLt.so.13`；编 cubin 用 nvcc 13.1 + `sm_103a`；**无 `rust-toolchain.toml` / `rust-version`**（CI 用 `stable`）；**无 Dockerfile**（release 文档明确不做镜像）；CI 只跑 `cargo test -p kern-manifest` + 三个 Python 单测，`kern-runtime` / `kern-run` / `kern-serve` 的测试与任何 GPU 门禁都不在 CI 里。
- 成熟度：GitHub 27 star / 0 fork；唯一 tag `v0.1.0`（2026-09-08）；主要作者一人；manifest schema v4 与常量命名 9 月 7–8 日仍在改；README "under 3,000 lines of Rust" 与当前 `kern-manifest + kern-runtime` ≈ 11.9k 行不符（口径未给出）。文档相当一部分为中文工作日志（`qwen38-bringup.md`、`roadmap.md`、`serve.md`）。
- 七个远端分支巡检（只读 git，未 checkout；由子代理完成并经本报告复核关键 SHA）：

| 分支 | HEAD | 与 master 关系 | 对 4090 的意义 |
|---|---|---|---|
| `feat/manifest-constants` | `0935fa3` | **已是 master 祖先**（PR #2 合入） | 无独有内容 |
| `deploy/performance-atlas-20260905` | `c7c3ad0` | 同功能另一 SHA（master 用 `fbd4f70`） | 部署快照，GB300 数据 |
| `k5-span` | `af1e102` | 同主题另一 SHA；落后 44 commit | **Kimi-K3 span/MegaMoE**，与 Qwen3.8 无关 |
| `fuse/qwen38-decode` | `958efa0` | **未合入**，落后 122 commit | `gemm8.cu`（M≤8，注释写明 Blackwell sm_103a）+ `gdn_spec.cu` + tray14 对比数据；master 走了 `gemm16` + TRTLLM-GEN 另一条线 |
| `trtllm-base` / `agent-opt/claude-fable-trtllm-1` | `0736fe7` / `c336a4a` | **树哈希相同**；被重写为 master `c5848cd` | 内容已在 master |
| `merge/trtllm-base` | `3b21729` | 非当前 master 祖先 | 缺 master 后续的 `load` program / 权重 bind |

  结论：**没有任何分支提供 Ada / sm_89 / 低比特权重路径**；`fuse/` 是唯一未合入的实质代码，且仍是 sm_103a BF16。
- 与 POC 直接相关的源码事实核对：

| POC 陈述 | 源码 | 判定 |
|---|---|---|
| 固定 `5188aaf8dc99…`，schema v4 | 本地 master HEAD 一致，`schema_version: 4` | ✅ |
| `handwritten.py` 的 cubin 缓存键不含 arch/toolchain，靠 mtime | `arch = os.environ.get("KERN_SM","sm_103a")`；文件名只含 name+defines；`st_mtime` 比较 | ✅（S08） |
| `cudarc = "=0.19.7"` + `cuda-13000` | `Cargo.toml` 一致；`tokenizers = "=0.22.2"` | ✅ |
| kern-serve 独立 workspace，依赖需单独 vendor | `exclude = ["crates/kern-serve"]`；`pegainfer-frontend = { git = …, rev = "1e3b6f23…" }` | ✅，且多一个 git 依赖 |
| 非 greedy 只 warn 仍 argmax | `scheduler.rs:594–602` | ✅（S07） |
| `max_seqs` 默认 256 | `lib.rs:87` | ✅ |
| GDN state 3,211,264 B/层；KV 64 KiB/token | manifest 常量 | ✅ |
| verifier 227 KiB shared-mem 上限不代表 Ada 支持 | `verify.rs:56` `MAX_DYN_SHARED_MEM = 232_448` 注释"sm90/sm100/sm103" | ✅，Ada 实际 99 KiB/block |
| "旧 Kern 捕获曾固化 784 页，后来 TRTLLM 路线改用 64" | 784 只剩在 `qwen38-bringup.md` 的历史记录与 `pages.rs:17` 注释；**pinned master 已是 64 页 + TRTLLM-GEN** | ⚠️ 表述滞后，结论不变 |
| 可把 W4 GEMM + activation 封成一个逻辑 Op 多次 launch | op = `{"params": [...], "impl": {"launches": [...]}}`，launches 为列表 | ✅ 可行 |
| PDL 需关闭 | master decode_batch 含 PDL；Ada 无 PDL | ✅ |
| 未提及 | **GEMM 是 `extern:cublaslt_*`，不是 manifest 内 cubin** → W4A16 不是"换一个 cubin"，要在 `kern-runtime/compile.rs` 增加新的 extern/op 类型或以自写 cubin 替换全部 GEMM 调用点 | ❌ POC 03/06 低估 |
| 未提及 | attention cubin 来自 TensorRT-LLM trtllm-gen，**没有 sm_89 版本**；Ada 要另找 FlashInfer / FA2 sm_89 构建或手写 | ❌ POC T09 一张卡片 |

---

## 5. 核心判断：kern 在 4090 上是否是更好的优化路线

### 5.1 带宽账（decode，单序列）**[推断]**

RTX 4090：GDDR6X 1008 GB/s，实际可达 ~85%。

| 路线 | 每 step 必读字节 | 理论上限 | 实际上限（85%） | 实测 |
|---|---|---|---|---|
| kern P0 W4A16，短上下文，无投机，BF16 lm_head | 12.55 GB（24.33 B 参数 × 4.125 bit）+ 2.54 GB lm_head + ~0.3 GB GDN state r/w ≈ 15.4 GB | 65 tok/s | **~56 tok/s** | — |
| kern P0，64K，BF16 KV | 15.4 + 64K×64 KiB = 4.29 GB ≈ 19.7 GB | 51 tok/s | **~44 tok/s** | — |
| NInfer int8 KV，无投机 | 16.96 GiB 权重（含量化 lm_head）+ 少量 KV | ~55 | — | **50.5**（上游） |
| NInfer rk4v4-e8 + MTP3，64K | 权重 + 64K × ~17 KB = 1.1 GB；一步验证 3 draft，接受 ~2–2.5 token | — | — | **111–129** |

结论：**POC 的性能门禁（≥50 / ≥20）设置在 roofline 之下，"通过"不代表任何相对现网的进步**；P0 设计上就把决定 decode 的两个杠杆（投机解码、低比特 KV）都排除了，而这两个正是 NInfer 领先 llama.cpp / vLLM 的全部原因（报告 11 §1）。

### 5.2 显存账（P0，64K + 2K 输出，`seqs=4`）**[推断，基于实测 header]**

| 项 | 估算 |
|---|---|
| W4 packed + F16 scale（语言层 Linear） | 11.7 GiB |
| BF16 `embed_tokens`（248320×5120） | 2.37 GiB |
| BF16 `lm_head` | 2.37 GiB |
| BF16 `in_proj_a/b`、norm、conv1d、A_log、dt_bias、rope 表 | ~0.1 GiB |
| KV BF16 73,728 token | 4.5 GiB |
| GDN state 4 slot × 147 MiB | 0.58 GiB |
| 激活 / cuBLAS workspace / FLA chunk 中间量 / graph / context | ~1.0 GiB |
| **合计** | **~22.6 GiB / 23.99 GiB** → 余量 ~1.4 GiB |

能装，但只剩 POC 自设的 1 GiB 硬线附近。最大的可避免开销是 **4.7 GiB 的 BF16 embed + lm_head**——POC 04 没有把这两项单列出来，而 P0 合同又写"embedding / lm_head 保持源精度"。本机权重目录里 recipe 已经把它们改成 INT8（正是为了在 24 GB 上放开窗口），POC 把这项推到 P1c 是把最便宜的 2.4–4.7 GiB 留到最后。

### 5.3 工程量与风险 **[源码][推断]**

POC 的 24 张任务卡是同一模板生成（Goal = 标题 + "输出可独立复核的成果"，五步固定），没有工作量估计。按 kern 现状逐项看：

| 任务 | 实际要做的 | 量级 |
|---|---|---|
| T04 packed buffers / repack | 读 compressed-tensors `pack-quantized` → Marlin tile 布局；load 程序里做 | 中 |
| T05/T06 W4A16 GEMM | 把 vLLM Marlin（CUTLASS 风格模板、workspace + 全局 lock、split-k）剥离 PyTorch 变成 flat-ABI cubin；M=1…512 全 shape 与 oracle 对齐；**kern 现无非 cuBLAS GEMM 入口** | 大（周级） |
| T07/T08 GDN | 把 `chunk_h/chunk_o/kkt/solve_tril/gdn_decode` 从 sm_103a 移到 sm_89：shared mem ≤ 99 KiB、无 cluster/TMA/PDL、FP32 state 契约、last-token 走 decode 核的语义 | 大 |
| T09 分页 attention | 64 页 BF16 paged attention + RoPE，sm_89 版本要另源或手写；prefill 与 decode 两条 | 大 |
| T10 生成器 | `gen_qwen38_sm89_w4a16.py`、artifact_key、ABI 登记、manifest v4 | 中 |
| T11–T14 eager/graph/oracle 对齐/64K | 数值对齐要重走 kern 团队在 GB300 上花掉的整个 bring-up（他们记录了 near-tie 翻转、ATen 舍入顺序、FFMA 收缩等问题） | 中–大 |
| T15–T23 缓存/协议/Pi/门禁 | kern-serve 补 4xx、trace 端点、append 缓存、Pi 联调 | 中 |

再叠加两条 4090 特有的约束：**每次 GPU 验证都要停生产**（空闲显存 1.5 GiB，无法与 NInfer 共存），以及 **PCIe 3.0**（park/wake、host 预算的假设都要重算）。保守估计这是 1–2 人·月的专家级 CUDA 工作，产出是一个 64K / greedy / 无投机 / ~50 tok/s 的引擎。

### 5.4 与 NInfer 逐项对比

| 维度 | NInfer 现网（44a2c6c） | kern P0（若全部 PASS） | kern 追平所需 |
|---|---|---|---|
| decode 4k / 64k | 112–127 / 111–129 | ≤56 / ≤44 | P1b（MTP/DFlash2）+ P2（低比特 KV） |
| 窗口 | 262144 | 65536+2048 | P2（120K→200K，仍不到 262K） |
| 采样 | 全 | greedy only | P1a |
| thinking | medium 兼容层注入 | off | P1a |
| prefill 184k | 94 s | 未定义（P0 不测） | — |
| Agent 缓存 | rolling-tool + user-turn anchor + L1/L2 | append 命中（T15） | anchors、continuation cache |
| 视觉 | 有 | 无 | — |
| sm_89 内核 | 原生，三个 fork 持续调 | 0 | 全部新写 |
| 社区 | 5+ 活跃 fork，上游 803 commits | 27 star / 0 fork | — |
| 可审计性 | 一般（artifact SHA + docker tag） | **强**（manifest 哈希、attest） | — |

### 5.5 什么时候 kern 才有意义

- 你要的是 **"制品可证明"**（每个内核 sha256、ABI 静态校验、跨机器 bit-exact 门禁）而不是 tok/s。这时正确做法是 **把 NInfer 已验证的 sm_89 内核（或其 SASS）以 dump/capture 方式登记进 kern manifest**（kern 自己就是这么对 vLLM 做的：`tools/kernel-capture`、`dumped-kernels`），而不是重写。
- 或者未来 4090 被 Blackwell 卡（sm_120 RTX 50 系 / GB10）替换：kern 的 sm_100/103 资产、trtllm-gen cubin、FP4 MoE 才开始有复用价值。

---

## 6. POC 文档逐项核实

判定含义：✅ 与实际一致；⚠️ 表述不准或滞后，不改变计划；❌ 与实际不符或缺失，**会改变计划**。

### 6.1 机器与运维（`01-machine-and-operations.md`、`AGENT_START.md`、`source-lock.json`、`preflight`）

| # | POC 陈述 | 实际 **[实测]** | 判定 | 影响 / 建议 |
|---|---|---|---|---|
| M1 | "600GB SSD" | 915 GiB NVMe，557 GiB 可用 | ⚠️ | 改为"≥500 GiB 可用" |
| M2 | "该机默认不能直连 GitHub"，因此全套 git bundle / vendor 离线流程 | `curl https://github.com` 200；`hf-mirror` 200；`huggingface.co` 不通 | ❌ | 离线 bundle 降为后备；但 `pegainfer-frontend` git 依赖与 crates.io 仍需锁定策略 |
| M3 | 假定 Pi 在本机，`java_runner` 指向 `127.0.0.1:18041` | 4090 上无 `pi`；Pi 在 Mac 控制端（`~/.pi/bin`），通过 `output/qwen38-27b-4090-pi-ab/scripts/log_proxy.py` + SSH 隧道打 4090 | ❌ | POC 缺"控制端拓扑"：谁跑 Pi、隧道、日志代理、`PI_CODING_AGENT_DIR` 配置；应直接复用 `run_pi_java.sh` / `run_pi_java_tools.sh` |
| M4 | 维护窗口用 `systemctl stop/start` | 需 sudo；现有流程用 `sudo-wrap.sh` 喂密码 | ❌ | `guard_gpu.py` 直接 `systemctl` 会挂在密码提示；需接现有 wrapper，且不要把密码写进日志（见 §9 安全提醒） |
| M5 | 偏好 `nvidia/cuda:13.0.1` userspace | 本机 13.0.1 只有 `base`（无 nvcc）；**13.2.0-cudnn-devel 已在本机且被 NInfer 镜像验证** | ❌ | toolchain 容器直接用 13.2 devel；cudarc `cuda-13000` 是 API 级别，与 13.2 兼容 |
| M6 | cargo / nvcc 由执行者准备，无步骤 | 均缺 | ⚠️ | 给出 rustup 离线/在线安装与固定 toolchain 版本 |
| M7 | 未提 PCIe 代数 | Gen3 x16 | ⚠️ | 09/13 里 park/wake、host 预算需按 ≤12 GB/s 重算 |
| M8 | `preflight` 输出 `ssd_gb: 600` 等"user_declared" | 与实测混排 | ⚠️ | 把 declared 与 observed 分列并自动 diff |
| M9 | 工作目录 `/data/kern-sm89-poc` | `/data` root 所有 | ⚠️ | 用 `/data/models/qwen/`（hhtele 所有）或 `~/` |
| M10 | 端口 18041/18042 | 空闲 | ✅ | — |
| M11 | 生产白名单 / 串行 GPU | 与实际服务名、容器名一致 | ✅ | — |
| M12 | `self_check.sh` "63 项通过" | 有 numpy 的 venv 下 63/63 OK；系统 python 34 通过 + 1 import error，脚本 exit 1 | ✅/⚠️ | README 应把 numpy 写成硬前置，而不是"已有 numpy 时可直接自检" |

### 6.2 模型与权重（`02`、`04`、`06`、T02）

| # | POC 陈述 | 实际 **[实测]** | 判定 | 影响 / 建议 |
|---|---|---|---|---|
| W1 | 需从 dbirks 下载 W4A16，`source-lock` revision 为 null | 已在 `/home/hhtele/qwen38-vllm/models/Qwen3.8-27B-W4A16-AutoRound`，revision `1f05c441c4e64ae0549de44fa9ea5a6d43610314` | ❌ | 直接锁定此 revision；但见 W2 |
| W2 | "原始文件只读、embedding/lm_head 保持源精度" | 目录已被 recipe 改写：INT8 embed/lm_head、shard 6/7 替换、`model_extra_tensors`；原件为 `.bak_embed` / `.bak`；root 所有 | ❌ | 要么从 `.bak` 重建 pristine 目录并校验 HF sha256，要么重新下载 shard 6/7；否则 oracle 与 provider 读到的不是同一权重 |
| W3 | scale 为独立 buffer | 是，但 **dtype F16**，非 BF16 | ⚠️ | manifest DType 有 F16，生成器与 GEMM 内核要按 F16 scale 处理 |
| W4 | 04 显存表只算 KV/state | 未列 BF16 embed + lm_head 4.7 GiB（占总量 20%） | ❌ | 04 必须加权重分项；P0 应允许 embed 留主机或 INT8 lm_head，否则 1 GiB 余量贴线 |
| W5 | "约 50 GiB BF16 权重" | kern 文档一致；本机**没有** BF16 全量 safetensors | ✅ | kern 原生 BF16 路线在本机不可行，坐实必须 W4A16 |
| W6 | 模型结构 64/48/16、4 kv heads × 256、GDN 48v×128、conv 4、group 128 sym | 全部与 `config.json` / header 一致 | ✅ | — |
| W7 | GDN state 3,211,264 B/层 | 与 kern manifest 一致 | ✅ | — |

### 6.3 kern 源码（`02`、`03`、`05`、`07`、`18`、`sources.md`）

见 §4 末表。总结：**9 项 ✅、1 项 ⚠️（784 页表述滞后）、2 项 ❌ 缺失**（GEMM 是 cuBLASLt extern 而非 cubin；attention 是 trtllm-gen Blackwell cubin，无 sm_89 同类）。这两处缺失直接决定 T05–T09 的性质从"移植"变成"新写"。

另一处 POC 没有覆盖：kern 的 `decode` 程序一步 646 个 call。在 Ada 上 eager 模式（T11）单步 launch 开销 ≈ 646 × 4–6 µs ≈ 3 ms，相当于 decode 上限的 15–20%；eager 阶段的性能数据不能用于判断，POC 13 应写明。

### 6.4 计划与门禁设计（`00`、`08`、`10`、`12`、`13`、`tasks.json`）

| # | 问题 | 判定 | 建议 |
|---|---|---|---|
| P1 | 性能硬门 "短 ≥50 tok/s、64K ≥20 tok/s" 低于 roofline，且 ≈ NInfer no-spec；通过与否**对"是否值得替代 NInfer"没有信息量** | ❌ | 门禁应改为相对口径：同 prompt 下 kern P0 no-spec vs `ninfer --spec none` 与 vLLM 原生 Marlin；P0 只能证明"kern 能在 4090 跑"，文档要把这一点放到 README 第一段 |
| P2 | 24 张任务卡模板化，无工作量与人力估算，"一小时资格测试"被读者当成总成本 | ❌ | 在 00 增加分阶段工作量与停止点（例如 T06 若两周内 M=1 GEMM 未对齐即止损） |
| P3 | oracle 用 kernel-sanders patched vLLM，"显式 no-spec / BF16 act / FP32 GDN / BF16 KV" | ⚠️ | recipe 的 INT8 GEMM / fp16 state / KVarN 补丁是源码级，不一定有开关；oracle 应用 **stock vLLM 镜像 + dbirks 原目录**（模型卡即如此部署），`--max-model-len` 视显存 |
| P4 | Java 夹具是 POC 自带的 `java-01/02/03` | ❌ | 现网所有对照（WORK / NInfer / vLLM）都用 `docs/qwen38-4090-vllm-extreme-v1.0/fixtures/java-agent-{1,2,3}` + `verify.sh`；POC 必须复用，否则结果不可比 |
| P5 | P0 greedy + thinking off；现网 temperature 1.0 / top-p 0.95 / top-k 20 / medium | ⚠️ POC 已声明 | 但 P0 结束时依然无法回答用户问题；应把"P0 通过 ≠ 值得替代"写进 12 的 verdict 字段而不是只在 00 |
| P6 | 12 的"一小时"预算含 12 分钟 Pi Java 三题 | ⚠️ | 现网 medium 三题 25/13/19 s 是 NInfer 127 tok/s 下的数字；50 tok/s 引擎 + greedy 三题 3–5 分钟合理，但 64K 容量段 10 分钟里含 ~1 分钟以上 prefill（64K / ~1000 tok/s） |
| P7 | 09 要求 `exact_lcp_tokens / reused_tokens / computed_prefill_tokens` 三字段 | ✅ 好设计 | 与 NInfer `prefix_cache_hit_tokens / prompt_tokens_total` 口径对齐后才能比 |
| P8 | 16 提到"kern 不超过 NInfer 时，已验证 sm_89 内核与数值测试器可反哺 NInfer" | ✅ | 这其实是 POC 最有价值的产出方向，建议前移为主目标（见 §7） |
| P9 | 15 止损条件 | ✅ | 建议增加两条：T06 GEMM 对齐超期；P0 显存余量 < 512 MiB 且 embed/lm_head 不允许降精度 |
| P10 | `tasks.json` 全部 PENDING、`generation-environment.json` 标注 nvcc/cargo 不可用 | ✅ 诚实 | — |
| P11 | 10 要求流式 `tool_calls`（arguments 分片）与 Pi 联调（T16/T17）；kern-serve 源码中 `tools` / `tool_calls` / `reasoning_effort` **均 not found** | ❌ | Pi Java 门禁前提是 tool-call 解析与流式输出；这部分要么在 `pegainfer-frontend` 里已有（POC 未核实），要么是 T16 之外的一整块新工作。任务卡应先做一次 `tools` 请求的 HTTP smoke（现有 `run_pi_java_tools.sh` 已有此步） |
| P12 | 09 的 append 缓存门（48K→64K 追加 tool 结果、`exact_lcp_tokens`）默认 kern 能做前缀复用 | ⚠️ | kern `serve.md` 写明：带 GDN state 的模型只在请求结束 `retire`，只有"续上一轮完整上下文"才命中，**同 prompt 重发不命中、中途分叉不命中**。Pi 的顺序 tool 追加能命中；但 09 里"改写最近消息"场景与 NInfer 的 user-turn anchor（报告 12：改最新 user 仍 100% 复用）没有对等物，P0 门禁应明确这一差距而非留给实施者发现 |

### 6.5 工具与夹具（`17`、`poc_tools/`、`scripts/`）

- `poc_tools` 共 740 行 Python：preflight / memory / manifest 静态检查 / SSE 解析 / http 探针 / Java runner / 数值比较。**都能跑，但都是薄壳**；GateResult 契约（`PASS/FAIL/BLOCKED/INCOMPLETE` + evidence sha256）是好约定。
- `preflight` 在 4090 上实测可运行、只读、输出正确（检测到 ninfer-serve 22590 MiB、production active、nvcc/cargo/pi 缺失）。
- `guard_gpu.py` 的 `systemctl` 路径未处理 sudo（M4）。
- `check_bundle.py` PASS（24 任务 DAG 无错）。
- `requirements-tools.txt` 只有 numpy / tokenizers；oracle 与数值比较必然要 torch / safetensors，未列。

---

## 7. 若仍决定做 kern POC：必须先改的 10 件事（按优先级）

1. **改目标**：P0 目标从"在 kern 里新写 sm_89 内核"改为"**把 NInfer / vLLM-Marlin 已验证的 sm_89 内核以 capture/dump 方式登记进 kern manifest**"，P0 交付物 = 可 attest 的制品 + 与 NInfer 同 prompt 的 no-spec 对照，而不是 tok/s 门禁。这样 kern 的真正价值（可验证制品）与 4090 的真正瓶颈（内核）才对得上。
2. **权重**：锁 `1f05c441c4e64ae0549de44fa9ea5a6d43610314`；从 `.bak` 或重下载重建 pristine 只读副本（hhtele 所有），记录每 shard sha256；决定 embed/lm_head 精度策略并写进 04。
3. **oracle**：stock vLLM（非 patched recipe）镜像 + pristine 权重 + BF16 KV，`--max-model-len` 按显存；T03 里写明 vLLM 版本与 Marlin 路径确认命令（`--quantization compressed-tensors` 自动检测）。
4. **控制端拓扑**：写一节"Mac 控制端 + SSH 隧道 + log_proxy + sudo-wrap"，Java 夹具改用 `docs/qwen38-4090-vllm-extreme-v1.0/fixtures/java-agent-*`，runner 复用 `output/qwen38-4090-compare/scripts/run_pi_java.sh`。
5. **工具链**：toolchain 容器指定 `nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04`（已在本机）；rustup 固定版本；`KERN_SM=sm_89` 进入 artifact_key（POC 05 已计划，要落到 `handwritten.py` 补丁）。
6. **显存表**：04 补权重分项（W4 11.7 / embed 2.37 / lm_head 2.37 / KV 4.5 / state / workspace），并给出 embed 留主机、lm_head INT8 两种变体的余量。
7. **性能口径**：13 增加 roofline 段（每 step 字节数 → 上限），eager 阶段不报 tok/s；门禁改相对口径。
8. **工作量与止损**：00 加分阶段估算；15 加 T06 超期、余量不足两条止损。
9. **网络策略**：GitHub 可达时走在线 `cargo vendor` + 校验；离线 bundle 作后备；`pegainfer-frontend` git 依赖必须进 vendor。
10. **文档滞后修正**：784 页表述；"600GB SSD"；`preflight` declared/observed 分列；`self_check` numpy 前置。

---

## 8. 推荐路线（替代 kern）

| 优先级 | 动作 | 成本 | 预期 | 风险 |
|---|---|---|---|---|
| A | **保持 NInfer 44a2c6c 现网不动**；把 12-D 的 `rk8v4` 200192 档作为"性能优先"备选 profile（systemd 第二 unit，不改默认） | 配置，1 小时 | decode +15–30%（4k 145 / 64k 129 / 184k 104） | 窗口 200192；需再跑一次 medium 阶梯确认 |
| B | NInfer 源码 P2（报告 09 已列）：draft-head Ada MMA、`e8_root_codec` bfi/redux、`--auto-long-anchors` 设计移植（仅当真实 OpenClaw 会话抓到 `full_reset`） | 周级，C++/CUDA，且是 sm_89 已有代码的增量 | decode / prefill 各 3–10% | 每项需单独 tag + bench，报告 13 的 3%/10% 阈值可直接沿用 |
| C | **一次有界实验**：本机 `~/qwen38-vllm` 用 `CTX=fast SPEC=dflash2`（64K）跑同一套 HTTP 阶梯 + Java 三题 | 半天，无内核工作，镜像与权重已在 | 回答"DFlash2 在 4090 上是否真到 130–160 tok/s greedy"；若是，这是 NInfer 的下一步方向 | vLLM 的 Agent TTFT（4k 6.7 s vs 1.2 s）与首题 JIT 已知差；采样下接受率会掉 |
| D | 跟踪 NInfer 上游对 DFlash2 draft 的支持；一旦 loader 契约更新，优先在 NInfer 里做 | 观察 | 1.5–2× decode 潜力 | 依赖上游 |
| E | kern 仅作为"可审计制品"研究：按 §7-1 的方向做一个**不追求性能**的 manifest 化实验 | 周级 | 制品可证明；为将来 Blackwell 卡预研 | 与生产无关，不要占用 4090 维护窗口做性能对比 |

不建议：Lucebox（报告 01：180k prefill 164 s / 1100 tok/s，慢于 NInfer）；llama.cpp WORK 回退；rk2v4-e8（Java 题3 失败）。

---

## 9. 附录

### 9.1 关键实测命令（可复现）

```bash
ssh 192.168.10.29 'nvidia-smi; nvidia-smi --query-gpu=pcie.link.gen.max,pcie.link.width.max --format=csv'
ssh 192.168.10.29 'which nvcc cargo pi; /usr/local/cuda-12.3/bin/nvcc --version | tail -1'
ssh 192.168.10.29 'docker images | grep -E "cuda|ninfer|qwen38"; docker ps --format "{{.Names}} {{.Image}}"'
ssh 192.168.10.29 'ss -ltn | grep -E "18343|18030|28343|18041|18042"'
ssh 192.168.10.29 'cat /home/hhtele/qwen38-vllm/models/Qwen3.8-27B-W4A16-AutoRound/.cache/huggingface/download/tokenizer.json.metadata | head -1'
ssh 192.168.10.29 'timeout 6 curl -sS -o /dev/null -w "github:%{http_code}\n" https://github.com'
# POC 自检 / 只读 preflight（在 /tmp 副本上执行后已删除）
bash scripts/self_check.sh      # 需 numpy；63 tests OK
bash scripts/preflight.sh       # results/preflight.json
```

kern 侧：

```bash
cd /Users/luo/Documents/github/kern
git rev-parse HEAD                                  # 5188aaf8dc992ebe635f111d17c269969706da27
rg -n 'KERN_SM' tools/                              # 默认 sm_103a
rg -n 'extern:cublas' crates/kern-runtime/src/compile.rs
python3 -c "import json;m=json.load(open('examples/qwen3.8-27b.json'));print(m['constants'])"
```

### 9.2 数字来源速查

- 4090 带宽 1008 GB/s：NVIDIA 规格（GDDR6X 21 Gbps × 384 bit）。
- dbirks 参数计数：模型卡"24.33 B in 4-bit tensors + 3.45 B BF16 = 27.78 B"，"about 4.1 effective bits/weight"。
- NInfer no-spec 50.5 / MTP3 148.6 / 115K prefill 2409：`tensorninja/ninfer-4090` README。
- kern GB300 105 / 261：`docs/site/getting-started/index.md`（claim，无 raw）；80.8 / 177.9 vs vLLM 95.0 / 175.6：`docs/qwen38-bringup.md` L381–387（2026-08-31）；105.1 / 181.4 vs 95.1 / 171.4：分支 `fuse/qwen38-decode` 提交 `958efa0`（tray14，2026-09-01）；conc1 114：`docs/serve.md`（2026-09-03）。
- vLLM recipe 4090 单用户 121/130/163.5 tok/s：本机 `~/qwen38-vllm/README.md`（= `kernel-sanders/qwen38-27b-rtx4090-vision`，pinned `36317835`）；本地仅测过 `SPEC=mtp CTX=huge`（报告 11）。

### 9.3 安全提醒（与本任务相关，未处理）

[REDACTED sudo credential line]

### 9.4 本报告的局限

- 带宽与显存账是推算，不是 kern 在 4090 上的实测（kern 目前无法在 4090 上运行，也不存在可实测的 sm_89 制品）。
- kern 7 个远端分支只做了 git 级巡检（`log` / `diff --stat` / 树哈希 / `show` 关键文件），未 checkout、未编译、未逐文件审阅；与 POC 结论直接相关的提交（`29dbc9c`、`0736fe7`、`3b21729`、`c5848cd`、`958efa0`、`c7c3ad0`、`0935fa3`）已亲自核对。
- kern-serve 是否经 `pegainfer-frontend` 间接支持 `tools` / `tool_calls`，未读该 git 依赖的源码；报告中的 "not found" 仅限 kern 仓库本身。
- vLLM `CTX=fast SPEC=dflash2` 的 130–163 tok/s 是 recipe 作者数字，本机未验证。
- 未评估 kern / NInfer 的许可证细节对"内核反哺"的约束（kern Apache-2.0；NInfer fork LICENSE 11357 B，形似 Apache-2.0，未逐字核对）。
