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
| V7（**num-3**，用户 2026-11-26 采用；规则 `tools/t19/rule_num3.json`，在 C 组结果出来之前提交推送） | 用 fork `logit_compare.py judge-paired` 在**同一批位置**上比较 Astral（step 为参考侧、prefill 为候选）与参考形状对照（llama.cpp 逐 token 对 ub512）：① argmax 不同只允许出现在 step 一侧 top-2 margin < 0.5 的位置；② 候选 / 参考的比值：`near_w`（窗口内按参考概率加权的 log-prob 差）的 mean、p90 ≤ 2，KL 的 mean、p90、max ≤ 2；③ `max_near` 只记录、不判定；④ 位置齐全、唯一、有限，参考侧同样要求。**判定集是全新的 C 组**（`tools/t19/prompts_set_c.json` 16 个 prompt × 5 个长度 = 80 个位置，llama.cpp 贪心续写 160 token）；A、B 组看过 num-2 结果，只作描述 |
| V7（num-2，2026-11-26 09:02 UTC 冻结（提交 `92f4c40`），用户确认前为提案；T19 按此判 FAIL，规则缺陷见 §6.4） | 用 fork `logit_compare.py`（[05](05_validation.md) §6.1 的口径）在 T19 的 A 组 96 个位置上比较 Astral step（参考侧）与 prefill（候选）。① argmax 不同只允许出现在 step 一侧 top-2 margin < 0.5 的位置；② `max_near` 与 `KL` 的 mean / p90 / max 各自 ≤ 2 × 参考形状对照（llama.cpp 逐 token 对 ub512，同一批 A 组位置、同一计算器）的对应值：max_near ≤ 0.627 / 1.620 / 3.133，KL ≤ 0.00143 / 0.00305 / 0.041；③ 位置齐全、唯一、有限，否则判不完整。系数 2 沿用 V4 的 2·N0。B 组 32 个位置用同一规则作保留集。规则文件 `tools/t19/rule_num2.json`（来源 `ref_shape_a.jsonl` SHA256 `e94dc19867934647…`） |

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

**T20 补测后的覆盖（v3.0.11，结果在 `tools/t20/results/`）**：

| 路径 / 形状 | 位置 | 方法 | 结果 |
|---|---|---|---|
| 全 step / prefill / prefill → decode / verify 2·4·8 行 | B 组 16 个 prompt：Lp、Lp+1…Lp+16、+32、+64、+96、+128（336 个位置；生成位置 320 个） | num-3，按路径配对，参考侧都是 llama.cpp ub512 对 ub1 | 全部 PASS，比值 0.59–1.09；verify 三种批长逐位相同；每种批长的行号都覆盖到（k = 7 时 0–7 行各至少 7 个位置） |
| 自由生成 prefill → decode | B 组 16 × 160 token | V5 口径 | 首个分歧全部在近平局处（参考 margin ≤ 0.27）；严格一致的前缀共 895 / 2560 token |
| 分块与窗口边界 | D 组 4 篇长文档：8/9、64/65、1023–1025、2047–2050、2056/2057、4096/4097（64 个位置） | num-3 | **FAIL**（见 §6.6）：KL mean、max 超过比值限制，argmax 硬门也不通过（prefill 3 处、decode 1 处翻转在参考 margin ≥ 0.5）；超限集中在几个分岔位置，不在边界的系统位置上 |
| 长上下文密集测量 | c4096 × 4 chunk，2048–4094 位置，共 8188 个 | V4 公式，N0 在同一文件上重测 | step 与 prefill → decode 都满足 V4 |
| 运行间复现 | D 组 184 个文件 | 逐位 | 0 个不同 |


### 5.1 模板问题的结论（更正评审 §3.5 的前提）

评审 §3.5 依据的是 T13 初稿中“样本缺少 `<|message_model|>` 生成提示”的记录；该记录是误判，07:20 已更正：Inkling 的 chat 模板没有生成提示，模型自己先输出 `<|message_model|>`，16 个参考序列都以 `<|message_model|><|content_thinking|>` 开头。所以 **V5–V8 用的 prompt 已经是真实的助手生成场景，不需要因模板问题重跑**。评审要求记录的模板指纹仍然采纳，写入 §7 的 `run.json`。

