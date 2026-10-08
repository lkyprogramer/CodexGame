# Qwen3.8-27B on RTX 4090：极致推理优化的物理上限与路线图

日期：2026-09-09  
范围：单卡 RTX 4090（192.168.10.29）、Qwen3.8-27B、单并发 agent 负载（Pi / OpenClaw：thinking=medium、tool loop、rewrite、60k–184k 上下文）。  
姊妹文档：`docs/kern-sm89-4090-evaluation-and-poc-review.md`（kern 路线评估与 POC 核实，本文不重复其内容）。

标注约定：**[实测]** 本机 / 本仓库报告中的测量；**[fork 文档]** 4090 fork `docs/maintainer/*` 中作者自己的测量；**[公开]** 外部可核对来源；**[推断]** 由公开规格 + 实测反推，未直接测量。

---

## 0. 结论

1. **"极致"在这张卡上不是一个数，而是三个独立的天花板**，杠杆互不相同：

| 维度 | 现网 **[实测]** | 物理上限（roofline）**[推断]** | 工程可达目标（本文路线）**[推断]** | 主杠杆 |
|---|---|---|---|---|
| 短上下文 decode（4k，agent 采样） | 127 tok/s（≈2.5 tok/step；code greedy 上游 148.6 ≈3.0） | 每 step ≈16 GB 必读 → ≤62 step/s；tok/s = step/s × 每步接受 token 数（AL） | agent 混合流量 **AL 3.5–4.5 → 175–225 tok/s**；纯代码 AL ~4.4 → ~220；复制/改写型输出 AL 8–15 → 350–500+ | 投机解码（DFlash2 block 8–16 + suffix/lookup 混合） |
| 长上下文 decode（184k） | 87–98 tok/s | 每 step ≈21 GB → ≤48 step/s | **AL 3.5–4.5 + attention kernel 重写 → 140–180 tok/s** | 投机解码 + 多行验证的 E8 decode attention kernel |
| 冷 prefill（184k TTFT） | 94 s（1974 tok/s） | INT8 tensor core 660 TOPS → 理论 24 s，但 W4A8 指令混合使 GEMM 只能到 INT8 上限的 ~34%（fork 已实测） | **Sage 类 INT8/FP8 attention → 65–75 s；再加 Ada 专属 W4A4 IMMA GEMM（质量门禁通过才算）→ 45–55 s** | prefill attention 重写（当前 41% 上限）+ 换 MMA 指令 |

2. **decode 的 step 时间已经接近带宽墙**（短上下文 ≈20 ms/step vs 带宽下限 ≈16 ms，约 80%；184k ≈31 ms vs ≈21 ms，约 68%）。这意味着：
   - 任何"把 kernel 写得更快"的 decode 工作（融合、megakernel、更好的 GEMV）**上限 1.25×，现实 1.1×**；
   - **唯一能翻倍的杠杆是"每步接受更多 token"**：MTP3 的 AL≈2.9–3.0（现网采样 medium ≈2.5），DFlash2 block 8 在公开基准 AL 4.1–5.5，Lucebox 在**本机**用 block 16 在短代码上做到 avg_commit 8.9–14.0、decode 230–341 tok/s（greedy）**[实测]**。但要诚实：**同一块宽下 DFlash2 对 MTP 的 AL 增益只有 +5–12%**（z-lab 表；kernel-sanders 在其 4090 上 3.14–3.34 vs 2.9–3.0），倍增来自 (i) 块宽 8→16 在可预测输出上的外推，(ii) 复制/改写场景用 prompt 直接填草稿（kernel-sanders：16 宽 + lookup 复现上下文 381 tok/s、15 tok/step）。agent 混合流量的真实 AL 必须先量（§6 P0）。
   - 因此"哪怕写 kernel"的正确落点不是 GEMV，而是：**(a) 让宽验证（8–16 行）在 184k 上下文下不涨 step 时间的 decode attention kernel；(b) prefill attention 从 41% 上限往 70–80% 推。** 这两处确有 kernel 级空间，其余地方没有。

3. **基座选择：继续深挖 NInfer 4090 fork，不换引擎、不上 kern。** 理由是排他性的：它是唯一同时满足 (i) dense GEMM / attention 已在 BF16 roofline 附近（作者 nsys+bench 双向核对）、(ii) 已有 INT8 prefill 路由与 E8 KV、(iii) 已有 DFlash 运行时骨架（`dflash_context_impl.h`，35B-A3B 在用，27B 只是被配置关掉）、(iv) 现网依赖的 serving 语义（prefix restore、rolling-tool、turn checkpoint、`preserve-thinking`）的代码库。其他引擎（Lucebox、vLLM recipe、exllamav3 fork、SageAttention、Marlin W4A8）在本文中的角色是 **kernel / 算法 donor 与测量 oracle**，不是替代基座。kern 在这个问题上是"执行器 + 可验证工件"层，不携带任何 sm_89 kernel，也不改变上述三个天花板中的任何一个（详见姊妹文档 §5）。

