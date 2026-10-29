# 单格式GU整数融合探针（2026-10-27）

**完成：NO_BENEFIT，未过探针扩展门。** IQ3_S nt=1的数值、ISA及实际命中检查通过；生产线程布局中的完整专家耗时改善 **−0.152%**，配对95% CI **[−0.570%, +0.245%]**。未达到预登记“改善≥3%、CI不跨零”。按停止条件，不扩展格式/nt/512位/预打包，不进入整机候选验证。此结果不证明其他等价优化已穷尽，也不构成请求性能或任务质量采用结论。

生产目录和配置未改。13个保护文件hash不变，服务继续inactive/dead、仍enabled，GPU 1MiB且无计算进程，18089已关闭，本轮实验进程已退出。没有提交、推送或部署。

## 冻结范围与真实输入

隔离树：`/home/hhtele/strata-lab-4090/workspace/trees/gu-probe-20261027`，基于 `f615cc8d11c7f705a7c29b2884af415886c21f9c`。保持原完整配置与EXACT6：KVRES20480、AUTOMAX16384、CPUSHARE4096、PT0、reply reuse1、spec4；仅实验端口18089。配置与源/构建身份分别保留在 [config.json](../workspace/gu-probe-20261027/config.json)、[FINAL_BUILD.json](../workspace/gu-probe-20261027/FINAL_BUILD.json)。未改生产和回滚树。

[PREREGISTRATION.json](../workspace/gu-probe-20261027/PREREGISTRATION.json)在测量前固定主指标、6对AB/BA各3对、每臂预热30秒/测量60秒、3%扩展门与停止条件。[BENCH_FREEZE.json](../workspace/gu-probe-20261027/BENCH_FREEZE.json)在性能测量前冻结候选源码、同一二进制和fixture，并记录用户后续授权root读MSR；统计门与样本数未改变。CPU探针二进制SHA256为 `2fe1e998ad53631dea7f212c4f489e5cbe5875f886b2b8f754a9f6002ae876cf`。

完整配置重放3K/40K的思考、回答各一题，temperature=1、top-p=.95、top-k=20、seed=20261027，每题输出2048 token；qualification单独扣除。回答段保留既有reasoning budget128诊断设置，不作真实Pi任务质量验收。短请求可能包含CPU prefill，以下是请求实际CPU miss，不能称严格decode-only。

共 **208846 CPU expert miss job、283141 token entry，其中163242个nt=1 job**。job、entry、worker CPU时间及GU阶段墙钟分别统计；逐格式/nt满足 `entries=jobs×nt`、`rows=jobs×640`，总计闭合。

| GU格式 | 全部miss job | nt=1 job | nt=1 GU worker秒 | nt=1 GU worker耗时占比 |
|---|---:|---:|---:|---:|
| IQ2_XXS | 40721 | 31941 | 18.605897 | 15.418% |
| IQ2_XS | 46116 | 37091 | 24.485925 | 20.291% |
| IQ3_XXS | 19756 | 15353 | 12.108455 | 10.034% |
| IQ3_S | 59904 | 46110 | 44.931646 | 37.233% |
| IQ2_S | 42349 | 32747 | 20.544262 | 17.024% |

| GU格式 | nt1 | nt2 | nt3 | nt4 | nt5 | nt6 | nt7 | nt8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| IQ2_XXS | 31941 | 6165 | 1476 | 486 | 178 | 192 | 147 | 136 |
| IQ2_XS | 37091 | 6440 | 1470 | 493 | 173 | 187 | 127 | 135 |
| IQ3_XXS | 15353 | 2838 | 741 | 365 | 165 | 137 | 105 | 52 |
| IQ3_S | 46110 | 9390 | 2459 | 862 | 329 | 313 | 245 | 196 |
| IQ2_S | 32747 | 6580 | 1690 | 592 | 238 | 198 | 156 | 148 |

按最高nt=1 worker成本，唯一锁定 **IQ3_S(type21)、nt=1**。其nt=1 job占全部nt=1 job的28.246%。完整原始分布见 [SELECTION.json](../workspace/gu-probe-20261027/SELECTION.json)。现场fallback记录的实际函数偏移 `0x87e1c0` 经该二进制符号表确认为 `ggml_vec_dot_iq3_s_q8_K`，使用madd组合。不能从缺VBMI或某个CMake开关推断整个ggml是AVX2-only；当前ggml能力函数含AVX512支持，oracle使用实际执行函数。

