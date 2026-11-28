# TensorFold（Inkling-2-Mini-RTX-5090-TensorFold）研读：对 4090 上 Astral 的可借鉴项

日期 2026-11-28。范围：patches 0001–0028，但不含 0018 / 0019 / 0020 / 0026（DFlash2 相关，由另一个 agent 负责）。0004 / 0010 / 0015 / 0016 / 0017 只看了标题和要点，它们是 reply split、reasoning 字段、structured output、vision 和 server 兼容，与性能无关。

## 0 标注与路径

- 【事实】：从源码或文档读到，标注 `文件:行`。.patch 文件给的是补丁文件内的行号。实验包文档里的数字是本实验已经测得的。
- 【自报】：TensorFold 自己报告的数字（README、commit message、注释），本次没有复现。
- 【推断】：我的计算或判断，依据写在旁边。

路径简写：

- `TF/` = `/root/github/inkling-research/repos/Inkling-2-Mini-RTX-5090-TensorFold`。release 仓库，含 README、28 个 patch 和 tools，1.5 MB。
- `UP/` = `/root/github/inkling-research/repos/TensorFold-dc2ca8a-files`。上游 TensorFold 在 dc2ca8a 提交的约 20 个单文件，逐个 raw 下载，352 KB，没有 clone。
- `FORK/` = Astral fork（scratchpad 下的 `fork`，只读）。
- `LAB/` = `/root/github/CodexGame/docs/inkling-4090-lab-v3.0`（只读）。

## 1 结论：按对 4090 上 Astral 的价值排序

| # | 可借鉴项 | 无损 / 有损 | sm_89 可行性与所需指令 | 与 Astral 现状和 K/R/T 的重叠 | 收益估计与依据 | 建议验证 |
|---|---|---|---|---|---|---|
| 1 | **FP8 KV cache**（0003）：每个 (token, kv head) 存 e4m3 码，加一个 fp32 scale，scale = amax/448 | 有损 | 可行。用 `cvt.rn.f16x2.e4m3x2` 解码（sm_89 起支持，正好对应 Astral 的 f16 注意力）。decode 时把 K 的 scale 乘进 score、V 的 scale 乘进 p；prefill 解码进 smem 的 f16 tile 后复用现有 MMA | 06 §4 的“模型特定的有损量化”；T17 / T25 长上下文；T21 长上下文下的 DSpark | 【推断】128K decode 从 73.7 到约 95–105 tok/s（+30–45%），64K 从 97.4 到约 115–120。最大上下文约 1.6–2 倍。依据：128K 时每 token 读全局 KV 4.29 GB，有效带宽约 670 GB/s，FP8 读量减半 | 先把量化误差和 kernel 误差分开测（06 §4）；8K、32K、64K、128K 的 KL 与 top-1；T25 的 num-4L；passkey 9 格；代码和中文样本 |
| 2 | **fragment-major 的 Q8_0 小 T kernel**：T = 1–8 共用同一个 kernel，K 序固定（来自 ck_lane / qmmf 的权重 fragment 排布与 16 B lane load） | 相对当前 int8 激活路径无损（按固定的 K 序可做到逐位一致） | 可行。`mma.sync m16n8k32 s8`（Astral 已在用）加离线重排权重，一个 lane 一次 16 B load | K6（mma5 / fragment 路径接入）、K2（T=1 和 T=2–8 用不同路径）、K5 / T20 / V8（decode ≠ verify） | 【推断】融合输入投影占 decode 25.8%，有效带宽约 540 GB/s。到约 900 GB/s 可省约 10%，o 投影同理再加 2–3%。同时让 decode ≡ verify（Q8_0 部分） | 逐位对比旧 kernel（同一 K 序）；T20 三组；num-3；DSpark 接受率 |
| 3 | **batch-invariance 契约**扩到其余算子：注意力 chunk 与合并顺序固定、NVFP4 专家、controller、prefill 与 decode 同一种激活量化；再加 `tools/exact.py` 式的三路 SHA 回归 | 无损 | 可行，不需要新指令。关键是 split-K 只依赖 (N, K)、行补零进 fragment、关闭 FMA 收缩（`__fmul_rn / __fadd_rn` 或 `--fmad=false`） | K5、T20、V8、K2 的阻塞条件（T=1 dp4a 的 decode 与 prefill 差超限）、T34 v1、R14 的“无损”前提 | 不直接提速。收益是 DSpark 输出与关闭草稿时逐位相同，可用 SHA 代替 KL 阈值做回归；也是 T34 与 R14 的前提 | 先用 T15 的 `astral trace` 在同一位置比较 decode 步和 verify 第 0 行，逐算子找第一个不同的地方，再决定改哪个 kernel |
| 4 | **prefill 的张量核与注意力**：INT8 W4A8 / W8A8，epilogue 去掉 I2F 瓶颈；prompt 注意力改成 cp.async 多级流水并融合 slide（0009 / 0011 / 0023）；chunk 4096（0013） | GEMM 有损（激活为 int8），但与 decode 的量化一致；注意力流水无损 | 可行。`mma m16n8k16/k32 s8`；e2m1×2 是精确的 int8；epilogue 用 0x4B400000 magic number 代替 I2F。不可用：FP4 张量核、block-scale MMA、cp.async.bulk、cluster | Astral 已有 int8 路径 `gemm_nvfp4_mma2`，因精度改走 f16 `mma3`；与 K6、K10、T19 重叠 | 【推断】2K 预填中两个 mma3 GEMM 占 kernel 时间的 62.7%，NVFP4 GEMM 约 67 TFLOPS（f16 峰值的 40%）。GEMM 到 2 倍时 2K 预填约 +45%；128K 下注意力占比更高，收益看实测 | 先用 ncu 看 mma2 是否受 I2F 限制；用 nsys 拿 32K / 128K 预填的注意力占比；KL 与 T19 的可复现性 |
| 5 | 小融合：SwiGLU epilogue 直接量化（0021）、2 warp 拆分 gate-up（0007）、prompt gate_prep 融合（0028） | 无损（0021 在 Astral 里是 Q8 激活，与现有 `situ_q8` 同一算式） | 可行 | K1、K3、K8；K9 是同一类思路 | 【自报】0007 的 gate-up 121→113 µs。【推断】在 Astral 上 decode 约 +1%；situ_q8 占 2K 预填 2.7% | 逐位对比原算子 |
| 6 | **keyed Gumbel race 采样**（0006 / 0008）：噪声由 (seed, pos, token) 决定，草稿与目标用同一份噪声 | 无损：有无草稿时采样输出相同 | 可行，纯算术 | Astral 只有贪心（`FORK/crates/api/src/lib.rs:10`），没有重叠 | 功能项，不是速度项 | exact.py 式比较：temp > 0 时有无草稿 SHA 相同 |
| 7 | **certified lazy head**（0008） | 无损（可证明的候选集加精确重算） | 可行，但 FP8 proxy 在 Astral 上没有意义；只有 4 bit 位平面 proxy 值得考虑 | T26（head 侧 NO_BENEFIT）、R 类无 | 【推断】上限约 decode 3%、DSpark 轮 2%。依据：head 占 decode 7.3%、占一轮 4.8% | 离线：从 T15 trace 取 hidden，numpy 算候选数分布；中位数 ≤ 64、溢出 < 1% 才实现 |