4. **优先级（按 期望收益 / 工程量 排序）**：
   1. DFlash2 移植到 27B（上游 Neroued 已为 5090 落地，fork 有骨架）→ 短上下文 +25–60%、184k +20–45%（取决于 P0 量到的 AL）；1–3 周。
   2. suffix-tree / prompt-lookup 与 DFlash2 的**混合**草稿器（改写、复制、tool JSON 场景 AL 10+）；1–2 周。
   3. 长上下文 decode attention kernel（E8 解码 + 8–16 行验证一次读 KV）→ 184k step 31→~25 ms；2–4 周；**前置：打开 `ncu` 计数器权限**。
   4. prefill attention 重写（SageAttention2 类 INT8-QK/FP8-PV、FP16 累加）→ 184k TTFT −20–30%；4–8 周。
   5. Ada 专属 W4A4 IMMA prefill GEMM（Q4 code 直接做 s4 操作数，零解码指令）→ GEMM 再 +50–80%，**质量门禁高风险**；3–6 周。
   6. 用自家 Pi/OpenClaw 轨迹微调 DFlash2 drafter（+0.3–0.5 AL）；需 4× H100 级算力做在线蒸馏，4090 本机做不了。
   7. 低比特权重（3.5 bpw）、megakernel、显存超频：上限各 ≤10–15%，且前者有质量证据不利、后者工程量极大——放最后。

---

## 1. 问题定义：极致 = 什么

用户负载（`output/qwen38-27b-4090-ninfer/reports/10-pi-prefix-prod.md`、`12-rewrite-checkpoint.md`）**[实测]**：
- 单并发；每轮 prompt 追加式增长（prefix 命中 ~85%，`restore_user_turn_anchor` 100%）；
- thinking=medium，采样 T=1.0 / top_p 0.95 / top_k 20（OpenClaw 默认）——**投机方案必须在采样验证下仍成立**（Lucebox 本机 S0 车道：不开 sampled-verify 时 T=1.0 直接退回 51 tok/s AR）；
- 输出类型：tool JSON（短、高度可预测）、Java 代码（中）、rewrite（长、大段复制）、思考链（最不可预测）；
- 上下文 4k–184k，262k 容量是硬需求（E8 4-bit KV 换来的）。

因此"极致"要在三个坐标上同时评价：短上下文 tok/s、长上下文 tok/s、TTFT；并且**每一步都要过现有门禁**（Java 三题 3/3、28k/139k 针、rewrite 检查点）。

---

## 2. 物理账本（roofline）

### 2.1 卡的规格 **[公开 / fork 文档]**

| 项 | 值 |
|---|---|
| GDDR6X 带宽 | 1008 GB/s（fork 测得 decode 端到端可达 ~80–85%） |
| L2 | 72 MB |
| BF16/FP16 MMA，FP32 累加 | 165.2 TFLOPS（fork 寄存器驻留微基准 171.7） |
| FP16 MMA，FP16 累加 | 330.3 TFLOPS（微基准 342.9） |
| INT8 IMMA，INT32 累加 | 660.6 TOPS（微基准 686.1） |
| INT4 IMMA，INT32 累加 | 1321.2 TOPS（Ada 保留 INT4 tensor core；Hopper 起弃用） |
| FP8（E4M3）MMA | 660 TFLOPS（Ada 有 FP8 tensor core，无 FP4） |
| 动态 shared memory / block | ~99 KiB（fork 实测 101,376 B 可用） |
| `ncu` 计数器 | **不可用**：`RmProfilingAdminOnly: 1`，无 sudo → 任何 kernel 级工作的第 0 步是让管理员开 `NVreg_RestrictProfilingToAdminUsers=0` |

### 2.2 decode 每步字节数 **[推断，基于实测反推]**

模型：hidden 5120、64 层（16 attention + 48 GDN）、intermediate 17408、q 24 / kv 4 / d 256、vocab 248,320。

| 项 | 字节/step |
|---|---|
| 非 embedding 权重（Q4G64/Q5G64 + W8 lm_head） | ≈15.7 GB（18.2 GB 工件 − 2.5 GB bf16 embedding） |
| GDN state 读+写（48 × 3.2 MB） | ≈0.3 GB |
| MTP 草稿 3 步（1 层 block + 草稿头） | ≈0.3–0.6 GB |
| KV @184k，`rk4v4-e8` 26.4 KB/token（fork 实测斜率） | ≈4.9 GB |
| **合计** | 短上下文 ≈16.5 GB → 下限 16.4 ms；184k ≈21.4 GB → 下限 21.2 ms |

对照实测 **[实测/公开]**：
- no-spec 50.5 tok/s（上游 README）→ 19.8 ms/step → **带宽利用 ≈80%**；
- MTP3 code greedy 148.6 tok/s，AL≈2.9–3.0 → ≈20 ms/step（草稿几乎免费）；
- 184k：87.2–98.5 tok/s，AL≈2.9 → 30–33 ms/step → **≈65–70%**，多出的 ~6–10 ms 是 E8 lattice 解码算力 + 4 行验证的 attention kernel 效率（fork 文档："E8 staging time is lattice-decode compute"）。

旁证 **[fork 文档 / 报告 07]**：UDP 树的 Q4/Q5 权重 shuffle 微优化在本机 Linux sm_89 上测得 Q5 **−52.6%**（被拒），GDN shuffle 优化 **~0.1%**（"已 memory-bound"）；NInfer 与 llama.cpp 在相同接受率下仍更快，差在验证步时而非草稿质量。

