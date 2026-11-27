# Inkling 4090：因果自适应循环探索与验证方案

> **Implementation Plan · 2026-11-27 · Asia/Shanghai · v1.0**
>
> **交给工程 AI：**按 AD00—AD09 顺序执行；每项具有输入、实现位置、测试、证据与停止条件。执行环境若提供 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans`，可用其逐任务实施；本文件同时给出完整执行合同，不依赖插件才能理解和执行。
>
> **当前状态：方案已完成源码与历史实验记录审阅；本方案新增的实现和 4090 实验全部为 `NOT_RUN`。**文中的仓库历史数据不是本次重新实测的结果。新增文件、接口、CLI 均明确标为 **NEW**。

**Goal：**在现有 Rust + CUDA 引擎中，让 Inkling varloop 根据当前 token 的可用信息，决定是否执行第三遍核心计算，并验证这种决策能否以可接受的质量损失换得真实端到端收益。

**Architecture：**冻结专家与主体权重；先完成请求级固定深度对照，再实现每 token 的 2/3 遍选择。采用唯一明确的缺失历史补齐规则，训练本地小型收益判断器；仅在必要时增加有界的循环 gain 校准。Jev 是请求级对照，DSpark 是现有强基线，本轮不把两者放进动态 token 路径。

**Tech Stack：**现有 `inkling-4090-engine`、Rust、CUDA 12.8、RTX 4090 sm_89；Python/NumPy/SciPy 用于离线数据、拟合和统计；模型资产沿用 A1/A3/A4。

**Spec：**本文件第 1—10 节就是设计规范；第 11 节是实施任务；第 12—15 节是执行、预算、交付和来源。与现有实验室的 R1/R2/R6/R9 衔接，不重开通用推理底座。

---

## 1. 唯一选择：学习“第三遍的边际价值”

**选择的方向是：因果收益驱动的自适应循环，而不是固定多跑几遍。**

核心问题是：第二遍结束时，凭已经计算出来的状态，能否预测继续执行第三遍对最终答案的收益？如果可以，就把计算留给真正需要它的 token。若跳过导致后续历史失真，则用明确、可测试的状态规则和有限的循环校准处理。

这一方向同时触及模型结构、时间状态和决策学习，研究上限高于单独调一个 kernel；但**上限高不代表成功概率高，也不代表一定快于现有 DSpark**。本轮必须允许得出“第三遍的价值不可预测”“状态补齐损害质量”或“收益不足”的结论。

完整研究假设是：

1. 同一 A4 模型中，第三遍的任务收益在不同问题、不同生成位置上存在可利用的差异。
2. 这些差异能被停止时已存在的廉价特征预测。
3. 提前退出后的历史状态能够以低成本补齐，长期生成不会持续放大偏差。
4. 节约的计算足以覆盖判断器、状态维护、graph 分段和同步开销。

前两条不成立，就没有必要继续写复杂调度；第三条不成立，就不能把离线轨迹上的选择变成在线算法；第四条不成立，则保留研究发现，停止工程化。

### 1.1 本轮与未来上限

| 层次 | 本轮决策 |
|---|---|
| 实验主体 | A4 `TML-d24-varloop-research`，同一权重、同一加载精度 |
| 最小闭环 | 每 token 在第 2 遍结束时选择停止或继续第 3 遍 |
| 第一阶段对照 | 整请求固定 2/3 遍；1/4/5 遍只做小规模深度响应测量 |
| 状态语义 | 第 5 节定义的 `depth_clamp_v1`，仅这一种 token 动态策略 |
| 判断器 | 本地 12 维特征、三分类线性模型；先与简单规则比较 |
| 动力学校准 | 条件触发；最多 96 个新增 gain 系数，主体权重保持冻结 |
| 未来扩展 | 只有 2/3 遍闭环通过后，才另冻结一次 2/3/4 遍实验合同 |

不同时推进 KV 量化、专家 offload、SSD 缓存、通用框架、多模型服务、树推测或新量化格式。现有 T21/T24/T25 等任务继续按原合同管理；本文件不覆盖其状态。

## 2. 当前项目事实与本方案起点

### 2.1 固定的审阅快照

| 对象 | 本次读取的身份 | 用途 |
|---|---|---|
| 引擎 | `lkyprogramer/inkling-4090-engine`，`aa837c7e1242cf89f11f7f556a567c14bd065e04` | 实现基线 |
| 实验室 | `lkyprogramer/CodexGame`，分支 `4090-report`，`159edbb0f115a69dedb37866dc94f0f42767bc98` | v3.0.18 实验记录与执行合同 |
| 实验室目录 | `docs/inkling-4090-lab-v3.0/` | AGENTS、验证规则、任务与脚本 |
| A1 | `Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf` | 正式 Mini 固定 3 遍对照 |
| A4 | `thinkingmachines/TML-d24-varloop-research@91a57fe2b779bbd12c0f74d1f518cbd5b84e8d0d` | 主实验模型 |
| 机器 | 单 RTX 4090 24 GiB、64 GB RAM | 所有目标实测的环境 |

引擎提交时间为北京时间 2026-11-27 17:33:16，实验室提交时间为 17:34:26。后续执行若 HEAD 已变化，先记录差异并重新建立基线，不能默默沿用本文件的性能数字。[S1][S2]

### 2.2 已经做过的工作：直接复用

| 已有能力或结果 | 对本方案的约束 |
|---|---|
| T15 已有 `astral trace`，覆盖 decode 的 controller、消息、路由、注意力和 residual | 不重写通用观测平台；完整 trace 仅诊断，不拿其速度当线上判断成本 |
| T18 已有 `ASTRAL_PASSES=1..10` 与 A4 原生加载 | 这是加载期覆盖，改变遍数会重建状态；不等于已有逐请求或逐 token 动态接口 |
| T17 已有 SWA ring；A1 无草稿容量到 132096，DSpark 到 73728 | 不能再把“引擎只有 8K”写成现状；本轮从 ≤8K 开始是控制研究成本 |
| T22 修复了 GEMM 自测读取全零 FP16 平面的问题 | 新测试必须检查实际输入和负控制，不能只看两个错误输出彼此一致 |
| T16 第二轮保留 DSpark 小批 dp4a，撤回 decode dp4a | 当前默认 kernel 与第 1 轮不同，不能以撤回版本建立收益对照 |
| T20 的 D 集仍有已知 num-3 FAIL，后续独立集合从 E 开始 | 保留失败记录；B/C/D 只能回归和诊断，不能重新命名为盲测 |

以上来自当前源码与实验室记录，并非本次模型复测。[S2][S3][S4]

### 2.3 历史数值及其边界

T18 的 A4 测量使用 W1、c512×8、2040 个评分位置。它描述一个小语料上的 PPL 与固定深度速度，**不能证明任务正确率、动态策略或长生成质量**。[S5]

| 模型 | 固定遍数 | PPL | decode tok/s |
|---|---:|---:|---:|
| A4 varloop | 1 | 3.6669 | 280.6 |
| A4 varloop | 2 | 3.6262 | 189.8 |
| A4 varloop | 3 | 3.5631 | 143.3 |
| A4 varloop | 4 | 3.5516 | 115.8 |
| A4 varloop | 5 | 3.5425 | 96.8 |
| A1 固定 Mini | 2 | 6.3795 | 190.5 |
| A1 固定 Mini | 3 | 3.5359 | 143.4 |

这组记录支持优先研究 A4；A1 直接砍成两遍已经存在明显退化证据。A4 与 A1 是两个模型，不能把二者差别归因于深度调度。[S5][S6]

当前 T16 第二轮在另一套 32 prompt×5 次的协议上报告：A1 plain **142.0 tok/s**，DSpark **206.3 tok/s**。它与上表不是同一模型、同一负载，不能直接计算候选胜负，但足以说明“超过旧的 143 tok/s”不是完整的实用价值证明。[S7]

### 2.4 从 RSE 项目借鉴什么

`Recursive-Self-Improving-Loopers@765453d13878804c49876a656f39b57a4384dca4` 提供的可借鉴点，是循环控制参数值得独立研究。必须修正以下理解：[S8][S9][S10]

- 326 指可编辑张量的数量级，不是 326 个标量；不能据此推断训练几乎不占显存。
- 作者 64 题结果中，最终编辑模型三遍答对 44 题、四遍 45 题。较原始三遍的提升同时涉及权重变化，不能全部归因于多一遍。
- FP-Solve 的计时不包含加载与导出；公开入口整模加载的条件不等于目前 Astral 的 4090 量化路径。
- 后续 GSPO 的评分代码读取题库 `answer`。无外部教师不等于全过程无答案标签。
- 固定提交的单卡 gate 路径存在只生成部分模式、却汇总全部模式文件的问题；缺省训练文件也需要另外提供。

因此，本轮**不以复制作者脚本为前置条件，不承诺复现其耗时和分数**。采用当前量化引擎内可执行的小判断器与有界系数实验；二者是本方案的新实验，不称为 FP-Solve 或 GSPO 的复现。

## 3. Global Constraints：执行合同

1. 主体代码仍是 Astral fork，主实验仍是 A4；A1/A3 的现有数值与 DSpark 基线保留。
2. 不修改 NVIDIA 驱动，不运行驱动安装器、DKMS、内核模块操作，不改 GPU 功耗/时钟，不 drop page cache。
3. 沿用用户目录 CUDA 12.8 工具链；每次安装或构建前后使用已有 `driver_guard.sh check`，不重新生成基线掩盖差异。
4. 工作放在既有 `$LAB=$HOME/inkling-lab-v3` 的独立实验目录；不覆盖旧构建、旧模型、旧结果。
5. 同一 GPU 串行执行；CPU 分析可并行；模型前向不可偷偷并行占卡。
6. 生产停启遵守**最新授权与现场状态**。当前 runbook 记录用户曾要求 Strata 保持停止，此状态下不能调用会自动恢复生产的 `lab_window.sh`。若后来恢复生产，则按授权窗口和原工具进入实验；不凭本文件擅自改变停启状态。[S11]
7. 不自动更换量化格式、不自动下载未批准的 >30 GiB 资产、不推送代码或发布权重。本轮文档请求本身不代表已经执行这些动作。
8. 继承原状态枚举：`NOT_RUN / RUNNING / PASS / FAIL / BLOCKED / NO_BENEFIT / DEFERRED`。缺 GPU、样本不足、缺数据等写进 `reason`，不新增相似状态造成误判。
9. 不改旧 num-3 阈值，不删除 D 集失败点，不把研究策略的输出差异包装成无损实现优化。
10. 每项修正最多两轮有数据支持的尝试；达到预设 GPU 时间预算就结案。优化器的预注册迭代次数不算“失败后重新改合同”的轮次。

### Review Focus：五个必须由测试覆盖的风险

| 风险 | 本文件对应验证 |
|---|---|
| 两遍退出后，第三遍 KV/卷积缺项、串槽或沿用脏值 | AD02/AD03 的逐位置状态 oracle、毒化与漏写负控制 |
| 判断器看到了第三遍结果、未来 token 或标准答案 | AD04 特征白名单、后缀置换与标签隔离 |
| 离线 oracle 很漂亮，真实生成沿错误历史不断漂移 | AD05 两轮 on-policy 分叉与自由生成验收 |
| 少算一遍，但同步、graph、探针、coda 或补齐更贵 | AD07 原生固定端点、强制策略与分项计时 |
| 小样本、重复看盲集或替换基线造成虚假通过 | AD00 数据封口、AD08 配对统计与预算检查 |

## 4. 先算收益账，再决定实现投入

用历史 A4 数字作规划示例：两遍约 **5.269 ms/token**，三遍约 **6.978 ms/token**，差额约 **1.710 ms/token**。恒两遍相对恒三遍的延迟降低约 24.5%，吞吐提高约 32.4%；这不是动态策略已获得的收益。[S5]

令 `p3` 为执行第三遍的比例，`o` 为每 token 判断、补齐、额外同步的平均开销，则粗略估算：

```text
T_dynamic ≈ T_native2 + p3 × (T_native3 − T_native2) + o
```

若 `o=0.15 ms`，要比三遍降低 10% decode 时间，历史数字要求 `p3≤0.504`，即约一半 token 能提前退出。它只是容量规划，不能代替实测：请求长度、上下文、prefill、输出长度和 graph 路径都会改变结论。

**开发投入门槛（本方案提出，非历史实测）：**

- 固定深度任务数据上，事后选择器优化 `sum(log(T_i,D / T_i,3))`，约束总答对数不低于B0答对数减去 `floor(0.01*N)`，每题只可选2或3遍。用按答对数的整数动态规划求解；耗时采用完整请求时间。它知道答案且忽略在线路由代价，是该样本上请求级方案的乐观边界。
- 请求级oracle若连10%时间改善都做不到，只将请求级分支记 `NO_BENEFIT`，不能据此否定token级。预先允许一次不超过1GPU小时、最多16个train任务×4个分叉位置的token探针，计入AD03/AD04预算；仅在状态测试已通过后执行。探针仍无可预测收益则停止主线，不扩大采集。
- token 动态 eager 参考稳定后，先量 `补齐+判断+同步`，目标不超过实测 `T3−T2` 的 10%，且不超过 0.15 ms/token；二者取较小值。超出时只允许一次有 profiler 依据的缩减。
- 学习控制器必须和最好的简单策略比较。复杂度本身没有验收价值。

## 5. 状态语义：本方案最重要的实现规范

### 5.1 已有状态布局

源码中循环的每一遍都从 prelude 输出重新开始，第二遍起读取上一遍的消息。不能把它当作对上一步 hidden 原地多迭代一次。[S12]

本文件自然语言的 pass 从 **1** 开始；现有 trace 的 pass 从 **0** 开始。所有新记录必须同时明确两者，禁止混用。

| 阶段 | 物理层 | 缓存 slot | 作用 |
|---|---|---|---|
| prelude | 0–5 | 0–5 | 每输入 token 一次 |
| core 第 1 遍 | 6–17 | 6–17 | 原生计算 |
| core 第 2 遍 | 6–17 | 24–35 | 原生计算 |
| core 第 3 遍 | 6–17 | 36–47 | 可选计算 |
| coda | 18–23 | 18–23 | 所选遍数之后恰好一次 |

现有 `Session` 自己持有 `Weights`、按 slot 分配的 KV/conv 和 graph；没有可直接调用的通用快照/克隆接口。因此分叉实验默认**同一模型逐分支重放**，不能新建两套 Session 后假设权重自动共享。[S12]

### 5.2 唯一混合策略：`depth_clamp_v1`

第一版只允许 `D_t∈{2,3}`，预分配三遍的全部 slot。`t` 是当前**已经输入模型**的 token 的绝对位置；该步输出预测的是 `x_(t+1)`。

当 `D_t=3`：所有 core slot 正常执行，原生更新状态。

当 `D_t=2`：第三遍不执行，按下面规则补齐第三遍在位置 `t` 的历史：

1. 对全部核心物理层 `6..17`，把第二遍当前 token 的 **实际 FP16 K/V 存储行**复制到第三遍相应槽。
2. 全局层使用绝对行 `t`；SWA 层使用现有 `kv_row(t, rows)` 对应的物理环行，不能拿窗口 1024 代替真实 ring 容量。
3. 第三遍每一处短卷积保留自己的历史，执行一次左移，再追加第二遍同一卷积位置的**最新原始输入**。
4. 不复制第二遍的整段三项历史，不构造不存在的第三遍 block/message，不多运行一次 coda。

四处短卷积的新增历史来源如下。当前 CUDA kernel 已把这些原始输入写入对应 slot 的第三项历史，因此可在第二遍末尾读取，不需要保存整层激活。[S13]

| 卷积位置 | 追加到第三遍的来源 | 每层通道数 |
|---|---|---:|
| K | 第二遍 K 卷积之前的投影值 | 1024 |
| V | 第二遍 V 卷积之前的投影值 | 1024 |
| attention output | 第二遍注意力输出投影之后、post-conv 之前的值 | 2304 |
| FFN output | 第二遍专家加权求和的**输出**、post-conv 之前的值 | 2304 |

设第三遍某通道历史为 `(a,b,c)`，第二遍该通道本次原始输入为 `u2_t`，更新必须是：

```text
H3_new = (b, c, u2_t)
```

绝不能写成 `H3_new = H2_new`。在 `3→2→3` 时，前者保留真实第三遍产生的较早历史，后者会把它抹掉。

**语义边界：**这是本方案提出的近似历史算法。复制出来的 K/V 不等于“第三遍如果真的算过会得到的值”；第三遍未来卷积的历史也已改变。因果性和内存完整性可由测试证明，任务质量仍需实测。不得称其为原模型的精确动态执行。

### 5.3 单步顺序

```text
输入已提交前缀、x_t、过去的深度计划
  → prelude 一次
  → core 第 1 遍
  → core 第 2 遍
  → 只从此时可用的状态构造特征并选 D_t
      D_t=3：按原生规则恢复 prelude / 构造跨遍消息，执行第 3 遍
      D_t=2：补齐第三遍当前行和四处卷积历史
  → 使用实际所选遍留下的 blocks / residual 执行 coda 一次
  → output mix、norm、head、softcap、选 x_(t+1)
  → 同步提交：pos 只增加一次，写入 depth_history