不建议借鉴：

- 在 decode 上用 FP8 投影（0012）：Q8_0 是 8.5 bit 每权重，FP8 per-tensor 只省 6% 而且更不准。这与 K7 的初衷相悖，见 §4.4。
- 原生 `e2m1x2 / e4m3x2 → bf16x2`（0024）、W4A4 `kind::mxf4nvf4`（0014）、`cp.async.bulk` 和 cluster（0025、ck_lane）：只能在 sm_120 或 sm_90+ 上用。
- 64 项宽图缓存（0013）：Astral 只服务单流，已经按 k 捕获 graph。
- PDL：sm_89 不支持，对方在 GB10 上测得 <1%（`TF/patches/0005-mini-speed.patch:836`）。

## 2 Q1：certified lazy head（0008）

### 2.1 算法【事实】

kernel 都在 `TF/patches/0008-mini-lazy-head.patch`：
- `tf_ink2_lazy_delta`：:191
- `lazy_low`：:271
- `lazy_low2`：:311
- `lazy_pick`：:342
- `lazy_exact`：:378
- `lazy_full`：:404

常量在 :823–827：`cands = 256`、`max_rows = 64`、`eps = 4e-3`、`abs = 0.02`。

步骤：

1. 离线：bf16 head W（V × H）转成一份 per-tensor e4m3 proxy，scale = amax/448（:650）。
2. 离线：算 `delta[v] = ‖W_v − proxy_v‖₂`，用 fp64 计算并向上取整。
3. 每行：用 proxy 做 GEMV 得到 z̃，并算 ‖x‖。误差界 `B_v = (delta_v + eps)·‖x‖ + abs`。由 Cauchy–Schwarz，|z_v − z̃_v| ≤ B_v。
4. 贪心：先取 `L = max_v (z̃_v − B_v)`，候选集为 `{v : z̃_v + B_v ≥ L}`，真 argmax 一定在候选集里。
5. 采样（mode 1，`lazy_low2` :311–320）：把 race score 加上 keyed Gumbel 噪声后同样取界。只在 top_k 关闭、top_p = 1、`min_log ≤ −24`（`kNever = 24`，:230）时启用。
6. 候选 ≤ 256 时，`lazy_exact` 用 qmmf 的 bf16 lane MMA 链逐位重算这些行，其余 logit 设为 −inf。超过 256 时（:384），`lazy_full` 精确算整行。
7. 每轮最多 64 行（verify 宽度），用独立的 `graphs_lazy`。

