# 下一步优化方向（2026-11-26）

生产：B2-TS5，即 v0.2.17 + PT0 + B1 参数 + `STRATA_ROUTE_TAIL_SKIP=5`，2026-11-26 上线（[依据](../reports/RESULTS-B2APPROX-XP-SURVEY-20261125.md)）。本文只是方案，任何一步都还没有执行；每一步停机前、上生产前都要用户确认。

## 现状

事实：

- **关键路径在 CPU 专家行上。** 在 resident 专家之后每层加 20 µs，窗口耗时几乎不变（斜率约 −0.05）；在门铃前每层加 20 µs，斜率约 0.56；每层加 8 个空图节点，变化在测量分辨率以下（survey-20261125 的 M 组）。也就是说 GPU 侧有余量，一直在等 CPU，所以 GPU 侧的开关和图结构优化不会有收益，这与 K 组的实测一致。
- **主机：** Xeon Silver 4216，16 核 32 线程，AVX-512 VNNI，单 NUMA 节点，L3 22 MiB，内存 62 GiB。引擎 CPU 池用 16 个线程。同机的 OCR 容器（`onnxocr-ppocrv6-small-cpu-compat`，硬限 4 核）和 Strata 共用这颗 CPU 和内存带宽。
- **测量成了瓶颈。** 2026-11-25 的对照噪声为 3.3–3.4%（11-23 的 ABBA 为 0.6%），+5–6% 的效果分辨不出来。8 次运行因思考预算用满后续写回答（一次请求在引擎日志里记成两条）被判无效，白跑了约 2 小时。
- **上游最新为 v0.2.22**（本地 `/root/github/Strata` 已同步）。0.2.21 和 0.2.22 的发布说明没有提到 Qwen3.8-Flash-Next 在 sm_89 上提速；ECAP（#3545）和 DEFER（#2690）都没有合入。v0.2.20 之后，Qwen 引擎路径（core、kernels/cuda、program、prefill）改了 33 个文件，增删合计约 1.3K 行。
- **sm_89 默认开关表**（`engine/src/core/nv_defaults.cpp`）：显存大于 16 GiB 的卡会自动打开 `STRATA_VERIFY_DEVICE_HITS=1`，这是 v0.2.19 慢 13% 的原因（[V0219 报告](../reports/V0219-UPGRADE-GATE-20261122.md)）；表里还有 `STRATA_ADAPT_LAG=2`。用 `STRATA_SM89_PERF=0` 可以整表关掉。

推断：

- **v0.2.20 慢 9.9% 的主因可能是 #4870 的覆盖率中段曲线**（`engine/include/strata/core/adapt_coverage_rules.hpp`）。从 0.1.66（v0.2.20）起，专家缓存覆盖率在 15%–65% 之间时（我们约 38%），自适应参数默认改成 `--adapt-every 2 --adapt-swaps 192 --adapt-decay 0.92`。11-23 的长上下文回放实测 `--adapt-every 2` 每窗口慢 4.4%（[B2_ADAPT_LONG](B2_ADAPT_LONG_20261123.md)）。v0.2.21 起可以用 `STRATA_ADAPT_MID=0` 关掉它，一键过门的 `--env` 就能传进去，不用再改树里的配置（V0220 报告里记的障碍已经消失）。

## 方案（按建议顺序）

### N1 · 修测量工具（不停机，约半天）

1. `upgrade_gate.py` 的基线改为 rank 5：
   - `TAIL_SKIP = '5'`；
   - KL 的 B2 存档换成 b2-approx-20261124 的 ts5 运行；
   - 任务门的基线臂换成存档的 b2-route_tail_skip5；
   - 补单元测试。
2. 回放的对齐检查要接受"思考预算 12288 用满后的续写"：一个请求对应两条引擎记录，前一条的 prompt 加 generated 与后一条的 prompt 相差不超过 64，两条 generated 之和与该请求的 completion 相差不超过 64。依据是 `/data/strata-data/upgrade-gate/logs/split-check-20261125.json`：8 次无效里有 6 次符合这个模式。不符合的照旧判无效。
3. 回放支持 ABBA×3 的预登记写法和判定：门线 max(2.2%, 2×对照极差)；ms/窗口和 tok/窗口分别报告。
4. 只读分析：用生产监控的请求明细（`/data/strata-data/prod-observe/monitor/data/`，带同机负载）和这几天的回放运行，量化 OCR 的 CPU 占用对 ≥32K decode 的影响。

完成标准：单元测试通过；用 2026-11-25 的原件重算，结论与原判定一致；拿到 OCR 影响的估计和置信范围。

### N2 · v0.2.22 快速测速（停机约 1.5 小时）