**结论**：短上下文 decode 的 kernel 侧最多再挤 20%；184k 还有 ~30% 的 kernel 空间，全在 decode attention。tok/s 的乘数在 AL。

### 2.3 prefill 的 FLOP 账 **[fork 文档 + 推断]**

fork `docs/maintainer/prefill-throughput-plan.md`（2026-08-18 起，nsys 与 bench 两路核对到 0.2%）：
- dense GEMM 48.65 GFLOP/token；attention 196,608 × C FLOP/token（C 为上下文）；
- 118k prompt、Phase 0：dense GEMM 68.0%、GQA prefill attention 27.8%、其余 4.2%；**kernel 占 98.5% 墙钟，launch/sync 只有 1.5%**——"prefill 没有 launch 开销问题"；
- BF16 GEMM 路由 120.85 TFLOP/s = **73% 的 165.2 上限**，"There is no 2× hiding in the BF16 kernels"；
- **INT8 prefill GEMM 已落地**（Q4/Q5 code 本身就是 INT8 范围内的整数，权重侧零误差；激活 group-64 对称 INT8）：单 kernel 1.76×，六个 Op 聚合 1.68×，端到端 **1.435×（1739 → 2496 tok/s @115k）**；
- INT8 为什么止步 1.76× 而不是 4×：每 32 条 IMMA 伴随 ~850 条其他指令（地址计算 319、per-group rescale 192、Q4→INT8 解码 136）；128 个 FP32 累加寄存器把 CTA 钉在 1 个/SM。**这是 W4A8 group-64 在 Ada 上的固有代价，不是调参问题。**
- GQA prefill attention：`d256-h24-kv4` INT8 KV 下 161–180 TFLOP/s，为 **440 TFLOPS 混合上限（INT8-QK + FP16 累加 PV）的 37–41%**；`rk4v4-e8` 再慢 25%。作者核实"损失大头是 barrier 与 softmax 结构，不是 KV 解码"，并把 head-packing（Lever 2）在测量上关掉（上限仅 1.04×）。
- 184k 下 attention 份额升到 ~45%（FLOP 与 GEMM 同量级：6.7 vs 9.0 PFLOP）。

**结论**：prefill 剩余空间只在两处——attention kernel（41% → 70%+）与更换 MMA 指令（INT4）。二者都是货真价实的 kernel 工程，也都有公开先例（§3.3）。

---

## 3. 杠杆全景（按潜力）

### 3.1 杠杆 A：每步接受 token 数（AL）——唯一的倍增器

**A1. DFlash2 block-diffusion 草稿器（z-lab/Qwen3.8-27B-DFlash2）** **[公开]**
- 一次前向出整块，top-k 候选 + 选择器走一条路径，两抽头动态卷积抑制块尾衰减；greedy 无损、采样保分布。
- H200 / SGLang / T=1.0 / xhigh：AL GSM8K 5.46、MATH-500 5.28、HumanEval 4.39、MBPP 4.79、MT-Bench 4.10（block 8，最大 8）；MTP 同表 5.02 / 4.72 / 3.91 / 3.99 / 3.74。**同一模型同一硬件，DFlash2 对 MTP 的 AL 增益是 +9–12%，不是倍增**——倍增来自 block 变宽：Lucebox 文档实测 Qwen3.8-27B IQ4_XS + Q8 drafter，`--draft-block-size` 8/10/12/16 输出逐字节一致而每步提交递增。
- **本机实测 [实测]**（`output/qwen38-27b-4090-lucebox/reports/02-spec-ab.md`，block 16，短代码 ≤256 tok）：greedy decode 341 / 239 / 230 tok/s，avg_commit 14.0 / 9.2 / 8.9；`DFLASH_SAMPLED_VERIFY=1` 下 T=1.0：241 / 213 / 138 tok/s，avg_commit 12.6 / 10.4 / 6.3。token 加权 greedy 261、sampled 187 tok/s。
- **kernel-sanders vLLM recipe [公开，作者自家 4090 @450 W，非本机]**（`github.com/kernel-sanders/qwen38-27b-rtx4090-vision`）：int4 重量化 DFlash2 drafter，8 条真实 greedy prompt 118 / 126 tok/s、3.14 / 3.34 tok/step（MTP int4 版 114 / 118–124、2.8–3.0）；六类任务合计 67 tok/s / 3.15 tok/step（vision on、8 slots、`CTX=huge`），其中 copy 164 / 7.83 tok/step、code 109、edit 83、qa 43；`LOOKUP=1 DFLASH_TOKENS=15` 复现上下文 **381 tok/s、15 tok/step**，聊天场景只多 1%。
- **本机 llama.cpp PR27342 [实测]**：接受率 0.58–0.92 但 tools 路径只有 32–43 tok/s；思考/闲聊接受率 0.3–0.5（MTP 0.6–0.8）。两个混杂因素：(i) drafter 用的是 **Q2_K（705 MB）/ Q4_K_M（1.14 GB）** 量化，公开表与 Lucebox 用的是 bf16 / q8_0（2.0 GB）；(ii) 同卡 Lucebox（q8 drafter）短代码 230+ tok/s、kernel-sanders 混合任务 3.15 tok/step，说明 tools 路径 32–43 tok/s 主要是该实现的每步开销。此前"DFlash2 不适合 tool loop"的结论（`dflash2/reports/03-decision.md`）应改写为"llama.cpp PR27342 + 低比特 drafter 的组合不适合"；**思考链上 DFlash2 是否真的低于 MTP，要用 q8 drafter 在 P0 复测**。
- **NInfer 现状 [源码]**：fork `src/targets/qwen3_8/impl/runtime/dflash_context_impl.h` 等 40 个文件实现 DFlash（v1，block 16，35B-A3B 六层 companion 在用）；`round_state.h` `kDFlashDecodeMaximumDrafts = 15`；27B variant `enable_dflash=false`。上游 Neroued 已发布 27B DFlash2 工件（19.03 GiB vs 16.96 GiB，即 companion +2.07 GiB；5090 用）。4090 fork 与 5090 fork 按 `port-ledger.md` 是同源互 cherry-pick 的树。
- **显存 [推断，文件大小为实测]**：现网 262k `rk4v4-e8` 余量 ~1.9 GiB；companion 参考大小：GGUF Q2_K 705 MB、Q4_K_M 1.14 GB、q8_0 2.0 GB（本机文件），上游 `.ninfer` 工件差 2.07 GiB；可行路径：W4 companion + 262k，或 W8 + ~240k，或 `rk2v4-e8`（Java 题 3 曾失败，不建议）。
- **验证宽度 [源码]**：fork decode attention 已有 `T = 1..8` 调度 → block 8（7 草稿 + 1）**零 kernel 改动可跑**；block 16 需新增 T≤16 调度（见杠杆 B）。