### 5.2 V7 的口径问题（确认属实）

| 比较项 | 参考噪声 N0_near_p99（`nearcmp.py` / `near_top_diff.py`） | Astral 侧（`cmp-prefill`） |
|---|---|---|
| 数值 | u16 编码的归一化 log-prob | float32 原始 logits |
| 窗口 | 两侧 log p 都 > −16 的交集 | step 一侧距其最大 logit < 16 |
| KL | 截断求和（u16 文件里低于 max−16 的值被钳位） | float64 全词表求和 |
| 位置 | KLD 语料的 2040 个位置 | 16 个 prompt 末位 |

所以 v3.0.4 复判中的“1.18 ≤ 3.15”“0.0147 ≤ 0.0284”**不是同一统计量的比较**。（v3.0.10：T19 已用统一口径按 num-3 在保留集 C 上复判通过，见 [07](07_tasks.md)；下段为当时的处理，保留作记录。）这不说明 V7 实际不通过（原始 logit 整体平移不改变分布，log-prob 差反而可能更小），只说明那次复判不能算严格完成。处理：T12 保持 PASS 的历史记录，但 V7 一栏标注“口径未统一，待 T19 复核”；G2 在 T19 完成前视为**有条件通过**。T15 之后依赖 G2 的研究可以开工，但涉及 prefill / step 差异的结论要等 T19。

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

### 6.4 num-2 在 T19 中暴露的缺陷与 num-3（2026-11-26 用户采用）

T19 按冻结的 num-2 规则判 FAIL（[07](07_tasks.md) 执行记录），但失败点集中在规则本身：

1. **窗口过宽，max 被极小概率 token 主导。** A 组唯一超限的位置（`a00` 长度 39）窗口内只有 2 个 token，第二名在 Astral step 里 log-prob 约 −12.7（概率约 3e-6），prefill 里约 −19，差 6.3；该位置 KL 只有 1.6e-5。`max_near` 的 max 统计量对这类 token 极敏感，与分布差异几乎无关。
2. **绝对限值不能跨位置分布迁移。** 限值来自 A 组位置（长 prompt 末位与生成段），B 组是短 prompt 的中段和末位，熵更高：llama.cpp 自己在 B 组的形状对照 KL 均值 0.0077，同样超过限值（0.0014），而 Astral 在 B 组是 0.0055，比参考自己还小。

**num-3**（用户已采用，定义见 §3；因为是看过 T19 结果之后提出的，用新的保留集 C 判定，A、B 只作描述）：

- 同位置配对：候选与参考形状对照在**同一批位置**上比较，判定量是候选 / 参考的比值（mean 与 p90 各 ≤ 2），不再使用从别的位置集算出的绝对限值；
- 窗口内的差按参考概率加权（或把窗口收窄到 log p ≥ max − 8），`max_near` 的 max 只记录、不判定；KL 的 max 仍判定（≤ 2 × 同位置参考的 max）；
- argmax 规则不变。

### 6.5 Astral prefill 的运行间不确定性（T19 发现，已修复）

