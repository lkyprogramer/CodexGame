# 版本变更

## v3.0.12 · 2026-11-26

T15 完成：fork `2c2f424` 的 `astral trace` 只读探针（schema 见 fork `docs/trace.md`）；探针关、探针开、eager 三者逐位一致，decode 速度不变，主机重算与 GPU 输出对账误差 ≤ 1.1e-6。记录见 [07](docs/07_tasks.md)；[06](docs/06_loop_research.md) §3 注明实现范围。

## v3.0.11 · 2026-11-26

T20 完成（[07](docs/07_tasks.md)）：fork `18bf3e3` 新增 decode 路径与 DSpark verify 行的 logits 导出；保留集 B 上 prefill、decode、verify 2 / 4 / 8 行按 num-3 全部通过；自由生成首个分歧都在近平局处；c4096 密集 KLD 按 V4 公式通过。长文档 64 个边界位置按 num-3 FAIL，原因是双峰分岔位置（llama 自身也有），[05](docs/05_validation.md) §5 覆盖表、§6.6；长上下文判定口径的建议待用户决定。

## v3.0.10 · 2026-11-26

T19 完成并改判 PASS：修复后 Astral prefill / step 两次运行 208 个文件逐位相同；V7 按 num-3 在保留集 C（80 个位置）上通过，Astral prefill 对 step 的差异是 llama.cpp 自身 ub512 对逐 token 差异的 0.36–0.87 倍；`verify-model` 与 128 token 贪心输出不变。G2 解除“有条件”。结果在 `tools/t19/results_c/`。

## v3.0.9 · 2026-11-26

查清并修复 Astral prefill 的运行间不确定性（两条 split-K 路径的 float `atomicAdd`；fork `35de94a` 改为分片写工作区、按固定顺序归约，16 token prefill +2.5%，更长无差别），[05](docs/05_validation.md) §6.5。用户采用 V7 的 num-3（同位置配对比值，概率加权的窗口差），fork `f8c976e` 实现 `judge-paired`；新增保留集 C（`tools/t19/prompts_set_c.json`），在其结果出来之前冻结。

## v3.0.8 · 2026-11-26

执行 T19。fork 新增 `astral dump-final-logits`、`bench/llamacpp_compare/final_logits.cpp`、`logit_compare.py`（含离线测试，`a8ca269`）；本包新增 `tools/t19/`（manifest、导出、判定脚本、冻结的规则与小体量结果）。按先冻结规则（`92f4c40`）再看候选的顺序，V7 num-2 在 A、B 两组都判 FAIL；分析表明失败来自规则的两个缺陷（窗口 max 被极小概率 token 主导；绝对限值不能跨位置分布迁移），同位置上 Astral 的 prefill / step 差异与 llama.cpp 自身的 ub512 / 逐 token 差异同量级。num-3 提案写在 [05](docs/05_validation.md) §6.4，待用户决定。另发现 Astral prefill 路径两次运行之间不逐位一致（§6.5），[06](docs/06_loop_research.md) 的逐位一致要求限定在 step 路径。

## v3.0.7 · 2026-11-26

逐条核实用户提交的研究评审（仓库 `docs/Inkling-4090-Lab-v3-Research-Review-2026-11-26.md`，[09](docs/09_sources.md) S31）后修订文档。Astral 源码相关结论对照 fork 源码核实，外部来源 13 条按固定 commit 抓原文核对（9 条属实，4 条部分属实，按原文修正了表述）。

- **验证（[05](docs/05_validation.md) §5–§7）**：V7 在 v3.0.4 复判时两侧不是同一统计量（原始 logit 对 u16 log-prob、窗口与 KL 定义不同、16 个末位对 2040 个位置），T12 的 V7 降为“有条件通过，待 T19 复核”；写明各项 PASS 的实际覆盖范围；起草统一数值口径 num-2、三类噪声对照、阈值校准规则和 `run.json` 记录格式。已批准的阈值不变。评审 §3.5 的前提（缺少生成提示）来自 T13 初稿的误记，已不成立，不需要因模板问题重跑。
- **任务（[07](docs/07_tasks.md)）**：T04 关闭为 PASS；新增 T19（口径复判）、T20（覆盖补测）、T21（DSpark 成本模型）；T15–T18 按评审 RV-03 / 05 / 06 / 07 重写交付物；研究依赖拆开（R4 不再等 T17）。
- **代码地图（[04](docs/04_astral_fork.md)）**：默认解码注意力是已有的 split-K online softmax，`logit[MAX_CTX]` 只在 simple 路径；8192 上限分散在四处；WP-D 改为四段并补上 SWA 环形缓冲的同批覆盖问题与边界用例；新增调优候选 K1–K7；fork 已公开。
- **研究（[06](docs/06_loop_research.md)）**：重写 R1–R7（坐标与状态约定、tanh 门、三种读出、R4 三臂按原文核实），新增 R8（量化误差经循环传播）、R9（历史深度与当前深度）、R10（局部稳定性，可选），KV 压缩降为局部实验。
- **其他**：[00](docs/00_plan.md) 的 330 tok/s 带宽上限与 launch-bound 改为待测假设（原算式不自洽）；[01](docs/01_model.md) 补 varloop 的 1:2:6:2:1 训练方式、随遍数变化的状态预算；[03](docs/03_engine_landscape.md) 补齐外部数字的条件、重新定位 v2 删除的参考项目；[09](docs/09_sources.md) 固定 S21，新增 S25–S31；[08](docs/08_runbooks.md) 标明命令模板与已执行脚本的区别；[VALIDATION](VALIDATION.md) 标为历史记录；`tools/check_package.py` 支持 R1–R10 和合并的研究行。

## v3.0.6 · 2026-11-26

Astral fork 拆成独立公开仓库 [lkyprogramer/inkling-4090-engine](https://github.com/lkyprogramer/inkling-4090-engine)：删除 `patches/astral/`，通用分析脚本迁到 fork 的 `bench/llamacpp_compare/`（新旧名对照见 [08](docs/08_runbooks.md) §9）。按评审（`docs/Inkling-4090-Lab-v3-Research-Review-2026-11-26.md` §4.1）核实源码后，更正 [04](docs/04_astral_fork.md)：Inkling 的预填走 `mma3`，不是 `mma5`。

## v3.0.5 · 2026-11-26

T14 性能基线完成，G3 通过：Astral 无草稿 143.1 tok/s，是同一 GGUF 下 llama.cpp 的 1.92 倍。脚本在 `tools/t14/`。另外更正 T13 记录：prompt 格式本来就对（Inkling 模板没有生成提示，模型自己输出 `<|message_model|>`），初稿把接受率低归因于缺少生成提示，是误判。

## v3.0.4 · 2026-11-26

经用户同意修订 V7 阈值（[05](docs/05_validation.md) §3）：由“全词表最大绝对差 ≤ 1.0 logit”改为相对 llama.cpp 自身噪声底的判定（概率窗口内最大差 ≤ N0_near_p99，KL ≤ N0_p99）。依据是 T12 的实测：llama.cpp 自身批量对逐 token 时，19.4% 的位置超过 1.0。按新阈值，T12 复判为 PASS。

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