同配置另跑一次40K思考请求，捕获192个原始expert blob、115个原始batch、317个expert job和509个token entry。权重397516800字节（379.10MiB），超过22MiB LLC；批内分组和顺序保持原样。nt分布为1:196、2:78、3:22、4:14、5:7。该样本nt=1占61.83%，低于选择请求中IQ3_S的76.97%，不重加权，不把有限捕获称为全部生产分布。fixture详情和1008个文件hash见 [FIXTURES.json](../workspace/gu-probe-20261027/FIXTURES.json)。

## 唯一算术改动与正确性

从实际ggml IQ3_S函数的AVX2分支提取代码，仅把两组整数 `_mm256_madd_epi16` 加 `_mm256_add_epi32` 换成非饱和EVEX256 `_mm256_dpwssd_epi32`。原解包、符号、scale查表、FP FMA及规约顺序保持；保留 `GGML_CPU_FP16_TO_FP32` 的原查表宏。SwiGLU表达式不变，quant/down、多token及其他格式走原路径。C++指针显式转换仅用于语法适配。生成器见 [make_kernel.py](../tools/gu_probe/make_kernel.py)，完整源码见 [source-final](../workspace/gu-probe-20261027/source-final/)，tracked补丁见 [FINAL_PATCH.diff](../workspace/gu-probe-20261027/FINAL_PATCH.diff)。新文件单独保存，未用git diff遗漏未跟踪源码。

新增独立baseline dispatcher与EVEX256 TU；新路径默认关闭，只在IQ3_S/nt1/无tail及严格能力检查下开启。检查AVX2、FMA/F16C现有资格、ISA cap、FORCE_AVX2、OSXSAVE/XCR0及F/BW/VL/VNNI。旧 `cpu_avx512_ok`、`cpu_avxvnni_ok`、旧宽TU保持字节不变；没有直接放宽现有ISA门。

| 检查 | 实际结果 |
|---|---|
| 可信错误占位dot返回0 | 真实GU比较按预期exit2，`BIT_MISMATCH stage=GU-dot byte=0`；red源码/二进制保留 |
| 整数极值及回绕 | 100000组逐bit一致 |
| 实际oracle vs 新GU dot | 1310720组逐bit一致 |
| SwiGLU、quant bytes、实际down、分行范围哨兵 | 1024组逐bit一致；覆盖原Q2_0及native down分支 |
| 生产ExpertPool回放 | 115 batch、509输出数组逐bit一致；15worker在1–15，host在0 |
| 实际候选命中 | pool parity命中4191个row call；所有开启测量臂命中为正，关闭为0 |
| 回退 | 其他格式nt1、IQ3_S nt2/4/8共4场景一致，新路径命中0 |
| 强制ISA限制 | FORCE_ISA=avx2及FORCE_AVX2=1时新资格false |
| ISA/编码审计 | 新TU EVEX256 VPDPWSSD；无VBMI/VPOPCNTDQ/VEX VNNI/ZMM；baseline dispatcher无VEX/EVEX |
| CPU archive ODR审计 | 554函数、72含宽指令、0违规；仅专用脚本登记3个实验入口，不改上游检查源 |

数值证据见 [correctness/COMPLETE.json](../workspace/gu-probe-20261027/correctness/COMPLETE.json)、[parity.log](../workspace/gu-probe-20261027/correctness/parity.log)、[pool-parity.log](../workspace/gu-probe-20261027/correctness/pool-parity.log)。ISA证据见 [ISA_AUDIT.json](../workspace/gu-probe-20261027/isa-v2/ISA_AUDIT.json) 与 [isa-v2-console.log](../workspace/gu-probe-20261027/isa-v2-console.log)。实机旧宽门与旧VEX VNNI门仍false，新资格true。

## 完整专家六对结果