softcap 是单调变换，不影响 argmax 与候选判定【推断】。

### 2.2 成本与命中率

- 【事实】README 和 commit message 都没有命中率或候选数分布。只有 `TF_INKLING2_LAZY_TRACE` 打印的直方图（运行时才有）。
- 【推断】成本：
  - proxy 读 463 MB，加 delta 0.8 MB，加候选行 256 × 2304 × 2 B ≈ 1.2 MB。原 bf16 head 读 926 MB，无溢出时 head 字节约减半。
  - proxy 本身多占 463 MB 显存。
  - Cauchy–Schwarz 对随机方向偏松约 √H ≈ 48 倍，所以候选数取决于 top logit 的间隔分布，不能先验估计。

### 2.3 对 Astral 的适用性【推断】

- Astral 的 head 是 Q8_0（8.5 bit，492 MB），不是 bf16。FP8 proxy 有 463 MB，即使零溢出也只省约 6% 的 head 字节，还要多占 463 MB 显存。**不值得做**。
- 可考虑的变体是 4 bit 位平面 proxy：
  - 把 Q8_0 head 重排成“高半字节平面 + 低半字节平面 + scale”，总字节不变，不多占显存。
  - proxy 只读高平面（约 260 MB）；候选行再读低平面，按原 dp4a 顺序重组 int8，结果与现在逐位一致。
  - 误差界比 e4m3 proxy 松约 4–6 倍，候选数和溢出率更高。
  - 上限：head 占 decode 的 7.3%（T16）、占 DSpark 一轮的 4.8%（T26，NO_BENEFIT），所以最多省 decode 约 3%、一轮约 2%。
- DSpark verify：k+1 行共用一次 proxy 权重读，各行有自己的候选集；任一行溢出就只补算那一行。这在形式上可行。
- 结论：优先级最低。实现前先离线测候选数。从 T15 trace 取 coda 输出的 hidden，约 1 万个位置，用 numpy 分别算 e4m3 和高半字节两种 proxy 的候选数分布；中位数 ≤ 64、P99 ≤ 256、溢出 < 1% 才值得实现。
- “可证明的候选集 + 精确重算”与 keyed race 的组合思路，在加入采样时可以复用（排序表第 6 项）。

## 3 Q2：drafted 与 `"draft": false` 如何逐位一致

### 3.1 tools/exact.py 测什么【事实】

`TF/tools/exact.py:2–14, 41–42, 74, 87`：同一组贪心请求（temperature 0，seed 4321，thinking 关闭）各发三次，比较回复文本的 sha256、token sha 和 finish reason：

- serial：逐个发送，按服务端默认起草；
- nodraft：逐个发送，带 `"draft": false`；
- conc：多线程并发发送。

服务端没有实际起草时，结果标为 UNCHECKED。这个脚本只做端到端检查，逐位一致靠的是内核层的契约。

### 3.2 内核层的不变性契约【事实】

1. **qmmf 字节契约**（`UP/zig/src/cuda/qmmf.md`，:69 附近）：
   - 每个 K slice 的累加器都从 +0 开始；
   - K 按 64 元素升序访问，每步 4 个 `mma.sync m16n8k16`；
   - split-K 只由 `splitK(N, K)` 或 `Weight.sk` 决定，**不依赖 M 和 CTA 尺寸**；
   - 最后只做一次 RNE bf16 舍入。
   
   结果：同一行无论和多少行同批，位都相同。
2. **FP8 投影**（`UP/zig/kernels/cuda/ck_lane.cu:1`）：“rows alone, K slices by shape, so rows invariant”。
   - M 方向超出的 m16 tile 直接跳过（:94），不影响其他行。
   - cluster 路径不改变 slice 的求和顺序（:166）。
   - reduce 按 slice 顺序逐个 fp32 相加（:184–192）。
