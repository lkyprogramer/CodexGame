# 05 · 验证方法与冻结阈值

## 1. 原则

- 参考实现：**同一个 GGUF（A1）上的 llama.cpp b12751**。Astral 的模型语义本来就是逐步照 llama.cpp 写的，同文件对比可以排除量化差异。
- 阈值相对于参考自身的噪声底设定：Astral 不会被要求比 llama.cpp 自己更一致。
- 下文 §3 的阈值随 v3.0 冻结；V7 于 v3.0.4 经用户同意修订（原阈值为“全词表最大绝对差 ≤ 1.0 logit”）。噪声底 N0 在 T12 中**先于** Astral 的 KLD 测量。
- v3.0.7 按评审核实后补充 §5–§7：各项 PASS 实际覆盖了什么、V7 两侧口径不一致的问题、统一的数值计算口径和运行记录格式。**§3 已批准的阈值不因此放宽或收紧**；统一口径如需新数值，按 §6.3 先由参考对照给出依据、在看候选结果之前冻结，再经用户确认。

## 2. 验证阶梯

| 级 | 检查 | 工具 | 任务 |
|---|---|---|---|
| V0 | 每个 kernel 对 CPU 参考 | `astral selftest` | T07 |
| V1 | GGUF 张量表：类型计数（Astral 在 A100 上读到 NVFP4 ×40、Q8_0 ×154、F32 ×518、BF16 ×32），按类型统计的字节数与文件大小相符 | `astral gguf-info A1 --tensors` | T08 |
| V2 | 分词：16 个 prompt 经 chat 模板后的 token id，Astral server 与 `llama-tokenize` 完全相同 | `serve` 的 tokenize 路径、llama.cpp | T10 |
| V3 | 逐算子**采样**对照：embedding 与整条前向对 `llama-eval-callback` 日志（固定 golden prompt，比较日志里打印出的行首尾各 3 个值和整张量 sum，不是全张量逐元素） | `astral verify-embd`、`astral verify-model`、`bench/golden_llamacpp.sh` | T09 |
| V4 | 分布：KLD 与 top-1 一致率 | llama.cpp `--kl-divergence-base` + Astral logits 导出 | T12 |
| V5 | 贪心序列：前 128 token | `astral generate`、`llama-cli` / `llama-server` | T10、T12 |
| V6 | teacher-forced：在参考序列上逐位置比较 argmax，记录 top-2 margin | Astral 的 teacher-forced 路径 | T12 |
| V7 | 批量预填对逐 token 解码：每个 prompt 只比较**最后一个位置**的 logits（16 个 prompt = 16 个向量） | `astral cmp-prefill` | T12 |
| V8 | 投机解码与普通贪心**在容差内**一致（允许近平局处分歧；严格 token 一致率另报） | `astral spec-generate`（自带普通解码对照） | T13 |

V4 的 Astral 侧用 T12 新增的 `astral dump-logits` 导出。llama.cpp KLD base 文件的格式以 b12751 的 `tools/perplexity/perplexity.cpp` 为准。分析脚本原放在本包 `tools/w2/`，现已迁到 fork 的 `bench/llamacpp_compare/`（[08](08_runbooks.md) §9）。

## 3. 冻结阈值（G1 / G2）

| 项 | 阈值 |
|---|---|
| V0 | 全部 PASS（使用 Astral 自带容差） |
| V3 | `verify-model` 输出 PASS |
| V4 噪声底 N0 | llama.cpp 对自身：`-ub 512` 与 `-ub 1` 两次运行之间的平均 KLD 和 p99 KLD；语料用 `golden_llamacpp.sh` 的确定性语料，c512 × 8 chunk |
| V4 Astral 对 llama.cpp | 平均 KLD ≤ max(2·N0_mean, 0.005)；p99 ≤ max(2·N0_p99, 0.05)；在参考 top-2 margin ≥ 0.5 logit 的位置上 top-1 一致率 ≥ 99.5% |
| V5 | 在 llama.cpp 自身一致的 prompt 上，前 128 token 完全相同；若有分歧，分歧点在参考中的 top-2 margin 必须 < 0.5 logit |
| V6 | 16 个 prompt × 500 位置；不一致只允许出现在 margin ≤ 1.0 logit 的位置 |
| V7 | **（v3.0.7 注：此行两侧不是同一个统计量，见 §5.2；T12 按此行的复判降为“历史判定，待 T19 复核”）** argmax 相同；距 top 16 logit 以内的 token 上最大绝对差 ≤ N0_near_p99；KL(step‖prefill) ≤ N0_p99。N0_near_p99 是 llama.cpp `-ub 512` 对 `-ub 1` 时，每个位置在同一窗口内最大 log-prob 差的 p99（2026-11-26 实测 3.15）；N0_p99 与 V4 的定义相同（实测 0.0284）。全词表最大差只记录，不参与判定 |
| V8 | teacher-forced 下，投机 token 与普通贪心不同的位置全部是近平局（margin ≤ 1.0 logit） |
| V7（num-2，2026-11-26 09:05 UTC 冻结，用户确认前为提案） | 用 fork `logit_compare.py`（[05](05_validation.md) §6.1 的口径）在 T19 的 A 组 96 个位置上比较 Astral step（参考侧）与 prefill（候选）。① argmax 不同只允许出现在 step 一侧 top-2 margin < 0.5 的位置；② `max_near` 与 `KL` 的 mean / p90 / max 各自 ≤ 2 × 参考形状对照（llama.cpp 逐 token 对 ub512，同一批 A 组位置、同一计算器）的对应值：max_near ≤ 0.627 / 1.620 / 3.133，KL ≤ 0.00143 / 0.00305 / 0.041；③ 位置齐全、唯一、有限，否则判不完整。系数 2 沿用 V4 的 2·N0。B 组 32 个位置用同一规则作保留集。规则文件 `tools/t19/rule_num2.json`（来源 `ref_shape_a.jsonl` SHA256 `e94dc19867934647…`） |