同一输入跑两次：Astral **step 路径逐位相同**，**prefill 路径每个位置都不同**（两次之间 KL 均值 7.6e-5、最大 0.0024，`max_near` 最大 4.5，argmax 不变）。llama.cpp 逐 token 两次逐位相同。**根因（消融确认）**：prefill 的两条 split-K 路径——分组张量核 GEMM（`Gemv::launch_mma` / `gemm_mma3`）和 loop controller 的下投影（`InklingOps::ctrl_t`，K 切 8 份）——都用 float `atomicAdd` 合并各分片，舍入取决于 block 完成顺序。只关其中一条仍不可复现，两条都关后 24/24 个文件逐位相同；MoE 分组用的整数 `atomicAdd` 不影响结果；不是竞争条件。直接关掉拆分会让 16 token 的 prefill 慢 40%，所以没有采用。**修复**（fork `35de94a`）：各分片把部分和写进工作区里自己的一份，再由新的 kernel 按分片顺序相加。修复后 prefill 两次运行逐位相同；交替各 8 次的 A/B 中位数：16 token 59.5 → 61.0 ms（+2.5%），128、512 token 无差别。selftest 新增两条路径的可复现性用例（85/85 通过；**v3.0.14 更正**：GEMM 两组用例的 FP16 输入平面为零，只有 controller 的用例有效，见 [07](07_tasks.md) T22。修复本身由真实模型 prefill 的 24/24 与 T19 的 208 个文件逐位相同证明，不依赖这些用例）。修复后，T15 / T18 的“逐位一致”检查在 prefill 路径上同样适用。

### 6.6 长上下文的分岔位置（T20 发现）

D 组 64 个位置按 num-3 判为 FAIL：KL mean 比值 2.8 / 2.5（prefill / decode），KL max 比值 6.9 / 5.2。超限只来自 4 个位置（`d02_s` 1023、`d03_l` 2056、`d00_l` 2056 的 decode、`d03_l` 4096），不在分块或窗口边界的系统位置上。这些位置的分布是**双峰**的，引擎的不同变体会落到不同的峰：`d00_l` 2056 处，llama 逐 token 与 Astral decode 都给 149895 约 0.96 的概率，llama ub512、Astral step 和 prefill 都只给 0.37–0.46。llama 自己两种批长之间在 D 组也有 KL 0.69 的位置。所以这里的超限说明不了哪个引擎错了；64 个位置太少，mean 和 max 都被一两个分岔点主导。

为此在同一批长文本上补了密集测量（`tools/t20/t20_long.sh`）：c4096 × 4 chunk，8188 个位置。N0（llama ub1 对 ub512）为 mean 0.0049、p99 0.0495，是 c512 时的约 2.5 倍，说明长上下文下模型本身对数值噪声更敏感。Astral 对 llama ub512：逐 token mean 0.0053、p99 0.0502；prefill → decode mean 0.0052、p99 0.0487；margin ≥ 0.5 处 top-1 一致率均为 99.87%（llama 自身 99.86%）。按 V4 已批准的公式，限值为 mean ≤ 0.0098、p99 ≤ 0.099、top-1 ≥ 99.5%，两条路径都满足。单点 KL max 为 3.4 / 3.9，llama 自身为 1.0；V4 不判 max。

**更正（v3.0.14，方案 10 §2.5，S32；已按 `tools/t20/results/num3_d_*.json` 核实）**：上面只写了 KL 超限，漏了 argmax 硬门。prefill 有 3 处翻转发生在参考 margin ≥ 0.5 的位置（`d02_s` 1023 的 1.016、`d03_l` 2056 的 1.087、`d03_l` 4096 的 0.703），decode 有 1 处（`d03_l` 2056 的 1.087）。这些位置和分岔位置重合，但按定义不是近平局，不能概括成“参考分母太小”。另外，密集 V4 用的是 W1 语料拼接，D 是指定文档截取再加 chat 指令与模板，两者不是同一批 token，密集 V4 通过不能改判 D。

处理：D 组的 num-3 FAIL 照实记录，不改规则，也不改判。**已生效（用户 2026-11-27 采用；v3.0.14 按方案 10 修订，取代原先“num-3 只用于不含分岔点的集合”的说法）**：① D 的全部失败点留作固定回归，不在看到结果后剔除；② 在相同的 D token 前缀上补密集诊断（多位置的 V4 式统计，以及失败点的中间张量和路由 margin 定位）；③ 长文判定规则先冻结（例如密集 V4 加上硬门的例外条件），再在独立的 E 集上验证。B、C、D 已用于诊断，今后只作回归；新的未见集合从 E 开始命名。任务见 [07](07_tasks.md) T25。

