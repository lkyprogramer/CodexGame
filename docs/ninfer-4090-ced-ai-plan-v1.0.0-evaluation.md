# NInfer-4090 CED / Late-State Prefill 计划（v1.0.0）实机评估报告

评估对象：`docs/ninfer-4090-ced-ai-plan-v1.0.0/`（9 Phase / 53 Task，2026-09-11）。
评估基准：4090 主机 `hhtele@192.168.10.29` 实测、`/home/hhtele/ninfer-4090`（PINNED_COMMIT `44a2c6c`）源码、`output/qwen38-27b-4090-ninfer/reports` 既有报告、`docs/qwen38-4090-ninfer-extreme-v2.0.0`（以下称 extreme v2）。
评估日期：2026-09-11。本报告只读，未改动生产、未编译、未训练。

---

## 0. 结论

**技术上可行，但对本机真实 Agent 工作负载的期望收益太低、质量风险太高、工期太长；不建议现在启动 53 任务全程。建议把它降为一个"先计量、再做 3–4 周可学习性 kill test、通过后才谈 runtime"的条件分支，主线仍是 extreme v2。**

支撑结论的五个数字（§2–§6 有推导与证据等级）：

| 项 | 数值 | 性质 |
|---|---:|---|
| CED-16 对**冷 ≥32K 前缀**的 prefill 加速上界 | ≈1.30×（184K：94 s → ≈72–78 s） | 由维护者 nsys 归因 + 本机 1974 t/s 推导 |
| 它能触达的流量 | 仅 `uncached ≥ 32768` 的冷请求；本机实测 Pi 会话前缀命中 85%、append TTFT 3.5 s，该会话内触发次数 = 0 | 报告 10/11 实测 |
| 最接近的已发表先例（Apple KV Prediction，砍 25% 层 + 全量微调辅助模型 + 64×H100 训练） | TriviaQA 生成准确率保留 **0.78**，换 1.21× TTFT | 文献实测 |
| CED-16 到 P6 裁决的工期 | 4.5–6.5 个月串行；生产停机累计 35–50 h | 估算 |
| CED-16 通过 P6 质量门（Java −2 pp、36 个 64–200K 检索题）的主观概率 | ≤25% | 判断 |

同时要说清楚：计划包本身写得**准确**——对 44a 源码的结构描述全部核对通过（§2），自带工具 24 项测试与 SHA 全过，安全姿态正确。问题不在文档质量，在方向的期望值。

---

## 1. 方案是什么

- **不是** DeepSeek-V4.1-Flash 的原生 CED（20 层因果编码器 + 20 层解码器，解码器全局 KV 由编码器最终 hidden 投影，训练时就是这么设计的）。
- **是** 对冻结的 Qwen3.8-27B 做 *Late-State Prefill*：冷前缀 `[0,p)` 只跑前 `s` 层（48/40/32），用一个 rank-256 的逐 token 小 Predictor 从 `h_split` 预测后 `64−s` 层的 attention K/V 投影、GDN pre-conv QKV、g/β、final hidden；再用**真实**的 K-norm/RoPE/codec、真实 width-4 卷积、StateOnly GDN 递推把这些写成状态；最后 `[p,n)`（默认 2048 token 尾部）跑完整 64 层。解码不改，但读的是近似状态。
- 默认关闭、只对 `cache off + cold + uncached ≥ 32K + n ≤ 200000` 触发；MTP 单列 Phase（P5），需要额外预测 final hidden。

---

## 2. 实机核对：计划声明 vs 已验证