3. **专家**（`UP/zig/kernels/cuda/nvfp4_experts.cu:562`）：“The decode form's factored sums on the prompt tiles, bit for bit”。prompt tile 复用 decode 的累加式。
4. **注意力**（`UP/zig/kernels/cuda/inkling2/attention.cu:126`）：global chunk 的 key 按 kSub 子块折叠，split 与不 split 得到相同的位。
   - 0009 的 `slideTile` 复现 decode 的 partial 与合并舍入，用 `TF_INKLING2_SLIDE_CHECK` 核对。
   - 0011 的 `attn_db` 声明 same bits（`0011-mini-attention-prefetch.patch:166, 224`）。
5. **conv**（`UP/zig/kernels/cuda/inkling2/ops.cu:383`）：每行由前三个输入重算，same bits。
6. **编译选项**（`UP/zig/build/cuda_kernels.zig`）：
   - inkling2_ops / rows / loop 用 `glue` 选项：`--fmad=false --ftz=false --prec-div=true --prec-sqrt=true`。
   - 专家、qmmf、attention 只用 `-O3`，靠 decode 与 prompt 共用同一段代码保证收缩一致。
7. **重写前后逐位相同**：0005 的 tiled gates（`0005-mini-speed.patch:382`）、pass messages（:884–889）、0008 的 `lazy_exact`、0013 的 ZCAP grid-stride（partial 不依赖 grid 大小）都声明与原实现逐位相同。
8. **采样**：0006 的 `tf_ink2m_vocab8_n` 让草稿的 logit 使用“the very noise the target's”同一份 keyed 噪声（`0006-mini-drafts.patch:122–124`），所以采样时有无草稿输出相同。

### 3.3 Astral 的差距

- 【事实】在 sm_89 上，T = 1 的 Q8_0 走 int8 MMA：`astral_gemv_q8_0_multi_mma`（`FORK/crates/kernels-src/cu/gemv.cu:442`），4 个 warp 各算 1/4 的 K，在 smem 里求和。T = 2–8 走 dp4a 的 `q8_multi_t<T>`（:381, :512），fork 提交 `aa837c7`（`LAB/docs/07_tasks.md:115`）。两条路径都把 x 按每 32 个元素量化为 int8，块内整数点积是精确的，但 fp32 的累加顺序不同。
- 【事实】T20 的结果：verify 行在批长度 2/4/8 下逐位相同，但与图化的 decode 不同；V8 在分歧位置的最大 logit 差为 0.61（`07_tasks.md:123`）。K2 记录了 T=1 改成 dp4a 能快 9.4%，但 T20 B 组 decode 的 num-3 FAIL，原因是 decode 与 prefill 的差异超限，所以撤回了（`LAB/docs/04_astral_fork.md` K2 行）。
- 【推断】`multi_t<T>` 每个 token 的算术与 T 无关，这能解释 2/4/8 之间逐位相同；T=1 用的是 MMA，是 decode ≠ verify 的头号嫌疑。以下原因还没有排除：
  - NVFP4 专家在 decode 和多行时用的是不同 kernel；
  - controller 在 decode 走 `gemv_f32`，多行走 `sgemm_tn`；
  - 注意力的 split 参数。
- 【事实】prefill 用 f16 激活（`mma3`，见 `04_astral_fork.md:29, 38`），decode 用 int8 激活，所以两者按设计就不一致。split-K 改为工作区按 slice 顺序相加后（fork `35de94a`，`05_validation.md:129`），prefill 可复现，但仍不等于 decode。

### 3.4 建议路线【推断】

1. **定位**：用 T15 的 `astral trace`，在同一位置分别跑 decode 步和 verify 第 0 行，逐算子比较位，找到第一个不同的算子。这不需要写新 kernel。
2. **Q8_0**：T = 1–8 共用一个 fragment-major kernel（排序表第 2 项）。`m16n8k32` 的 n = 8 一列对应一个 token；只要每列的 K 序和 smem 归约顺序固定，各 token 的结果就与 T 无关。这同时解决 K2 的取舍：不必在 MMA 与 dp4a 之间二选一。
3. **注意力**：`astral_ink_attn_split`（`FORK/crates/kernels-src/cu/inkling.cu:945`）中，split sp 取 chunk sp、sp + gridDim.y、…，所以 partial 依赖 gridDim.y = max_splits。K4 调整 split 数时，要改成 TensorFold 的 ZCAP 写法：chunk 到 partial 的映射只由长度决定，合并顺序固定。
4. **prefill 与 decode**：同一公式在两个 kernel 里可能收缩成不同的 FMA。改为共用 device 函数，或显式写 `__fmul_rn / __fadd_rn`。GEMM 方面，把预填改为 int8 激活（排序表第 4 项），会让预填与 decode 用同一种量化。这正好是 K2 撤回的原因（decode 与 prefill 差异超限）的根治方向。
5. **回归**：照 exact.py 做三路 SHA（DSpark / `ASTRAL_NO_DRAFT` 类开关 / 不同 k），作为 G2 门的一部分。

