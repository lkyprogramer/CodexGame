# v0.2.7 IQ3_S 单 token AVX2 gather 探针（2026-10-28）

**完成：REGRESSION，扩展门 NOT_MET。** 六对完整专家耗时增加 **33.04%**，配对 95% CI 为 **31.40%～34.61%**。三对单核热 GU 也变慢 **77.96%**。拒绝当前独立 AVX2 gather 候选，停止，不扩格式、不进入整机候选验证。原六项 FAIL 和 P6 正确性门保持；不改生产、不部署。

## 固定范围与身份

通过 `jssh 29` 在独立树 `workspace/trees/gather-probe-20261028` 执行。源码固定 `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`，保留 P6 的六文件 #1536/PT 移植。当前模型、EXACT6、KVRES20480、int8 KV、spec4、15 workers＋host、CPUSHARE4096、AUTOMAX16384、131072 总上下文与 4096 预留均保持；新增数值路径维持关闭。

只替换实际 `ggml_vec_dot_iq3_s_q8_K` AVX2 分支中的两处标量 codebook 向量组装，改用 `_mm256_i32gather_epi32`。整数 `madd + add`、解包、符号、scale、浮点规约、SwiGLU、quant/down 均保持。仅 `gu_type=21 && nt=1 && !tail_off` 进入独立候选；未叠加 P5 VNNI，其他格式与多 token 路径不替换。

- 原 P6 引擎 SHA256：`58ffaf7f67535049baf996dd8793202b2ba4d2d7090569cfcc13019a28269f22`。
- 本轮引擎 SHA256：`67f3e8454522e6f5491479d57c2f960789ba7899b4d57c770d3c942cda96d8dd`。
- 回放二进制 SHA256：`1f4dd50b19b0191a74571761f1dce82d06b892d1bd25a5e18b728a38c4022095`。
- 实际 P6 ggml 依赖为 `llama.cpp-3cf0325`，相关 9 文件与 P5 oracle 一致；`quants.c` SHA256 为 `3c489fdc77e3ab484a5f188bff9c60c0e9483c951ed65c1a562a04c249d5628e`。

见[预登记](../workspace/gather-probe-20261028/PREREGISTRATION.json)、[最终源码](../workspace/gather-probe-20261028/source-final)、[补丁](../workspace/gather-probe-20261028/source-final.patch)。默认关闭的实验开关仅存在于隔离树。

## 当前完整配置覆盖

候选关闭，复用冻结的 `think-4096`、`think-102400` 原请求，两项实际 prompt 为 4095/102400、生成均为 2048、reused 均为 0。扣除 qualification 后，IQ3_S nt1 有 17042 jobs、10906880 rows，占全部 nt1 GU worker 时间 **36.246%**，仍为最大单格式项。实际函数偏移与本轮链接二进制的 `ggml_vec_dot_iq3_s_q8_K` 符号匹配。

| 格式 | nt1 GU worker 时间占比 |
|---|---:|
| IQ3_S | 36.246% |
| IQ2_XS | 19.984% |
| IQ2_S | 16.869% |
| IQ2_XXS | 15.003% |
| IQ3_XXS | 11.898% |

完整格式×nt 计数、请求及实际 oracle 偏移 `10728592` 见[COVERAGE.json](../workspace/gather-probe-20261028/COVERAGE.json)。

实际进程环境核对 P6 冻结开关及 `STRATA_IQ_MT_MIN=2` 默认语义；#1536/PT、KVRES、16384 chunk 生效，auto cache 为 P6 已记录的 10272 slots。两个请求的完成判定不代表任务质量通过。计数包含本次请求的全部相关工作，不是严格 decode-only 分解，也不是性能收益。

## 正确性、ISA 与命中

| 检查 | 实际结果 |
|---|---|
| 故意错误内核 | 返回零的 red stub 被真实 dot 对照捕获，exit 2、`BIT_MISMATCH stage=GU-dot` |
| 查表与逐 bit | 100000 组 lookup、1310720 组真实 dot、1024 组专家阶段全部逐 bit 相同 |
| 完整 ExpertPool | 115 批次、509 输出数组相同，候选实际命中 4191 次 row 调用 |
| 回退 | 4 组其他格式／多 token 对照通过，候选未命中 |
| CPU 能力 | 正常与 AVX2 限制下支持，AVX 限制下拒绝；旧 wide/VEX-VNNI 门始终 false |
| 新 TU 指令 | 实际 dot 中 8 条展开后的 `vpgatherdd`；无 EVEX、AVX512、VNNI；dispatcher 无 VEX/EVEX |
| 源码边界 | 独立只读核对：除两处 lookup 及函数接口适配外，计算主体逐字符一致；16 个最终文件 hash 一致 |