| 计划声明 | 核对方式 | 结果 |
|---|---|---|
| 64 层，`(i+1)%4==0` 为 full attention（16/48）；attn 24Q/4KV/d256，rotary 64；GDN Q/K 16×128、V 48×128、pre-conv `[10240,T]`、conv width 4；MTP 1 层 | `docs/maintainer/qwen3.8-27b-model.md` | **一致** |
| `run_layers(x, ph, tap)` 为 0..64 简单循环，`Tap::capture_layer(layer, x)` 在每层 MLP 后取 residual | `text_context_impl.h:1067-1121`、`text_context.h:131/157` | **一致**；`run_layers_range` 是平凡改动，`h_split` = 第 47 层 capture |
| prefill 中 pre-conv QKV 是独立张量，可 tap | `text_context_impl.h:990-994`：`gdn_input_projection(...) → qkv`，再 `causal_conv1d_silu(qkv, conv1d, conv_state, ...)` | **一致**，Teacher 导出无需重算 |
| MTP prefix 准备消费 final norm 之后的 hidden | `text_context_impl.h:1273 rmsnorm → xf`，`:1347/1367 mtp_prefill_chunk(ids, xf, …)` | **一致**，P5 的 final-hidden head 确有必要 |
| ReplaySSM 域 T=2..16，不能扩到 100K | `gated_delta_net.h:89-90` | **一致** |
| 需要新的 StateOnly 大 T 路径 | `gdn_replay.h:21-37` 已有"只推进 state/conv、不读 q、不产出"的 `gdn_replay_fold`，但域 ≤ record_capacity | **部分正确**：短 T 先例已存在；大 T 的必要性见 §7 第 4 条（可不写新 kernel） |
| conv history BF16 `[C,3]` oldest→newest | `causal_conv1d_silu.h:10-29` | **一致** |
| 每 token 标签 287,232 B；100K 标签 26.75 GiB；状态轨迹 144 MiB/token | 手算 + `tools/budget.py` | **一致** |
| Predictor rank256 ≈ 36.6M 参数、69.8 MiB BF16 | `tools/budget.py --split 48 --rank 256` | **一致** |
| 空载显存 22594 / 余量 1970 MiB | `nvidia-smi` 今日：used 22600，**free 1511** MiB（驱动保留约 460） | **偏乐观**；按计划自己的规则"新增 ≤1024 + 余量 ≥512 = 1536" 在 262144 下**差 25 MiB 不满足** |
| RAM 62.5 GiB / SSD 600 GB | `free -g` 62 GiB；`df` 915 GB 盘、**557 GB 可用** | 数字过时但结论不变（够用） |
| 训练用 PyTorch 独立环境 | 主机系统 python3 与 anaconda3 base 均无 torch；有 conda envs | 需新建环境，无阻塞 |
| 生产 unit / 端口 / 镜像 / 制品 SHA | 与 extreme v2 `docs/22` 一致 | **一致** |
| 包内工具"现在即可运行" | `validate_package.py` PASS（9 phases/53 tasks）、`unittest` 24 OK、`SHA256SUMS` 0 失败 | **一致** |

未核对：P1–P3、P5–P8 phase 文档逐条断言；`session_snapshot_impl.h`/`continuation_image.h` 的 framing 版本字段是否足以承载 provenance（P5-T03 风险，估计中等）。

---

## 3. 性能：上界与现实值

### 3.1 时间构成（本机口径）

维护者在 4090 上对 118K prompt（rk4v4-e8）的 nsys 归因（`docs/maintainer/prefill-throughput-plan.md §2.5`）：dense GEMM 68.0%，GQA prefill attention 27.8%，GDN core 1.6%，conv 0.3%，其余 ≈2.3%。按其 context 阶梯做线性拟合：`t(n) ≈ 302 µs + 1.22 µs·(n/1K)`；代入 184K 得 526 µs/token，与本机实测 **1974 t/s = 506 µs/token**（报告 11）吻合。

由此 184K 冷 prefill 每 token ≈ **300 µs GEMM+固定 / 206 µs attention**（59% / 41%，推导值）。

### 3.2 CED-16 节省与新增

| 项 | 每 token | 依据 |
|---|---:|---|
| 省：跳过 `[48,64)` 的 GEMM/MLP | −75 µs | 25% × 300 |
| 省：跳过 4 个 attention 层 | −52 µs | 25% × 206 |
| 加：Predictor（36.6M MAC/token，BF16 小 N GEMM） | +1.5–2.5 µs | 40–50 TFLOPS 有效 |
| 加：12 层真实 conv + StateOnly | +2.4 µs | 保留的 25% × (1.6%+0.3%) |
| 加：4 层 K-norm/RoPE/codec append、`h_split` 搬运、两段式 chunk 调度 | +3–5 µs | 估算 |
| **净** | **≈ −118 µs → 388 µs/token** | |