```

所有补齐写入必须在后续 token 读状态之前完成。首版在同一有序 stream 中执行。过程中出错则将 Session 标为不可继续，reset 后从 token 与深度计划重放；不要假装已经具备事务回滚。

### 5.4 Prefill 的唯一首版选择

**实际性能版固定用原生三遍 prefill，进入 decode 后才做 2/3 遍决策。**这样保留已有批量 prefill 和完整提示历史；第一个生成 token 来自原生三遍 prefill 的最后输出。

另提供 `all_tokens_replay` 诊断模式：从第一个提示 token 起，按 token-major 顺序执行强制深度计划。它用于状态 oracle 与固定端点检查，不拿来宣称服务 TTFT 提升。

- `all_tokens_replay + 全2` 与原生全2比较。
- `all_tokens_replay + 全3` 与原生全3比较。
- `native3_prefill + 全3 decode` 与原生三遍服务路径比较。
- `native3_prefill + 全2 decode` 是“深提示历史、浅生成”的混合策略，**不等于原生全2**。

不把任意 token 动态直接塞入当前 layer-major 批量 prefill；不同 token 读取的历史会不同，需要新的算法合同。

### 5.5 两个必须分开的验证结论

1. **端点实现正确性：**强制全2/全3在匹配的输入历史和计算路径上复现对应原生端点。
2. **混合策略正确性：**任意混合计划复现独立实现的 `depth_clamp_v1` 语义。

第二条不蕴含“复现原生三遍输出”。质量门独立于内存/算子正确性门。

## 6. 判断器、标签与可选动力学校准

### 6.1 特征：12 维，全部在停止之前可得

第 2 遍结束时已有 `h1`（上一遍出口，现有 `bank_out`）与 `h2`（当前 residual）。新增 GPU reduction 只产生小向量；不用整套 trace，不先跑 coda2，不新增一次 20 万词表 head。

| 编号 | 特征定义 |
|---|---|
| 0 | `log1p(t)`，绝对输入位置 |
| 1 | `log1p(prompt_tokens)` |
| 2 | `log1p(generated_inputs)`，已经作为输入处理的生成 token 数 |
| 3 | 剩余生成预算占初始 `max_new_tokens` 的比例，截到 `[0,1]` |
| 4 | 前一个已完成输入步骤的深度减 2；首步置 1 |
| 5 | 最近至多 16 个已完成 decode 步中第三遍的比例；无历史置 1 |
| 6 | `||h2-h1||2 / max(||h1||2, 1e-6)` |
| 7 | `dot(h1,h2) / max(||h1||2*||h2||2, 1e-12)`，截到 `[-1,1]` |
| 8 | `log(max(||h2||2,1e-6)/max(||h1||2,1e-6))` |
| 9 | `max_i(h2_i²) / max(sum_i(h2_i²),1e-12)` |
| 10 | 上一个已完成模型步骤的最终输出熵，除以 `log(valid_vocab)` |
| 11 | 上一个已完成模型步骤的最终 top-2 logit margin，截到 `[0,30]` 后除以 30 |

10/11 来自已经运行过的 final head；预填充末位也可提供。`AllTokensReplay` 的绝对位置0没有上一步head，固定置 `entropy=1, margin=0`，另记非特征元数据 `prev_head_valid=false`；后续为true，reset时清除。此首步哨兵是合法例外，其余缺失按错误处理。不允许用当前尚未运行的第三遍或当前 coda 的熵冒充这两个值。全词表概率必须在有效词表上计算；在GPU尾部reduction只留下两标量，不调用每步复制全行logits到主机的路径。额外 reduction 开销计入实测。

训练集拟合标准化均值和标准差，零方差按 1；部署固定使用同一参数。缺失、NaN、Inf 或模型/策略 hash 不匹配时停止该次研究运行并记录原因；用于演示的保守回退可选三遍，但必须单独计数，不能把回退混成正常收益。

### 6.2 两类标签，不能相互冒充

**廉价筛选标签：**同一输入前缀上的 NLL 差、最终读出差和额外毫秒，用于发现有信号的区域。raw lens 不是原生浅层输出；需要额外 coda 的诊断读出，单独计成本。NLL 也不能直接拿 `astral score` 的原始 target logit 替代，需在有效词表上做 `logsumexp`。[S12][S14]

**主要训练标签：**从当前策略真实走到的同一状态分叉，比较“现在停在两遍”与“现在继续三遍”，两条分支随后使用同一份后续策略与同一剩余预算，最终用客观验证器评分：

```text
y = score(continue3 then policy) - score(stop2 then policy)
y ∈ {-1, 0, +1}
```

`+1` 表示第三遍修复任务，`-1` 表示第三遍反而损害任务，`0` 表示判分相同。记录两条分支的真实耗时；它们可以自然产生不同后续文本。

分叉时保存的是可重放的输入：原始 prompt token、已经生成且输入的 token、此前深度计划、模型/校准/策略 hash、预算和 RNG（首版贪心）。先从头重放分支 A，再 reset 重放分支 B；分叉前 token、状态摘要必须一致。无需同时驻留两份模型。

禁止把固定全3轨迹中“第2遍看起来够好”当成混合历史下的准确标签；也禁止把逐 token 最优选择的拼接称为整个序列的可实现全局上界。早退会改变之后访问的状态。[S15]

### 6.3 唯一首版学习器

- 模型：`softmax(Wf+b)` 三分类线性模型，`W` 为 `3×12`，`b` 为 3；共 **39 个参数**，加标准化统计。
- 类别顺序固定为 `harm, tie, help`，分别对应 `y=-1,0,+1`。
- 优化：CPU 上双精度 L-BFGS，交叉熵加 `1e-3 * (||W||² + ||b||²)`，连截距一起正则化；每个原始任务总权重相同，防止长任务采样更多位置而支配训练。至少128个有效分叉、64个独立任务、32个非tie分叉且来自至少16个任务，否则学习阶段 `BLOCKED`、`reason=insufficient_informative_labels`。缺类仍可有限拟合，但要报告缺类，不声称该类概率经过验证。
- 决策：估计 `v=P(help)-P(harm)`；当 `v > lambda * extra_ms` 时继续第三遍，否则退出。`extra_ms` 来自开发集按上下文桶测得的真实差额，不是参数量推算。
- 开发集只搜索 `lambda∈{0,0.0001,0.0003,0.001,0.003,0.01}`；单位是最终任务得分/ms。dev筛选要求总体准确率点差≥−1pp、每任务族点差≥−3pp；在可行者中选端到端时间最小者。此处是开发筛选，不以256题宣称正式非劣。无可行值则保持全3并判该候选无收益。
- 训练两轮：首轮使用强制/随机计划采样；第二轮从第一轮策略实际生成的历史重新采样并标注。最多再拟合一次，不无限自举。

任何校准只在 train/dev 做；盲集答案不进入训练进程。模型置信概率不等于正确性证明。

### 6.4 动力学校准：条件触发，严格限规模

若 AD05 发现补齐历史造成系统性质量损失，但仍有清晰的可预测收益，才进入本节。否则直接跳过，记 `DEFERRED` 或 `NO_BENEFIT`。

对核心 12 层、4 种 controller、后续两遍（第2/3遍），各增加一个系数，共 **96 个新增标量**：

```text
x_out = (x - tanh(forget) * x) + alpha[pass, layer, site] * tanh(gain) * message
alpha 初始为 1，范围 [0.9, 1.1]
```

它只缩放 gain 注入项；不在 controller 输入之前缩放 message，不修改 forget。实现保持原kernel的 `x - tanh(forget)*x` 舍入顺序，不擅自改写成 `(1-tanh(forget))*x`。`alpha=1` 要走原实现分支，避免额外乘法改变逐位基线。它是本方案定义的受控干预，不是作者“326 张量编辑”的等价缩小版。

首版所有臂的prompt都用未校准的原生三遍prefill，**alpha只应用于decode**。校准后的fixed3也明确称为“原生三遍prefill＋校准三遍decode”，不能误写为整个模型都经过同一种校准。暂不改多token prefill controller。

为适应现有无反向传播的 Rust 量化运行时，首版使用**前向有限差分 SPSA**，不引入整模型 PyTorch 训练：

1. 固定训练任务、teacher-forced 正确参考序列与混合深度计划；生成参考解必须先经训练集验证器判对。
2. 目标为 `0.5*NLL(R3_decode;alpha) + 0.5*NLL(depth_clamp_schedule;alpha) + 10*mean((alpha-1)^2)`，只评分train的目标续写，prompt历史固定为未校准原生三遍。两项NLL都必须使用当前扰动后的alpha；第一项不是常数基线。
3. 最多 32 次更新，种子 20261127；每次使用同一 16 任务 batch 比较正负扰动；每条最多评分 256 个有效 token。
4. 第 k 次：`c_k=0.01/(k+1)^0.101`、`a_k=0.005/(k+1)^0.602`；以独立 Rademacher 向量作扰动，梯度估计 `(L_plus-L_minus)/(2*c_k) * delta`，更新后投影到 `[0.9,1.1]`。正负评估点同样投影，命中边界时记录其有限差分偏差，不把它称为精确梯度。
5. 仅在第 0/16/32 次做 dev 任务评价；最终只保留一个候选。总 GPU 预算 4 小时，用尽即停。
6. 四臂对照：原权重固定3、原权重动态、校准后固定3、校准后动态。它们比较各自适配后的pipeline，不自动证明纯gain因果作用。另在dev用相同强制深度计划比较alpha=1与候选alpha，并用同一旧policy参数做自由生成诊断；这两项用于减少策略重拟合的混杂。所有专家与原始权重文件hash不变。
7. 校准改变特征分布，必须重新生成训练特征并重拟合/重选策略，不能拿旧控制器直接进入盲测。校准训练首版全eager，或以稳定地址的96系数buffer复用同一非单位alpha图并在更新前同步；不能每个扰动hash保留一套graph耗尽显存。最终候选再独立捕获并绑定hash。

若固定3质量下降、混合质量不恢复、或校准收益仅存在于 teacher-forced NLL，则撤回系数，保留 `alpha=1`。

### 6.5 Jev 的具体位置

Jev 官方接口针对 state 返回类型化选择、概率或分数，适合请求级预算路由。[S16]

本轮只设置一个**可选的请求级对照**：生成前选择整请求两遍或三遍；输入仅含任务文本、可用预算和长度，输出不得含标准答案。远端延迟、失败率与费用全部计入。不把它作为 token 级热路径，不让它“证明”答案正确。

没有已授权的访问条件时，该臂记 `DEFERRED`；本地主线照常完成，不为了这个对照索取密钥或引入服务依赖。

## 7. 数据、对照与实验矩阵

### 7.1 数据注册与分割

新增 `bench/adaptive_loop/data_registry.json`，每项必须记录：来源 URL/本地路径、固定 revision、文件 SHA256、许可、题目 ID、题族/仓库/文档组、题面、标准答案或判分器引用、数据用途。没有真实数据的项保持缺失并阻塞相关实验，不能临时用 mock 填满数量。

使用三类可客观判分的任务：

| 任务族 | 数据与判分 | 限制 |
|---|---|---|
| 数学 | 优先现有已登记题库；补充 GSM8K 官方数据。最终答案规范化后严格比较；有歧义的表达式须有冻结的解析规则 | 公开 test 与预训练污染无法排除，只能称“对本控制器封口” |
| 代码 | 优先现有可运行测试；补充 LiveCodeBench 官方冻结快照，使用其测试与判分口径 | 先证明官方 harness 可运行；缺容器/依赖时该族 `BLOCKED`，不改成模型自评 |
| 多跳/长依赖 | 新建确定性生成器：有向无环图上的路径/指针追踪，hop 为 1/2/4/8/16，随机标识符与干扰项；生成器自己提供精确答案 | 这是机制实验，不能用成千上万同模板变体冒充真实代码任务泛化 |

官方数据入口见 [S17][S18]。执行时先解析并锁定实际仓库与数据 revision，之后不随 `main/latest` 浮动。

分割规则：

1. 按原始题目、文档、代码仓库或生成模板族分组后拆分，所有变体、切片、种子衍生题随组走。
2. 首轮训练目标 512 个独立组；dev 256 个独立组，数学/代码/多跳按 2:2:1 尽量分层。数量不足时记录实际覆盖，不复制题目补数。
3. 从 dev 另预先划出 64 个 pilot 组，用于固定深度成本与标签流程调试；仍属于已见数据。
4. 最终test的**储备池**组名单和hash在调候选前封口；最终N只由dev与预算在揭盲前确定，再冻结实际抽样名单。执行代理可以读取题面运行推理，拟合与调参进程不得读取其答案或中间评分。
5. 本项目已有 B/C/D 集只用于工程回归。新的统计 test 名称用 `AD-E1`，与 T25 的工程 E 集分别命名、分别记录；若共享任务，必须披露且不得算独立未见数据。
6. 数据注册器对跨集合规范化题面重复、代码 AST/模板重复、来源组重复做检查。检查能发现部分泄漏，不能证明消除了模型预训练污染。

**统计范围必须另行登记：**train/dev的2:2:1配额不等于最终抽样设计。合成多跳只作机制/压力证据，不并入真实数学和代码的主要质量非劣结论。AD-E1必须在开盲前选择 `sampling_design=iid_population` 或 `fixed_benchmark`：前者要求预注册明确目标总体、独立同分布抽样协议/超总体假设，每个独立组只计一个主问题，才使用第9.3节的二项/三项推断；固定题库、固定族配额或相关模板题不能自动被程序认定满足该条件。若现场只有固定benchmark，则默认后者，报告该有限题集的精确差值，总体非劣门记BLOCKED。不得看到结果后补写“IID”以取得PASS。固定分层设计若要总体CI，需要另行预注册分层错误概率分配并重算功效，不沿用本文件的三个样本量示例。

首轮 `max_new_tokens=1024`、贪心、batch=1；主延迟集提示长度 ≤2048 token。代码题若在 pilot 中大量触顶，允许在看候选结果之前把**所有策略**的上限一次性改成 2048 并重新封口。token 上限、thinking 模式、模板、EOS 规则随后不再变。

额外压力集：提示 2K/8K，生成最长 2048 token，观察重复循环、截断和深度漂移；16K/32K 只在主线通过且所需长文数值合同已具备时做，不直接扩展到 128K。

### 7.2 对照组

所有 A4 对照使用同一加载器、同一权重 hash、同一有效词表和同一模板。每个对照必须记录 prefill 策略。

| ID | 策略 | 目的 |
|---|---|---|
| B0 | A4 native 全3，现有原生 graph | 主质量与性能基线 |
| B1 | A4 native 全2 | 固定低成本端点 |
| B2 | 请求级本地路由选择 native 全2或全3，选择在 prefill 前完成 | 测量更便宜的请求级方案 |
| B3 | native3 prefill；decode 用匹配深度比例的随机 2/3 计划 | 区分“聪明决策”与“少算一些” |
| B4 | native3 prefill；按 `||h2-h1||/||h1||` 单阈值选择 | 廉价相似度基线；阈值仅在 dev 选 |
| C0 | native3 prefill；本地收益判断器；`alpha=1` | 主候选 |
| C1 | C0 加第 6.4 节校准；以及对应校准后 fixed3 | 条件触发；另用相同强制计划控制重拟合混杂 |
| J0 | Jev 请求级整请求选择 | 有访问条件时的可选对照 |
| P0/P1 | A1 plain3 / 现有 DSpark3 | 项目实用参照；不用于归因 A4 调度增益 |

B2首版采用CPU逻辑回归，输入只含提示token数、预设任务族、可用生成预算三个特征；权重与截距都用1e-3 L2正则。train中若两策略正确性不同，标签选正确者；相同则选完整请求耗时更小者，耗时完全相同选3。dev阈值从0.25/0.5/0.75选择，质量筛选与第6.3节相同；未知任务族保守选3并计数。不得把标准答案、题目ID或固定策略运行后的结果放入请求特征。

请求级 B2 的离线诊断可以先把任务分桶，分别加载固定深度跑完；这只能报告“已驻留模型的推理成本”。真实逐请求切换若仍需重载模型，必须计入重载时间；不能把它包装成已具备低成本的在线请求路由。首轮无需为 B2 重构权重共享。

B3 的浅深比例在 dev 按 C0 冻结，种子预先固定；test 不再根据候选实际通过率调整随机比例。B4 阈值从训练特征分位数 `{10,25,50,75,90}` 中选择，在 dev 质量约束内取最快者。

### 7.3 阶段矩阵与避免无谓笛卡尔积

| 阶段 | 模型/深度 | 数据规模 | 允许结论 |
|---|---|---|---|
| 固定深度 pilot | A4 2/3；少量 1/4/5；A1 2/3负对照 | 64 dev 组；1/4/5各只选16组 | 是否存在任务差异与可用成本空间 |
| 状态正确性 | A4 强制计划，不训练 | 小张量单测＋16个真实前缀/边界用例 | 实现符合规定语义 |
| 第一轮标签 | 同一混合历史下 stop/continue | 128 train 任务，各最多2个分叉点 | 拟合首版控制器 |
| 第二轮标签 | 第一轮策略自身历史 | 128个 train 任务，各最多2个分叉点 | 纠正访问状态的偏移 |
| 开发比较 | B0—B4、C0；必要时 C1 | 256 dev 组 | 冻结唯一候选、参数和样本量 |
| 封口验证 | B0、唯一候选；选定简单对照作次要比较 | 按第9节计算，受真实数据与预算限制 | 有限总体/指定任务分布上的质量与延迟结论 |
| 压力检查 | 唯一候选、对应 fixed3 | 2K/8K、长生成、reset与边界 | 可靠性与适用范围；不是无限长保证 |

分叉位置在读取分叉结果之前，用基于已访问前缀的固定hash/reservoir规则选取，每题最多两个，并记录抽样概率。不能将最终生成长度或尚未出现的后缀变成线上特征。若一个任务没有足够可分叉位置，记录并保留在任务计数中，不能只挑“能展示收益”的位置。

## 8. 正确性验证：测试必须有证明力

### 8.1 CPU 独立状态 oracle

新增一个与 CUDA 实现不同结构的 NumPy 小模型。维度可以缩小，但必须包含：物理层/遍数/slot 映射、按真实 token 时间推进的四路短卷积、全局 KV、SWA 环行、最后所选遍的 coda 输入和单次位置提交。

此 oracle 负责验证**状态规则**。真实张量数值仍需 GPU 对照；小模型通过不能替代 A4 验收。

强制计划至少包括：

```text
[2,2,2,2]   [3,3,3,3]   [3,2,3,2]   [2,2,3,3]
[3,3,2,2,2,3]   固定种子生成的64步混合计划
```

每一步比较全部核心层的写入来源、各卷积历史和位置，而不是只比较最终 logits。

### 8.2 必须失败的负控制

| 错误注入 | 必须被哪项断言捕获 |
|---|---|
| 只补全局层，漏 SWA | 当前环行或后续注意力历史不同 |
| 只补 KV，漏某一处 conv | 4路状态 oracle 对账失败 |
| 把 H2 全部复制到 H3 | `3→2→3` 时历史来源失败 |
| 补齐错误的 slot 或物理层 | 不同层使用非同值哨兵，立即发现串槽 |
| SWA 写 `t%1024` 而不是实际 ring 行 | 实际 `rows−1/rows/rows+1` 边界失败 |
| 在一次 token 内执行两次 coda/推进两次 pos | 调用计数/状态递推失败 |
| 特征含 `x_(t+1)`、标准答案、pass3 tensor | 特征来源检查或后缀置换失败 |
| 复用 reset 前的判断历史/conv | A→reset→B→reset→A 与全新A不同 |
| 主动把待覆盖K3/V3当前行填成NaN；conv旧态使用分层分时刻有限哨兵 | KV仍残留毒值或conv不等于`(old1,old2,H2_newest)`则失败；不能把需保留的合法conv历史也毒化 |

只比较“重复两次输出相同”无法排除固定错误。每个关键测试要运行正确版本和对应错误版本，保留后者确实失败的输出。

### 8.3 真模型端点与混合语义

1. `adaptive disabled` 对当前基线，固定真实 token 输入，step/prefill/decode 保持逐位一致。
2. 诊断 token-major 全2/全3，分别与 native 全2/全3 的相同 eager 路径比较；先比较中间执行槽，再比较最终有效词表 logits。
3. 动态 CPU oracle 不复刻整个神经网络；真实混合计划再与**独立、慢速的 GPU reference**比较。后者按物理层逐项执行和显式更新历史，不调用候选补齐 kernel。
4. `native3_prefill` 的不同chunk划分接同一强制decode计划。相同算术形状要求逐位一致；跨chunk形状按预先冻结的原生三遍自对照误差界比较，并固定D，避免数值差异改变门控后混淆状态验证。
5. 边界覆盖 token 0/1/2/3、1023/1024/1025、实际 ring 行数前后、prefill chunk 尾和首个 decode、capacity−1。
6. 固定前缀、此前深度计划、prompt长度、预算和其他线上可见元数据，改变未输入的后缀，前缀各步输出和特征不得变化；绝对首步head哨兵单独验证。
7. EOS/最大长度/取消：返回的最后预测 token 未必已经作为输入提交，沿用现有不变量；取消后不得继续使用半步状态。
8. 若未来增加持久快照或 prefix cache，另立功能；首版收到这类动态状态请求应明确拒绝，不能声称已有支持。

同 kernel、同算术顺序的重排先要求逐位一致。若优化引入新的算术路径，先定位原因，再按原有数值合同验证；不得自动把“不相同”改成“差不多就通过”。新策略相对 native3 的差异属于质量实验，不用数值容差掩盖。

### 8.4 与既有回归的关系

- 原生 A1 路径仍跑原合同要求的相关 G2/T20 回归；不能只跑 T19 C 集重复 T16 第1轮的漏测。
- D 集保留已有 FAIL，并检查是否出现新增异常；不能把它换个名字算新通过。
- A4 比较使用 A4 自己的 native 参考；`verify-model` 中的 A1 golden 不能强制用于 A4。
- 工具输出必须记录实际 dispatch、有效输入平面、非零响应和失败退出码。空目录、空结果或 JSON 中 `NaN` 一律不通过。

## 9. 性能和统计验收

### 9.1 两种计时，各有用途

**固定 token replay：**所有策略吃完全相同的 token 序列，隔离算子、判断、补齐和 graph 开销。可固定输出步数；不声称它反映整题完成时间。

**真实自由生成：**同题同模板同预算，正常 EOS，包含 tokenization、prefill、判断、状态维护、生成与终止。模型加载时间另列冷启动；实际请求需要重载时，必须计入该请求延迟。

主报告最少包含：

| 指标 | 定义 |
|---|---|
| 任务准确率 | 客观判分成功任务/全部计划任务；超时、无答案、截断按冻结规则计失败 |
| end-to-end latency | 请求开始到最后输出/终止的 wall time，带 CUDA 同步确认 |
| TTFT | 请求开始到第一个输出 token；首版 prefill 固定3，不默认预期有收益 |
| decode time / token | native3 prefill已给出第一个输出；decode分子仅计 `max(emitted_tokens−1,0)`，分母匹配后续decode wall时间 |
| overall decode tok/s | `sum(max(emitted_tokens−1,0)) / sum(decode_seconds)`；只有一个输出的请求仍计入TTFT/E2E，与“每题速度均值”分开 |
| latency p50/p95 | 按独立题目/请求汇总；同时给输出 token 数分布 |
| 第三遍比例 | 每题、每任务族、生成位置桶和上下文桶分别报告 |
| 分项成本 | prefix两遍、third pass、feature/gate、fill、coda/head、同步与其他 |
| 资源 | NVML 峰值、进程/分配器高水位、主机RSS、graph/工作区；采样间隔明确 |
| 稳定性 | 复读、EOS、截断、非有限值、fallback、异常退出、reset错误 |

短 trace 或 profiler 的吞吐单列，不与无 profiler 计时混合。只读记录温度、功耗、时钟；测试顺序随机交叉，先 warm-up，固定性能子集每策略5次，先按题汇总再做配对统计。

### 9.2 最终共同门槛

下表是**本方案建议并预先冻结的工程标准**，不是已有结论：

| 门 | 通过条件 |
|---|---|
| 语义/状态 | 第8节必测和负控制通过；无未解释的数据缺项、NaN、错位或半步提交 |
| 质量主门 | 对 B0 的准确率差，单侧95%置信下界严格大于 `−0.01` |
| 端到端主门 | 配对请求延迟的相对改善，其95% bootstrap下界至少 `10%` |
| 长尾 | TTFT p95 与整题延迟 p95 的候选/基线比值，各自95% bootstrap上界≤`1.10` |
| 分族警戒 | 任一预注册任务族准确率点估计下降超过3个百分点则失败；每族CI照报，不把总体通过解释为每族均证明非劣 |
| 稳定性 | 无运行错误；复读/截断新增率相对B0不超过1个百分点的点估计，附区间；涉及大量不确定时不能宣称长期稳定 |
| 资源 | 峰值不超过物理容量；相对相同capacity的B0额外显存≤256 MiB，且至少留512 MiB余量 |

质量与速度必须同时通过才记本轮主候选 `PASS`。内存/状态错误直接 `FAIL`；没有净收益为 `NO_BENEFIT`；统计或资源不足为 `BLOCKED` 并说明原因。

针对 B2/B4 的比较属于次要分析：若学习器不优于最好的简单策略，不能宣称学习复杂度必要。若 A4 主候选通过但不优于 A1+DSpark，结论可以是“自适应循环机制成立，尚无现有项目整体速度优势”。

### 9.3 配对质量统计：避免小样本假通过

每个独立题目只计一次主要判分。定义：

- `W`：候选正确、B0错误。
- `L`：候选错误、B0正确。
- `D=W+L`，`N` 为全部有效计划的独立题数。
- 准确率差为 `(W−L)/N`；共同正确和共同错误均计入 N。

不要对两组独立比例置信区间相减，也不要把 token、重跑次数或同题变体当成 N。

**仅在AD00预注册并有依据的IID配对抽样/超总体模型下**，首版采用下述保守有限样本下界。记 `q=P(判分不一致)`，`r=P(候选赢 | 不一致)`，则差值为 `q*(2r−1)`。对q取单侧99% Clopper–Pearson上界，对r取单侧96%下界；预分配错误概率0.01+0.04，在该假设下得到覆盖至少95%的非劣下界。独立但不同分布、固定分层或同模板相关题不能直接套用。固定benchmark报告有限题集精确差值，不将这个函数的输出冒充无条件总体保证。

以下函数是**统计实现规范**，不是模型测试结果：

```python
def paired_noninferiority_lower(wins: int, losses: int, n: int) -> float:
    from scipy.stats import beta
    if not (n > 0 and 0 <= wins and 0 <= losses and wins + losses <= n):
        raise ValueError("invalid paired counts")
    d = wins + losses
    q_upper = 1.0 if d == n else float(beta.ppf(0.99, d + 1, n - d))
    r_lower = 0.0 if wins == 0 else float(beta.ppf(0.04, wins, d - wins + 1))
    return min(0.0, q_upper * (2.0 * r_lower - 1.0))