阈值来源：Unsloth 报告 Q4_K_XL 对 Q8 的 KLD 为 0.0107，同一文件跨引擎的差异应明显低于量化误差，因此平均 KLD 下限取 0.005。Astral 作者在 H100 上观察到批量 kernel 与单 token kernel 的差异最多约 1 logit，V6–V8 的 1.0 logit 来自这里。tqllm 精确模式对 BF16 的 KLD 0.0023 只作外部旁证。 V7 改为相对噪声底判定的原因：T12 实测 llama.cpp 自身批量对逐 token，在概率窗口内有 19.4% 的位置最大差超过 1.0（p99 3.15），原阈值连参考实现自己都达不到；尾部 token 的绝对差对分布几乎没有影响，所以改用窗口内的差和 KL 来判定。

## 5. 已有 PASS 的实际覆盖范围（v3.0.7，按评审核实源码）

| 项 | 判定时实际测了什么 | 依据 | 不能据此声称 |
|---|---|---|---|
| V3 | 固定 golden prompt 逐 token 跑 `step`，48 个 slot 的 `l_out` 与 llama.cpp 日志中**打印出的值**比较（日志每行只打首尾各 3 个值），外加整张量 sum | fork `crates/cli/src/main.rs` `cmd_verify_model` | 全张量逐元素一致；prefill 路径一致 |
| V4 | c512 × 8 chunk，每 chunk 评分位置 256–510，共 8 × 255 = **2040** 个位置；均走 Astral 的逐 token decode 路径 | llama.cpp `perplexity.cpp` 的 KLD 评分范围；T12 记录 | 4096 个独立测点；prefill / verify 形状 |
| V5 | W2 的参考序列用全 step 的 teacher-forced 打分；T10 的 128 token 贪心走 `generate`（prefill → decode） | `tools/w2/w2.sh`、T10 记录 | W2 部分单独覆盖默认 `prefill → generate` |
| V6 | 16 个 prompt × 500 位置，逐 token step | T12 记录 | prefill 与 decode 交接处 |
| V7 | 每个 prompt 只比较**最后一个位置**：16 个 logits 向量 | `cmd_cmp_prefill` 只取 `s.logits()` | 16 × 500 个位置；chunk 边界 |
| V8 | DSpark k = 6，16 个 prompt；允许近平局处分歧 | T13 记录 | 投机与贪心逐 token 严格等价 |

这些结论仍然成立，但只在上表范围内成立。补测在 T20：prompt 末位、生成第 1/2/8/32/128 个位置、prefill chunk 边界前后、verify 批长 1/2/4/8，按风险挑选，不做笛卡尔积。

### 5.1 模板问题的结论（更正评审 §3.5 的前提）

评审 §3.5 依据的是 T13 初稿中“样本缺少 `<|message_model|>` 生成提示”的记录；该记录是误判，07:20 已更正：Inkling 的 chat 模板没有生成提示，模型自己先输出 `<|message_model|>`，16 个参考序列都以 `<|message_model|><|content_thinking|>` 开头。所以 **V5–V8 用的 prompt 已经是真实的助手生成场景，不需要因模板问题重跑**。评审要求记录的模板指纹仍然采纳，写入 §7 的 `run.json`。

### 5.2 V7 的口径问题（确认属实）

| 比较项 | 参考噪声 N0_near_p99（`nearcmp.py` / `near_top_diff.py`） | Astral 侧（`cmp-prefill`） |
|---|---|---|
| 数值 | u16 编码的归一化 log-prob | float32 原始 logits |
| 窗口 | 两侧 log p 都 > −16 的交集 | step 一侧距其最大 logit < 16 |
| KL | 截断求和（u16 文件里低于 max−16 的值被钳位） | float64 全词表求和 |
| 位置 | KLD 语料的 2040 个位置 | 16 个 prompt 末位 |