- **上界**：prefix 部分 1.30×；含 2048 尾部整请求 ≈1.30×（184K）。
- **现实值**（工程损耗、小 GEMM 效率、fallback 计入）：**1.20–1.28×**。计划的 1.10× 门与 1.15× stretch 都在可达范围内——**性能不是这个方案的瓶颈，质量才是。**
- 绝对值：184K TTFT 94 s → ≈72–78 s（−16～−22 s）；64K ≈25–30 s → 省 5–7 s；32K（触发下限）省 ≈2–3 s。
- CED-24 上界 ≈1.55×，CED-32 ≈1.9×（计划自己也否定"必然 2×"，正确）。

### 3.3 它不加速什么

- warm append（本机 3.5 s）、exact hit（0.5 s）、任何 `uncached < 32768` 的请求——**完全不触发**。
- decode——不变；若 P5 的 MTP final-hidden 预测降低接受率，decode 反而变慢（计划 R3 已列）。
- 尾部 2048 token 与 early 48 层里 12 个 attention 层的 n² 注意力——照常全付。

---

## 4. 工作负载适用面（决定期望值的关键）

已观察事实：
- 报告 10/11：真实 Pi 三题会话，prefix 命中 154,961 token vs 实算 26,845（**85% 命中**）；exact TTFT 0.5 s，append TTFT 3.5 s。会话内**没有一次** `uncached ≥ 32768` 的请求，CED-16 触发次数为 0。
- 报告 12：用户消息改写走 `restore_user_turn_anchor`，TTFT 0.9 s；只有旁路 rewind 时 `full_reset`（~21 s）。
- 生产容器**没有** `--request-log-jsonl`、没有 logs 挂载（`docker inspect ninfer-4090-prod`）——冷/热分布目前**无法回溯统计**。`/home/hhtele/ninfer-4090/logs/ninfer-request.jsonl` 里只有 09-09 23:19 测试容器的 20 行。

推断：CED-16 的收益只落在"新会话灌入 ≥32K 冷仓库 / system prompt 改写导致 full_reset / 重启后无 L3"三类事件；每次省 2–22 s。若每天 ≤5 次，日节省 ≤2 分钟；对比 Java 题 24–38 s 的墙钟由 decode 与工具循环主导（报告 11）。**计划 R6 自己承认这一点，P0-T05 的失败条件"主要耗时不在未缓存 prefill → NO-GO"用现有证据已经可以先答一半。**

---

## 5. 质量风险（主要否决理由）

### 5.1 最接近的先例

Apple *KV Prediction for Improved Time to First Token*（arXiv 2410.08391）：用辅助模型预测冻结基座的 KV cache，基座只在 decode 时跑全层——与本方案同构。其 **KVP-LP-0.75**（砍掉 25% 层的辅助模型 + 线性预测器；辅助模型剩余层**全量微调**；RefinedWeb+ArXiv+Wiki，70k step × 64 H100，约 2.3B token）：

| 指标 | 基座 | KVP-LP-0.75 | 保留率 |
|---|---:|---:|---:|
| TriviaQA 1-shot（生成） | 23.57 | 20.73 | **0.78** |
| 7 项 MCQA 平均 | 63.43 | 62.21 | −1.2 pp |
| TTFT 实测缩减 | 1.00 | 1.21× | |

KVP-LP-0.50（砍 50%）：TriviaQA 保留 0.66，MCQA −2.7 pp。论文还观察到 value 误差随深度**累积**。

本计划的训练条件弱得多：基座完全冻结、Predictor 是 36.6M 的逐 token MLP（允许 ≤3 token 因果上下文）、标签上限 262K（+262K）token、单卡分时训练。可合理预期其生成任务保留率**不高于** 0.78。

### 5.2 本方案独有的、无先例的风险

- 被跳过的 16 层里 **12 层是 GDN**：预测的 k/v/g/β 经 12 层 StateOnly 递推、自由运行 18 万 token，state 误差跨层跨长度累积；文献里没有对 DeltaNet/GDN 递推状态做学习式近似的结果。计划 R2 提到了，但没有先例说明可控。
- Java Agent 任务是多步、精确标识符、工具循环——错误会跨轮放大；36 个 64–200K 检索题直接考被近似的长程记忆（尾部 2048 精确对它们没有帮助）。
- 计划 P3 的自由运行 state 门 `p95 NRMSE ≤ 0.5`、`64K/32K 误差比 ≤ 2.0` 相当宽松：50% 的状态误差可以过 P3 却过不了 P4。
- P6 用 24 题 × 3 seed 判 −2 pp，计划自己算过：零 harm 要 ≈150 个独立任务才能把 95% 上界压到 2%——结论最多是 `private_opt_in_only`。