**A2. suffix-tree / prompt-lookup 与模型草稿的混合** **[公开 + 实测]**
- SuffixDecoding（NeurIPS 2025 Spotlight，已合入 vLLM `method: suffix`，SGLang `--speculative-algorithm SUFFIX`）：对 prompt 与历史输出建 suffix tree，按分支频率动态出草稿，agentic 基准最高 5.3×，比 EAGLE-2/3 快 2.8×、比 Token Recycling 快 1.9×；CPU-only、无权重。
- 用户负载正是它的靶子：rewrite（大段复制）、tool JSON、多轮同结构输出。`12-rewrite-checkpoint.md` 的 60k 改写场景是天然测试集。
- 同卡公开旁证 **[公开，kernel-sanders 4090]**：`LOOKUP=1` 复现上下文 130 → 259 tok/s，再加 16 宽验证块 → 381 tok/s（3090 历史数据 260 → 382）；聊天场景只 +1%，即这是"按场景开"的杠杆。
- NInfer 姊妹 fork（UDPSendToFailed）有分层 n-gram prompt-lookup（v0.8.0），但 tensorninja 评估"MTP 开着时几乎不开火，skip"，现网 `continuation_lookup_hits` 仍为 0（`udp-fork-comparison.md`、报告 10）。正确形态是：**有 ≥k 的长匹配用 suffix 草稿（可 16–32 宽），否则用 DFlash2**；验证路径复用同一套宽验证。NInfer 家族里没人实现这个混合。

**A3. DDTree 树验证** **[公开 + 实测]**
- 论文（arXiv 2604.12989）：Qwen3-8B、MATH-500、budget 256–512 最优；Lucebox 实现 budget 22（3090）/40（5090），`chain_seed` 把 AL 从 ~4 拉回 ~9。
- **本机 [实测]**：短 greedy 代码上 DDTree budget 28（255 tok/s）**没有赢** chain block 16（261 tok/s）。树的价值在链接受率低的场景（采样、思考链）；排在 A1/A2 之后。

**A4. 用自家轨迹微调 drafter** **[公开]**
- z-lab / vLLM speculators / NeMo AutoModel 都开放 DFlash2 训练配方：5 层、block 16、SWA 2048、Muon + AdamW、目标模型隐藏态在线抽取；speculators RFC：定向数据从 epoch 0 混入 **+0.1–0.15 AL**。
- 代价：27B 目标模型在线蒸馏推荐 4× H100 级（2 张 vLLM + 2 张训练）；4090 单卡放不下目标 + 训练。收益上限 +0.3–0.5 AL（~+10%）。放最后，且只在 A1–A3 落地后做。

**A5. 长上下文自投机（TriForce / MagicDec / QuantSpec）** **[公开]**
- 思路是让 drafter 只读稀疏/量化 KV 以绕过 KV 带宽墙。对本模型：184k 时 KV 只占每步字节的 ~23%，权重占 73%；DFlash2 drafter 本身就是"小模型 + 2048 滑窗"，已经包含了这一思想。**不构成独立杠杆。**

### 3.2 杠杆 B：长上下文 decode attention kernel（kernel 级）