每个sweep依次完成115个原始batch，包含317个expert job及509个token entry。测量通过真实ExpertPool执行 **GU→SwiGLU→quant→实际down**，包含同步和非nt1路径；同一二进制/fixture，每臂独立进程，15worker+host，GPU空闲，持有既有全局实验锁。没有用单核或热缓存结果替代此主指标。

| 对 | 顺序 | off毫秒/sweep | on毫秒/sweep | 改善 |
|---|---|---:|---:|---:|
| 1 | off/on | 30.085900 | 29.996604 | +0.297% |
| 2 | on/off | 30.183388 | 30.409354 | -0.749% |
| 3 | on/off | 30.112361 | 29.968858 | +0.477% |
| 4 | off/on | 30.042861 | 30.111475 | -0.228% |
| 5 | off/on | 30.068333 | 30.022697 | +0.152% |
| 6 | on/off | 30.222891 | 30.484934 | -0.867% |

推断单位为6个配对round，计算 `log(on/off)` 均值，再转回几何时间比。95% CI使用全部6^6=46656个配对round bootstrap重采样；没有将row或sweep当成独立样本。点估计与CI使用未舍入值判断门槛。分阶段与p95仅作诊断，不改主指标或补挑结果。

| 指标 | off均值毫秒 | on均值毫秒 | 配对改善 | 配对95% CI |
|---|---:|---:|---:|---|
| 完整专家 | 30.119289 | 30.165654 | -0.152% | [-0.570%, +0.245%] |
| GU（含SwiGLU） | 21.744888 | 21.746627 | -0.006% | [-0.446%, +0.402%] |
| quant | 0.397516 | 0.395922 | +0.375% | [-1.866%, +2.668%] |
| down | 7.951680 | 7.997578 | -0.575% | [-1.038%, -0.101%] |
| p95 sweep | 30.262950 | 30.351313 | -0.288% | [-0.868%, +0.261%] |

完整链时间比1.001518561，**未过3%点估计，CI也跨零**。所有12臂最终输出hash均为 `13508333946730536415`。单核1号核心热GU三对改善1.025%，CI为[0.727%,1.273%]，仅诊断，不能触发扩展。完整pool中GU几乎不变；down代码未改，其约0.575%耗时差异只作描述，不能据此建立因果解释。统计及逐臂完整值见 [ANALYSIS.json](../workspace/gu-probe-20261027/ANALYSIS.json)、分析器见 [analyze.py](../tools/gu_probe/analyze.py)。

## 有效频率与内存行为

普通账号无法读系统级APERF/MPERF后，用户明确授权root。root直接SSH口令认证拒绝，经现有普通账号SSH后su root成功；不修改SSH、perf权限、频率或系统设置。root只以1Hz读取CPU0–15的MSR计数，benchmark由runuser降为hhtele执行。凭据仅在认证时使用，没有写入文件、日志或git。

每臂APERF/MPERF均100%调度，按C++实际测量起止截取并丢首尾2秒，每臂保留56个区间；epoch锚与perf启动有小量exec延迟，因此不是精确的指令级对齐。owner `cycles/task-clock` 覆盖加载+预热+测量整臂，单列口径。下表是6臂均值，PSS为各臂峰值范围。

| arm | 测量窗APERF/MPERF | 整臂owner有效GHz | PSS峰值MiB范围 |
|---|---:|---:|---:|
| off | 1.12806682 | 2.34682289 | 401.40–402.16 |
| on | 1.12868167 | 2.34622862 | 398.19–402.10 |

测量窗A/M开启相对关闭约+0.055%，owner GHz约−0.025%；本样本未显示明显频率下降，不能仅凭使用EVEX256就假设不存在降频。APERF/MPERF是所选物理核的聚合计数，仍含该核其他系统工作。原始例见 [r0-off/aperf-mperf.csv](../workspace/gu-probe-20261027/bench/r0-off/aperf-mperf.csv) 与 [owner-perf.csv](../workspace/gu-probe-20261027/bench/r0-off/owner-perf.csv)。

