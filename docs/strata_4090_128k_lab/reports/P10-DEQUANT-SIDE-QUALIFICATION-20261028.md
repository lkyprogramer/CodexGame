# DEQUANT_SIDE关闭状态的路径与成本核查（2026-10-28）

**完成：NO_BENEFIT_SCREEN，本轮停止，不开启 `STRATA_DEQUANT_SIDE=1`。** 三种请求的目标基线路径确有覆盖；在本次profiled时间线中，即使将所有dequant候选全部删除、保持其他工作耗时不变，TTFT的条件空间也只有 **1.22% / 1.73% / 1.36%**，低于沿用的P3请求改善4%门。候选已经包含尚未逐指针区分的IQ内核超集，未以过窄归因压低成本。

这是对本次样本的机制筛查，不是实测加速、未插桩环境的严格收益上限或所有shape无收益的证明。`SIDE=1` 的实际启动、数值等价、额外显存/槽位代价及配对性能均未测试；原P6正确性门仍FAIL，原六项FAIL和评分不变。生产未改、未部署。

## 冻结身份与执行范围

复用P6 v0.2.7隔离树 `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`、原生二进制SHA256 `58ffaf7f67535049baf996dd8793202b2ba4d2d7090569cfcc13019a28269f22`、六文件#1536/PT移植和完整配置：IQ3_XXS、EXACT6、int8 KV/resident20480、spec4、原线程布局、131072总上下文及4096预留、CPUSHARE4096、AUTOMAX16384。P6保守开关均保持，实际engine环境确认 `STRATA_DEQUANT_SIDE=0`。

未编译新Strata二进制或改kernel；客户端仅增加NVTX请求范围及首输出标记。首输出复用原SSE parser的`on_first`分类，role/progress不算输出；观察范围结束后恢复原parser。模型生成内容未作为宿主机代码执行。

工具为29已有 **Nsight Systems 2023.3.3**，`--trace=cuda,nvtx --sample=none --cpuctxsw=none --cuda-graph-trace=node`，不启用需root的CPU采样或GPU计数器。profile launch使用明确的环境白名单，未记录主机无关凭据。未安装/更新工具链、驱动或模型。

## 原始请求与真实性边界

| 场景 | 冻结来源/hash | 实测prompt / reused / read | 生成token / 原gold结果 |
|---|---|---|---|
| 32K完整重读诊断 | P3 `performance-corpus.json:append-prime`，`cfa1c067…0903` | 32771 / 0 / 32771 | 2 / `ACK` PASS |
| 随后的约3K续接 | 同语料 `append-0`，`5d2af977…d0ed` | 35993 / 32764 / 3229 | 5 / `1730` PASS |
| 新引擎100K冷读 | P6 `102400-prime.request.json`，`fbd40639…64d9` | 102392 / 0 / 102392 | 8 / `6395887`，原完整gold `2390975-001086`仍FAIL |

完整body、hash、gold及源路径见 [cases.json](../workspace/combination/dequant-side-20261028/cases.json)。每次均使用原body、max_tokens32/32/64、采样参数和评分器，未改提示、缩短上下文或截取gold。3K续接在同一引擎紧跟32K准备请求，100K使用另一个新引擎，不把带长前缀命中的旧性能请求当冷读。

**没有找到已归档的真实Pi compaction后请求。** 前两项本身也是P3冻结的合成transcript；32K请求只标记 `DIAGNOSTIC_SUBSTITUTE_FULL_REREAD_NOT_REAL_COMPACTION`，代替重读计算形态，不能声称真实compaction/摘要链已验证。实际用户流量、新八轮任务链和新版取消续接不在本轮覆盖内。

原预登记为三个请求各一次profile。取得时间线后，考虑profiler改变实际缓存槽数、且历史测量已有明显扰动，**在观察control结果前**追加同三个请求各一次无nsys对照，只用于测量扰动检查。见 [PREREGISTRATION.json](../workspace/combination/dequant-side-20261028/PREREGISTRATION.json)、`PREREGISTRATION-AMENDMENT-1.json`。共四个引擎阶段、六请求；不是off/on A/B，也没有反复重跑挑最好结果。

## 源码资格与实际覆盖

