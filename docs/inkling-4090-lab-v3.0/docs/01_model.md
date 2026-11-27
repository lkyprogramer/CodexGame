# 01 · 模型、状态与资产

## 1. 配置事实（官方 `config.json` @c9d0283，S01）

| 项 | 值 |
|---|---|
| 架构 | `inkling2_loop`：24 个物理层；核心层 [6,18) 跑 3 遍 → 每 token **48 个 slot（层访问）** |
| 维度 | hidden 2304；Q 24 头 / KV 8 头；head_dim 128 |
| 注意力 | 20 个 SWA 物理层（窗口 1024）+ 4 个全局物理层（5/11/17/23）→ 40 个 SWA slot + 8 个全局 slot。**无 RoPE**：位置信息来自学习的相对位置 bias（`d_rel` 16，extent 1024；全局层带对数缩放 τ）、注意力 sink 和 sigmoid 输出门 |
| 短卷积 | kernel 4，作用于 K、V、注意力输出、FFN 输出；每个 slot 有独立的递推状态 |
| 残差 | 块级注意力残差 mix（每块 6 层），各 slot 输入是若干历史块的 softmax 加权 |
| 循环控制 | 核心层的 Q/K/V/FFN 各有一个 controller，rank 64：`x' = x − forget·x + gain·m`，m 是从上一遍构造的消息。forget 与 gain 都经 **tanh**（HF 实现核实），可以为负、keep 可以 > 1，不是概率 |
| MoE | 128 专家，top-8，intermediate 1152；sigmoid 路由，bias 只参与选择；SiTU 激活；route_scale 8；softcap gate 4 / up 25 |
| 输出 | 词表 201024（有效 200058），final logit softcap 30 |
| 草稿 | 原生 MTP/DSpark：3 层，block 8，target layers [5,23,41,48] |
| 原生精度 | 专家 NVFP4，部分层 MXFP8，其余 BF16；约 20.2 GB。A1（GGUF）是 NVFP4 ×40 + Q8_0 ×154 + BF16 + F32 的混合，不是单一 4 位；原生 MXFP8 在 GGUF 里变成 Q8_0，把 NVFP4 解码成 BF16 也恢复不了原文件没有存的信息 |

逐算子语义以 llama.cpp `inkling2_loop` 图为准，HF transformers `modeling_inkling2_loop.py` 为第二参考。Astral 的 spec 06（S10）已把语义逐条写清，本包不重复，研究时直接读它。

## 2. varloop 研究版（S02）

`thinkingmachines/TML-d24-varloop-research` @91a57fe 与正式版结构相同（文件大小逐个相同），差别是 `loop_config.is_varloop: true`。模型卡原文（v3.0.7 核实）：第一阶段中训练与 Mini 共用；中训练的其余部分按 **1:2:6:2:1** 抽样 **1–5 遍**训练，之后以 **3 遍**做 post-training。所以 1–5 遍是它的训练分布内，6 遍以上是外推；它与固定 Mini 的后期训练不同，是另一个模型身份。它是 [06](06_loop_research.md) 中“改遍数”实验的主体；正式版只作截断敏感性对照。A4 是原生格式，A1 是 GGUF，跨两者比较前先统一或写明加载与计算精度，避免把格式差异归因到循环。

## 3. 4090 显存预算（推断，P1/P4 实测校准）

