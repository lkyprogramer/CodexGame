# 版本变更

## v3.0.3 · 2026-11-26

T11–T13 执行完毕。T11 定位并修复了 Astral 的跨 stream 同步缺陷（T07 的 MXFP4 失败由此引起），T07 改判 PASS；T12 的 V4–V6 通过，V7 按冻结阈值判 FAIL，并附上 llama.cpp 自身噪声的对照数据，阈值待用户决定；T13 的 V8 通过。W2 的脚本放在 `tools/w2/`。

## v3.0.2 · 2026-11-26

W1（T07–T10）执行完毕，结果记在 [07](docs/07_tasks.md)：T08、T09、T10 PASS；T07 的 selftest 有 4 项 MXFP4 失败（Qwen 路径，Inkling 不用），定位工作并入 T11。W1 实际使用的脚本放在 `tools/w1/`。

## v3.0.1 · 2026-11-26

P0 执行后的修正：conda-forge 改走清华镜像；包列表补上 `cuda-driver-dev`、`cuda-nvml-dev`（llama.cpp 需要）；Astral fatbin 的路径改为 `target/release/build/astral-kernels-src/*/out/`；[07](docs/07_tasks.md) 记录 T00–T06 的结果。Strata 已按用户指示停止，恢复前 GPU 任务直接执行，不再经过 `lab_window.sh`。

## v3.0 · 2026-11-26（Asia/Shanghai）

全面重写，取代 `docs/atomic-inkling-4090-plan-v2.0`（v2.0/v2.1）。

- **方向变化**：目标从“以 Atomic 为底座的服务候选”改为“自有 Rust 单模型引擎 + 循环研究”。依据是社区调研（[03](docs/03_engine_landscape.md)）：Inkling-2-Mini 的瓶颈是大量小算子而非带宽，专用单模型引擎在 4090 上比通用框架快 2–4 倍；而 Atomic 落后上游且其显存预算/专家流式能力在 24 GB + PCIe3 上用不上。
- **用户决策**：Rust（Astral fork）；用户目录安装 CUDA 12.8；先用量化 GGUF；不动驱动。
- **删除**：Atomic 移植、Ghost、Magnitude、CUDA Rust 形式证明、LoomKV Tier/Pool、2DSD/LoopCD 的服务化路线、148 项计划测试和 44 任务 DAG。其中仍有价值的研究点并入 [06](docs/06_loop_research.md)。
- **保留**：现场事实与停服流程、证据纪律、配对统计工具、上游 llama.cpp 作为参考的结论（v2.1 §43）。
- **新增发现**：Astral 当前上下文硬上限 8192（`MAX_CTX`，注意力 logits 放在共享内存），且 48 个 slot 全部按满容量分配 KV；长上下文是移植的独立工作包（[04](docs/04_astral_fork.md) §5）。