### 5.3 对方向的判断

在"冻结基座 + 小预测器 + 小数据"条件下，让近似长程状态在 200K 检索与多步编码任务上做到"观察不到下降"，与已有证据相悖；更可能的结局是 P4 的 24 项 smoke 或 KL 门 FAIL。我给 CED-16 通过 P6 的主观概率 ≤25%，CED-24/32 明显更低。

---

## 6. 资源与运维

| 项 | 计划要求 | 本机 | 判定 |
|---|---|---|---|
| 显存新增 | ≤1024 MiB 峰值 + ≥512 余量 | 262144 下 free 1511 MiB；200192 下 ≈3108 MiB | 262144 按计划规则不满足（差 25 MiB）；**200192（用户已决定）下满足**。CED-16 实际新增估算 150–300 MiB（Predictor 70 + 流式激活 + 复用 GDN workspace），与 extreme v2 的 DFlash2（+1734 MiB）在 200192 下**可并存但余量只剩 ≈0.9 GiB**；与 rk8@200192 不能三者同存 |
| 磁盘 | 128 GiB 数据 + 16 GiB + 保留 ≥64 GiB | 557 GB 可用 | 满足 |
| 训练环境 | PyTorch 独立环境 | 无 torch，需新建 conda env | 无阻塞 |
| 构建 | CUDA 13.2 容器、BUILD_TESTING=ON | 容器已存在（extreme v2 docs/22） | 满足 |
| 权限 | guard 需 `systemctl stop/start` | sudoers 已免密（extreme v2 docs/22 §1.2） | 满足；计划的 P0-T02 guard 可直接复用 `tools/remote_guard.py` |
| 生产停机（估算） | — | P0 2–3 h；P1 2–4 h；P2 1–2 h；P3 Teacher 导出 ≈4 h（256 个 1024-token 窗口、平均 60K 前缀）；P4 每轮 ≈3 h × 2–3 轮；P5 3–5 h；P6 每轮 ≈6 h × 2 轮；P8 1–2 h | **CED-16 全程 ≈35–50 h**；P7 再 +15–25 h |
| 遥测 | P0-T05 需冷/热分布 | 生产无请求日志 | **必须先开 `--request-log-jsonl`**（改 unit + 重启一次） |

---

## 7. 工作量与难点

### 7.1 按 Phase 估算（一人 + AI 结对，串行，人·周）

| Phase | 内容 | 估算 | 备注 |
|---|---|---:|---|
| P0 | 冻结基线、guard、runner、fixture 清单、瓶颈测量 | 1.5–2 | 与 extreme v2 T00/T01 大量重叠，可复用 |
| P1 | `run_layers_range`、Teacher tap、导出/注入、off 回归 | 2–3 | 注入需要把 KV codec 编码、conv history、FP32 state、frontier 一起搬对 |
| P2 | StateOnly、conv/KV 构造器、流式 workspace | 1.5–3 | 见 7.2 第 4 条：v1 可不写新 kernel，降到 1–1.5 |
| P3 | 数据 manifest、C++ 流式导出、PyTorch 训练、state-anchor 损失、`.ninfer` 打包 + binder | 3–4 | 打包/绑定要进 27B 私有 binder 与 artifact 校验链 |
| P4 | admission/CLI、两段式流式执行、tail/事务回退、no-spec 质量与 KL、性能 | 3–4 | 运行时最重的一段 |
| P5 | final-hidden head + MTP prefix 准备、provenance 进 lane/checkpoint/image/alias、L1/L2 测试、取消与故障矩阵 | 3–4 | 要升 image framing 版本、新 namespace |
| P6 | 12×3 长上下文题、24 个 Java fixture（broken/reference/judge 三角）、Pi 循环、统计 | 3–4 | fixture 编写本身 ≈2 周 |
| P8 | 封装、回退演练、报告 | 1–1.5 | |
| **CED-16 合计** | | **18–26 周 ≈ 4.5–6.5 个月** | |
| P7（可选） | CED-24/32 各自独立数据、训练、接入、验收 | +6–10 | |