- 目标：8–16 行验证在 184k 下**只读一遍 KV**、E8 解码不成为算力瓶颈、step 从 31 ms 压到 ~25 ms。
- 现状证据 **[fork 文档]**：decode attention 有 `T=1..8` 调度；`rk4v4-e8` 的 prefill 路径比 int8 慢 25%（unpack + 两次 Hadamard）；decode 侧 E8 "staging time is lattice-decode compute"。
- Lucebox 的反例 **[实测]**（`04-longctx-why.md`）：8k 以上把验证宽度 16→8 砍半，180k 只剩 52 tok/s——这是 ggml tile kernel 的限制，不是物理限制：16 行 × 184k × 256 × 2 × 24 头 × 16 层 ≈ 1.2 TFLOP，FP16 MMA 7 ms、INT8 2–3 ms，可以做到"宽验证几乎免费"。
- 可借鉴：FlashInfer 的 multi-query decode（sm_89 有构建）、SageAttention 的 INT8-QK 在 decode 小 M 下的 tensor-core 用法、Lucebox 的 tree-aware SSM rollback kernel（GDN 层的宽/树验证回滚，直接对应 NInfer 的 GDN 层）。
- 工程量 **[推断]**：2–4 周，一个人；**必须先有 ncu**。

### 3.3 杠杆 C：prefill（kernel 级）

**C1. attention 重写到 Sage 类** **[公开]**
- SageAttention2 / 2++（thu-ml，Apache-2.0，明确有 Ada kernel）：Q/K INT8 或 INT4（per-thread 粒度 + 平滑），P/V FP8 E4M3、FP16 累加；**RTX 4090 上峰值 485 TOPS，比 FlashAttention2 快 3.0×（8+8）/ 3.9×（4+8）**；语言/图像/视频端到端指标"negligible loss"。
- 与 fork 现状对比：fork 的 INT8-QK + FP16-acc-PV kernel 在 180 TFLOP/s（41% 上限）。Sage 的 PV 走 FP8 而不是 FP16，并且把 warp 结构做对——这正是 fork 作者判定"barrier 与 softmax 结构"损失的地方。
- 收益 **[推断]**：attention 1.8–2.2× → 184k prefill +25–35% → TTFT 94 → 65–75 s。
- 注意：Sage 的 KV 是 INT8/FP8 而不是 E8 4-bit；要么在 prefill 时对刚生成的 K/V 先用 int8 路径再写入 E8（多一次量化），要么把 E8 解码融入 kernel（保留 4-bit 容量）。这是设计决策点。

**C2. Ada 专属 W4A4 IMMA GEMM** **[公开 + fork 文档 + 推断]**
- Ada 保留 `mma.sync … .s4.s4.s32`（1321 TOPS，Hopper 起弃用、Blackwell 移除）。fork 的 Q4G64 code 落在 [-8, 7]，**直接作为 s4 操作数，权重侧零误差、零解码指令**——恰好消掉 fork 实测中 INT8 路由的两个瓶颈（Q4→INT8 解码 136 条/组、per-group rescale 仍在）。
- 激活 INT4：Atom / QuaRot 类需要 Hadamard 旋转压异常通道；fork 的 KV 路径已有 Hadamard-64 机制，converter 侧折叠 `W·Hᵀ` 的方案已写在 `prefill-throughput-plan.md` §4.11 第 4 级。Q5 层（down / o / gdn_out）没有 s4 表示，要保留 INT8 路由或重量化为 Q4。
- 收益 **[推断]**：GEMM 部分再 1.5–1.8× → 184k prefill 再 +25–35%。**质量风险最高**，只有过 AIME/GPQA 或至少 Java 3/3 + 长文针 5/5 才算数；fork 作者为 A8 只跑了 12 条 greedy 一致性 + 139k 针（未跑 AIME/GPQA），A4 必须补全套。

**C3. 已被 fork 关掉、不要再做的事** **[fork 文档]**：GQA head-packing（shared memory 不够，`Bc=32` 实测 −4.2%，上限 1.04×）；prefill chunk 调参（+0.6%）；D2D 拷贝/同步清理（0.18% / 1.5%）；把 KV 换成 int8 提升 prefill（+6% 但丢 262k 容量）。

### 3.4 杠杆 D：权重比特（带宽侧）

- 每 −0.5 bpw ≈ −1.5 GB/step ≈ +10% decode step。
- 质量证据 **[公开]**：Qwen3.8-27B EXL3 3-bit mix（GestaltLabs 11.5 GB）对 BF16 的 KL 是官方 FP8 的 **11×**；EXL3 K5K6（5–6 bit）KL 0.0032 优于 FP8 的 0.0053；Mia-AiLab 3.5 bpw 明写"inferior to FP8 in divergence"。即 **4 bit 以下有可测的质量代价**，对以 Java 3/3 为门禁的 agent 负载不值得当默认。
- 若做：只对 GDN 层试 Q3/Q4 混合 + 现有 `bench/ops` oracle；上限 +10–15%。

### 3.5 杠杆 E：megakernel / persistent kernel

- 证据 **[公开]**：Hazy Research Llama-1B bs=1 H100 megakernel 带宽利用 78% vs vLLM/SGLang ~50%；MPK（Mirage）Qwen3-8B A100 14.5 → 12.5 ms/step（理论 10 ms），1.0–1.7×，"improvements are most significant for smaller models"；Lucebox 在 3090 上做了**混合 DeltaNet/Attention 架构的 megakernel**（Qwen3.5-0.8B，413 vs 267 tok/s），证明 GDN 混合模型可以 mega 化。
- 对本模型 **[推断]**：fork 已在 80%（短）/ 68%（184k）带宽；64 层 ~640 launch 全在 CUDA Graph 内；上限 1.25×，现实 1.1×。工程量数月。**放最后**。