| 项 | 大小 |
|---|---|
| 设备总量 | 24564 MiB；CUDA context 与驱动保留约 0.5 GiB |
| 权重：UD-Q4_K_XL | 17,629,760,736 B = 16.42 GiB |
| DSpark 草稿（原生 mtp 转换） | ≈0.6 GiB |
| KV，Astral 现状（48 slot × capacity，f16） | 192 KiB/token → 8192 时 1.5 GiB；**现状最多约 2.7 万 token**，且被 `MAX_CTX=8192` 卡住 |
| KV，P4 目标（40 个 SWA 环形 1024 + 8 个全局按需分配） | 160 MiB 固定 + 32 KiB/token → 32K 1.16 GiB；64K 2.16 GiB；128K 4.16 GiB |
| KV，T17 的实际设计（v3.0.14；SWA slot 为 W + max(tmax, 8) 行，取整到 64；[04](04_astral_fork.md) §3.2） | 默认 tmax 2048：SWA 3072 行，共 480 MiB 固定 + 32 KiB/token → 32K 1.47 GiB；64K 2.47 GiB（比上一行 +14%）；128K 4.47 GiB（+7.5%）。`ASTRAL_TMAX=512` 时 SWA 240 MiB：64K 2.23 GiB，128K 4.23 GiB |
| T17 实测峰值（`nvidia-smi` memory.used，不开草稿，[07](07_tasks.md) T17） | 16K 19674 MiB；32K 20190；64K 21220；128K 23280（余约 1.25 GiB）。开 DSpark：32K 21702，64K 23474，73728 能放下，77824 OOM |
| conv 状态 | 48 slot × 6656 通道 × 3 × 4 B ≈ 3.7 MiB |
| DSpark 草稿 KV（fork `dspark.rs`，v3.0.14 核实） | FP32，3 层 × 8 头 × 128 × K / V，按 capacity 全长分配：24 KiB/token → 32K 0.75 GiB，64K 1.5 GiB，128K 3.0 GiB |
| 回滚快照、工作区、CUDA graph | 未知，P1 用 `nvidia-smi` 与 `astral hw` 实测 |

以上都是按已知形状算出的理想稳态容量，不是分配器实测；verify 窗口的暂存、回滚余量、对齐、coda lens 副本、graph、工作区、草稿器和 CUDA context 另计。SWA 环形缓冲还要处理同批写入覆盖（[04](04_astral_fork.md) §3.2：W = 1024、C = 512 时多约 79.8 MiB）。

**遍数 R 改变时状态也跟着变**（保持同样的层结构）：visit = 12 + 12R，全局 visit = 2 + 2R，SWA visit = 10 + 10R；每个 visit 每 token 的 f16 KV 为 2 × 8 头 × 128 × 2 B = 4096 B。

| R | visit | 全局 | SWA | 128K 理想 f16 KV（SWA 环形 1024） |
|---:|---:|---:|---:|---:|
| 1 | 24 | 4 | 20 | 2.078 GiB |
| 2 | 36 | 6 | 30 | 3.117 GiB |
| 3 | 48 | 8 | 40 | 4.156 GiB |
| 4 | 60 | 10 | 50 | 5.195 GiB |
| 5 | 72 | 12 | 60 | 6.234 GiB |
| 6 | 84 | 14 | 70 | 7.273 GiB |

所以 R1 的深度研究和 128K 研究要分开做：三遍 128K 放得下，不代表五遍、六遍加多套读出缓存也放得下。

结论：P4 完成后，128K（f16 全局 KV、三遍、**不开草稿**）在 4090 上按预算可行，余量约 1.5–2 GiB（推断，T17 实测）；全局 KV 改成 q8 后可以更长。开 DSpark 时，128K 的草稿 KV 3.0 GiB 加目标 KV 4.47 GiB，与权重、context 合计已超过 24 GiB：要么草稿 KV 压缩（local 层 ring、FP16，T21），要么长上下文时关草稿。G4 按用户决定（2026-11-27）改为“4090 显存能放下的最大上下文”，不强制 128K，预算对照只作记录（[00](00_plan.md) §2）。

## 4. 资产（下载走 ModelScope；以 HF 的 LFS SHA256 校验）

4090 无法直连 huggingface.co；hf-mirror 的大文件仍跳到 HF 的 xethub CDN，实测 0.06–1.5 MB/s。ModelScope 七个仓库都有镜像，SHA256 与 HF 一致，实测约 10.9 MB/s（2026-11-26）。ModelScope 的 `master` 不是 HF 的 commit，所以**身份以下表的 SHA256 为准**。