对照：extreme v2 全包估算 4–7 个月。两者**不可能并行**（同一块 GPU、同一个人、同一批维护窗口）。

### 7.2 难点（按对结果的影响排序）

1. **可学习性本身**（P3→P4）：逐 token MLP 从第 48 层 residual 预测第 51/55/59/63 层的 K/V 与 12 层 GDN 输入，且要经 StateOnly 自由运行到 200K。这是全计划的存亡点，也是唯一无法靠工程解决的点。
2. **Teacher 数据只能从 NInfer 内部取**：没有 HF/PyTorch 路径能给出 INT8 prefill profile 下的"真值"（计划 R7 正确地禁止换精度）。所以导出工具必须是 C++ tap（pre-conv QKV 在 prefill 已是独立张量，K/V 投影需在 norm/RoPE 之前加 tap）；每个标签窗口要真的 prefill 到对应位置，导出成本 = 停机时间。
3. **两段式 prefill 的状态不变量**：`[0,p)` 早期层推进、晚层由预测写入、`[p,n)` 全层——chunk 边界、frontier、page 归属、conv 三列历史、MTP `t/t+1` 对齐、事务回退，任何一个错都表现为"能跑但输出微妙变差"，只能靠 P1 的 Teacher 注入 oracle 兜底。
4. **StateOnly 大 T kernel 其实不必写**：GDN core 只占 prefill 1.6%，被跳过的 12 层份额 ≈0.4%。v1 直接调用现有 `gated_delta_net`（喂预测 k/v/g/β 与任意 q，丢弃输出）即可，`gated_delta_net_state_only` 只做接口包装；这能砍掉 P2-T02 的 sm_89 kernel 与其数值门 1–2 周。
5. **provenance 全链路**：approximate 标记要进 resident lane、turn checkpoint、L1/L2 image、stable/session alias，且旧版本安全 miss；这是 P5 里最容易留后门的地方（近似状态被当 native 复用）。
6. **MTP 叠加近似**（P5）：MTP prefix KV 依赖逐 token final hidden，再加一层预测；接受率下降会直接吃掉 decode（本机 MTP 贡献 3.5×）。
7. **统计功效**：24 题 × 3 seed 证明不了 −2 pp；36 个检索题在 200K 深度 95% 的位置对近似记忆最敏感。
8. **工程环境**：要在 CUDA 13.2 容器内以 `BUILD_TESTING=ON` 构建带 tap 的实验二进制，另建 PyTorch 环境；不难，但都是 P0 前置。

---

## 8. 与 extreme v2 的关系

| 维度 | 关系 |
|---|---|
| 目标 | extreme v2 主攻 decode（Suffix/MTP、DFlash2、W16）+ 精确 prefill 加速（T13 d256）；CED 只攻冷长前缀 TTFT。目标正交，可叠乘，但不是同一批人同时做 |
| GPU/工期 | 完全互斥：同一张卡、同一批 sudo 维护窗口、同一个执行者 |
| 显存 | 200192 下 CED-16（实际 ≈150–300 MiB）可与 DFlash2 并存但余量 ≈0.9 GiB；与 rk8@200192 三者不能同存 |
| 可复用 | T00 preflight/memory-ledger、T01 `remote_guard`、fixture 与统计协议（应统一为 ≥8 配对 + A/A 噪声底，CED 计划的"5 次 + bootstrap 10000"要改）、Java fixture 语料（CED 24 题 vs extreme 3 题，应合并为一个语料库） |
| 容量口径 | CED 计划坚持"262144 是必须保留的 native 能力"；用户 2026-09-09 已决定候选 profile 为 200192，CED 的 `qualified_context=200000` 与之相容，但文档措辞要对齐，避免执行 AI 再回到 262144 |
| TTFT 的替代路径（精确、零质量风险） | extreme v2 **T13**（d256 attention kernel，attention 在 184K 占 ≈41%，1.6× → 整体 ≈1.2×，且对 warm append 也有效）；维护者自己的下一杠杆 INT8 `attn_input_proj`（当前 51.9% 效率）；`--auto-long-anchors` 设计移植（报告 07 评为"最值得"，改写 TTFT 16.6 s → 0.6 s）；L3 磁盘缓存解决重启冷启动。这四项合起来覆盖的真实 TTFT 场景比 CED-16 多，且不需要训练 |

---