所以 v3.0.4 复判中的“1.18 ≤ 3.15”“0.0147 ≤ 0.0284”**不是同一统计量的比较**。这不说明 V7 实际不通过（原始 logit 整体平移不改变分布，log-prob 差反而可能更小），只说明那次复判不能算严格完成。处理：T12 保持 PASS 的历史记录，但 V7 一栏标注“口径未统一，待 T19 复核”；G2 在 T19 完成前视为**有条件通过**。T15 之后依赖 G2 的研究可以开工，但涉及 prefill / step 差异的结论要等 T19。

## 6. 统一的数值口径（策略 num-2，v3.0.7 起草，T19 落实）

### 6.1 定义

两侧都导出**同一 token 前缀、同一位置**的 float32 logits（词表截到有效的 200058），离线用 float64 计算：

- `lp = log_softmax(z_ref)`，`lq = log_softmax(z_cand)`；
- 窗口只由参考一侧决定：`S = {i : lp_i ≥ max(lp) − 16}`，不用候选是否进入窗口来筛掉差异；
- `max_near = max_{i∈S} |lp_i − lq_i|`；
- `KL(p‖q)` 全词表求和；另记 `S` 之外的概率质量；
- 参考 / 候选的 argmax 和各自 top-2 margin；`gap_ref = z_ref[argmax_ref] − z_ref[argmax_cand]`、`gap_cand` 对称定义；
- 非有限值个数、词表 mask、token 位置。

V4 的 u16 KLD 文件继续使用，但抽少量位置同时导出 float32 logits，核对 u16 编码和截断带来的误差。

### 6.2 噪声分解

参考噪声分成三份，各自保存，不再合成一个“噪声底”：

1. **重复性**：同一引擎、同一形状、同一输入跑两次（判断是否确定性）。
2. **形状**：同一引擎的 prefill 对 step、不同 verify 批长、llama.cpp `-ub 512` 对 `-ub 1`。
3. **跨引擎**：同一资产、同一前缀，Astral 对 llama.cpp。

候选落在形状对照的尺度内，只说明它在已观察到的工程误差范围内，不说明它比参考更正确。

### 6.3 阈值校准

- 旧阈值（§3）保留为历史值，不把 3.15、0.0284 直接搬到新口径。
- 新口径的阈值由**参考自身的形状对照**用同一计算器算出，判定规则（配对分位数、超阈率或 winner-gap 规则）在看 Astral 结果之前写进 §3 并提交，经用户确认后生效。
- 样本：prompts A（`prompts16.json`）已在 T10–T13 看过，只用于定位和校准；prompts B（`promptsB.json`）在 T14 只用于计时、未用于任何数值判定（推断，T19 开始前核对脚本记录），作为数值保留集。若发现 B 已被用于选阈值，另冻结一个小的 C 集。
- 位置数少时不再要求“候选所有位置的最大值 < 参考 p99”；改用事先选定的分位数或超阈率，并按 prompt 聚类统计。

## 7. 运行记录格式（v3.0.7 起）

每次实验一个目录，不新增服务：

```text
run.json            模型 / 模板 / 语料 hash、Astral 与 llama.cpp commit、构建 flags、运行参数、pass/cache 策略、测量模式、判定策略版本
metrics.json        汇总指标与 verdict
positions.jsonl     逐位置结果（小）
stdout.log / stderr.log
evidence.sha256     上述文件及大文件（logits、KLD base）的 SHA256 与实际路径
```

`run.json` 必须包含 `template_hash`、`rendered_token_ids_hash`、`add_generation_prompt`、`special_token_policy`、`eos_policy`、`reasoning_mode`。大文件不进 Git，只记 hash、命令和存放位置。判定脚本必须：检查 case 数、位置数、唯一性与有限值；缺项直接失败；总 verdict 映射到退出码（fork 的 `teacher_forced_verdicts.py` 已按此实现，策略 `tfv-1`）。

## 4. 性能测量协议（G3）

- 负载：Astral 仓库的 `prompts16.json` 与 `promptsB.json`，共 32 个 prompt。通过 chat 模板转成 token id 后，经流式 `/v1/completions` 发送；每个 512 token，`ignore_eos`，单请求，ctx 8192。
- 对照：llama.cpp `llama-server`（同一 A1，`-ngl 99 -fa on`，相同 token id）。草稿对照：Astral DSpark 对 llama.cpp DSpark（A6）。
- 每种配置重复 5 次，取中位数，剔除 warm-up。每轮只读记录 `nvidia-smi` 的 SM/显存时钟、温度、功耗。
- 比较用 `tools/paired_stats.py`：按 prompt 配对，case 等权 bootstrap。报告 decode tok/s、TTFT 和 ITL 的 p50/p95。
- 外部数字（Xolotl、atlas-ingine、作者的 H100 数据）只作背景，不参与 G3 判定。
