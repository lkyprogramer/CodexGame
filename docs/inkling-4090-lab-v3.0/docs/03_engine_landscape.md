# 03 · 引擎调研（2026-11-26 快照）

数字均为作者或社区报告，**不是本机结果**，除非标注“4090 实测”。所有仓库按 [09](09_sources.md) 锁定 commit。

| 引擎 | 语言 / 许可 | Inkling 支持 | 报告的速度 | 与本项目的关系 |
|---|---|---|---|---|
| **Astral**（S10） | Rust 主机 + 手写 CUDA，Apache-2.0 | 专为 Inkling-2-Mini（另有 Qwen3.8）；GGUF 与原生 safetensors 都能加载；DSpark 自适应草稿长度 + conv 状态回滚 | H100 PCIe：172 tok/s 无草稿，233 tok/s 带 DSpark（32 prompt 平均）；vLLM 130 / 210 | **选定底座**。sm_89 能构建但作者未测试；上下文上限 8192 |
| llama.cpp mainline（S20） | C++，MIT | `inkling2_loop` 已合并；DSpark 已合并；CUDA 侧的索引化相对 bias（#33063）与融合（#33060）尚未合并 | 4090 社区 ≈51 tok/s | **数值参考**：同一 GGUF 的 eval-callback、KLD 基准 |
| HF transformers `inkling2_loop`（S21） | Python | 官方语义实现 | — | 语义第二参考；BF16 全量需 >48 GB，本机只能读代码 |
| tqllm（S11） | C++，Apache-2.0 | 加载官方 checkpoint；精确模式 KLD 0.0023（对 BF16）；支持 DFlash2；声明支持 RTX 30/40/50 | — | 可选速度 / 精度对照（Docker，需用户同意） |
| Xolotl（S12） | 基于 Strata，MIT | 4090 实测 | 113–127 tok/s，DSpark 136；k8v4 KV 下 512K | 4090 上的现实参照 |
| atlas-ingine（S13） | Apache-2.0 | 自有 atlas-12g 量化 | 4090 报告 236.7 tok/s（64K） | 4090 上的速度上界参照；量化不同，不能直接比较 |
| LoopBridge（S14） | Python | 预填 / 解码的循环拆分研究（Mini 与 varloop） | — | R4 / R6 的方法参考 |
| prototux llama.cpp 补丁（S15） | C++ | 跨遍 KV 共享 | 上下文约 2 倍，但出现重复退化 | R4 的反例数据 |
| erisinky（S16） | Rust + Metal | 从零实现 | — | Rust 写法参考，不能在 CUDA 上用 |
| Strata v0.2.22 + SQ 包（S17） | MIT | Inkling SQ-10/15/20 | — | 可选业务对照；与生产同栈 |
| vLLM / SGLang | Python | 仅 Hopper+（社区有 sm80/86 移植） | H100 130 / 136 | 不在 4090 上使用 |

## 为什么是 Astral

1. **结构正好**：单模型，整条前向在 `crates/model/src/inkling.rs` 的 `forward` / `layer` 中，一层对应 llama.cpp 的一次 `build_layer`。改遍数、插探针、换 KV 布局，都是在一个文件里改。
2. **验证工具现成**：
   - `selftest`：每个 kernel 对 CPU 参考。
   - `verify-embd` / `verify-model`：逐算子对 llama.cpp 的 eval-callback 日志。
   - `cmp-prefill`：批量预填对逐 token 解码。
   - `spec-generate`：投机解码对普通贪心。
   - `bench/golden_llamacpp.sh`：生成 llama.cpp 侧的参考数据。
3. **sm_89 风险低**：kernel 选择不依赖 `ArchProfile`，而是看 fatbin 里有没有对应 SASS，以及少数显式的 cc 判断（PDL 要求 cc ≥ 9，wgmma 要求 cc = 9）。非 Hopper 路径用 `mma.sync` / `dp4a` / `cp.async`，sm_89 全都支持。详见 [04](04_astral_fork.md) §2。
4. **许可与语言**符合用户选择（Rust，Apache-2.0）。

## 主要风险

- 作者只在 A100 和 H100 上做过验证；sm_89 只有 100 KB/SM 共享内存、128 个 SM、72 MB L2，调优参数需要重做。
- 8192 上下文上限需要新写 kernel。
- 项目很新（2026-11 起），上游变动快：锁定 commit，按需 cherry-pick。