## 9. 计划包若要执行必须先修的地方

1. **容量口径**：`docs/01/07`、`configs/experiment.json` 的 262144 保留声明改为"生产 262144 不动；候选 profile 200192（用户决定）；CED 资格化到 200000"。
2. **显存事实**：free 1511 MiB（非 1970）；按计划自己的 1024+512 规则，CED 只能在 200192 候选上做。
3. **P0-T05 前置**：生产先加 `--request-log-jsonl` 采集 ≥2 周，统计 `uncached ≥ 32768` 事件数与累计秒数；没有这个数字，P0-T05 的 NO-GO 条件无法判定，也没有理由投入 P1+。
4. **Phase 顺序**：把"可学习性 kill test"提到 runtime 工作之前——只做 P1-T02（tap）+ P3-T01/T02（32K–64K 标签导出）+ P3-T03/T04（训练与自由运行 state 验证）+ 离线指标；P1 注入、P2、P4 全部延后。目标是 3–4 周、≤6 h 停机内拿到杀/不杀信号。
5. **P3 门收紧**：自由运行 state `p95 NRMSE ≤ 0.2`（非 0.5）、32K→64K 误差比 ≤1.5（非 2.0）、attention K 经 norm+RoPE 后中位余弦 ≥0.98；并加一个离线可算的"注意力分数扰动"指标（用 Teacher q 对预测 K 与真实 K 的 softmax 分布做 KL）。
6. **P2-T02 降级**：v1 复用现有 `gated_delta_net`，`state_only` 只做接口；新 kernel 列为 P7 之后的可选优化。
7. **统计协议统一**：改为 ≥8 配对 ABBA 跨两次启动 + A/A 噪声底 ≤3%（与 extreme v2 `tools/metrics.py` 一致），保留 bootstrap 作辅助。
8. **guard/fixture 复用**：P0-T02 直接用 extreme v2 `tools/remote_guard.py`（18041 候选端口、`qwen38.lab.run` label）；Java fixture 与 extreme v2 合并语料。
9. **训练环境锁定**：写明在主机新建 conda env（当前无 torch），固定 wheel 版本；导出/训练分时规则已在 `docs/04 §4`，保留。

---

## 10. 建议路线

```
现在（零风险、都该做）
 ├─ 生产开 --request-log-jsonl，采 2 周：统计 uncached≥32K 事件/天、累计秒/天
 ├─ extreme v2 继续：T00→T01→T02→T07；TTFT 走 T13 d256 + attn_input_proj INT8 + auto-long-anchors 移植
 └─ CED 包按 §9 修文档，状态 DEFERRED

2 周后看流量
 ├─ 冷≥32K 累计 < 5 min/天  → CED NO-GO（局部收益），归档
 └─ ≥ 5 min/天（或 ≥5 次/天 ≥64K）→ 启动 3–4 周 kill test（§9 第 4 条），≤6 h 停机

kill test 结果
 ├─ K 余弦/state NRMSE/注意力扰动 KL 任一不达 §9 第 5 条 → NO-GO，保留证据
 └─ 全部达标 → 才进入 P1 注入 → P2 → P4（先 no-spec），并在 extreme v2 的 GPU 窗口排期中单独占位
```

不建议的做法：现在就按 53 任务顺序从 P0 开工；或在没有流量数据的情况下先写 runtime 再训练。

---

## 11. 证据等级与未验证事项

**已观察**：源码结构（§2 全部核对项）、本机显存/磁盘/内存/torch 缺失、生产容器无请求日志、包内工具与 SHA、维护者 nsys 归因数字、本机 184K TTFT 94 s / 1974 t/s、Pi 会话 85% 命中、KV Prediction 论文表格。

**基于证据的推断**：184K 时 GEMM/attention 59%/41% 的拆分（线性拟合，误差约 ±5 pp）；CED-16 1.30× 上界与 1.20–1.28× 现实值；CED-16 实际新增显存 150–300 MiB。

**估算/判断**：工期、停机小时、各 Phase 通过概率、日节省分钟数。

**未验证**：P1–P3、P5–P8 phase 文档逐条；continuation image framing 能否无痛承载 provenance；主机是否能直接拉 PyTorch wheel；CED 与 DFlash2 并存时的真实峰值显存；本机真实的冷 ≥32K 事件频率（需要先开日志）。
