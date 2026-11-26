# 05 · 验证方法与冻结阈值

## 1. 原则

- 参考实现：**同一个 GGUF（A1）上的 llama.cpp b12751**。Astral 的模型语义本来就是逐步照 llama.cpp 写的，同文件对比可以排除量化差异。
- 阈值相对于参考自身的噪声底设定：Astral 不会被要求比 llama.cpp 自己更一致。
- 下文 §3 的阈值随 v3.0 冻结。噪声底 N0 在 T12 中**先于** Astral 的 KLD 测量。

## 2. 验证阶梯

| 级 | 检查 | 工具 | 任务 |
|---|---|---|---|
| V0 | 每个 kernel 对 CPU 参考 | `astral selftest` | T07 |
| V1 | GGUF 张量表：类型计数（Astral 在 A100 上读到 NVFP4 ×40、Q8_0 ×154、F32 ×518、BF16 ×32），按类型统计的字节数与文件大小相符 | `astral gguf-info A1 --tensors` | T08 |
| V2 | 分词：16 个 prompt 经 chat 模板后的 token id，Astral server 与 `llama-tokenize` 完全相同 | `serve` 的 tokenize 路径、llama.cpp | T10 |
| V3 | 逐算子：embedding 与整条前向对 `llama-eval-callback` 日志 | `astral verify-embd`、`astral verify-model`、`bench/golden_llamacpp.sh` | T09 |
| V4 | 分布：KLD 与 top-1 一致率 | llama.cpp `--kl-divergence-base` + Astral logits 导出 | T12 |
| V5 | 贪心序列：前 128 token | `astral generate`、`llama-cli` / `llama-server` | T10、T12 |
| V6 | teacher-forced：在参考序列上逐位置比较 argmax，记录 top-2 margin | Astral 的 teacher-forced 路径 | T12 |
| V7 | 批量预填对逐 token 解码 | `astral cmp-prefill` | T12 |
| V8 | 投机解码与普通贪心等价 | `astral spec-generate`（自带普通解码对照） | T13 |

V4 若 Astral 缺少 logits 导出，在 T12 中补一个只读的导出路径（`score` 或新的 `dump-logits`）。llama.cpp KLD base 文件的格式以 b12751 的 `tools/perplexity/perplexity.cpp` 为准，解析脚本放在 `$LAB/src/analysis`，不进 Astral 主干。

## 3. 冻结阈值（G1 / G2）

| 项 | 阈值 |
|---|---|
| V0 | 全部 PASS（使用 Astral 自带容差） |
| V3 | `verify-model` 输出 PASS |
| V4 噪声底 N0 | llama.cpp 对自身：`-ub 512` 与 `-ub 1` 两次运行之间的平均 KLD 和 p99 KLD；语料用 `golden_llamacpp.sh` 的确定性语料，c512 × 8 chunk |
| V4 Astral 对 llama.cpp | 平均 KLD ≤ max(2·N0_mean, 0.005)；p99 ≤ max(2·N0_p99, 0.05)；在参考 top-2 margin ≥ 0.5 logit 的位置上 top-1 一致率 ≥ 99.5% |
| V5 | 在 llama.cpp 自身一致的 prompt 上，前 128 token 完全相同；若有分歧，分歧点在参考中的 top-2 margin 必须 < 0.5 logit |
| V6 | 16 个 prompt × 500 位置；不一致只允许出现在 margin ≤ 1.0 logit 的位置 |
| V7 | argmax 相同，且最大绝对差 ≤ 1.0 logit |
| V8 | teacher-forced 下，投机 token 与普通贪心不同的位置全部是近平局（margin ≤ 1.0 logit） |

阈值来源：Unsloth 报告 Q4_K_XL 对 Q8 的 KLD 为 0.0107，同一文件跨引擎的差异应明显低于量化误差，因此平均 KLD 下限取 0.005。Astral 作者在 H100 上观察到批量 kernel 与单 token kernel 的差异最多约 1 logit，V6–V8 的 1.0 logit 来自这里。tqllm 精确模式对 BF16 的 KLD 0.0023 只作外部旁证。

## 4. 性能测量协议（G3）

- 负载：Astral 仓库的 `prompts16.json` 与 `promptsB.json`，共 32 个 prompt。通过 chat 模板转成 token id 后，经流式 `/v1/completions` 发送；每个 512 token，`ignore_eos`，单请求，ctx 8192。
- 对照：llama.cpp `llama-server`（同一 A1，`-ngl 99 -fa on`，相同 token id）。草稿对照：Astral DSpark 对 llama.cpp DSpark（A6）。
- 每种配置重复 5 次，取中位数，剔除 warm-up。每轮只读记录 `nvidia-smi` 的 SM/显存时钟、温度、功耗。
- 比较用 `tools/paired_stats.py`：按 prompt 配对，case 等权 bootstrap。报告 decode tok/s、TTFT 和 ITL 的 p50/p95。
- 外部数字（Xolotl、atlas-ingine、作者的 H100 数据）只作背景，不参与 G3 判定。
