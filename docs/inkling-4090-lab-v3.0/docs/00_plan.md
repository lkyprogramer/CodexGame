# 00 · 总计划

## 1. 第一性原理：为什么是单模型自有引擎

| 事实 | 数值 | 含义 |
|---|---|---|
| 每 token 读取的权重 | **待测**。3.1B 权重 × 4.5 bpw 本身只有约 1.74 GB；实际字节数还取决于三遍回访、NVFP4 / Q8_0 混合、top-8 专家路由、LM head、KV、工作区和缓存复用。v3.0 写的“≈3 GB → 带宽上限约 330 tok/s”算术上不自洽（v3.0.7 按评审更正） | 只有在实测每 token 恰好读 3.0 GB DRAM、且达到 1008 GB/s 时，才得到约 336 tok/s 的理想上限；尚未由本机 profile 证实 |
| 每 token 算子数 | 48 个层访问 × 每层约 15 类小算子；llama.cpp mainline 每 token 约 5.7k 次 kernel launch（#33060 的说明） | **假设**：短上下文下存在融合与 launch 调度的优化空间；长上下文可能转为 KV 带宽受限。5.7k 是 llama.cpp 的实现特性，CUDA graph 的节点数也不等于 CPU 端 enqueue 次数，需要对 Astral 分阶段实测（T16） |
| 4090 上的已报数字 | llama.cpp mainline ≈51；Xolotl 自有 14 GB XQ 权重 113–127（DSpark 136），NVFP4 parent 89（DSpark 137）；atlas-ingine 236.7 tok/s（自有 atlas-12g 权重、FP8 dense / KV、**开推测解码**）；**4090 实测（T14）**：Astral 143.1，同 GGUF 下 llama.cpp 74.7 | 外部数字的权重、精度和是否投机都不同，不能当成统一的上界（[03](03_engine_landscape.md)） |
| Astral 在 H100 PCIe | 172 tok/s（无草稿），vLLM 130.2，SGLang 135.6 | 作者已在专用引擎上验证过融合 + CUDA graph 路线 |
| 状态量 | 全局 KV 每 token 32 KiB（8 个全局 slot，f16）；SWA 每个 slot 固定 4 MiB；conv 状态 < 4 MiB | 长上下文主要受全局 KV 限制，**不需要专家流式**（PCIe Gen3 x16 实测约 8 GB/s，流式没有价值） |

结论：把一个模型的整条前向写成少量融合 kernel，并用 CUDA graph 回放，能拿到大部分收益（T14 已证实对 llama.cpp 有 1.92 倍；剩余瓶颈在哪里要等 T16 的分阶段测量）。这正是 Astral 的结构；Rust 主机侧还让“改循环、加探针、换调度”成为普通的代码修改，而不是去改大框架的图构建器。

## 2. 阶段与门槛

| 阶段 | 内容 | 停服 | 门槛（全部满足才进下一阶段） |
|---|---|---|---|
| P0 准备 | 驱动基线、用户目录工具链、资产下载、Astral 和 llama.cpp 构建 | 否 | G0：驱动指纹未变；`astral version` 显示 `kernels built for: ["89"]`；全部资产 SHA256 与 [01](01_model.md) §4 一致；CPU 侧 `cargo test` 通过 |
| P1 首次上卡 | hw/selftest，GGUF 解析，逐算子比对，贪心生成 | W1 ≈60 min | G1：selftest 全部 PASS；`verify-model` 对 llama.cpp 的 eval-callback 日志 PASS；贪心前 32 token 与 llama.cpp 一致 |
| P2 数值对齐 | 噪声底、KLD、top-1、teacher-forced、投机等价；T19 统一口径复判、T20 覆盖补测 | W2 ≈90 min | G2：[05](05_validation.md) §3 冻结阈值全部满足（v3.0.7：V7 待 T19 按统一口径复核，见 [05](05_validation.md) §5.2） |
| P3 移植与性能 | Sm89 档案、观测钩子、4090 调优、DSpark | 若干次 W ≤90 min | G3：无草稿 decode ≥ 同 GGUF 下 llama.cpp 的 1.5 倍，且每次优化后 G2 不回退 |
| P4 长上下文 | 解除 8192 上限：SWA 环形缓冲 + 全局 KV 分块注意力 | 若干次 W | G4：32K 下 G2 指标不回退；64K、128K 的显存实测与 [01](01_model.md) §3 的预算偏差在 10% 以内 |
| P5 循环研究 | [06](06_loop_research.md) R1–R10 | 按实验 | 每项研究交付数据 + 结论（支持 / 不支持 / 不确定）；不设速度门槛 |

P3 的速度目标：llama.cpp ×1.5 是必须达到的（T14 已达到 1.92×）；120 tok/s 是期望值（已达到 143）；atlas-ingine 的 236.7 带推测解码且权重不同，只作机制参照，不是无草稿上界。G3 不通过不影响 P5：研究只需要 G2 级别的正确性。

**v3.0.7 的阶段调整（评审 §15.2）**：P3–P5 不再严格串行。T19 / T20 完成后，T15（探针）、T16（调优）、T17（长上下文）、T18（遍数）可以分别准备；R4 的语义实验在 8K 内进行，不等 P4；R1 的深度研究与 128K 研究分开做。同一张 GPU 上的测量仍串行。建议顺序：验证复判 → 固定三遍观测 → 一个机制干预 → 分阶段性能基线，之后由数据决定投入深度、内核、长上下文还是草稿器。

## 3. 停止规则

- 驱动指纹变化，或安装输出涉及驱动：立即停止，通知用户（[AGENTS](../AGENTS.md) 红线）。
- G1 在两个窗口内仍不通过：根因在 sm_89 SASS 层面的，按 [04](04_astral_fork.md) §6 回退到 `ASTRAL_CUDA_ARCHS=80` 的 cubin（sm_80 SASS 可在 8.9 上运行）做二分定位；根因在模型语义的，对照 llama.cpp 逐层输出定位。两条路都走不通就报告用户，候选方案是 tqllm 或 Xolotl。
- 某项 4090 调优两轮 profiler 驱动的尝试后收益 < 3%：标记 `NO_BENEFIT` 结案。
- 任何改动让 G2 回退：先回滚，再分析原因。

## 4. 时间与资源估计（推断，未经实测）

| 项 | 估计 |
|---|---|
| P0 | 0.5–1 天；耗时主要在构建，下载约 1 小时（ModelScope 实测 ~10.9 MB/s） |
| P1+P2 | 2–3 个窗口 |
| P3 | 1–2 周，取决于 sm_89 上 kernel 表现与 A100/H100 的差异 |
| P4 | 1–2 周（新写注意力 kernel） |
| 磁盘 | ≈95 GB，见 [01](01_model.md) §4；根分区剩余 213 GB |
| 主机内存 | 生产运行时只有约 9 GiB 可用：构建限制并发，GPU 任务全部放在窗口内 |