## 4 Q3：FP8 KV、FP8 投影与 FP8 K/V 异步暂存

### 4.1 0003 FP8 KV 格式【事实】

`TF/patches/0003-mini-kv-cache-fp8.patch`：

- 格式：K、V 每行先舍入为 bf16，再除以 scale 存为 e4m3 码。每个 (key head, slot) 一个 fp32 scale，等于该 128 维行的 amax/448（:47, :76）。每个位置的字节数 = kvw + 4 × kv heads（:482）。
- 量化发生在 prep：K 在 clip 之后、V 在 RMS 之后。
- 反量化：`deq8`（:25, :212）把码乘以 scale 转成 bf16，然后走 bf16 MMA。
- 48 个 visit（包括 SWA 环）都量化；snapshot 也保存 scale。
- 质量证据只有 `TF/tools/needle.py`，仓库里没有 KL 测试。【自报】README:15、:99：默认 256K 上下文配 fp8 KV，每 64K token 约 1.15 GiB。

### 4.2 sm_89 上的做法【事实 + 推断】

- 【事实】`UP/zig/kernels/cuda/common/fp_pairs.cuh:7–15`：原生 `cvt.rn.bf16x2.e4m3x2` 需要 PTX ISA 9.2 和 sm_120 家族。软件解码 `fp8pair`（:35–40）用 `fma.rn.bf16x2`，sm_80 起可用。
- 【推断】Astral 的 KV 本来就是 f16，用 `cvt.rn.f16x2.e4m3x2` 就够了（Ada 起原生支持，对应 `__nv_cvt_fp8x2_to_halfraw2`）。
- decode（`inkling.cu:945–1040`）：
  - 每个 lane 现在读 8 B（4 个 f16 维），改为读 4 B 的 e4m3。
  - 每个 key 另读一个 fp32 scale（warp 内广播）。
  - 点积完成、shuffle 归约之后再乘 k_scale；V 的 scale 乘进 p 后再 fmaf。
  - 这几处改动在 kernel 内部，可以保持现有的 GK=4 交错读取。
- prefill：e4m3 先解码到 smem 的 f16 tile，再复用现有的 f16 MMA。
- Inkling 有利于 FP8 的特点：V 来自 short conv，经过没有可学习 gain 的 per-head RMSNorm（`LAB/docs/06_loop_research.md` §4 已记录）；K 经过 clip。值域有界，per-token amax scale 很合适。但仍需先实测存储后的范数分布（06 §4 的要求）。

### 4.3 收益估计【推断】

- 依据：decode 在 1K 时约 140 tok/s，128K 时 73.7 tok/s（`07_tasks.md:35, :116`），每 token 多出约 6.4 ms。128K 时每 token 读全局 KV 8 visit × 131072 × 8 head × 128 × 2 (K, V) × 2 B = 4.29 GB，有效带宽约 670 GB/s。
- 128K decode：FP8 读量减半，scale 只加 1.6%，可省约 3.1 ms，到约 95–105 tok/s。
- 64K decode：97.4 到约 115–120 tok/s。
- DSpark：77K–106K 时为 104–122 tok/s，预计提升比例相近。
- 容量：全局 KV 从 32 KB/token 降到约 16.5 KB/token，128K 时省约 2 GiB。最大上下文约 1.6–2 倍，但其他工作区也随上下文增长，需要按 T17 的方式实测。
- SWA 环：每 token 168 MB，FP8 后省约 84 MB，短上下文下约 2%。

### 4.4 FP8 投影（0012 / 0022 / 0025）【事实 + 推断】

- 【事实】三个 patch 的内容：
  - 0012（`0012-mini-attention-fp8-optin.patch:9`）：注意力投影存一份 per-tensor FP8 副本，有损，可选开启。
  - 0022（:46, :146）：prompt 行的激活按行量化为 e4m3，与 per-tensor FP8 权重相乘（`tf_ck8_128_row`），有损。
  - 0025：prompt 投影用 128×128、8 warp、3 级的 FP8 权重 + BF16 MMA，依赖 `cp.async.bulk` 和 mbarrier。【自报】prefill +2.0–2.6%。
