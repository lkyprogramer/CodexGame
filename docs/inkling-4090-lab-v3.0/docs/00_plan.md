# 00 · 总计划

## 1. 第一性原理：为什么是单模型自有引擎

| 事实 | 数值 | 含义 |
|---|---|---|
| 每 token 读取的权重 | ≈3 GB（约 3.1B 不同权重 × ~4.5 bpw；核心层权重每 token 读 3 遍但 L2 放不下） | 4090 带宽约 1008 GB/s，**带宽上限约 330 tok/s** |
| 每 token 算子数 | 48 个层访问 × 每层约 15 类小算子；llama.cpp mainline 每 token 约 5745 次 kernel launch | 实际是 **launch / 同步受限**，不是带宽受限 |
| 4090 上的已报数字 | llama.cpp mainline ≈51；Xolotl 113–127（DSpark 136）；atlas-ingine 236.7 tok/s | 同一硬件上，专用引擎比通用框架快 2–4.6 倍（均为作者报告，未在本机复测） |
| Astral 在 H100 PCIe | 172 tok/s（无草稿），vLLM 130.2，SGLang 135.6 | 作者已在专用引擎上验证过融合 + CUDA graph 路线 |
| 状态量 | 全局 KV 每 token 32 KiB（8 个全局 slot，f16）；SWA 每个 slot 固定 4 MiB；conv 状态 < 4 MiB | 长上下文主要受全局 KV 限制，**不需要专家流式**（PCIe Gen3 x16 实测约 8 GB/s，流式没有价值） |

结论：把一个模型的整条前向写成少量融合 kernel，并用 CUDA graph 回放，就能拿到大部分收益。这正是 Astral 的结构；Rust 主机侧还让“改循环、加探针、换调度”成为普通的代码修改，而不是去改大框架的图构建器。

## 2. 阶段与门槛

| 阶段 | 内容 | 停服 | 门槛（全部满足才进下一阶段） |
|---|---|---|---|
| P0 准备 | 驱动基线、用户目录工具链、资产下载、Astral 和 llama.cpp 构建 | 否 | G0：驱动指纹未变；`astral version` 显示 `kernels built for: ["89"]`；全部资产 SHA256 与 [01](01_model.md) §4 一致；CPU 侧 `cargo test` 通过 |
| P1 首次上卡 | hw/selftest，GGUF 解析，逐算子比对，贪心生成 | W1 ≈60 min | G1：selftest 全部 PASS；`verify-model` 对 llama.cpp 的 eval-callback 日志 PASS；贪心前 32 token 与 llama.cpp 一致 |
| P2 数值对齐 | 噪声底、KLD、top-1、teacher-forced、投机等价 | W2 ≈90 min | G2：[05](05_validation.md) §3 冻结阈值全部满足 |
| P3 移植与性能 | Sm89 档案、观测钩子、4090 调优、DSpark | 若干次 W ≤90 min | G3：无草稿 decode ≥ 同 GGUF 下 llama.cpp 的 1.5 倍，且每次优化后 G2 不回退 |
| P4 长上下文 | 解除 8192 上限：SWA 环形缓冲 + 全局 KV 分块注意力 | 若干次 W | G4：32K 下 G2 指标不回退；64K、128K 的显存实测与 [01](01_model.md) §3 的预算偏差在 10% 以内 |
| P5 循环研究 | [06](06_loop_research.md) R1–R7 | 按实验 | 每项研究交付数据 + 结论；不设速度门槛 |

P3 的速度目标：llama.cpp ×1.5 是必须达到的；120 tok/s（Xolotl 水平）是期望值；atlas-ingine 的 236.7 只作参考上界。G3 不通过不影响 P5：研究只需要 G2 级别的正确性。

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