- `prepare v0.2.22`（PT0 补丁按 v0220 的移植，补丁打不上时先移植）。
- 设置 `STRATA_VERIFY_DEVICE_HITS=0 STRATA_ADAPT_LAG=1 STRATA_ADAPT_MID=0`：
  - 先跑 `gate --limit 40` 测速；
  - 再跑长上下文回放，ABBA，对照为生产树。
- 判定：
  - 速度与生产持平以内（差异在 N1 的门线内），就把实验基线换到 v0.2.22，再走完整的一键过门（KL 约 2 分钟，任务门约 2 小时），决定是否切换；
  - 仍然更慢，就留在 v0.2.17，同时记录"关掉中段曲线后仍慢多少"。
- 意义：这一步本身不指望提速，换来的是上游修复（#6713、#6776、#6905 等）、`STRATA_ROUTE_TAIL_RENORM`，以及以后移植成本更低。代价是 ECAP/DEFER 要在 v0.2.22 上重新移植。

### N3 · DEFER 与 ECAP 24 复测（叠在 TS5 上）

- 2026-11-25 的结果：
  - D01（`STRATA_VERIFY_DEFER_CPU=1`）+5.1%，ms/窗口 −3.7%；
  - E24（`STRATA_VERIFY_ECAP=24`）+6.3%，ms/窗口 −1.8%；
  - 门线被噪声抬到 6.65%，所以判 NO_GAIN。
- 当时是叠在 rank 7 上测的，这次叠在 TS5 上、用 ABBA×3 复测，再加一臂 D01+E24 的组合。
- 两者都会改变输出：KL 筛选（≤0.10，agent 段 ≤0.25）通过后，每项回放约 1.5 小时；过了第二阶段的再跑 305 题质量门（每项约 2 小时，margin 5%，与精确路由 ts0 比较）。
- 基线跟随 N2 的决定：留在 v0.2.17 就直接用现成的 `v0.2.17-xp` 树；换到 v0.2.22 就要先重新移植。

### N4 · TS4 与尾部重归一化

- TS7 到 TS5 带来约 +5%（TS6 +3.25%），TS5 的质量还有余量（pass@1 262 对 ts0 260，pass@2 292 对 292）。
- 假设：TS4 能再快 2–3%，但质量风险随之上升。`STRATA_ROUTE_TAIL_RENORM=1`（跳过尾部专家后，对保留下来的权重重新归一化）可能减小这部分损失。
- 流程：KL 筛选，TS4 和 TS4+RENORM 各一组，以及 TS5+RENORM；然后回放（ABBA×3）；然后 305 题门。
- RENORM 从 v0.2.19 起才有：N2 决定换到 v0.2.22 就直接可用，否则要移植到 v0.2.17，需要先读源码评估改动量。

### N5 · CPU 专家路径（代码级，不确定性最高）

1. 先做微基准（调研里的 M6）：CPU 专家行的实际吞吐占内存带宽的比例，并扫描池线程数（12/14/16/20）。在生产空闲时进行，单次几分钟。
2. 比例低（算力受限）时，再考虑把上游 hy4 引擎 CPU 专家池的做法移植到 Qwen 引擎：数据流调度（`STRATA_CPUEXP_SCHED`）、跨 4 KiB 页的行预取（`STRATA_CPUEXP_PF`）、L3 预取、按物理核绑核。比例已经接近带宽上限，就关闭这条线。
3. 同机隔离：给 OCR 容器绑定固定 CPU，避开 Strata 池线程所在的物理核。这会改动另一个服务的配置，要用户决定；依据是 N1 第 4 步的结果。

## 已关闭的方向

证据都已入库，不再重复：

- 采样投机：COUPLED、GUMBEL、PROB+top；
- 无损开关：L2_PF、FUSE_WAIT=2、QIL、GRAPH_PRIO；
- QFUSE 和 VERIFY_DEVICE_PLAN：实测不逐位一致；
- megakernel：上游的 `STRATA_MEGAKERNEL` 只有 HIP 版，而且 GPU 侧不在关键路径上；
- 自适应参数、起点 profile、采样温度；
- TS6、DEFER BELOW=1、ECAP 16。

## 预期与资源

- 预期（推断）：N3 和 N4 都成立时，相对当前生产合计约 +5–8%；N5 的收益要等微基准结果才能估；N1 和 N2 不带来提速，但它们决定后续结论是否可信、基线放在哪个版本。
- 停机预算（估计）：N2 约 1.5 小时，加完整过门约 2 小时；N3 约 6–10 小时；N4 约 6–8 小时。都用现有的 chain 脚本放在夜间跑，开始前要用户确认。
- 不变的约束：
  - 不启用 `STRATA_STAGE_PIN` 和 `STRATA_ROUTE_RESIDENT`；
  - 不改驱动和 CUDA 12.3；
  - 只按 PID 结束进程；
  - 失败记录保留；
  - 生产配置和 Pi 配置的改动要用户确认。