**num-4L（v3.0.20，T25 冻结；2026-11-28 用户确认采用，v3.0.22 起判定工具 fail-closed，见 §6.8）**：用于 4K token 以上、套 chat 模板的长文档，teacher-forced。位置为第 512 位到末尾的全部位置；prefill 路径每 64 个长度取一次，另加 prompt 长度。每条候选路径（serve、step、prefill；各自对 Astral step 和对 llama ub1）都与同一批位置上 llama.cpp 自身的形状对照（ub1 对 ub512；prefill 用 ub1 对 batch）比较，全集合位置合并计算：KL 均值比 ≤ 1.5；密集位置 p99 比 ≤ 1.5，抽样位置 p90 比 ≤ 2；参考 margin ≥ 0.5 和 ≥ 4 的 argmax 翻转数各 ≤ 1.5 × 对照 + 3；单份文档的均值比 ≤ 2.5；不得缺位置，不得有非有限值。KL max 只记录。依据：D 组上 llama.cpp 自己换批长，就会在 ub1 margin ≥ 8 的位置翻转约 1%，绝对门不可用。E 集 PASS。局限：已撤回的 dp4a 判不出来（负控制），所以 num-4L 只是长上下文下抓大偏差的门，不能替代 B 组 num-3 与 W1 密集 V4。规则文件为 `tools/t25/rule_num4l.json`，判定脚本为 `t25_judge.py`。

### 6.7 测试合同与负控制（v3.0.14，方案 10 §2.4、§7.7、§12.6、§12.7）

- **输入有效**：被测 kernel 实际读取的每个平面都要写入非零、有正负、有幅度差的数据；先检查输出非零、改一个有效输入能改变输出，再比较重复性和参考。分配过的内存不等于有效数据；T19 的 GEMM split-K 自测就是反例（[07](07_tasks.md) T22）。
- **负控制**：关键测试各配一个必须失败的错误版本，例如错 slot、错一行 bias、漏一个 expert、漏写 FP16 平面、提前提交一行。负例不失败，说明测试本身没有证明力。
- **候选命中**：开关打开不等于走了那个 kernel。性能 A/B 与数值对照都记录 graph 捕获时实际选中的 kernel、shape、激活平面与 fallback 原因；从未命中的候选不报收益。
- **请求状态**：Session 复用必须经过完整 reset，不继承上一请求的草稿上下文、接受统计或候选有效长度。“重复得到同样输出”与“等于 plain 输出”是两回事；严格重复性（逐位）与 num-3 容差分开报告。
- **输出模式**：普通末行、全行与 verify 行可能选不同的 head kernel，三者在同一 hidden 上直接对照，数值保证写明；不为此在生产路径物化全行 logits（2048 × 201024 的 FP32 约 1.53 GiB）。

变化类别在 [06](06_loop_research.md) §1.3 四类之外再细分：round / shape 调度变化（数学相同，舍入路径要测）、目标权重重编码（新权重身份，重做基线）、草稿权重量化（目标与草稿的保证分开，计接受率与净收益）、prompt 模板或 thinking 尾部的改动（输入 token 变化，单独作 API / 模板实验）。

v3.0.17（方案 11 §1、§10.3）再分出五类改动，分别验收：

| 类别 | 对应任务 | 验收要点 |
|---|---|---|
| 草稿提案近似 | T26 | 只改草稿，目标 verify 不变；报告提案召回与净收益，不称无损 |
| 数学等价的依赖裁剪 | T27 | 先争取逐位一致；不一致时定位到 dispatch / tile / split 顺序，不改质量门 |
| 目标近似 | T28 | 局部误差界只作参考，最终质量以冻结预算后的 E 集为准，历史 FAIL 不覆盖 |
| 状态复用 | T29 | 与从头重放新序列的结果比较 |
| 控制流迁到 GPU | T30 | 保持“返回的最后一个 token 尚未送入模型”这一不变量 |