### 3.6 杠杆 F：硬件与运行环境

- 显存超频：社区口径 +1500 MHz ≈ +10% tok/s **[公开，弱来源]**；Linux 下需 LACT/NVML offset 或 Coolbits，未在本机验证；GDDR6X 结温需 <95 °C。免费但要单独 A/B 与稳定性 soak。
- 时钟/功耗：fork 测量协议已要求记录 SM clock / power（480 W、3165 MHz），prefill 会降频；`nvidia-smi -lgc` 锁频可减少抖动，不提高上限。
- `ncu` 权限（§2.1）：不是性能项，是所有 kernel 工作的前提。

---

## 4. 基座选择

| 候选 | 4090 上现状 **[实测/公开]** | 作为极致基座的致命项 | 在本文中的角色 |
|---|---|---|---|
| **NInfer 4090 fork（tensorninja `rtx4090-port`，现网 44a2c6c）** | 短 127–148、184k 87–98、262k、prefill 1974@184k；INT8 prefill 已落地；DFlash 骨架已有 | 无；缺的是 DFlash2 for 27B 与两个 kernel | **基座** |
| Lucebox（C++/CUDA on ggml） | 短代码 230–341 greedy、187 sampled；28k 115.6 / 64k 69.1 / 128k 61.3 / 180k 51.5；180k 冷 prefill ~1100 tok/s **[实测]**；DDTree、TQ3 KV、tree-aware SSM rollback | prefill 慢于 llama.cpp；>8k 砍验证宽度 16→8；ggml kernel 天花板；OpenClaw 小工具前缀命中 0；未测 Pi Java | **AL 的测量 oracle**（1 天内可在真实 Pi 轨迹上量出 block 8/16 的 AL）；tree rollback kernel 参考 |
| vLLM（本机 huge-mtp **[实测]** / kernel-sanders recipe **[公开]**） | 本机：prefill 2802@185k（最快）、184k decode 53、Java 3/3 但 p50 48 s；kernel-sanders 4090：DFlash2 118–126、混合任务 3.15 tok/step、lookup 复现 381 | Python/Triton 开销，decode 步长 ~26 ms vs NInfer 20 ms；TTFT 6.7 s@4k；显存紧 | DFlash2 int4 drafter 参考实现、split-KV verify attention、Marlin W4A8（Ada 走 lop3 回退）、KVarN |
| exllamav3（MiaAI-Lab fork） | Qwen3.8 hybrid + DFlash2 + 软件 NVFP4 KV（Ada 可编）；无 4090 数据，GB10 47.5 tok/s | Python；权重 3.5 bpw 质量证据不利 | 软件 NVFP4 KV 编解码参考 |
| llama.cpp（WORK / PR27342 / buun / VBR） | 日常 agent p50 27 s 最快；DFlash2 实现拖累 | 无 E8、无 INT8 prefill、DFlash2 实现慢 | 现网 fallback；无 donor 价值 |
| SageAttention（thu-ml） | Ada 内核，4090 3.0–3.9× FA2 | 不是引擎 | **prefill attention donor** |
| kern（pegainfer） | 全部 sm_103a、BF16、cuBLASLt；无 Ada 工件（姊妹文档 §4–5） | 不携带任何 sm_89 kernel；不改变三个天花板；serving 语义缺失 | 无；其"typed opaque kernel + 校验"思想可借鉴为 fork 的 op oracle 纪律（fork 已有） |
| 从零写引擎 | — | 重复 fork 已到 roofline 的 80% 工作 | 否 |

**为什么"深挖 NInfer"是对的而不是保守**：三个天花板中，两个的剩余空间是 kernel（B、C），一个是算法（A）。A 在 NInfer 里只差配置 + 上游合并；B、C 在任何引擎里都要重写，而 NInfer 是唯一已把 roofline 账算清、有 op 级 FP64 oracle 与 bench 的树，新 kernel 落进去的验证成本最低。

---

## 5. 已经测过什么（避免重测）**[实测，来自 `output/` 报告]**