- 【事实】README:126–128 显示前两项默认开启。
- 【推断】对 Astral decode 没有价值。Q8_0 是 8.5 bit 每权重、每 32 个元素一个 scale；FP8 per-tensor 只省 6%，精度更差。瓶颈是 kernel 只到约 540 GB/s 的有效带宽，不是存储格式。
- 【推断】对 Astral prefill：
  - sm_89 的 FP8 MMA（`m16n8k32 e4m3`，f32 累加，`UP/zig/kernels/cuda/mma4.cuh:32–43`，限 `__CUDA_ARCH__ >= 890`）峰值 330 TF，是 f16 的 2 倍。
  - 但 Q8_0 转 e4m3 有损（int8 有 7 位幅值，e4m3 只有 3 位尾数）。不如直接用 INT8 MMA 算 Q8_0（660 TOPS）。
  - 所以 **K7（Q8_0 → FP8）在 4090 上基本没有理由做**：decode 受带宽限制；prefill 用 INT8 更合适。
- 【事实】ck_lane 的 cluster 路径低于 sm_90 时直接 `__trap`（`ck_lane.cu:114–116`），0025 的 `cp.async.bulk` 也不能用于 sm_89。替代做法是 16 B `cp.async` 多级流水，Astral 的 `mma3` 已经是 3 级（`gemv.cu:984–1081`）。

### 4.5 0023 FP8 K/V 异步暂存【事实 + 推断】

- 【事实】作用于 prompt 侧注意力（读带 FP8 KV 的前缀）：
  - 原始 fp8 码用 3 级 cp.async 暂存，每级 16 KB（`0023-*.patch:69`）；
  - 在 smem 里用 `deq8_fast` 成对原生解码（:43, :112–113）；
  - 同时裁掉 global 的 grid.z（:5, :327）。
- 【事实】0011:237：在 decode 侧，先预取码再解码测得更慢，所以 fp8 decode 保持同步读取。
- 【推断】在 sm_89 上，cp.async 可用，bf16x2 原生解码不可用，但 f16x2 原生解码可用。预填注意力接 FP8 KV 时照搬 3 级暂存；decode 维持寄存器直读。

## 5 Q4：内核优化逐项与 Astral 对照

| patch | 做什么【事实】 | 无损 | Astral 现状【事实】 | 价值【推断】 |
|---|---|---|---|---|
| 0005 | tiled loop gate（`gate_prep` / `gate_down_rows` kDR=8 / `gate_lin_rows` kLR=64），与原实现逐位相同（:382）；`loop_mix_layers` 一次 launch 多层；`rel_table` 16 B load；`msg_all` 每遍只构造一次消息（默认开，:884–889）；PDL <1% 所以关（:836）；mix narrow 更慢，38 vs 27 µs（:964） | 是 | 消息构造与 T24 对应；controller 走 `ctrl_t` / `sgemm_tn` | pass messages 是 T24 的旁证；tiled gate 只影响 prefill 和 verify，收益小 |
| 0007 | decode NVFP4 专家拆成 2 warp 的 half_body。【自报】GB10 上 gate-up 121→113 µs，down 无收益（:133） | 是 | 专家占 decode 26.5%（T16） | 对应 K1；按比例估算 decode 约 +1% |
| 0009 | `tf_ink2_route`（:12，0010 删除）；n > 1 行时 6 个投影合成一个 GEMM（`split_cols`，:78, :528）；`slideTile` 把滑窗 prompt 注意力、sink 和 gate 融成一个 launch（:326） | 是 | `astral_ink_router_fused`（`inkling.cu:459`）已有；输入投影已融合；预填注意力是单独的 kernel | slideTile 思路可用于预填（第 4 项） |
| 0011 | `tf_ink2_attn_db`：bf16 KV 的 decode 注意力用 cp.async 双缓冲，same bits（:166, :224）；fp8 KV 保持同步读（:237） | 是 | `attn_split` 用寄存器直读，4 个 key 交错（`inkling.cu:945` 起）；预填 `attn_prefill` 在 commit 后立刻 `cp_async_wait<0>`（`inkling.cu:1512`），没有流水 | 预填值得做多级流水；decode 侧值得在长上下文做一次 A/B。对方没给 0011 的收益数字 |
| 0021 | gate-up 的 SwiGLU epilogue 直接量化成 NVFP4 / MXFP8 给 down 用（`_tc_qq`，:100, :216） | 对方有损（prefill TC 路径）；在 Astral 中等价于 Q8 量化，无损 | 独立的 `situ_q8`，占 2K 预填 kernel 时间 2.7%（`LAB/tools/t16/results/before/pf2048_cuda_gpu_kern_sum.csv`） | 小；与 K3 / K8 同类 |
| 0024 | expert 解包改用原生 e2m1x2 / e4m3x2。【自报】+0.15–0.65% | 是 | Astral 用位构造解码到 f16，已经很便宜 | sm_89 不可用，也不需要 |
| 0027 | 把 K/V 的 4 tap conv（静态与动态）融进 prep，并记录 rollback 用的 hist。【自报】每轮少 96 次 launch，plain1 42.2→42.6 tok/s（+0.95%，commit :9） | 是 | `astral_ink_attn_prep`（`inkling.cu:621–700`）已融合 conv | 已有 |
| 0028 | prompt 的 gate_prep 融进 `gate_down_rows`（:98, :153）；`ck8_128_row_split` 直接写多个平面 | 是 | — | 只影响预填，收益小 |
| 0012 / 0022 / 0025 | 见 §4.4 | 有损 / 有损 / 有损 | — | decode 无价值；预填用 INT8 代替 |