新 TU 单独以 AVX2/FMA/F16C 编译，显式禁用 AVX512/VNNI 与 LTO，原 ISA 门控文件未变。上游 archive guard **不是全量 PASS**：P6/P12 均返回 1，完整 violation 列表相同，均为 `iq_avx512.cpp.o` 的两个既有 public 函数未登记；该对象 SHA 完全相同。本轮判据是新 TU 检查通过且 archive **无新增 violation**，未修改旧 guard。

见[正确性回执](../workspace/gather-probe-20261028/correctness/COMPLETE.json)、[ISA 检查](../workspace/gather-probe-20261028/isa-delta/ISA_AUDIT.json)。

## 完整专家测量

复用 P5 冻结的 1008 个 fixture 文件，全部 SHA 验证；索引也与原 `BENCH_FREEZE` 一致。192 个权重 blob 共 397516800 bytes（379.10 MiB），大于 LLC；115 个原批次、317 jobs、509 entries 保留原 grouping/nt，其中 nt1 为 196 jobs（61.83%）。这是所选格式的真实捕获回放，组成不等于当前所有请求。

同一二进制，只切换候选。15 个 worker 固定物理核 1–15、host 核 0；每臂新进程，预热 30 秒、测量 60 秒。六对顺序预先固定为 AB/BA/BA/AB/AB/BA。统计以完整配对轮次为单位，枚举 6^6 bootstrap；扩展门为完整专家改善 ≥3% 且配对 95% CI 排除零。三对 warm2s/measure10s 单核热 GU 仅诊断，不参与扩展门。

| 指标 | 关闭均值 | 开启均值 | 配对耗时变化及 95% CI |
|---|---:|---:|---|
| 完整 GU→SwiGLU→quant→down | 30.304 ms/sweep | 40.320 ms/sweep | **+33.038% [31.401%, 34.607%]** |
| GU/SwiGLU 阶段 | 21.883 ms/sweep | 31.722 ms/sweep | +44.948% [43.447%, 46.429%] |
| quant 阶段 | 0.408 ms/sweep | 0.371 ms/sweep | −9.020% [−10.455%, −7.563%] |
| down 阶段 | 7.987 ms/sweep | 8.200 ms/sweep | +2.636% [0.696%, 4.434%] |
| 每臂 sweep P95 | 31.988 ms | 41.263 ms | +28.988% [27.606%, 30.311%] |
| 单核热 GU（三对，仅诊断） | 0.785 ms/call | 1.397 ms/call | +77.960% [77.951%, 77.969%] |

六对完整耗时比为 1.34893、1.33569、1.29960、1.34568、1.34863、1.30473。12 臂输出 hash 全部相同；开启臂均有候选命中，关闭臂均为零。表中均值是各臂算术均值，配对变化是对内比值的几何均值；P95 也是以六个臂级指标配对，未将 sweep 当作独立重复。

增加的时间主要出现在 GU/SwiGLU。quant/down 没有修改，它们的局部计时变化不构成新的优化或独立因果结论。正式结论只依据完整链，见[ANALYSIS.json](../workspace/gather-probe-20261028/ANALYSIS.json)。请求性能及任务质量采用门均未通过本轮探针获得替代证明；候选开启的整机请求测试 NOT_RUN。

## 有效频率与内存

root 只读取 CPU0–15 的系统 MSR，benchmark 由 `runuser` 降为 uid1000。每臂按实际测量起止截取、丢弃首尾 2 秒，保留 56 个 APERF/MPERF 区间且计数器 100% 调度。owner 计数另覆盖加载、预热及测量整臂。

| 指标 | 关闭 | 开启 |
|---|---:|---:|
| 测量窗 APERF/MPERF 六臂均值 | 1.12656 | 1.14550 |
| 整臂 owner 有效 GHz 均值 | 2.34419 | 2.37802 |
| 实际 benchmark PSS 峰值范围 | 402.16～410.25 MiB | 400.32～402.38 MiB |
| 测量窗 major faults | 每臂 0 | 每臂 0 |
| 测量窗 minor faults | 每臂 6 | 每臂 6 |
| 进程 VmSwap | 0 | 0 |

开启 A/M 约高 1.68%、owner GHz 约高 1.44%，本次聚合测量不支持“降频导致退化”。A/M 仍含所选核上的其他系统工作，epoch 与 perf 启动有微小偏移，不能当作逐指令频率。每臂有 55 个测量窗进程内存样本；未观察到候选的明显额外内存占用或 major fault。

