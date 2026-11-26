# 09 · 来源登记

读取日期均为 2026-11-26。“锁定”是本包使用的版本；升级需要另立任务。

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
| S21 | HF transformers `models/inkling2_loop/modeling_inkling2_loop.py` | main，读取时 85,906 B | 语义第二参考 |
| S22 | llama.cpp PR：已合并 #32217、#32694、#32704、#32799、#32855、#32218、#33053；未合并 #33063、#33060、#33049、#33073 | 状态以 v2.1 `43` 文档记录为准 | 长上下文 bias 语义与 4090 融合参考 |
| S23 | conda 频道 `nvidia/label/cuda-12.8.1` | label 即版本 | 用户目录 CUDA 编译工具 |
| S24 | rustup / static.rust-lang.org；备用 rsproxy.cn | Rust 1.100.0（由 S10 的 `rust-toolchain.toml` 决定） | 用户目录 Rust |

v2.x 中的其他来源（Atomic、Ghost、Magnitude、2DSD、CUDA Rust 等）不再使用，仍保存在 `docs/atomic-inkling-4090-plan-v2.0/docs/02_evidence_register.md`。
