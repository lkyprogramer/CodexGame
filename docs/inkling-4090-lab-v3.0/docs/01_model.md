# 01 · 模型、状态与资产

## 1. 配置事实（官方 `config.json` @c9d0283，S01）

| 项 | 值 |
|---|---|
| 架构 | `inkling2_loop`：24 个物理层；核心层 [6,18) 跑 3 遍 → 每 token **48 个 slot（层访问）** |
| 维度 | hidden 2304；Q 24 头 / KV 8 头；head_dim 128 |
| 注意力 | 20 个 SWA 物理层（窗口 1024）+ 4 个全局物理层（5/11/17/23）→ 40 个 SWA slot + 8 个全局 slot。**无 RoPE**：位置信息来自学习的相对位置 bias（`d_rel` 16，extent 1024；全局层带对数缩放 τ）、注意力 sink 和 sigmoid 输出门 |
| 短卷积 | kernel 4，作用于 K、V、注意力输出、FFN 输出；每个 slot 有独立的递推状态 |
| 残差 | 块级注意力残差 mix（每块 6 层），各 slot 输入是若干历史块的 softmax 加权 |
| 循环控制 | 核心层的 Q/K/V/FFN 各有一个 controller，rank 64：`x' = x − forget·x + gain·m`，m 是从上一遍构造的消息 |
| MoE | 128 专家，top-8，intermediate 1152；sigmoid 路由，bias 只参与选择；SiTU 激活；route_scale 8；softcap gate 4 / up 25 |
| 输出 | 词表 201024（有效 200058），final logit softcap 30 |
| 草稿 | 原生 MTP/DSpark：3 层，block 8，target layers [5,23,41,48] |
| 原生精度 | 专家 NVFP4，部分层 MXFP8，其余 BF16；约 20.2 GB |

逐算子语义以 llama.cpp `inkling2_loop` 图为准，HF transformers `modeling_inkling2_loop.py` 为第二参考。Astral 的 spec 06（S10）已把语义逐条写清，本包不重复，研究时直接读它。

## 2. varloop 研究版（S02）

`thinkingmachines/TML-d24-varloop-research` @91a57fe 与正式版结构相同（文件大小逐个相同），差别是 `loop_config.is_varloop: true`，即训练时遍数可变。它是 [06](06_loop_research.md) 中“改遍数”实验的主体。正式版只作为对照：没有为改遍数训练过，预期会退化。

## 3. 4090 显存预算（推断，P1/P4 实测校准）

| 项 | 大小 |
|---|---|
| 设备总量 | 24564 MiB；CUDA context 与驱动保留约 0.5 GiB |
| 权重：UD-Q4_K_XL | 17,629,760,736 B = 16.42 GiB |
| DSpark 草稿（原生 mtp 转换） | ≈0.6 GiB |
| KV，Astral 现状（48 slot × capacity，f16） | 192 KiB/token → 8192 时 1.5 GiB；**现状最多约 2.7 万 token**，且被 `MAX_CTX=8192` 卡住 |
| KV，P4 目标（40 个 SWA 环形 1024 + 8 个全局按需分配） | 160 MiB 固定 + 32 KiB/token → 32K 1.16 GiB；64K 2.16 GiB；128K 4.16 GiB |
| conv 状态 | 48 slot × 6656 通道 × 3 × 4 B ≈ 3.7 MiB |
| 草稿器 KV / 回滚快照、工作区、CUDA graph | 未知，P1 用 `nvidia-smi` 与 `astral hw` 实测 |

结论：P4 完成后，128K（f16 全局 KV）在 4090 上可行，余量约 1.5–2 GiB；全局 KV 改成 q8 后可以更长。

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

下载、改名、校验之后生成 `$LAB/models/models.lock.json`，逐文件记录来源仓库、ModelScope 路径、HF revision、字节数和 SHA256。磁盘占用：A1+A2+A3+A4 ≈ 61 GB，加上 A5/A6 约 63 GB；工具链与构建产物另需约 30 GB。

## 5. 指纹

每次运行记录 `model_sha256`、Astral commit、`BUILT_ARCHS`、`NVCC_VERSION`、llama.cpp commit、驱动指纹文件的 hash。换文件或换布局视为新的实验纪元，旧结论不能沿用。