每臂实际lab_gu_probe PID均被采样89次；测量内部窗口各55次。峰值VmRSS为409872–414328KiB，PSS峰值407743–411814KiB，主要为匿名页（PSS_Anon峰值405684–409680KiB），file约2MiB。所有臂VmSwap/VmLck/VmPin/Locked为0。截取测量窗口的进程major fault增量全为0，minor fault为6–23；owner整臂major fault为14–34，包含加载阶段，不能当作测量阶段缺页。

系统MemAvailable最低60187808KiB（57.40GiB）；12臂整臂vmstat合计pswpin=23页、pswpout=0，pgmajfault=18。系统swap-in不能归因于该基准，进程VmSwap为0；没有用单一MemAvailable替代进程构成。RSS在部分臂有小幅波动，短测不能建立长期内存稳定性。此CPU回放不含GPU模型/KV驻留，不替代P4完整引擎内存验收。未采集IMC/LLC流量计数，不能据此声称DRAM带宽或cache miss改善。

## 验证命令、失败记录与归档

29在隔离树运行的定向命令及退出日志已保存；以下路径从包根执行（GPU剖析启动完整参数另保存在selection/capture的plan和command日志）：

```bash
workspace/trees/gu-probe-20261027/build-lab/pool_tasks_test
workspace/trees/gu-probe-20261027/build-lab/lab_gu_probe parity workspace/gu-probe-20261027/fixtures.txt
workspace/trees/gu-probe-20261027/build-lab/lab_gu_probe fallback-parity workspace/gu-probe-20261027/fixtures.txt
workspace/trees/gu-probe-20261027/build-lab/lab_gu_probe pool-parity workspace/gu-probe-20261027/fixtures.txt
python3 -B tools/gu_probe/analyze.py workspace/gu-probe-20261027
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_gu_probe -q
```

- pool_tasks_test：360次bitwise通过；缺VBMI的其他模式skip不算通过。正式parity/fallback/pool、ISA/cap检查全部exit0。计时模式为 `bench INDEX off|on 30 60`；root只读外层与普通账号owner perf命令逐臂保存在root-perf-start.json/command.json。
- 工具定向测试：本机及29各7项通过，覆盖profile闭合/选择、ISA编码拒绝及3%/CI统计门；最终日志已归档。本机根仓库 `pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build` 均exit0，原始日志见 [local-verification](../workspace/gu-probe-20261027/local-verification/)。未新增全量lab selftest，未重跑P3/P4。
- 保留早期缺assets冻结而未启动GPU的失败、C→C++构建适配失败、红色stub失败、第一次ISA缺compile_commands失败。依赖是解压源码而无.git，收尾git身份查询exit128也单独保留，改记真实归档路径及依赖文件hash；没有编造commit身份。rsync因远端未安装失败，使用scp复制，随后逐文件校验。收尾直连SSH曾连续关闭连接，改用已配置jump后恢复，未修改任何网络/SSH设置。包校验另发现远端三份历史报告缺少本地已有的P3证据范围更正；检查diff、保留旧版和失败校验后同步现有更正版，不改历史测量。
- profile/capture时源码与最终候选源码分开保存；原oracle quants.c提前冻结，simd-mappings等依赖在收尾补快照，标明时点。profile/capture的strata二进制保留原receipt；**没有重新链接候选GPU引擎或运行模型候选**，因为扩展门未通过。没有把CPU命中当作整机候选命中。

原始目录在29和本地均为包内 `workspace/gu-probe-20261027`，索引见 [RAW_INDEX.md](../workspace/gu-probe-20261027/RAW_INDEX.md) 与 [RAW_MANIFEST.sha256](../workspace/gu-probe-20261027/RAW_MANIFEST.sha256)；含真实输入/权重、逐请求SSE、原生profile、red/green二进制、源码/构建、12臂完整数据、root计数和最终保护审计。fixture中的绝对路径指向29原目录，异地复现需保持目录或显式重写路径并记录新hash。raw目录被gitignore，不进入包MANIFEST；交付工具、测试和本报告进入包MANIFEST。

最终状态证据见 [FINAL_PROTECTION.json](../workspace/gu-probe-20261027/FINAL_PROTECTION.json)。**请求性能、任务质量和采用门未运行**；P3既有正式失败及质量非劣未建立结论保持。后续若继续探索，应另立一个有独立证据的新假设；本次探针到此停止。
