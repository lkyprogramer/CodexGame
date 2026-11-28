# 09 · 来源登记

读取日期均为 2026-11-26（S32–S39 为 2026-11-27，S41–S46 为 2026-11-28）。“锁定”是本包使用的版本；升级需要另立任务。

| ID | 来源 | 锁定 | 用途 |
|---|---|---|---|
| S01 | HF `thinkingmachines/Inkling-2-Mini` | `c9d028302cd0f035fdf8e7e91f089a4ce94d2195` | 配置、分词器、DSpark（A3） |
| S02 | HF `thinkingmachines/TML-d24-varloop-research` | `91a57fe2b779bbd12c0f74d1f518cbd5b84e8d0d` | varloop 研究模型（A4） |
| S03 | HF `unsloth/Inkling-2-Mini-GGUF` | `8078d149286eec7193795413b9e0643da6d11fa1` | A1、A2、A6 |
| S04 | HF `ggml-org/Inkling-2-Mini-GGUF` | `0bdc580634ceac4c4d921f452777bf44228de9af` | 未选用（类型不受 Astral 支持），备查 |
| S05 | HF `incoai/Inkling-2-Mini-DFlash2` | `4f9088ea66c21f2b99ed657d1941c306b03e84d2` | A5 |
| S06 | ModelScope 镜像（同名仓库） | 以 HF LFS SHA256 校验，不锁 revision | 4090 下载渠道 |
| S10 | GitHub `syntheticminds-lab/Astral-Inference-Server` | `49a0a2bee3270ad7518cebe7a059496b250180d1` | 自有引擎底座；spec 01/03/06/08、engineering-log、`bench/golden_llamacpp.sh` |
| S11 | GitHub `turbo-tan/tqllm` | `7df840632cd3f108de459e0944b9b6d115532689`；镜像 `ghcr.io/turbo-tan/tqllm:1.7.0` | 可选对照（O1） |
| S12 | GitHub `Indras-Mirror/Xolotl` | `3435d55daaccad3f60377e7b7886835e0c00f87d` | 4090 速度参照 |
| S13 | GitHub `Atlas3DSS/atlas-ingine` | `f0f2740b3e8c8ec0d7245676e22177c1fa44876e` | 4090 速度上界参照 |
| S14 | GitHub `yanghu819/loopbridge` | `cae30a0291d048e33c4c8d7459a441cbbd79c269` | R4、R6 方法参考 |
| S15 | GitHub `prototux/llamacpp-inkling2mini` | `694eb0e30c7204d463f6910c395915a28b940977` | R4 反例 |
| S16 | GitHub `Eriskii/erisinky` | `3890bd523577af0b7d438edddf62ea27b64028ec` | Rust 写法参考 |
| S17 | Strata v0.2.22 与 HF `strata-engine/Inkling-2-Mini-Strata` | `04996a1…`（v2.1 记录） | 可选业务对照（O2） |
| S20 | GitHub `ggml-org/llama.cpp` b12751 | `532d67426bb874f06a8acc6959af81b34206f7f9` | 数值参考 |
| S21 | HF transformers `models/inkling2_loop/modeling_inkling2_loop.py` | `3d2d3b3f7bed13f858da128cd932a2f8d36e1490`（v3.0.7 起；此前记为浮动的 main，读取时 85,906 B） | 语义第二参考；controller 的 tanh 门、per-pass cache 已按此 commit 核实 |
| S22 | llama.cpp PR：已合并 #32217、#32694、#32704、#32799、#32855、#32218、#33053；#33073（DFlash2）于 2026-11-26 合入（`55d4828`，首个包含它的 release 为 b12785，2026-11-28 核实）；未合并（2026-11-26 查询）#33060（head `89478df`）、#33063（`a5e1731`）、#33049（`39e7ac1`）、#33062（`93e5e76`）；#33072 已关闭未合并 | 未合并的按 head commit 记录，采用前另立任务 | 长上下文 bias 语义、4090 融合（K3）、DFlash2 契约、NVFP4 转换的参考 |
| S23 | conda 频道 `nvidia/label/cuda-12.8.1` | label 即版本 | 用户目录 CUDA 编译工具 |
| S24 | rustup / static.rust-lang.org；备用 rsproxy.cn | Rust 1.100.0（由 S10 的 `rust-toolchain.toml` 决定） | 用户目录 Rust |
| S25 | HF transformers PR #51161（last-history KV） | 动态 PR 页，状态以 2026-11-26 查询为准（open） | R4 的 B 臂 |
| S26 | Goodfire, *Interpreting Inkling 2 Mini*（2026-11-20），https://www.goodfire.com/research/interpreting-inkling-2-mini/ | 文章 | T15 / R2 的第一个复现目标 |
| S27 | LoomKV，arXiv:2611.32954v1 | v1 | KV 无损编码参考（[06](06_loop_research.md) §4） |
| S28 | Inkling SRFT KV，arXiv:2611.29092v1；GitHub `aminems/inkling-1m-mlx` | `51e1653dc55aa4153e809d43f76ace45ea7e7769` | 模型特定的有损 KV 量化参考 |
| S29 | GitHub `SqueezeAILab/2DSD` 分支 `feat/inkling-dspark` | `962874f303c3142406ab3eecfae2bb51567815c9` | 完整 coda 读出与 feature 契约参考 |
| S30 | GitHub `lkyprogramer/inkling-4090-engine`（本项目的 Astral fork） | `e484873` 起 | 自有引擎的代码真源 |
| S31 | 用户提交的研究评审，CodexGame 仓库 `docs/Inkling-4090-Lab-v3-Research-Review-2026-11-26.md` | 提交 `1747d69` | v3.0.7 修订的依据；其中外部来源按本表核实 |
| S32 | 方案 10，CodexGame 仓库 `docs/10_molt_loomformer_inkling4090_plan.md`（提案 1.0，基于 fork `18bf3e3`、本包 `9f6d4b0`） | 提交 `f145b79` | v3.0.14 新增 T22–T25、R11–R13 与 T16 / T17 / T21 细化的依据；其中代码结论按 fork 源码核实 |
| S33 | MoLT，arXiv:2611.34923v1（*Mixture-of-Loops Transformer*）；GitHub `hustvl/MoLT` | `1313b83adf05f666726bf009014f5f50ae345b23` | R12、R13 的严格前缀反馈参考 |
| S34 | LoomFormer，arXiv:2611.30634v2（*Rewirable Circuits in Transformers with Loom Attention*）；GitHub `Caiyun-AI/LoomFormer` | `e52e5761d36066ed62e061a044d8314437cb7b11` | R11、R13 的矩阵深度接口参考 |
| S35 | GitHub `ddalcu/mlx-serve` PR #1331（已合并） | head `ad695002aa89fda7ac27b901d7474ddc84299af8`，merge `6ba6d34ea0bc265dc19b5b737fa21138b2a228e1` | 开放 verify、few_tail（K9）、成本阶梯、请求隔离、末行 head 的工程参考（T21、T25） |
| S36 | GitHub `ddalcu/mlx-serve` PR #1330（open draft） | 2026-11-27 查询 head `5e556773ecf6923ada146b44bab534bf05e02ae3`（方案 10 记录时为 `6a22c34`，此后有新提交） | 只作参考，不是 #1331 的超集；采用前另立任务 |
| S37 | 方案 11，CodexGame 仓库 `docs/11_inkling4090_new_optimization_plan_20261127.md`（基于 fork `744e32a`、本包 `19a431a` / v3.0.14） | 提交 `e1941a9` | v3.0.17 新增 T26–T31 的依据。源码结论已按 fork `3f5a49d` 核实；它的外部来源（S01–S16）没有逐条复核，引用时标“方案 11 所述” |
| S38 | HF `ISTA-DASLab/Inkling-2-Mini-GSQ-RCO-GGUF`（GSQ arXiv:2604.18556，RCO arXiv:2605.00649） | revision `f0da1097633dd7c2f5733e4077cff861be122245` | [01](01_model.md) §4.1 的候选资产；ModelScope 镜像缺 dspark 文件 |
| S39 | HF `abenzerps/Inkling-2-Mini-GSQ-RCO-GGUF` | revision `78c95a16e097cb30ff975a0374293188aae0c339` | 同上；`SHA256SUMS.txt` 与 ModelScope 一致 |
| S40 | 方案 12，CodexGame 仓库 `docs/Inkling_4090_Adaptive_Loop_Exploration_Plan_20261127.md`（GPT，基于 fork `aa837c7`、本包 `159edbb` / v3.0.18） | 提交 `ccc951d`；§16 为本包 v3.0.19 的核实与编排补充 | T32–T36、R14 的依据；第 1–15 节的 NEW 接口全部未实现 |
| S41 | 方案 13，CodexGame 仓库 `docs/13_inkling_loop_model_extreme_research_plan_20261128.md`（GPT，基于 fork `7108b78`、本包 `475d4c8`） | 提交 `e3c61f4` | T37–T40 的设计、T41 的部分依据；对本包已有工作的核实发现见 [07](07_tasks.md) 的 v3.0.21 记录 |
| S42 | MTB 方案，CodexGame 仓库 `docs/Inkling_4090_Mirage_TileLang_Basalt_Exploration_Plan_20261128.md`（GPT，基于 fork `e83ef7d`、本包 `32ca786`） | 提交 `e3c61f4` | T41、T42、K14、K17 |
| S43 | GitHub `MiaAI-Lab/Inkling-2-Mini-RTX-5090-TensorFold`（RTX 5090 / sm_120 上对 `jschmied/TensorFold` `dc2ca8a` 的 0001–0028 补丁集） | `86f1d69` | T44（0003 的 FP8 KV）、T45（qmmf 契约）、K12、K13、K15；分析见 [tensorfold.md](../research/20261128/tensorfold.md)。sm_120 专有的 0014、0024、0025 在 sm_89 上不可用 |
| S44 | DFlash2：HF `incoai/Inkling-2-Mini-DFlash2`（A5，[01](01_model.md) §4）；`z-lab/dflash` `07ebd93`；论文 arXiv 2602.06036；`tonyd2wild/Inkling-2-Mini-NVFP4-DGX-Spark` `2fe0eb5`（vLLM 补丁与 CPU 参考 `inkling2_dflash2_ref.py`）；llama.cpp #33073（见 S22） | 同左 | T43；分析见 [dflash2.md](../research/20261128/dflash2.md) |
| S45 | `mirage-project/mirage` `ed771bd`（mpk）、`tile-ai/tilelang` `640fdca`、`losingle/basalt` `aa69624` | 同左 | T44 的 INT8 臂、T47、K14–K17；分析见 [kernels.md](../research/20261128/kernels.md) |
| S46 | LoopTitan（arXiv 2611.34821v1，`datamllab/LoopTitan` `a9f526a`）、QDA（arXiv 2611.23388v1，`humanfia/qda` `dc39a02`）、Self-Rewriting（arXiv 2611.21885v2） | 同左 | T37–T40 的先验、T46、R15；分析见 [papers.md](../research/20261128/papers.md) |

v2.x 中的其他来源（Atomic、Ghost、Magnitude、CUDA Rust 等）只作方法参考（[03](03_engine_landscape.md)），不再锁定，仍保存在 `docs/atomic-inkling-4090-plan-v2.0/docs/02_evidence_register.md`。