| ID | 仓库（HF revision） | 文件 | 字节 | SHA256（HF LFS oid） | 用途 |
|---|---|---|---|---|---|
| A1 | unsloth/Inkling-2-Mini-GGUF @8078d14 | `Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf_file`（下载后去掉 `_file`） | 17,629,760,736 | `e64276656f072e9b2197a61723667cbdb71da66a716ffd966e572c21088f3cd3` | **主模型**；Astral 和 llama.cpp 共用 |
| A2 | 同上 | `Mainline_Support/Inkling-2-Mini-UD-Q8_K_XL.gguf_file` | 22,867,452,896 | `2da51788d43a17e1f033bec420fa83ba9cb87ac1f0130dc9135a4d2ed2678b68` | llama.cpp 质量参考（部分 offload） |
| A3 | thinkingmachines/Inkling-2-Mini @c9d0283 | 除 `model-00001-of-00001.safetensors` 外的全部文件 | ≈0.68 GB | `mtp.safetensors` = `7c3b651317f01f73bcf4e1dceba66ef8b7e1a1eac6bc171e882e690a4b10a1d2`；其余小文件用 ModelScope 列表的 Sha256，记入 lock | 分词器、chat 模板、DSpark 草稿（Astral 的 `--checkpoint` 目录） |
| A4 | thinkingmachines/TML-d24-varloop-research @91a57fe | 全部文件 | 19,526,019,168 + 635,801,416 + 小文件 | shard `79e60b65c4f2a2a5acdb8e3c7b6994bf00da5477f45d18027afbfad752a64595`；mtp `905d548692b1eb1d1aa278b8798db66ff88d94d0fc7609bf77baab90e99c76c7` | P5 研究；Astral 直接加载原生 checkpoint（MXFP8 加载时转成 Q8_0） |
| A5（可选） | incoai/Inkling-2-Mini-DFlash2 @4f9088e | `model.safetensors` + config | 989,975,616 | `217980ab00d116693fa5946df7bbfd967caf5fac1f529afd541fbd470ddb54ee` | R7 草稿器研究 |
| A6（备用） | 同 A1 | `Mainline_Support/dspark-Inkling-2-Mini-Q8_0.gguf_file` | 503,889,952 | `3da00cf7c31bbe5662b3c0d373ecf782d74d32ef43990acc158ce60c2add72e0` | llama.cpp 的 DSpark 对照 |

**不选的文件**：

- UD-IQ4_XS 与 ggml-org IQ4_NL：Astral 只有 F32 / BF16 / Q8_0 / NVFP4 的 kernel，加载这两个会报 unsupported type。
- ggml-org NVFP4：ModelScope 上没有，而 A1 已经是 NVFP4 + Q8_0 布局（Astral 在 A100 上读文件头得出；P1 用 `gguf-info` 复核）。
- varloop 的 GGUF：只有 IQ4_NL / Q8_0 / BF16，所以研究直接用 A4 原生 checkpoint。
- GSQ-RCO 低位 GGUF（ISTA-DASLab、abenzerps，2026-11-26 发布）：见 §4.1，不替换 A1。

下载、改名、校验之后生成 `$LAB/models/models.lock.json`，逐文件记录来源仓库、ModelScope 路径、HF revision、字节数和 SHA256。磁盘占用：A1+A2+A3+A4 ≈ 61 GB，加上 A5/A6 约 63 GB；工具链与构建产物另需约 30 GB。

### 4.1 候选资产：GSQ-RCO GGUF（v3.0.17 评估，未下载）

来源是两个仓库的模型卡、HF API 与 ModelScope 文件列表（S38、S39），以及 4090 上用 gguf-py 读出的 A1 文件头。

| 仓库（HF revision） | 构建（文件字节） | 量化类型 | ModelScope |
|---|---|---|---|
| ISTA-DASLab/Inkling-2-Mini-GSQ-RCO-GGUF @f0da109 | IQ2_S 8,975,863,424；Q2_K_XL 9,792,516,224；IQ3_XXS 10,608,205,952；IQ3_S 11,425,259,648（卡上推荐，任务平均恢复 99.2%） | `ffn_gate_up_exps` 在 IQ1_S–IQ3_S 中逐层选择；`ffn_down_exps` 为 Q2_0 / IQ4_NL；注意力和 LM head 为 IQ4_XS / Q4_K / Q5_K / Q6_K / Q8_0；`token_embd` 为 BF16 | 有镜像，4 个构建 SHA256 前缀一致；**镜像缺 dspark 文件** |
| abenzerps/Inkling-2-Mini-GSQ-RCO-GGUF @78c95a1 | IQ2_XS 8,476,859,744；IQ3_XS 11,644,899,392（卡上推荐，对 BF16 的 KLD 均值 0.0199）；IQ4_XS 13,577,765,280（KLD 0.0088） | 专家混用 IQ2_XXS–IQ3_S、NVFP4、IQ4_NL、Q2_0；全局注意力（层 5 / 11 / 17 / 23）为 Q8_0；局部注意力为 Q6_K / Q8_0；embedding 与 LM head 为 Q4_K / Q5_K | 有镜像，含 dspark，`SHA256SUMS.txt` 一致 |