该开关作用于prefill的**dense权重反量化与GEMM之间的流水化**。`Gemm::native`沿用原dequant与f16 GEMM核，由第二scratch和ready/free事件建立顺序。`GEMM_SCRATCH=32<<20`个FP16元素，第二scratch名义为64MiB；实际净显存、prefill借用区和专家槽位变化仍须开启后才可测，不能把源码大小当作已测净代价。

`N*K > scratch_elems`的矩阵继续分行串行处理，不属于该旁路。CUDA上的HIP专用MMQ/填充路径也不能算入资格。源码快照在 [source-evidence](../workspace/combination/dequant-side-20261028/source-evidence)。

依据原GGUF张量形状/类型，2D量化张量中有300个符合scratch容量：245个非IQ的H16反量化、55个IQ-half候选。三个大2D张量（output、token embedding、PLE表）单独排除。静态清单及计算式见 [static-candidate-inventory.json](../workspace/combination/dequant-side-20261028/static-candidate-inventory.json)：

- 已观察plain H16 kernel：`gridX=ceil(N*K/8192)`、block256。production调用点来自`Gemm::native`；本轮没有大矩阵整片应出现的4096-block切片。
- IQ-half：`gridX=N*K/256`、block32。实现还可供MoE等调用，因此保留“候选超集”限定，不单凭kernel名断言逐张量归属。

| 请求 | 执行dense GEMM的prefill chunk数 | H16基线调用 | IQ-half候选 | 总候选 |
|---|---:|---:|---:|---:|
| 32K重读 | 2 | 490 | 110 | 600 |
| 3K续接 | 1 | 245 | 55 | 300 |
| 100K冷读 | 7 | 1715 | 385 | 2100 |

逐类型/grid直方图完全等于上述每chunk静态清单的相应倍数，见 [coverage-check.json](../workspace/combination/dequant-side-20261028/coverage-check.json)。32K最后的3个token没有被误算成又一个dense-prefill chunk。这里确认的是**关闭状态下待优化基线路径的覆盖**，不是声称开启side路径已命中。

## 时间线、成本及解释

两份SQLite分别有engine进程归属、CUDA kernel/runtime、NVTX范围和首输出mark。分析器从实际schema读取，以`PROCESSES`绑定真实engine PID，再验证runtime线程归属与唯一correlation；全部dequant候选成功关联对应launch API。请求和首输出标记使用同一个Nsight时间基准，不用应用epoch时间直接减GPU时间。初始化、请求间空闲和首输出后的decode另行排除。

| 请求 | trace首输出范围ms | 全dequant候选区间并集ms | 条件删除空间/TTFT | API.start乐观窗口合计ms |
|---|---:|---:|---:|---:|
| 32K重读 | 8689.658 | 106.193 | 1.222% | 106.193 |
| 3K续接 | 3083.633 | 53.310 | 1.729% | 52.156 |
| 100K冷读 | 27330.999 | 371.434 | 1.359% | 370.818 |

完整请求范围对应的条件删除比例为1.212% / 1.677% / 1.348%。这里只是短输出合成请求，不代表真实长thinking轮次；没有据此建立生产请求收益。

删除模型将所有候选都视为可以省掉且保持非目标工作耗时不变，实际side仅尝试重叠、并不删除工作，因此这是本次trace中的乐观筛查模型。它不包括调度/争用改变对其他kernel时长的间接效应，**不是未插桩环境的严格性能上限**。

另计算 `min(D.duration, max(0, D.start − launchAPI.start))`：开关不提前CPU发射，以API入口当最早可能enqueue，并假定权重ready、scratch空闲、并发资源无限。不能用API返回时刻替代入口，也不能将该合计称预计实际收益。

候选与其他kernel的实际时间交集为0；与memcpy活动交集分别为90.497 / 0.000416 / 275.137ms。**这些重叠不证明因果隐藏，不能直接用“dequant并集减copy重叠”计算收益。** 当前分析没有重建完整CPU/stream/event/权重准备依赖图，所以不声称得到精确关键路径。

两份导出未提供可用的丢弃事件计数，不能宣称绝对零丢失。CLI成功、候选类型/shape计数闭合、runtime关联及有效标记支持本轮诊断；缺trace/缺关联会单独记NO_TRACE/UNATTRIBUTED，不当作无命中。详见 [ANALYSIS.json](../workspace/combination/dequant-side-20261028/ANALYSIS.json)。

## 无profiler对照与停止决定