```

该下界特意截在0，只用于检验 `LB>−0.01`，**不能拿它证明正向质量提升**。若要主张质量提高，需要预先另立相应检验；本轮先报告差值和区间。

至少验证：非法计数报错；`W=L=0,N=100` 不通过1pp非劣；`W=L=0,N=1000` 可以通过；增加损失不会改善结论；与小N三项分布枚举对照，避免误用独立样本检验。

规划上，若真实质量相同、判分不一致概率为2%/5%/10%，采用这个保守规则，约需 **2600/4700/8100** 个独立题达到约80%功效。这是统计设计示例，执行时必须用 dev 的不一致率及其不确定区间重新枚举/模拟。

**实际流程：**先估每题时间与不一致率，再计算可负担 N。真实独立任务不够、或 GPU 预算无法完成所需 N，就执行已冻结的小规模验证并报告 CI，最终记 `BLOCKED`、`reason=insufficient_power`。不增大允许损失，不复制题目，不反复看结果直到通过。

### 9.4 延迟统计

每题先取5次性能重复的中位数，计算 `log(latency_candidate/latency_B0)`；以独立任务组为重采样单位，固定种子20261127，bootstrap 10000次。由平均log比值转换几何平均延迟比及区间，再转换相对改善。

若 test 使用多个预设任务族，按封口权重分层重采样。NLL 多位置、同题多个分叉和重跑次数均不能作为独立 cluster。p95 比值同样按任务重采样，短样本时必须披露区间宽度。

最终盲测只开一次。若观察后修改策略、特征、alpha、阈值、数据或 judge，原 test 立即降为 dev，新结论需要新的独立封口集。

## 10. 实现边界与文件/接口合同

### 10.1 EXISTING：已经存在，先读再改

| 文件 | 本轮关系 |
|---|---|
| `crates/model/src/inkling.rs` | Config、Session、forward、按pass执行、KV/conv/graph |
| `crates/model/src/inkling/probe.rs` | 诊断探针；不要让完整探针进入性能路径 |
| `crates/kernels-src/cu/inkling.cu` | 原生K/V与post-conv更新；新增补齐kernel的原始依据 |
| `crates/kernels/src/inkling.rs` | CUDA调用包装；按实际已有接口风格扩展 |
| `crates/cli/src/main.rs` | 加独立研究子命令；保留原命令行为 |
| `crates/loader/src/inkling_checkpoint.rs` | A4加载与转换身份；原则上不改变 |
| `bench/llamacpp_compare/logit_compare.py` | 复用已存在的数值比较口径 |
| 实验室 `tools/paired_stats.py` | 复用配对延迟统计思想，核对本轮任务cluster粒度 |

若现场文件结构已改变，AD00只记录实际对应关系，不照抄不存在路径。改动原源码前阅读其目录 AGENTS。所有新文件遵循现有许可证/NOTICE 约定。

### 10.2 NEW：拟新增文件

| 文件 | 单一责任 |
|---|---|
| `crates/model/src/inkling/adaptive.rs` | 配置、深度策略、前向分段及状态提交 |
| `crates/cli/src/adaptive.rs` | JSONL输入输出、研究运行/诊断命令 |
| `bench/adaptive_loop/schema.py` | config/run/decision/result严格校验 |
| `bench/adaptive_loop/state_reference.py` | 独立CPU状态oracle |
| `bench/adaptive_loop/datasets.py` | 数据注册、分组拆分、hash、判分适配 |
| `bench/adaptive_loop/collect.py` | 固定深度和混合历史分叉采集 |
| `bench/adaptive_loop/fit_policy.py` | 39参数模型拟合与dev选择 |
| `bench/adaptive_loop/calibrate_gain.py` | 条件触发的96系数前向校准 |
| `bench/adaptive_loop/paired_eval.py` | 配对质量下界、功效与延迟CI |
| `bench/adaptive_loop/run.py` | 依赖/预算/续跑/证据驱动的单一入口 |
| `bench/adaptive_loop/tests/` | schema、状态、泄漏、统计与负控制 |
| `bench/adaptive_loop/config.example.json` | 可校验的首版配置 |

本轮无需新增 web 服务、数据库、消息队列或通用调度框架。

### 10.3 NEW Rust 接口

以下是拟实现的接口，项目已有 `Result`/设备类型以其真实定义为准，不创造第二套错误处理体系。

```rust
pub enum PrefillPolicy { Native3, AllTokensReplay }
pub enum DepthDecision { Two, Three }
pub enum AdaptivePolicy {
    Forced(Vec<u8>),
    Constant(u8),
    Random { p_three: f32, seed: u64 },
    ResidualThreshold { threshold: f32 },
    LinearValue { policy_path: std::path::PathBuf },
}
pub struct AdaptiveConfig {
    pub prefill: PrefillPolicy,
    pub policy: AdaptivePolicy,
    pub max_new_tokens: u32,
    pub cache_policy: String, // must equal "depth_clamp_v1"
    pub gain_path: Option<std::path::PathBuf>,
}
pub struct AdaptiveStep {
    pub input_position: u32,
    pub input_token: u32,
    pub next_token: u32,
    pub chosen_depth: u8,
    pub features: [f32; 12],
}
// Methods to add on the existing Session:
// enable_adaptive(&mut self, cfg: AdaptiveConfig) -> Result<()>
// prefill_adaptive(&mut self, tokens: &[u32]) -> Result<u32>
// step_adaptive(&mut self, token: u32) -> Result<AdaptiveStep>
```

`prefill_adaptive`的返回值是首个预测token，不是已提交输入。`enable_adaptive`要求实际加载的 `cfg.passes==3 && n_slots()==48`，检查遗留 `ASTRAL_PASSES` 环境覆盖；已按R2分配的Session必须拒绝或重建，不能越界使用。prompt为空、budget为0、强制计划不足、depth不是2/3、启用spec或checkpoint非A4时明确报错。支持A1只限显式负对照模式。互斥必须双向：adaptive启用后再调用enable_spec也拒绝；普通step/prefill不能绕过已启用的adaptive状态造成历史污染。

**缓存补齐包装**：新增 `fill_missing_depth3`，参数为12层第二/第三遍KV指针、各层ring容量、四路conv指针、绝对位置、维度与stream。kernel不计算新的投影，只复制当前16位存储行并推进第三遍自己的三项F32历史。CPU与CUDA都使用显式形状检查。

**graph模式**：先保留旧一整张graph原样。新增两个阶段：G12执行prelude+两遍+小特征；主机作一次决定；G2执行补齐+coda/head，或G3执行第三遍+coda/head。`blocks/prelude_blocks/next_row/visit`当前是捕获时的Rust局部量，必须分别预编停止/继续尾图的行号计划，不能假设自动跨图保存。`prelude/bank/bank_out/cur`保持稳定设备地址，特征reduction在G3覆写bank_out前完成。最终推理图绑定权重/alpha身份、capacity、tmax、ring布局、prefill策略与模式；训练扰动按第6.4节复用或释放图，不累积历史版本。首版不依赖4090上不可用的Hopper专属机制。

### 10.4 NEW JSON 记录合同

每次运行保持原实验室文件布局，并增加决策/逐题结果：

```text
run.json             身份、环境、模板、资产、预算、模式、判定规则
config.lock.json     已封口配置及其hash
decisions.jsonl      输入位置、所选深度、12维特征、状态来源、计时
cases.jsonl          每题原始输出、token数、judge、停止原因与耗时
metrics.json         汇总、置信区间、状态与reason
stdout.log
stderr.log
evidence.sha256      以上文件和可恢复的大文件身份
```

`run.json` 继续保留原有 `template_hash/rendered_token_ids_hash/add_generation_prompt/special_token_policy/eos_policy/reasoning_mode`；另加 `engine_commit/binary_sha256/worktree_diff_sha256/model_sha256/loader_revision/gain_sha256/policy_sha256/prefill_policy/cache_policy/capacity/tmax/kernel_dispatch/trace_enabled/dataset_hash/judge_hash`。[S4]

数据结构硬规则：

- 复合键 `run_id+strategy_id+repeat_id+branch_id+case_id+input_position` 唯一；token位置连续，`depth_history`长度与实际已执行输入步骤一致，prefill/decode阶段显式标明。每个输出目录隔离对应运行身份，不跨策略覆盖。
- 特征只能有第6节的12项；target/answer/y存放于离线标签记录，不能成为在线feature字段。
- 同一次任务不能在中途换policy、gain或模型hash；封口test也不能热更新。
- 没有测量的值为 `null`，禁止填0伪装；非有限值拒收。
- 结果缺题、命令失败或原始输出不可恢复时不能生成PASS。
- 返回码：0表示指定阶段完成其合同；2配置/缺输入；3驱动守卫；10正确性或质量失败；11无收益；12资源/统计不足。JSON状态必须与返回码一致。

## 11. AI 可执行任务清单

依赖：`AD00 → AD01 → AD02 → AD03 → AD04 → AD05 →（条件AD06）→ AD07 → AD08 → AD09`。独立的CPU数据校验和文档整理可并行，GPU全部串行。每项完成后保存原始证据并做一次局部提交；本文件不授权对外推送。

### AD00 — 固定现场、资产、数据与判定合同

**Files：**NEW `schema.py`、`datasets.py`、`config.example.json`、对应 tests；读取现有 AGENTS/runbook/model lock，不改已有资产。

**Consumes：**第2节两个仓库SHA、A1/A4模型身份、既有环境文件与驱动基线。

**Produces：**`run.json`、`data_registry.json`、train/dev/test储备池manifest、`config.lock.json`；明确执行模式与预算。

- [ ] 读取现场 git status、commit、模型 lock、GPU 与生产授权记录；任何未提交用户改动保留。
- [ ] 校验 A1/A4 实际文件 hash、tokenizer/模板、加载转换精度；不把“名字相同”当作同一资产。
- [ ] 先写并运行 schema 失败用例：缺hash、非法pass、非有限数字、重复题、跨集同组、缺judge、无效状态退出码。
- [ ] 实现数据登记、分组检查与封口；test评分文件不传给拟合入口。
- [ ] 冻结第9节门槛、生成预算、数据推断范围和GPU总预算；逐项列出缺失项。
- [ ] 验证 CPU 测试通过、故意破坏配置被拒绝。无GPU时仅完成CPU部分，整体GPU前置记 `BLOCKED`。

**Gate：**没有明确模型、数据、参考或驱动基线，不进入GPU实验。

### AD01 — 复测固定深度与任务差异

**Files：**NEW `collect.py` 的 fixed-depth 模式、`run.py` 的 `fixed-depth` 阶段；复用现有 dump/compare，不改kernel。

**Consumes：**AD00锁定资产与64个pilot组。

**Produces：**B0/B1逐题结果、固定1/4/5小对照、成本表、请求级事后选择曲线。

- [ ] 用当前基线重跑A4 R2/R3，原生whole-request缓存各自重建，不跨深度复用。
- [ ] 验证完整judge能区分已知正确/错误答案，超时/无输出不被算为成功。
- [ ] A1只做少量截断负对照；不花预算重新寻找已证实有明显PPL退化的路径。
- [ ] 记录tokenization、prefill、decode、最终分数、输出长度、冷/热启动分别计时。
- [ ] 计算第4节定义的请求级成本空间，另列第三遍修复题和损害题，不能只记平均准确率。
- [ ] 冻结是否继续及限额探针理由；没有收益时按停止条件结案。

**Gate：**已有任务差异和可利用时间空间，或已按合同启用一次限额token探针；不因PPL略降就直接训练。

### AD02 — 先把混合历史规则做成可否证的参考

**Files：**NEW `state_reference.py`、`tests/test_state_reference.py`；模型中NEW `adaptive.rs`的配置/索引纯逻辑部分。

**Consumes：**第5节完整语义；输入为token位置、强制深度计划、明确原始卷积输入和K/V行。

**Produces：**独立状态oracle、slot/source表、边界与负控制测试输出。

- [ ] 先写 `3→2→3` 失败用例，明确H3必须保留它自己的前史；加入整段复制H2的错误实现。
- [ ] 实现四路conv、全局/SWA当前行补齐与单次pos提交，覆盖所有12核心层。
- [ ] 写后缀置换、reset隔离、非零正负输入和不同层哨兵；错误版本必须失败。
- [ ] 对强制全2/全3/混合64步计划逐步核对完整状态。
- [ ] 记录状态规则与原模型语义不同的地方；评审确认没有隐藏的缺失状态才进入GPU实现。

**Gate：**测试不能只由候选实现生成期望值；CPU oracle通过仅表示规则自洽。

### AD03 — 接入GPU补齐和eager动态前向

**Files：**Modify `inkling.rs`、`crates/kernels/src/inkling.rs`、`inkling.cu`；NEW `adaptive.rs`、CLI研究入口。

**Consumes：**AD02规则和测试向量。

**Produces：**`adaptive-run`/`adaptive-check`新CLI、强制计划eager路径、独立慢速GPU参考、状态/数值证据。

- [ ] 先增加真实kernel测试：缺一个conv位置或SWA层必须失败。
- [ ] 实现 `fill_missing_depth3`；使用第二遍slot的最新原始历史项，不从已复用scratch猜测输入。
- [ ] 把原生前向分成可审阅阶段，保持disabled路径；先只支持batch=1、无DSpark、无动态prefill。
- [ ] 实现显式慢速参考，不复用候选补齐kernel；对同一强制计划逐位置核对。
- [ ] 实测全2、全3端点、原生三遍prefill接全3decode；在同kernel路径上先要求逐位一致。
- [ ] 做第8节边界、取消、EOS、reset与毒化；记录coda调用恰一次、pos恰推进一次。
- [ ] 检查原生A1相关回归，没有引入新退化；D集保持历史标签并报告增量。

**Gate：**任一状态错误未解释则 `FAIL`；不允许进入学习阶段用训练“补偿程序bug”。

### AD04 — 提取廉价因果特征与分叉采集

**Files：**Modify GPU包装/模型；NEW `collect.py` 的branch模式、`tests/test_causality.py`。

**Consumes：**AD03已验证的真实混合状态与第6节12项特征。

**Produces：**`features.jsonl`、独立 `labels.jsonl`、branch来源与前缀一致证据。

- [ ] 构造未来token/答案混入特征的错误版本，确认白名单或前缀不变性检查会失败。
- [ ] 在G12对应位置读取h1/h2；上一步head只保留熵/margin两标量，禁止200K logits每步读回CPU。
- [ ] 收集第一轮128任务×最多2个分叉点。先重放A，再reset重放B，核对分叉前身份与状态摘要。
- [ ] 两分支都执行完整coda与后续生成；最终score产生help/tie/harm标签。
- [ ] 记录重放、分叉和后续生成的全部采集成本；不把离线数据成本写成线上开销。
- [ ] 检查有效标签数、独立任务数、类别分布及精确可重放性。

**Gate：**特征泄漏直接FAIL；信息量不足按第6节规则BLOCKED，不把大量tie强行解释为成功。

### AD05 — 训练并验证第一个真实在线控制器

**Files：**NEW `fit_policy.py`、`tests/test_policy.py`；完善 `run.py`。

**Consumes：**AD04训练数据、dev集合、AD01/AD03成本表。

**Produces：**39参数policy、标准化统计、B2/B3/B4/C0比较、第二轮on-policy数据、冻结候选。

- [ ] 先写参数维度、标签映射、标准化和非有限输入拒绝测试；对小型已知线性数据检查学习方向，测试结果不当作模型收益。
- [ ] 按第6.3节拟合和dev选择，记录每个候选lambda；对照必须用相同质量筛选条件。
- [ ] 用第一轮policy自由生成，再按冻结规则抽128任务×最多2个位置重做分叉标注。
- [ ] 重新拟合一次，比较最好的简单策略，核对错误退出是否集中在代码、长生成或特定位置。
- [ ] 选择唯一最终policy，或说明需要AD06/停止；不把三个不同指标最好的policy拼成一个“虚拟候选”。

**Gate：**计入全部在线开销后，dev质量筛选可行且端到端时间有改善；否则进入一次已有证据支持的修正或NO_BENEFIT。

### AD06 — 条件执行96系数校准

**Files：**NEW `calibrate_gain.py`；Modify模型controller调用及对应CUDA实现；新增干预测试。

**Consumes：**AD05明确的系统误差、训练参考、冻结的SPSA合同。

**Produces：**一个gain文件或回滚结论；四臂结果；重新拟合的policy。

- [ ] 先验证alpha=1回到原生实现；alpha=0诊断只去gain项、保留forget，避免改错位置。
- [ ] 每次扰动记录实际kernel命中与alpha hash；所有原始权重hash保持不变。
- [ ] 按第6.4节最多32步/4GPU小时，不能用缺失的反向传播接口作假实现。
- [ ] 用四臂分离校准和策略贡献；NLL下降而任务无收益则不保留。
- [ ] 校准保留后重新生成特征/拟合；不追加第三轮盲目搜索。

**Gate：**固定深度的保留能力和动态任务质量均有证据；否则恢复alpha=1，AD05仍可独立结案。

### AD07 — 把已正确的算法变成可测量的快速实现

**Files：**Modify `adaptive.rs` 的graph捕获/回放；已有原生graph保持；完善计时与日志缓冲。

**Consumes：**已冻结策略和语义正确的eager实现。

**Produces：**G12/G2/G3分段graph、严格输出对照、开销分解及同机性能数据。

- [ ] 明确host侧blocks/next_row静态计划与device缓冲地址，不把Rust局部变量当跨graph自动保存状态。
- [ ] graph捕获/预热在干净状态完成，之后reset/replay；捕获不能污染真实请求。
- [ ] G12末尾、G3覆写bank_out之前计算特征；主机同步点计入wall time。
- [ ] graph/eager在同一强制计划下比对，并检查alpha、policy、capacity变化会使旧图失效。
- [ ] 比较native3、分段全3、分段全2、实际policy；把分段本身的成本单列。
- [ ] 线上计时禁用完整trace和逐token同步落盘；日志先缓冲，采集/flush成本单列并保证生产可见开销被计入相应指标。
- [ ] 只允许一次有profiler依据的热点缩减；不顺势开始通用kernel平台改造。

**Gate：**在无质量变化的前提下通过状态/数值检查；成本超预算则NO_BENEFIT，不能用eager中的理想节省报最终速度。

### AD08 — 一次封口验证与强基线比较

**Files：**NEW `paired_eval.py`、`tests/test_paired_eval.py`；完善run调度。

**Consumes：**唯一候选、全部hash、真实采样设计、最终N、冻结judge与预算。

**Produces：**逐题输出、质量差与CI、端到端/长尾CI、资源/稳定性、最终状态。

- [ ] 在看test候选结果之前，用dev成本和不一致率做功效/预算计算，冻结最终N。
- [ ] 测试统计程序：边界计数、无分歧、有损失、缺题、无效数字、错配case、重复运行和返回码。
- [ ] 真实test运行B0与唯一候选；性能子集预先选64题、每策略5次，随机交叉；准确率每题只记首个规定运行。
- [ ] 跑选定简单对照及A1 plain/DSpark参照，明确哪些是次要比较和不同模型。
- [ ] 完整报告超时、截断和运行失败；出现运行错误时先标实验失败，不删除错误题后重算。
- [ ] 同时判断第9.2节各门；资源/样本不足时给出精确缺口，不给通过承诺。

**Gate：**只有全部主门满足才PASS；一旦改候选，原封口集降为开发用途。

### AD09 — 结案、复现与下一步决策

**Files：**结果目录完整证据；实验室任务记录中的AD章节或关联项；不覆盖旧结论。

**Consumes：**所有阶段的状态、原始输出与成本。

**Produces：**一个最终报告，列明机制、质量、速度、限制、停止原因和复现命令。

- [ ] 检查每个结论能追到同一版本的输入、命令和原始输出；大文件有实际可恢复路径，不只有hash。
- [ ] 更新原R1/R2/R6/R9的关联进展，不把历史T18或T16重复登记成新成果。
- [ ] 失败也保留可复现的最小反例：错slot、错误深度判断、状态漂移、成本被吃掉的具体位置。
- [ ] 默认保持功能关闭；研究PASS不等于生产切换授权。
- [ ] 根据第14节规则决定是否值得开启2/3/4遍后续合同；不自动开启。

## 12. 命令手册：区分现有能力与待实现接口

### 12.1 当前仓库已有的只读前置检查

以下在4090主机按既有用户执行，不需要安装新驱动或下载新大模型：

```bash
set -euo pipefail
source "$HOME/inkling-lab-v3/env.sh"
bash "$PKG/tools/driver_guard.sh" check "$LAB/evidence/driver-baseline.txt"
git -C "$LAB/src/astral" rev-parse HEAD
git -C "$LAB/src/astral" status --short
"$NVCC" --version
nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv
test -f "$MODELS/models.lock.json"
test -f "$MODELS/varloop-native/model-00001-of-00001.safetensors"
```

如果路径与现场不同，从既有env/model lock解析实际路径并记录，不能创建假文件让test通过。

### 12.2 已有的固定深度数值导出

下面复用T19已存在的manifest；它只是回归输入，不能当AD-E1盲集。目录缺失时记录BLOCKED或由数据注册任务生成独立manifest，不能凭空填路径。

```bash
set -euo pipefail
source "$HOME/inkling-lab-v3/env.sh"
AD_AST="$LAB/src/astral/target/release/astral"
AD_MODEL="$MODELS/varloop-native"
AD_C_DIR="$(cat "$LAB/runs/t19/LATEST_C")"
AD_MANIFEST="$AD_C_DIR/manifest_c.tsv"
AD_OUT="$LAB/runs/adaptive-loop/baseline-$(date -u +%Y%m%dT%H%M%SZ)"
test -f "$AD_MANIFEST"
mkdir -p "$AD_OUT"
ASTRAL_PASSES=2 ASTRAL_DUMP_KINDS=step,decode \
  "$AD_AST" dump-final-logits "$AD_MODEL" "$AD_MANIFEST" "$AD_OUT/r2"