A1 的实际构成（文件头）：NVFP4 共 11.47 GB（40 个专家矩阵）；Q8_0 共 6.00 GB（注意力、LM head、`token_embd`，以及 8 个专家矩阵）；合计 17.62 GB。官方发布的专家是 NVFP4 与 MXFP8，所以 A1 的专家与官方同格式（推断：MXFP8 专家转成了 Q8_0；NVFP4 专家是否与官方逐位相同未核实）。

**结论：不替换 A1。** 理由：
1. **加载不了。** Astral 的权重矩阵只接受 F32 / BF16 / Q8_0 / NVFP4，`astral_quant::dequantize` 也只支持这几种外加 F16；Q2_0 甚至不在 `GgmlType` 枚举里。要支持这些文件，需要给 decode、verify、prefill 写 IQ1_S / IQ1_M / IQ2_XXS / IQ2_XS / IQ2_S / IQ3_XXS / IQ3_S / IQ4_NL / IQ4_XS / Q2_0 / K 系列的解码与 GEMV / GEMM，并全部重新验证。
2. **精度更低。** 它们是从官方权重再量化到 2.6–4.2 bpw 的派生资产，A1 基本保持官方精度。本包的研究线（R1–R13）与数值基线（G1–G4、W1 golden、B / C / D 组）都绑定在 A1 上；换资产等于开一个新的实验纪元（§5）。
3. **显存收益有更便宜的替代。** IQ3_S 整个文件 11.43 GB（10.64 GiB，embedding 也放 GPU 时），比 A1 少约 5.8 GiB。按 32 KiB / token 推算，不开草稿理论上可以到约 32 万 token，但现在的上限是 `MAX_CONTEXT`（132096），突破它还要另做验证；开 DSpark 按 56 KiB / token 推算可以到约 18 万 token。不过 DSpark 跑 128K 也可以靠 T21 的草稿 KV 压缩（local 层 ring 加 FP16，128K 时 3.0 → 约 0.5 GiB），不需要换目标权重。
4. **速度收益未知，代价确定。** 按构建不同，专家字节少约 15–45%；dense 部分（注意力投影与 LM head）从 Q8_0 降到 Q4_K–Q6_K / IQ4_XS，字节少约 25–50%。T16 第 1 轮之后的 decode GPU 时间里，专家 GEMV 约占 29%，Q8_0 投影与 head 约占 39%。在同等带宽效率下，decode 的理论上限约快 15–45%（推断）；但 K / IQ 系列每字节的解码运算更多（IQ 还要查码本），4090 上能否达到 Q8_0 dp4a 的约 830–950 GB/s 未知，实际收益要实测。

**DSpark 草稿**：
- 两个仓库的 dspark GGUF 都是用 llama.cpp 从同一个 `mtp.safetensors` 转出来的（ISTA 卡上写明“the draft is not part of the GSQ-RCO search”），权重与 A3 相同。
- Astral 直接读 A3 的 BF16 `mtp.safetensors`，加载时自己转成 Q8_0，并把 Markov head 折叠进 LM head 后再量化（`fold`），所以这些 GGUF 对 Astral 没有新权重。
- 有价值的是一个对照问题：草稿保持 BF16 时接受率会不会更高。ISTA 用两个 prompt 测得 Q8_0 与 BF16 接受率相同；abenzerps 的 Q8_0 版（503,850,784 B）特意保留了 BF16 的 Markov head。这一臂并入 T21：比较草稿权重与 `fold` 用 Q8_0 和 BF16 时的接受率与轮次时间。
- llama.cpp 的 DSpark 对照继续用 A6（503,889,952 B，大小与 abenzerps 版接近，字节不同）。

可选的评估路线是 T31（暂缓）：先在 llama.cpp b12751 上测（卡上要求 ≥ b12611，DSpark ≥ b12720），确认值得之后才考虑给 Astral 写 kernel。

## 5. 指纹

每次运行记录 `model_sha256`、Astral commit、`BUILT_ARCHS`、`NVCC_VERSION`、llama.cpp commit、驱动指纹文件的 hash。换文件或换布局视为新的实验纪元，旧结论不能沿用。