| 请求 | profile HTTP TTFT秒 | 无nsys HTTP TTFT秒 | 两次实际生成token |
|---|---:|---:|---:|
| 32K重读 | 8.6896 | 8.3628 | 2 / 2 |
| 3K续接 | 3.0836 | 3.0209 | 5 / 5 |
| 100K冷读 | 27.3305 | 26.8112 | 8 / 8 |

实际expert-cache auto：profile为10264槽，control为10272槽；原参数均保持auto。该8槽差异属于本次观测环境差异，**不是开启DEQUANT_SIDE造成的槽位损失**。单次对照、顺序效应和缓存差异不能因果量化profiler开销，也不能把两列差值当优化收益。control记录沿用driver通用“非性能样本”标记；是否使用nsys以冻结launch command为准。

本轮按既定4%请求门参考停止：即使在profiled请求中把候选工作全删，仍不足4%，没有足够证据投入开启/配对实验。该决定限于本次模型、配置和三种形态，未证明其他短prompt、shape或模型上的DEQUANT_SIDE都无收益；也没有声称等价优化已经穷尽。

`SIDE=1`实际生效、`gemm_dequant_side_parity`、固定token状态/数值对照、额外64MiB的净缓存代价、配对性能均记 **NOT_RUN_SCREEN_AND_EXISTING_CORRECTNESS_GATE**。P6原门不变，未放宽gold或重新定义已知失败。见 [DECISION.json](../workspace/combination/dequant-side-20261028/DECISION.json)、[SUMMARY.json](../workspace/combination/dequant-side-20261028/SUMMARY.json)。

## 验证、保护和归档

- 新增 [trace_dequant.py](../tools/v027/trace_dequant.py)、[analyze_dequant.py](../tools/v027/analyze_dequant.py)。本机及29各10项定向测试通过：SSE首输出标记/恢复2项，区间去重、API.start边界、缺trace、owner/correlation歧义等8项；没有仅靠HTTP200宣称成功。
- 根仓库 `pnpm typecheck/lint/test/test:integration/build` 本轮全部exit0，保留原Phaser chunk提示。未重跑P6服务402项、全量native parity/lab selftest；源与二进制冻结证据复用。
- 独立code-reviewer只读检查源码与两份真实SQLite，未发现影响本次筛查决定的实质缺陷；未SSH、运行模型或执行单测，其意见不替代本轮实测。
- 四阶段209个1秒级资源样本，无abort；峰值70°C/23672MiB，最低MemAvailable9479MiB。采样覆盖实际server与engine后代，未只采Python父进程。
- 原生/六文件port及13个生产保护hash不变；P6原182、P7原373、P8原140、P9原71个证据文件及P3冻结输入不变，权重size/mtime仍匹配P9全hash身份。
- 4个engine、4个server、4个driver PID均退出，两次profiler也结束，没有残留本轮profiling agent；GPU1MiB/43°C、无计算进程，18089可绑定。4份临时key均已脱敏，生产仍inactive/dead/enabled。见 [FINAL_PROTECTION.json](../workspace/combination/dequant-side-20261028/FINAL_PROTECTION.json)。

raw：29 `/home/hhtele/strata-lab-4090/workspace/combination/dequant-side-20261028`，本地 [workspace/combination/dequant-side-20261028](../workspace/combination/dequant-side-20261028)。保留原请求/SSE/响应、实际PID/env/argv、SQLite和nsys-rep、实际schema、源码快照、控制修订及分析回执；没有复制模型。双端逐文件SHA256回执为 `RAW_MANIFEST.json` 与 `REMOTE_RAW_INTEGRITY.json`，实验包MANIFEST共217文件。没有提交、推送、改生产或部署，范围外已有修改保留。

复算入口（输出名必须新建，不能覆盖本轮证据）：

```bash
python3 -B -m unittest tests.test_dequant_trace tests.test_dequant_analysis -v
python3 -B tools/v027/analyze_dequant.py \
  --trace workspace/combination/dequant-side-20261028/append-v1-trace.sqlite \
  --run-folder workspace/combination/dequant-side-20261028/append-v1 \
  --trace workspace/combination/dequant-side-20261028/cold-v1-trace.sqlite \
  --run-folder workspace/combination/dequant-side-20261028/cold-v1 \
  --output workspace/combination/dequant-side-20261028/analysis-new.json
```