## 6 Q5：0013 / 0014 / 0001 / 0002 / 0006

- **0013**：
  - 【事实】`prompt_rows` 从 512 提到 4096（`0013-mini-rtx6000-sm120.patch:23`）。
  - 【事实】64 项宽图缓存（:37），key 为 (rows, streams, n_tiles, hist_on, lazy, taps_on)，轮转淘汰。环大小 `ringFor = alignForward(window + rows − 1, 64)`（`UP/zig/src/families/inkling2/kernels.zig:53–55`），与 Astral T17 的“SWA 环 3072 行 = tmax 2048 + window”是同一思路。
  - 【推断】chunk 改为 4096 时，SWA 环要 5120 行：40 visit × 5120 × 4 KB = 839 MB，比现在多 336 MB（f16），FP8 KV 下减半。换来的是更大的 GEMM M 维和更少的 launch，价值中等。宽图缓存对单流的 Astral 没有意义。
- **0014 W4A4 预填**：
  - 【事实】`tf_nvfp4_quant_x` 与 `tf_mxfp8_quant_x` 把激活预量化；GEMM 走 `kind::mxf4nvf4`（`mma4.cuh:16–30`，限 sm_120a / 121a）和 `kind::mxf8f6f4`（`0014-*.patch:27`）。只用于 prefill，有损，默认开（README:127）。
  - 【推断】sm_89 上的替代：
    - ① **W4A8 INT8**：e2m1 × 2 ∈ {0, ±1, ±2, ±3, ±4, ±6, ±8, ±12}，可以精确表示为 int8。每 16 个 K 做一次 `m16n8k16 s8`，然后乘 scale。
      - Astral 已有这条路径（`gemm_nvfp4_mma2`，`gemv.cu:648–662, 967`），后来因 int8 激活误差改走 f16 的 `mma3`（见 mma3 的注释）。
      - 我推断 mma2 不快是因为 epilogue 受 I2F 限制：每个 m16n8k16 每线程要 4 次 I2F 和 4 次 FFMA，而 sm_89 的 I2F 只有约 16/clk/SM，相对张量核大约慢 4 倍。
      - 改法：用 0x4B400000 magic number 做 int→float。|acc| ≤ 16 × 127 × 12 = 24384 < 2²²，结果精确，只需整数加和浮点加各一次。
    - ② **Q8_0 层**（注意力投影、20–23 层的专家）：`m16n8k32 s8` 每 32 个 K 做一次 epilogue，压力减半。decode 本来就是 int8 激活，所以这条路让预填与 decode 用同一种量化。
    - ③ **FP8 W4A8**：e2m1 能精确转成 e4m3，但 per-16 的 scale 与 k32 粒度对不上，需要拆开或接受额外误差，不如 ①。INT4 MMA 存不下 12（范围 −8..7），不可行。
  - 【推断】收益依据：2K 预填中，`nvfp4_mma3` 占 kernel 时间 45.5%、`q8_0_mma3` 占 17.2%（pf2048 csv:2–3）。由 44 visit × 2048 token × 2 × 8 expert × 3 × 2304 × 1152 / 172 ms 算得约 67 TFLOPS，为 f16 峰值 165 的 40%。GEMM 到 2 倍时，2K 预填约 +45%。
- **0001**：
  - 【事实】`tf_ink2m_conv_backup`（`0001-*.patch:78`）与 `tf_ink2m_tap`（:62）。宽 verify 前备份 conv 状态，记录每行输入的 hist，按接受的前缀回退（:520–624）。
  - 【事实】Astral 有 `hist_offsets`（`FORK/crates/model/src/dspark.rs:774`）和 `conv_commit`，已经具备。