各专项在 `run.json` 中另记以下字段：
- T26：筛选格式与 hash、L、召回、各阶段时间、额外显存。
- T27：源行数、7 / 4 区间、tail 的绝对位置、实际 dispatch、raw conv 末态差异、回退原因。
- T28：每个 slot / 组的保留块、真实漏失质量、参考界、回退、封口 epoch、元数据大小。
- T29：编辑的 token 映射、cut、guard、复用区间、失效范围。
- T30：B、computed_inputs、stop reason。

### 6.8 有损与改模型候选、判定工具（v3.0.21）

- **命名**：有损候选（T37–T40、T44、T47、R15，以及 K13 的 int8 激活）用独立的候选 ID 与资产身份，不走“PASS 即默认”的路径。改默认服务路径仍需完整 G2（含 T20）与 G3。
- **筛选与判定分开**：T46 的 top-128 加尾桶 KL 只用于筛选（它是全词表 KL 的下界）；正式门仍用全词表 KL、num-3、num-4L。有损候选还要同时报告 gencheck（截断、复读）与任务正确率，不能只看 teacher-forced KL。
- **判定工具 fail-closed**（T41）：预期的 case、pair、位置和词表宽度来自清单。负控制必须存在、被读取，并按登记的期望判定：登记为 `expect: caught` 的负控制没被抓到时，判定为验证器无效、非零退出。任何缺件、NaN、未知 schema 或子命令失败都不能得到 PASS；wrapper 保留每一步的返回码。
- **逐位一致回归**（T45 之后）：DSpark / DFlash2 与无草稿、不同 k 的贪心输出做 SHA 对比，作为 G2 的附加项。

## 7. 运行记录格式（v3.0.7 起）

每次实验一个目录，不新增服务：

```text
run.json            模型 / 模板 / 语料 hash、Astral 与 llama.cpp commit、构建 flags、运行参数、pass/cache 策略、测量模式、判定策略版本
metrics.json        汇总指标与 verdict
positions.jsonl     逐位置结果（小）
stdout.log / stderr.log
evidence.sha256     上述文件及大文件（logits、KLD base）的 SHA256 与实际路径
```

`run.json` 必须包含 `template_hash`、`rendered_token_ids_hash`、`add_generation_prompt`、`special_token_policy`、`eos_policy`、`reasoning_mode`。v3.0.14 起（方案 10 §2.5、§13.8）还要记：二进制的 SHA256 与工作区差异的 hash（T20 的 `identity.txt` 只有 commit 和 `git status`，缺这两项）、遍数与 plan 指纹、capacity / tmax / cache 布局（如 SWA ring 行数）、探针状态、实际选中的 kernel 与激活平面、成本表 hash（T21）。原始大文件可以不进 Git，但要能恢复：保留文件，或保留能逐位重新生成它的二进制、输入与命令；只剩 hash 不算可恢复。大文件不进 Git，只记 hash、命令和存放位置。判定脚本必须：检查 case 数、位置数、唯一性与有限值；缺项直接失败；总 verdict 映射到退出码（fork 的 `teacher_forced_verdicts.py` 已按此实现，策略 `tfv-1`）。

## 4. 性能测量协议（G3）

- 负载：Astral 仓库的 `prompts16.json` 与 `promptsB.json`，共 32 个 prompt。通过 chat 模板转成 token id 后，经流式 `/v1/completions` 发送；每个 512 token，`ignore_eos`，单请求，ctx 8192。
- 对照：llama.cpp `llama-server`（同一 A1，`-ngl 99 -fa on`，相同 token id）。草稿对照：Astral DSpark 对 llama.cpp DSpark（A6）。
- 每种配置重复 5 次，取中位数，剔除 warm-up。每轮只读记录 `nvidia-smi` 的 SM/显存时钟、温度、功耗。
- 比较用 `tools/paired_stats.py`：按 prompt 配对，case 等权 bootstrap。报告 decode tok/s、TTFT 和 ITL 的 p50/p95。
- 外部数字（Xolotl、atlas-ingine、作者的 H100 数据）只作背景，不参与 G3 判定。