未采集 IMC/LLC 流量或执行端口计数，因此没有 DRAM 带宽、cache miss 或某条指令周期的直接因果结论。CPU 回放不含完整 GPU 模型/KV 驻留，不能替代 P4 引擎内存或长时热稳定性验收。

12 臂整臂系统 vmstat 合计 swap-in 53 页、swap-out 0、major faults 92，包含其他系统活动；不能归因给测量窗口内 major faults 为零的 benchmark。18 个 CPU 诊断／完整链臂共 1158 个资源样本，GPU 最高 45°C，MemAvailable 最低 57318.87 MiB。

## 原因与解释边界

这次与 P5 不同：单核热路径本身已明显退化，不能主要解释为“多线程内存带宽掩盖了内核收益”。codebook 为 512×4=2 KiB；gather 不减少权重或取表总字节，仍需索引扩展、移位、OR，以及 AVX2 gather mask 的准备。当前候选汇编每 256 元素循环有 8 条 gather、8 条 mask 复制，并存在中间值栈读写；实际链接 oracle 的反汇编没有 gather。

候选是严格 AVX2 的独立 TU，原 oracle 按 P6 的 `-march=native` 编译。原函数虽来自源码的 AVX2 分支，实际还使用 EVEX256 的 `vpternlogq`、`valignd`，FP 累加器保持在寄存器；候选则存在累加器栈读写。源码只改查表不代表所有生成指令与寄存器分配都相同。因此实验拒绝的是当前实现，不能把全部差值分摊给 gather 指令、某处 spill 或微码。未继续调寄存器、改编译目标或叠加 VNNI，避免把单探针扩大成搜索。见[实际 oracle 汇编](../workspace/gather-probe-20261028/actual-oracle-disassembly.txt)。

29 实测 GDS 状态为 `Mitigation: Microcode`，CPU 为 Xeon Silver 4216，微码 `0x5003604`。Linux 文档明确该状态表示缓解生效；Intel 说明热路径依赖 gather 的程序可能受其性能影响。因此它是候选解释，未做关闭缓解的对照，不能定量归因。[Linux 状态定义](https://docs.kernel.org/admin-guide/hw-vuln/gather_data_sampling.html)、[Intel 性能说明](https://www.intel.com/content/www/us/en/developer/articles/technical/software-security-guidance/resources/gds-mitigation-performance-analysis.html)。系统设置保持不变。

## 验证与保留记录

两个前置尝试完整保留：第一次系统 Python 缺 `regex`，在 tokenizer 初始化、加载模型前停止；第二次沿用旧 P5 启动检查的 10290 槽位要求，在发出请求前停止。随后使用配置中的既有虚拟环境，并使用 P6 启动回执及 10272 槽位检查，覆盖请求完成。没有改变 `--expert-cache auto` 或重写失败记录。

本机 `python3 -m unittest discover -s docs/strata_4090_128k_lab/tests -p 'test_gather_*.py' -v` 共 17 项通过；根仓库 `pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build` 全部 exit 0。未重跑 P6 的 402 项服务测试、原六项长检索或全 lab selftest。

收尾确认 13 个生产保护 hash、P6 原生/六文件移植及本轮源码/二进制均未变化；P6～P11 共 1076 个旧 raw 文件 hash 不变。40 个拥有的 server/engine/perf/benchmark PID 全部退出，GPU 无计算进程、1 MiB/43°C，18089 可绑定；生产为 inactive/dead/enabled。

两次已加载引擎的覆盖尝试共 123 个资源样本，最高 73°C/23708 MiB，MemAvailable 最低 9999 MiB；没有触发资源 abort，两份临时 key 已脱敏。见[FINAL_PROTECTION.json](../workspace/gather-probe-20261028/FINAL_PROTECTION.json)。

原始数据在29 `/home/hhtele/strata-lab-4090/workspace/gather-probe-20261028` 及本地[同名目录](../workspace/gather-probe-20261028)。372 个文件、30499137 bytes 已完成双端 SHA256 核验。保留所有前置失败、red/green 构建、原输入/输出、逐 bit、ISA、汇编、18 臂计数与内存样本。独立评审从 raw 重新计算六对统计、MSR 和进程内存，均与报告一致；reviewer 未 SSH 或重跑模型。未提交、推送、改变生产或部署。

复算完整配对统计：

```bash
python3 -B tools/gather_probe/analyze.py workspace/gather-probe-20261028
```

该命令只重新生成派生 `ANALYSIS.json`，不重跑基准；原始证据以 `RAW_MANIFEST.json` 核验。扩展门不通过，本轮到此停止。