- **0002 / 0006**：
  - 【事实】DSpark drafter：3 层，block 8，Markov head rank 256（`0002-*.patch:264`）。0006 加了 FP8 draft head 与 phi、`vocab8_n` 的 keyed race，以及按宽度的 shared / lone 成本表（`0006-*.patch:162–176`）。【自报】GB10 lone：宽度 1 为 30.1 ms、4 为 44.9 ms、8 为 58.7 ms。
  - 【推断】这相当于每多一行约 +12% 的单步时间，与 Astral T21 的 8.3 + 0.96k ms（每行约为单步 7 ms 的 13%）几乎相同。说明 MoE 宽 verify 的成本结构两边一致，T21 的成本模型不需要改。
  - Astral 的草稿已经是 Q8_0 + F16 草稿 KV（G2），FP4 head 测试没有收益，所以 FP8 草稿层没有新价值。多流共享轮的规划器对单流无用。keyed race 是唯一的新东西（排序表第 6 项）。

## 7 Q6：性能数字中哪些是硬件差距、哪些是软件差距

| 项 | RTX 4090 | RTX PRO 6000（工作站版） |
|---|---|---|
| SM / L2 | 128 / 72 MB | 188 / 128 MB（网络搜索，Tom's Hardware，未逐项核实） |
| 带宽 | 1008 GB/s | 1792 GB/s（比值 1.78） |
| 张量核（dense） | f16（f32 累加）165、FP8（f32 累加）330、INT8 660 | FP4 约 2 PF、FP8 / FP16 约 1 PF（第三方数据，dense / sparse 口径不一，未核实） |

**decode**：

- 【自报】PRO 6000 + DFlash2 230.1 tok/s（README:38，采样）；300 W DSpark 的 prose 150.7 tok/s、code 231.1 tok/s（README:40）。
- 【推断】按带宽比折算到 4090：DFlash2 约 129、DSpark prose 约 85、code 约 130 tok/s。
- 【事实】Astral 的 DSpark 为 206 tok/s（贪心，T16 第 2 轮），无草稿约 142 tok/s。
- 【推断】采样和贪心的接受率不能直接比，但按带宽归一后，Astral 的 decode 效率不低于 TensorFold。两边每 token 读的字节相近（约 3.9–4.3 GB），差距**全部来自带宽这个硬件因素**。
- 4090 上的软件余量就是 142 tok/s 与约 254 tok/s 地板之间的差：注意力输入投影只有 540 GB/s（25.8%）、小 kernel 约 22%、间隙约 11%（T16）。

**prefill**：

- 【自报】128K 时 300 W 9,133 tok/s、600 W 15,198 tok/s，开 `ATTN_FP8_TC`（README:23–32）。
- 【事实】Astral 128K 预填 31.8 s，即 4,122 tok/s（`07_tasks.md:112`）。差 2.2 倍（300 W）或 3.7 倍（600 W）。
- 【推断】一次 128K 预填约 2.05 PFLOP：线性部分 8.7 GFLOP/token × 131072 ≈ 1.14 P；全局注意力 8 visit × 48·L²·d ≈ 0.85 P；SWA 约 0.07 P。
  - 折算算力：Astral 约 64 TFLOPS（f16 峰值的 39%），对方 300 W 约 143 TFLOPS、600 W 约 238 TFLOPS。
  - 对方在 300 W 下只用到 FP4 峰值的一小部分，128K 时主要受 bf16 注意力限制。
  - 硬件算力比在 3 倍（f16 对 bf16）到 12 倍（FP4）之间，实测差距 2.2–3.7 倍小于这个比值，所以**主要是硬件差距**。
  - 4090 的软件余量有三处：GEMM 只到 f16 峰值的 40%；INT8 峰值是 f16 的 4 倍；预填注意力没有流水。
- 下一步：用 nsys 测 32K 和 128K 预填的 kernel 占比，再决定先做 INT8 GEMM 还是注意力流水。

## 8 本地文件

- `/root/github/inkling-research/repos/Inkling-2-Mini-RTX-5090-TensorFold`：1.5 MB，release 仓库，已全部读完。
- `/root/github/inkling-research/repos/TensorFold-dc2ca8a-files`：352 KB，上游单文件，包括：
  - qmmf.md、cuda_kernels.zig、mma4.cuh、fp_pairs.cuh、ck_lane.cu、qmm_frag.cuh；
  - attention.cu、prompt_attention.cu、nvfp4_experts.cu、ops.cu、loop.cu；
  - mini_*.zig、kernels.zig 等。
  上游仓库没有 clone。`flashnext-draft-head/exactness.md` 已下载但没有细读。
- 本次没有编译、没有安装任何东西、没有运行重负载脚本。