ASTRAL_PASSES=3 ASTRAL_DUMP_KINDS=step,decode \
  "$AD_AST" dump-final-logits "$AD_MODEL" "$AD_MANIFEST" "$AD_OUT/r3"
```

`dump-final-logits` 首个长度不会有单独decode文件，后续长度才有；manifest和校验器必须尊重该语义。`generate` 当前接受数字token参数，不能假设它支持任意 `@file`。[S14]

### 12.3 构建与自测

在隔离工作树或已有环境的原生隔离机制中实施，先检查干净程度；不强制checkout覆盖用户工作。下列 `AD_ENGINE_DIR` 需由AD00记录为实际实施目录：

```bash
set -euo pipefail
source "$HOME/inkling-lab-v3/env.sh"
: "${AD_ENGINE_DIR:?set to the isolated engine checkout recorded by AD00}"
bash "$PKG/tools/driver_guard.sh" check "$LAB/evidence/driver-baseline.txt"
cd "$AD_ENGINE_DIR"
cargo fmt --all --check
ASTRAL_CUDA_ARCHS=89 NVCC="$NVCC" cargo build --release
cargo test --workspace
"./target/release/astral" selftest
bash "$PKG/tools/driver_guard.sh" check "$LAB/evidence/driver-baseline.txt"
```

这是已有构建/自测形式，不证明新增研究接口已经存在。没有CUDA/GPU时不能宣称构建或selftest通过。实验执行是否经停服窗口，按第3节和最新现场授权决定。

### 12.4 NEW：任务实现后才可运行的统一入口

**以下命令是交给工程AI实现的接口合同，当前快照中不存在这些子命令。**先完成对应任务及测试，CLI `--help` 与schema自检必须验证命令真实存在。

```bash
python3 bench/adaptive_loop/run.py preflight --config CONFIG_JSON
python3 bench/adaptive_loop/run.py fixed-depth --config CONFIG_JSON
python3 bench/adaptive_loop/run.py state-tests --config CONFIG_JSON
python3 bench/adaptive_loop/run.py collect --round 1 --config CONFIG_JSON
python3 bench/adaptive_loop/run.py fit --round 1 --config CONFIG_JSON
python3 bench/adaptive_loop/run.py collect --round 2 --config CONFIG_JSON
python3 bench/adaptive_loop/run.py fit --round 2 --config CONFIG_JSON
python3 bench/adaptive_loop/run.py calibrate --config CONFIG_JSON
python3 bench/adaptive_loop/run.py benchmark-dev --config CONFIG_JSON
python3 bench/adaptive_loop/run.py lock --config CONFIG_JSON
python3 bench/adaptive_loop/run.py evaluate --config CONFIG_JSON
python3 bench/adaptive_loop/run.py report --config CONFIG_JSON
```

`CONFIG_JSON` 是AD00生成的实际绝对路径，运行前替换。`calibrate` 只有AD06前置满足时执行，否则直接记DEFERRED。`lock` 发现身份/数据/门槛缺失即退出；`evaluate` 要求lock存在且完全匹配，不能隐式改配置。

新引擎CLI合同：

```text
astral adaptive-check <model_path> <config_json> <case_manifest_jsonl> <out_dir>
astral adaptive-run   <model_path> <config_json> <requests_jsonl>     <out_dir>
```

`requests_jsonl` 每行至少含 `case_id, input_token_ids, max_new_tokens`；强制计划在配置/manifest中固定。所有输入预tokenize，首轮不新建HTTP服务。开发中的eager、优化graph和native参考由配置显式区分。

### 12.5 重启与续跑

每题开始前登记输入hash，成功后原子写完整结果。中断时仅重跑没有完整结果的题；模型权重、policy、gain、代码、dataset或judge任一hash变化则建立新run，不覆盖旧目录。

已开封的test中断后可用相同二进制和配置继续完成预定样本；不能根据已看到的成绩改变剩余题数、策略、预算或停止规则。续跑不得重新抽题。

### 12.6 NEW：首版配置样例

下列JSON是AD00需要实现和校验的配置格式。`${LAB}`与`${MODELS}`只由白名单环境变量解析，不交给shell eval；相对路径以 `engine_dir` 为根。样例先选择constant3，用于端点检查；训练完成后由fit生成唯一候选配置，最终lock才封口。`null`不会自动变成默认测量值。

```json
{
  "schema_version": "adaptive-loop-v1",
  "engine_reference_commit": "aa837c7e1242cf89f11f7f556a567c14bd065e04",
  "lab_reference_commit": "159edbb0f115a69dedb37866dc94f0f42767bc98",
  "engine_dir": "${LAB}/src/astral-adaptive-20261127",
  "model_path": "${MODELS}/varloop-native",
  "model_file_sha256": "79e60b65c4f2a2a5acdb8e3c7b6994bf00da5477f45d18027afbfad752a64595",
  "dataset_registry": "bench/adaptive_loop/data_registry.json",
  "run_root": "${LAB}/runs/adaptive-loop",
  "capacity": 8192,
  "batch_size": 1,
  "max_new_tokens": 1024,
  "decoding": "greedy",
  "prefill_policy": "native3_prefill",
  "cache_policy": "depth_clamp_v1",
  "allocated_passes": 3,
  "allowed_decode_depths": [2, 3],
  "speculative_decoding": false,
  "trace_enabled": false,
  "policy": {"kind": "constant", "depth": 3, "path": null},
  "gain": {"mode": "identity", "path": null},
  "seed": 20261127,
  "sampling_design": "fixed_benchmark",
  "test_pool_manifest": null,
  "final_test_n": null,
  "quality_margin": 0.01,
  "min_e2e_improvement": 0.10,
  "max_tail_ratio": 1.10,
  "max_extra_vram_mib": 256,
  "min_free_vram_mib": 512,
  "gpu_hour_budget": 48,
  "block_minutes": 60
}
```

序列化取值统一为 `native3_prefill / all_tokens_replay`，分别对应Rust的Native3/AllTokensReplay。`gain.mode`只允许 `identity / decode_only`。其他策略种类为 `forced / random / residual_threshold / linear_value`，各自参数按第6和第10节严格校验。`test_pool_manifest`与`final_test_n`在evaluate之前必填；`sampling_design=fixed_benchmark`允许完成有限集报告，但不能通过总体非劣门。只有经AD00登记的抽样设计才可切到 `iid_population`，不能由成绩触发切换。

## 13. 资源预算与停止规则

这是计划的上限，**不是已经使用或已获准占用生产GPU的时间**。各任务开跑前按真实授权窗口切分；每个可续跑块不超过60分钟。

| 阶段 | 首轮GPU时间上限 | 超限处理 |
|---|---:|---|
| AD01固定深度与pilot | 2小时 | 报实际秒/题，缩小非核心1/4/5对照，不删除主比较 |
| AD03状态/真模型验证 | 4小时 | 最多两轮有证据修正，仍不通过即FAIL |
| AD04—AD05标签与dev | 8小时 | 不足标签/成本过高则BLOCKED或NO_BENEFIT |
| AD06可选校准 | 4小时 | 恢复alpha=1并记录未获收益 |
| AD07性能实现 | 4小时 | 只修已定位开销，不无限融合 |
| AD08封口与压力 | 剩余预算，最多26小时 | 先按功效计算；不够时报告限制 |
| **总计** | **48 GPU小时** | 这是拟议研究预算，执行前写入合同，不自动扩大 |

标签采集预算包含前缀重放，两分支后续生成和judge开销另记CPU时间。分支预算不足不表示硬件只能做到这个效果，只表示本次实验没有取得足够证据。

显存首轮上限：相对native3额外≤256MiB；只保存少量向量和当前状态，不导出每token×每层×全词表logits。小标量决策记录优先；选定诊断位置才保留大张量。临时证据磁盘建议上限20GiB，超过先停止采集并保留manifest，不删除唯一原始证据继续跑。

必须停止的情况：

- 驱动守卫变化、需要root或需要违反现有生产合同：BLOCKED并明确来源。
- 实际路径未命中、输入为空、负控制也通过：测试本身FAIL。
- 只有teacher-forced或错误历史上的收益：不得进入最终结论。
- 质量下降无法由96系数有限校准恢复：停止本缓存策略；不偷偷更换另一种历史算法继续算同一实验。
- 判断器只能靠先算第三遍或当前完整coda/head才能判断：对这一路线NO_BENEFIT，除非成本仍由完整实测证明有收益。
- 两轮后控制器没有超越简单规则：结束学习器分支，保留简单规则结论。
- 固定3本身未通过项目相关回归：先恢复基线，不能让策略研究掩盖基础故障。

## 14. 最终交付与后续判断

### 14.1 执行后的报告必须回答

1. 第三遍在哪些任务/位置修复答案，在哪些位置反而损害答案？证据来自同历史分叉还是固定深度比较？
2. 判断器在真实混合历史上能否识别这些位置？简单规则能达到多少？
3. 补齐KV与四路conv引入多大误差，是否随生成长度持续扩大？
4. 节约多少GPU计算，判断/同步/graph/补齐又花掉多少？
5. 质量门、端到端门、长尾门是否同时满足？统计推断范围是什么？
6. 相对现有A1+DSpark，是否有实际收益，还是仅完成机制验证？
7. 哪些结论是PASS，哪些是FAIL/NO_BENEFIT/BLOCKED？未执行项不能写成“预计通过”。

### 14.2 允许的结论

| 结果 | 应写的结论 | 后续 |
|---|---|---|
| 状态正确、质量与速度共同通过 | 在列明模型/任务分布/上下文范围内，自适应循环成立 | 再考虑2/3/4遍，另冻结数据与预算 |
| 状态正确、质量合格、无净加速 | 判断/同步或可退出比例限制了收益 | 保留机制结论，停止当前工程化 |
| 速度快、质量不合格 | 该近似历史/决策未守住质量 | 不切默认，不包装成无损加速 |
| 学习器不优于简单策略 | 当前特征/标签下未证明学习复杂度的价值 | 采用或保留更简单方案作研究结果 |
| 总体质量仅有有限benchmark成绩 | 只对该题集报告精确差值 | 不宣称总体1pp非劣 |
| 样本、数据或GPU预算不足 | 本次证据不足，具体缺口已知 | 不把BLOCKED误写成模型方向被否定 |

扩展到2/3/4遍前，还必须发现三遍未解决而四遍可稳定修复的独立任务信号。补齐规则需对每个缺失深度各自保留conv历史，成本重新计；不能把两遍复制一次的结论直接外推。额外遍数可能损害任务，多算不保证更正确。

DSpark只在上述机制闭环通过后另立整合任务。现有 `[5,23,41,48]` 是目标特征位置合同，不能凭比例换成二遍/四遍的层号。动态verify还涉及分支状态、接受/拒绝及补齐的回滚，不是打开一个现成开关。[S12]

### 14.3 给执行AI的起始指令

> 先阅读本文件和现场实验室AGENTS/runbook，执行AD00。当前新增算法状态全部NOT_RUN；不要声称文档里的NEW接口已经存在。先锁定真实HEAD、资产、judge、数据和预算，再用原生固定深度建立对照。只实现depth_clamp_v1这一种混合历史规则，先通过独立oracle、负控制和真模型端点，再提取因果特征和训练39参数判断器。条件满足才做96系数校准。GPU串行，原始证据逐项保存，不动驱动、不改变生产授权状态、不自动推送。若前置、语义、成本或统计门不成立，按合同记录BLOCKED/FAIL/NO_BENEFIT并给出可复现原因；不要扩大框架、换量化、降低阈值或用mock冒充实测。

## 15. 来源与审阅范围

本文件的源码/历史记录审阅截至2026-11-27。引用尽量固定到commit；公开官网用于方法和产品边界。代码中的新状态策略、39参数判断器、96系数校准、预算和验收阈值均为**本方案提出的设计**，不冒充任何来源已实现的能力。

- [S1] 引擎最新审阅提交：`aa837c7e1242cf89f11f7f556a567c14bd065e04`。
- [S2] 实验室v3.0.18 README与当前版本。
- [S3] 实验室任务与执行记录，含T15/T17/T18/T20/T22/T16撤回与第二轮。
- [S4] 原数值、数据、负控制、状态和性能合同。
- [S5] T18逐深度原始汇总，限定2040评分位置及对应测速。
- [S6] 官方varloop模型卡，训练深度分布与模型身份。
- [S7] T16第二轮32题×5次性能汇总。
- [S8] RSE作者README，方法与小样本公开结果。
- [S9] RSE FP-Solve入口、求解、计时与加载代码。
- [S10] RSE GSPO评分和门控代码。
- [S11] 当前实验室runbook，含生产保持停止的授权历史说明。
- [S12] 引擎配置、Session、循环、缓存、graph与DSpark前向合同。
- [S13] CUDA短卷积原始输入、KV存储与历史更新代码。
- [S14] 当前CLI命令参数与数值导出行为。
- [S15] CALM原始论文：动态退出与缺失历史问题的方法先例，非Inkling性能证明。
- [S16] TypeSafe官方Jev接口说明，限定其类型化决策能力。
- [S17] GSM8K官方数据入口。
- [S18] LiveCodeBench官方实现与评估入口。
- [S19] 当前探针schema与覆盖边界。
- [S20] A4原生checkpoint加载器；用于确认加载转换不是未经处理的BF16参考。

[S1]: https://github.com/lkyprogramer/inkling-4090-engine/commit/aa837c7e1242cf89f11f7f556a567c14bd065e04
[S2]: https://github.com/lkyprogramer/CodexGame/blob/159edbb0f115a69dedb37866dc94f0f42767bc98/docs/inkling-4090-lab-v3.0/README.md
[S3]: https://github.com/lkyprogramer/CodexGame/blob/159edbb0f115a69dedb37866dc94f0f42767bc98/docs/inkling-4090-lab-v3.0/docs/07_tasks.md
[S4]: https://github.com/lkyprogramer/CodexGame/blob/159edbb0f115a69dedb37866dc94f0f42767bc98/docs/inkling-4090-lab-v3.0/docs/05_validation.md
[S5]: https://github.com/lkyprogramer/CodexGame/blob/159edbb0f115a69dedb37866dc94f0f42767bc98/docs/inkling-4090-lab-v3.0/tools/t18/results/report.txt
[S6]: https://huggingface.co/thinkingmachines/TML-d24-varloop-research/blob/91a57fe2b779bbd12c0f74d1f518cbd5b84e8d0d/README.md
[S7]: https://github.com/lkyprogramer/CodexGame/blob/159edbb0f115a69dedb37866dc94f0f42767bc98/docs/inkling-4090-lab-v3.0/tools/t16/results/round2/t14_report.txt
[S8]: https://github.com/eelbaz/Recursive-Self-Improving-Loopers/blob/765453d13878804c49876a656f39b57a4384dca4/README.md
[S9]: https://github.com/eelbaz/Recursive-Self-Improving-Loopers/blob/765453d13878804c49876a656f39b57a4384dca4/rse_looper/fpsolve.py
[S10]: https://github.com/eelbaz/Recursive-Self-Improving-Loopers/blob/765453d13878804c49876a656f39b57a4384dca4/rse_looper/gspo.py
[S11]: https://github.com/lkyprogramer/CodexGame/blob/159edbb0f115a69dedb37866dc94f0f42767bc98/docs/inkling-4090-lab-v3.0/docs/08_runbooks.md
[S12]: https://github.com/lkyprogramer/inkling-4090-engine/blob/aa837c7e1242cf89f11f7f556a567c14bd065e04/crates/model/src/inkling.rs
[S13]: https://github.com/lkyprogramer/inkling-4090-engine/blob/aa837c7e1242cf89f11f7f556a567c14bd065e04/crates/kernels-src/cu/inkling.cu
[S14]: https://github.com/lkyprogramer/inkling-4090-engine/blob/aa837c7e1242cf89f11f7f556a567c14bd065e04/crates/cli/src/main.rs
[S15]: https://arxiv.org/abs/2207.07061v2
[S16]: https://docs.typesafe.ai/introduction
[S17]: https://github.com/openai/grade-school-math
[S18]: https://github.com/LiveCodeBench/LiveCodeBench
[S19]: https://github.com/lkyprogramer/inkling-4090-engine/blob/aa837c7e1242cf89f11f7f556a567c14bd065e04/docs/trace.md
[S20]: https://github.com/lkyprogramer/inkling-4090-engine/blob/aa837c7e1242cf89f11f7f556a567c14bd065e04/crates/loader/src/inkling_checkpoint.rs

---

## 16. 补充：现场核对、无损路线与执行编排（2026-11-27，实验室 v3.0.19）

> 本节在 fork `aa837c7`、实验室 v3.0.18 的现场上逐条核对第 1–15 节后补充，原文不改。两者冲突时以本节注明的证据为准。本节新增的路线与门同样全部是 `NOT_RUN`；文中的速度都是按已有实测推算的规划值，标为“估算”。

“保留最极致的掌控能力”在本节的含义：所有路线都在自有的 Astral fork 内实现，不依赖外部服务或黑盒；每条新路径都有开关，默认关闭，关闭时与 G2 基线逐位一致；**无损**（输出等于原生 R 遍贪心）与**有损**（改变模型语义）严格分开命名、分开验收。

### 16.1 核对结果

| # | 原文内容 | 核对结论 | 证据 |
|---|---|---|---|
| 1 | §2.1 快照 `aa837c7` / `159edbb` | 属实。之后 T21 在进行中：fork 工作树多了 `ASTRAL_SPEC_LOG` 逐轮日志（未提交，只在 DSpark 路径） | `git log`；07 T21 记录 |
| 2 | §2.3 T18 表 | 与原始汇总一致。**原文漏引的同表数据**：与 R = 3 的 top-1 一致率，A4 R = 1 为 93.24%、R = 2 为 94.71%、R = 4 为 97.65%；A1 R = 1 为 71.13%、R = 2 为 73.58%。这组数决定 16.2 的无损路线是否值得做 | `tools/t18/results/report.txt` |
| 3 | §5.1 slot 布局（第 2 / 3 遍在 24–35 / 36–47，coda 在 18–23） | 属实：`n_slots = n_layer + (passes − 1) · core`，第 p 遍（0 起）用 `n_layer + (p − 1) · core + li` | `inkling.rs` `Config::n_slots`、`forward` |
| 4 | §6.1 第 2 遍结束时 `h1 = bank_out` | 属实：每遍开始时 `bank_out ← cur`（上一遍出口），`cur ← prelude` | `forward` 的 pass 循环 |
| 5 | §6.4 controller 公式与舍入顺序 | 属实，但同一公式有 **4 个 kernel 实现**（decode、8 token 一块、prefill、融合版）。alpha 要在 4 处同时接入，AD06 的工作量按 4 处估 | `inkling.cu` 中 4 处 `(c - tanhf(f) * c) + tanhf(g) * msg` |
| 6 | §12.1 `driver_guard.sh check …` | 现场的入口是 `source env.sh; guard`（退出码 3 表示停止并通知），以现场为准 | `env.sh` |
| 7 | §7.2 P1 用 A1 + DSpark 作项目实用参照 | **缺一个更直接的强基线**：A4 自带 DSpark 草稿 `varloop-native/mtp.safetensors`（SHA256 `905d5486…`，与 A1 / A3 的 `7c3b6513…` 不同），`target_layer_ids [5, 23, 41, 48]` 正好对应 R = 3 的 48 个 visit，Astral `enable_spec` 的 tap 检查应能通过（推断，未运行）。新增 **P2 = A4 + 自带 DSpark** | `models.lock.json`、A4 `config.json` |
| 8 | §2.3 “DSpark 206.3 tok/s” | T21 第 1 阶段（A1）显示 DSpark 的收益强烈依赖负载：相对无草稿，短对话 1.31×、短代码 1.69×、16K 文本 2.05×、16K 代码 2.40×。AD 的端到端结论要按负载桶对照 P1 / P2 报告 | `runs/t21/20261127T101304Z/report.txt` |
| 9 | §9.3 功效：约需 2600 / 4700 / 8100 个独立题 | 可得的真实题量不够：GSM8K 官方 test 1319 题，LiveCodeBench 为数百到一千余题（随版本变化，未逐一核实），合成多跳不进主结论。除非 AD01 实测的不一致率远低于 2%，AD08 大概率记 `BLOCKED insufficient_power`（推断）。无损路线不需要这套统计，只需数值合同 | 原文 §9.3；公开数据规模 |
| 10 | §7.1 代码族用官方 harness | 4090 同时是生产机（Strata 当前停止）。现场没有 bwrap / firejail / nsjail，有 docker，非特权 user namespace 可用（`unshare -Urn` 实测可用）。执行模型生成的代码前先定隔离方案（无网络、只读根或临时目录、CPU / 内存 / 时间上限），经用户确认前代码族记 `BLOCKED` | 现场检查 |
| 11 | §6.5 Jev | 需要把题面发给外部服务，和“完全自控”及隐私约束冲突。维持 `DEFERRED`，不作为任何路线的依赖 | 原文 §6.5 |
| 12 | 与实验室 06 的关系 | AD01 ≈ R1；AD02–AD05 是 R6 第③步“近似历史”的一种实现，并直接做到 token 级；AD06 ≈ R5 的受控干预加训练。R6 要求先做请求级固定深度，AD 的 B2 与 §4 请求级 oracle 满足这一点 | `docs/inkling-4090-lab-v3.0/docs/06_loop_research.md` |

### 16.2 原方案没有用到的结构事实：浅遍是深遍的精确前缀

`forward` 中第 p 遍只读三样东西：同一 token 的 prelude 输出、同一 token 上一遍的 blocks 和出口（消息混合），以及更早 token 在**第 p 遍自己 slot** 里的 KV / conv。第 3 遍的状态从不回流到任何 token 的第 1、2 遍；coda 只读最后一遍。因此：

- 对任意 token，三遍执行中的前 d 遍（d < 3）与“同一前缀只跑 d 遍”的计算和状态完全相同。同一 kernel 路径下逐位相同，不同批形状下只差舍入（推断，依据是代码结构，待 L0 用逐位比较确认）。
- `depth_clamp_v1` 是近似，原因只在于跳过的第 3 遍在该位置缺 KV / conv。如果第 3 遍**事后补算**，而不是拿第 2 遍的值顶替，历史就是精确的。

由此得到一条**无损**路线：**循环深度自推测（LS）**。

- **起草**：只跑 prelude、前 d 遍（d = 1 或 2）、coda 和 head。coda 读已提交的三遍 coda 历史。连续起草 k 个 token。
- **验证**：对 anchor 加 k 个草稿共 k + 1 个 token，批量补算剩下的遍、coda 和 head。
  - v0 直接复用现有 DSpark verify 前向（三遍全算）。
  - v1 复用起草时已经算出的前 d 遍，只补后面的遍。
- **接受**：与 DSpark 相同（贪心前缀加 bonus token）。输出等于原生三遍贪心，数值沿用 T20 的 verify num-3 合同。
- 06 §5 只把 LoopSpec 列为方法参考；在 Inkling 上，这一性质由结构直接给出，不需要训练。

**估算**（A4，短上下文。T18 是 W1 协议，T21 的成本表来自 A1，A4 与 A1 结构相同，误差按 ±15% 看）：

- R = 1 起草每步 3.56 ms，原生 R = 3 为 6.98 ms。
- T21 的 verify(k) ≈ 7.0 + 0.96·k ms；v1 去掉第 1 遍，约为它的 0.75。
- 逐位置接受率用 R = 1 对 R = 3 的 top-1 一致率 0.932 近似。真实起草的 coda 读的是三遍历史，可能更高。

| 方案 | 每轮 | 期望提交 token / 轮 | 估算 tok/s | 相对原生 3 遍 |
|---|---|---|---:|---:|
| LS v0，R = 1 起草，k = 3 | 7.0 + 4.52·k ≈ 20.6 ms | 3.61 | ≈ 175 | ≈ 1.22× |
| LS v1，R = 1 起草，k = 3 | ≈ 7.4 + 10.7 ≈ 18.1 ms | 3.61 | ≈ 200 | ≈ 1.39× |
| LS v1，R = 2 起草，k = 3 | ≈ 4.5 + 15.8 ≈ 20.3 ms | 3.69 | ≈ 182 | ≈ 1.27× |
| 对照：A4 全 2 遍（有损，AD 的速度上限） | — | — | 189.8（T18 实测） | 1.32× |
| 对照：A1 + DSpark（T14 / T21 实测） | — | — | 206–222 | 1.44–1.56× |

由估算得出三点推论：

1. A4 上 LS v1 的无损收益与“全 2 遍”的有损上限同量级。**如果 L0 证实这一点，逐 token 2 / 3 遍动态深度在 decode 速度上就没有超过无损方案的空间**，AD 的价值只剩机制研究，或叠加在无损方案之上。由此新增门 AD-G0（16.4）。
2. LS 不需要额外的草稿模型，只用目标模型自己的 cache。DSpark 的草稿 KV 在 73728 token 后放不下，LS 在这个区间仍可用；它也可以和 DSpark 叠加（叠加形式在 L0 之后设计）。
3. A1 的 top-1 一致率只有 71–74%，估算 LS v1 约 160 tok/s，低于 A1 + DSpark。A1 只做一次信号测量，然后结案。

### 16.3 各循环模型的探索地图

| 模型 | 定位 | 极致方向（按优先级） | 对应任务 |
|---|---|---|---|
| **A1**（UD-Q4_K_XL，固定 3 遍，生产） | 无损速度的主战场 | ① 现有主线 T21 → T27 → T26 → T25 → T28，不变；② 循环结构服务速度：R3 跨遍专家局部性，为 T26 / T28 的 L2 驻留提供依据；③ 机制研究 R2 / R4 / R5 / R11 / R12 按原计划；④ LS 只在 L0 测一次接受率；⑤ 深度削减只作负对照（R = 2 时 PPL 6.38） | 07 现有行；L0 |
| **A3**（原生 checkpoint） | A1 的同一模型 | 提供 DSpark 草稿与原生参照，不单独开循环研究 | — |
| **A4**（varloop，1–5 遍训练） | 循环机制与深度的研究主体 | ① **无损提速**：LS（R = 1 / 2 起草）与 A4 自带 DSpark，二者择优或叠加；② **运行期请求级深度**：在三遍分配内按请求选 1–5 遍、不重载。整请求固定 d 遍就是精确的 d 遍模型，这是 AD-B2 与 R1 的工程前提，也给服务端“质量 / 速度档位”；③ **有损自适应深度**：AD00–AD09，加 AD-G0 门；④ **更深是否更好**：R1 / AD01 若显示 R = 4 / 5 在任务上有净修复，用 LS 同一机制做“3 遍起草、4 / 5 遍验证”，输出精确等于 R = 4 / 5，速度接近 3 遍；⑤ **训练级**：AD06 的 96 个系数、R12 / R13，放最后 | T32–T36（07） |
| **A5**（DFlash2 草稿） | A1 的另一种草稿 | R7，T21 之后按原计划 | R7 |

### 16.4 顺序与门

不打断现有主线。GPU 串行，主线优先；CPU 准备工作现在就可以和主线并行。

**阶段 0：准备（只用 CPU，与主线并行）**

- **L-P1**：AD00 的 CPU 部分。包括 schema；数据登记（GSM8K 锁定官方 revision）；多跳生成器；`paired_noninferiority_lower` 及 §9.3 列出的边界用例。
- **L-P2**：AD02 的 NumPy 状态 oracle 与负控制，同时加一条 LS 断言：浅遍状态与全深度执行逐位相同（小模型上）。
- **L-P3**：LS 与请求级深度切换的状态合同。内容包括：每个草稿 token 需要保留的 conv 历史与回滚表（复用 DSpark 的 `hist` 机制）；coda / 后续遍的 KV 覆写顺序；按深度预捕获的 graph。
- **L-P4**：代码判分的隔离方案，给出命令和影响，等用户确认。

**阶段 1：L0 信号测量（约 1 GPU 小时；排在主线 T28 之后，主线出现等待窗口时也可以提前插入）**

- (a) A4 + 自带 DSpark，按 T14 / T21 的协议测基线（现有代码，只需加载）。
- (b) LS 接受率：eager 诊断模式，在真实混合历史下（coda 读三遍历史），测 R = 1 / 2 起草与 R = 3 的逐位一致率，A4 与 A1 各一组。同时逐位确认 16.2 的前缀性质。
- (c) AD01 pilot（64 组，A4 R = 2 / 3，少量 1 / 4 / 5）：任务差异、请求级 oracle、不一致率（据此重算 AD08 的功效）。

**L0 之后的门**

| 门 | 条件 | 不满足时 |
|---|---|---|
| LS 继续 | 按 T21 成本模型和 L0 实测接受率，LS v1 预测 ≥ A4 DSpark × 1.05；或叠加预测 ≥ +5%；或在 DSpark 放不下的长上下文区间 ≥ 1.2× | LS 记 `NO_BENEFIT`，保留接受率数据 |
| **AD-G0（新增）** | B1（全 2 遍）实测速度 ≥ 最好无损方案 × 1.10，或 AD 叠加在最好无损方案之上仍有 ≥ 10% 的预测空间 | AD 降为机制研究：只做 AD01–AD05 的信号部分，不做 AD07 的性能工程，不跑 AD08 的速度门 |
| 更深方向 | AD01 中 R = 4 / 5 相对 R = 3 有可复现的修复题（W > L，且集中在可识别的任务族） | 记否定结论，不实现 |
| AD08 | 用 AD01 的不一致率重算功效后，可得题量满足 | 按原文记 `BLOCKED insufficient_power`，只报告有限题集的精确差值 |

**阶段 2：实现（按门的结果）**

依次做：请求级深度切换（小改动）→ LS v0（复用 DSpark verify）→ LS v1（复用浅遍）。每一步都过完整 G2（含 T20：这是 T16 第 1 轮的教训），再跑 T14。

**阶段 3–4**

AD02–AD07（AD-G0 通过才做）→ AD08 → 更深验证（R = 4 / 5）→ AD06 → R12 / R13。

实验室任务编号（v3.0.19）：L0 = T32，请求级深度 = T33，LS = T34，AD00–AD09 = T35，更深验证 = T36；LS 的研究问题登记为 06 的 R14。

### 16.5 预算与约束补充

- L0 约 1 GPU 小时；LS 的实现与验证估计 6–8 GPU 小时；AD 原有的 48 GPU 小时预算不变，但以 AD-G0 为前置。
- 新路径默认关闭；进入默认前要过完整 G2，A4 的路径用 A4 自己的原生参照。
- 数据只下载小体量的官方数据集。LiveCodeBench 下载前先评估体积，超过 30 GiB 先问；执行模型生成的代码以 16.1 第 10 条为准。
- 不引入外部服务；不改量化格式；不动驱动；Strata 的停启只按用户的最新指示。