| 引擎 / 方案 | 关键数字 | 结论（当时） | 本文修正 |
|---|---|---|---|
| NInfer MTP3 `rk4v4-e8` 262k（现网） | 4k 127 / 184k 98.5（medium）；184k TTFT 94 s；Java 3/3；prefix 命中 85% | 默认 | 基座 |
| NInfer `rk8v4` 200k | 4k 145 / 184k 103.7；针全中 | 未当默认（窗口） | DFlash2 后重评 |
| NInfer draft 4/5、`rk2v4-e8`、L3 | 无收益 / Java 题 3 失败 / 无收益 | 否决 | 维持 |
| WORK llama.cpp MTP n=2 200k | 日常 p50 27 s；184k TTFT 134 s、prefill 1383 | 日常最快 | 维持为 fallback |
| vLLM huge-mtp | 185k TTFT 66 s、prefill 2802；decode 弱于 NInfer | 不上线 | prefill 参考线 |
| llama.cpp PR27342 DFlash2（Q2_K / Q4_K_M drafter） | 短码 112–125、fib 96；tools 32–43（MTP ~75–88）；思考接受 0.3–0.5；Pi P-loop 16.2 s 慢于 WORK；250k 后 VRAM 剩 25 MiB | DFlash2 不适合 tool loop | **改为：该实现 + 低比特 drafter 不适合；思考链 AL 待 q8 drafter 复测** |
| Lucebox DFlash2 block 16（q8 drafter） | 短代码 230–341 greedy、187 sampled；28k→180k 115.6→51.5；180k prefill ~1100；DDTree 28 不赢 chain；小工具前缀命中 0 | 不能替代 WORK 200k | **AL 天花板的本机证据；P0 的测量工具** |
| NInfer sergiuszm 树（08-15/17） | MTP3 代码 128k 104 / 散文 77；E8 240k 代码 91.2；INT8 prefill 128k 1561 | 已融合进 tensorninja | 不切树 |
| NInfer udpsend 树 | **作者声称** MTP7 greedy 229.9（非 agent 采样）；DirectStorage 为 Windows only；lookup 在 MTP-on 下不开火 | 不切镜像 | 维持；lookup 思路进 P2 |
| buun-llama VBR | 空载 18.4 GB；64k 37 tok/s | 不当默认 | 维持 |
| Cold-Fusion YMQ-M / Hauhau TEXT / QCB S-list 权重 | 窗与针成立；Hard 46/96 vs 45/96 不显著 | 不换权重 | 权重侧无杠杆 |
| flash-next-mtp（35B，CPU expert） | 17→28 tok/s | 方向对 | 与 27B 无关 |
| Ornith-1.5-35B-A3B | 200k q4 ~155 tok/s；工具格式 invalid 41.7% | 备选模型 | 换模型不在本文范围 |
| EXL3 3.5 bpw（公开卡） | 无 4090 数据；KL 显著差于 4.5–5 bpw | — | 不作默认 |
| 报告已列、未做的 serving 项 | `--auto-long-anchors`（作者 46.7k TTFT 16.6→0.59 s）未移植；L3 未用真实 session 验证 | — | 与吞吐上限无关，但属低成本 UX 项 |

---

## 6. 路线图（每阶段可独立停止）

| 阶段 | 内容 | 预期 **[推断]** | 工程量 | 门禁 | 止损 |
|---|---|---|---|---|---|
| **P0 前置（1–2 天）** | 管理员开 `ncu` 计数器；用 Lucebox（q8 drafter）在 20 条真实 Pi/OpenClaw 轨迹（含 tool JSON、Java、rewrite、thinking）上量 DFlash2 block 8 / 16、sampled-verify 的 AL 分布，按输出类型分桶（thinking / tool JSON / code / rewrite） | 得到 A1 的真实 AL（预期 agent 混合 3.2–4.2，code ~4.4，rewrite 8+；thinking 桶是关键未知） | 2 人日 | — | AL(block 8, sampled, 混合) < 3.0（≈现网 MTP 2.5–3.0 的 +10% 以内）→ A1 期望收益 <15%，先做 P2/P3 |
| **P1 DFlash2 → 27B（NInfer fork）** | cherry-pick 上游 27B DFlash2（动态卷积 + selector）；converter 产 companion（W4 优先）；27B variant 开 `enable_dflash`，block 8 走现有 T≤8 调度；显存预算按 §3.1 | 短 +25–60%、184k +20–45%（随 P0 的 AL） | 1–3 周 | Java 3/3、139k 针 5/5、rewrite 检查点、sampled 分布抽检 | 184k 下 step > 35 ms 且 AL 增益 <25% → 先做 P3 再回 P1 |
| **P2 suffix/lookup 混合草稿** | CPU suffix tree（prompt + 会话历史）；长匹配走 16–32 宽草稿，否则 DFlash2；验证复用 P1 路径 | rewrite/tool JSON 场景 AL 10+ → 300–500 tok/s；混合流量 +10–20% | 1–2 周 | 12 号报告的 rewrite 集；tool JSON 完整性 | 误命中导致 AL 下降 → 提高最短匹配长度 / 只对 rewrite 开 |
| **P3 decode attention kernel（E8 + 宽验证）** | 一次读 KV 服务 8–16 行；E8 解码 LUT 化 / 张量核化；T≤16 调度 | 184k step 31 → ~25 ms；block 16 在长上下文可用 | 2–4 周 | bit-exact oracle（fork 已有 E8 oracle）；184k tok/s A/B | ncu 显示 attention 已达带宽 → 停止 |
| **P4 prefill attention（Sage 类）** | INT8-QK + FP8-PV + FP16 累加、warp 结构重做；与 E8 写入路径整合 | 184k TTFT 94 → 65–75 s | 4–8 周 | greedy 一致性 + 139k 针 + Java；建议补 AIME/GPQA 一次 | kernel 到 60% 上限仍 <1.5× → 收 |
| **P5 W4A4 IMMA GEMM（可选）** | Q4 code 直作 s4；激活 Hadamard-64 折叠 + INT4；Q5 层保留 INT8 | 184k TTFT 再 −25–35% | 3–6 周 | **全套 AIME25/26 + GPQA**（fork 未跑过） | 质量掉 → 两平面 INT8 兜底 |
| **P6 长尾** | drafter 微调（云算力）、GDN 层 Q3 混合、显存超频、megakernel | 各 ≤10–15% | 不定 | 同上 | — |

预期叠加（agent 混合流量，**[推断]**）：P1 × P2 × P3 ≈ 1.4 × 1.15 × 1.2 ≈ **1.9×**（短上下文 200–250、184k 150–180 tok/s）；rewrite / 复制类 3–4×（kernel-sanders 同卡 381 tok/s 是公开上界参考）；TTFT 经 P4（+P5）1.3–2×。若 P0 量到 thinking 桶的 DFlash2 AL 低于 MTP，则 P1 收益缩到 +15–25%，P2/P3 权重上升。

---

## 7. 来源

**本机 / 仓库**
- `output/qwen38-27b-4090-ninfer/reports/07,09,10,11,12`；`output/qwen38-4090-compare/results/{COMPARE.md,medium/REPORT.md}`；`output/qwen38-27b-4090-lucebox/reports/01–05`；`output/qwen38-27b-4090-20260818/dflash2/reports/01–04`；`output/qwen38-27b-4090-eval-20260824/00-v3-200k-dflash2.md`；`output/qwen38-27b-4090-pi-ab/01,02`；`output/qwen38-27b-4090-buun-llama/reports/01-eval.md`；`output/qwen38-qcb-4090-*/reports`；`output/ornith-35b-4090-eval-20260825/reports`。全量逐引擎账本由子代理汇总，已并入 §5。
- 4090 fork（`/home/hhtele/ninfer-4090`，2026-09-06 快照）：`docs/maintainer/prefill-throughput-plan.md`（roofline、INT8 GEMM 1.76×/1.435×、attention 41%、Lever 2 关闭证据、ncu 不可用）、`docs/maintainer/port-ledger.md`、`docs/udp-fork-comparison.md`、`src/targets/qwen3_8/impl/runtime/dflash_*`、`src/targets/qwen3_8/export/ninfer/targets/qwen3_8/round_state.h`、`src/ops/common/int8_rowsplit_gemm.cuh`、`src/ops/kernel/gqa_attention_prefill_i8.cuh`。

**公开**
- z-lab/Qwen3.8-27B-DFlash2 模型卡（AL / 吞吐表）：https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2
- kernel-sanders 4090 vLLM recipe（DFlash2 int4 drafter、lookup、按任务分桶 tok/step；作者自家 4090 @450 W）：https://github.com/kernel-sanders/qwen38-27b-rtx4090-vision
- DFlash 论文：https://arxiv.org/abs/2602.06036 ；DDTree：https://arxiv.org/abs/2604.12989
- Lucebox server README（block-size 外推、DDTree、TQ3 KV）：https://github.com/Luce-Org/lucebox/blob/main/server/README.md ；megakernel：https://www.lucebox.com/blog/megakernel
- SuffixDecoding：https://suffix-decoding.github.io/ ；vLLM PR #25784；SGLang issue #13165；Snowflake 工程博客
- SageAttention2 / 2++：https://arxiv.org/abs/2411.10958 ；https://arxiv.org/abs/2505.21136 ；https://github.com/thu-ml/SageAttention ；sm89 专用分支 https://github.com/fblissjr/SageAttention-ada
- Marlin W4A8 / Ada 回退：vLLM issue #49529、PR #50096
- Megakernel：Hazy Research "No Bubbles"（2025-05）、"Whole GPU"（2025-09）；MPK：https://arxiv.org/abs/2512.22219
- 长上下文投机：TriForce（2404.11912）、MagicDec（2408.11049）、QuantSpec（2502.10424）
- DFlash 训练配方：vLLM speculators `train_dflash_online.md`、RFC #979；NVIDIA NeMo AutoModel DFlash2 recipe；regolo.ai 教程（4× H100 建议）
- EXL3 质量数据：billmccartney 8 bpw、malaiwah K5K6、GestaltLabs 11.5 GB、Mia-AiLab 3.5 bpw 模型卡
- 显存超频口径（弱来源）：ventusserver、dasroot 2026-05

---

## 8. 局限与未验证项

- 所有 "[推断]" 的 tok/s 目标基于 roofline 与公开 AL，**未在本机跑通任何新 kernel 或 DFlash2-on-NInfer**；P0 的 AL 实测是第一块试金石。
- 上游 27B DFlash2 在 5090 的 tok/s 未采集；companion 精度格式（19.03 − 16.96 GiB 的构成）未核实。
- W4A4 的质量风险只有公开的 Atom/QuaRot 类先例，无 Qwen3.8 数据。
- Sage 类 kernel 与 E8 4-bit KV 的整合方式未设计。
- 显存超频在 Linux 无 X 环境的可操作性未验证。
- 本机所有 DFlash2 数据要么来自 llama.cpp（Q2_K/Q4_K_M drafter）要么来自 Lucebox 短代码 greedy/sampled；**没有任何本机数据覆盖"thinking=medium + tool loop + q8/bf16 drafter"这一现网形态**，这正是 P0 要补的。
- kernel-sanders 的数字是同型号卡的公开自测（450 W、vision on、8 slots），不是本机；用作量级参考而非基线。
