# P22 · 原10272槽下的完整memcheck验证

结论：**加载OOM已解决，完整默认memcheck通过。** 复用未改的P21引擎，保持10272个实际专家槽、17055MiB缓存、KV int8/resident20480、C借槽及实际16384计算块。一次纠正GEN1取得完整DONE，sanitizer退出0、`ERROR SUMMARY: 0 errors`。未过滤kernel、跳过launch、关闭heap检查、添加suppression或强制同步。

P20同C路径的16K逐字节数值证据和P21八请求生命周期证据直接复用，没有重跑。P21原EAGER加载OOM和本轮首次LAZY运行的verify watchdog失败均保留。本阶段正式性能样本0；成本诊断与性能仍须按后续门独立验收。原六个任务FAIL不变，不能据此声称提速或可采用。

## 加载OOM的原因与修正

冻结`generate.cpp:2896–2904`在环境未设置时主动选择`CUDA_MODULE_LOADING=EAGER`。最初独立Python探针返回LAZY，但没有执行该初始化代码，因此不能据此判断原Strata的加载模式；本轮已纠正这一判断。实际CUDA12.3/driver610.57.04未更新。

同一个微型CUDA/cuBLAS程序，在创建CUDA上下文后记录`cudaMemGetInfo`，再调用`cublasCreate_v2`。三种实际cuBLAS初始化增量为：

| 微型模式 | cuBLAS初始化占用增量 | 结果 |
|---|---:|---|
| 普通EAGER | 388MiB | exit0 |
| 默认memcheck + EAGER | 2718MiB | exit0、0 errors |
| 默认memcheck + 显式LAZY | 88MiB | exit0、0 errors |

先前关闭device-heap检查没有降低实测占用，未把该设置用于模型验证。初始三个footprint探针因传输引号错误在CUDA初始化前发生Python SyntaxError；失败JSON保留，修正源文件后才产生上表及其他有效探针结果。

NVIDIA说明lazy loading可降低工具的设备与主机内存占用；它只延迟加载，不要求关闭memcheck检查。[官方说明](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/index.html#memory-footprint)

## 保持物理缓存与分派合同

原`--expert-cache auto`先得到7677个最大blob名义预算槽，再按相同冻结profile和各层blob尺寸展开为10272个实际变长槽。直接传`--expert-cache 10272`会改变字节预算，不能用于本对照。

本轮仅在独立sanitizer进程把原自动结果冻结为`--expert-cache 7677`，并显式设置LAZY。源码`generate.cpp:6789–7035`仍执行原profile前缀和slot尺寸换算、全量预填充。`auto_cache`其余用途为warning、分配后清零/空间探测和自动缩槽；显式预算禁用自动缩槽，分配或实际配置不符即失败。生产配置没有改动。

发送GEN前，实际INFO中的21项有效配置与P21严格相等，并逐字段核对已有HC allocation。两次新启动均为10272槽、17055MiB、KV resident20480、15 workers、CPUshare MAX4096、AUTO MAX16384；原3787借槽、region大小、偏移和分派几何不变。加载后空闲显存900MiB，原正常EAGER运行为514MiB。该差值是诊断加载方式的结果，不计作候选性能或生产收益。

本轮没有重新导出4019条完整分派raw。同驻留/分派约束由冻结同一exe与profile、相同物理槽和C布局、运行时实际chunk/MTP几何支持；它不是一次新的逐字节分派回放。P20的完整raw、logits及有效状态数值证明单独列为复用证据。

## Verify阻塞与有因果依据的纠正

首次LAZY模型运行完成16384主块、48层FFN及MTP预填充，但尾部4-token verify窗口停在host step1：GPU已rang1，三个CPU服务flag仍为0，15个worker睡眠、0 jobs。原生60秒watchdog终止引擎。工具记录0个内存错误，同时明确报application error；请求没有DONE，原`RUN_RESULT=FAIL/NATIVE_PROTOCOL: None`保留，未改判通过。资源监控abort_reason为null，峰值71°C，未触发85°C或主存门。

冻结源码本来已有`HostGraphLaunch`和`STRATA_VERIFY_ASYNC_LAUNCH`：插桩后的`cudaGraphLaunch`可能阻塞启动线程，图又在等待该线程服务CPU doorbell。该开关只把原graph/stream的启动移至辅助线程；原线程继续按原顺序服务CPU工作。实际launch错误经release/acquire传递，成功先join再检查错误，异常先释放GPU等待再join。

先编译冻结仓库已有`tests/core/host_graph_launch_test.cu`，没有新增或修改CUDA内核：

| 微型控制 | 结果 |
|---|---|
| 普通同步启动 | exit0、PASS |
| memcheck同步启动负例 | 8秒测试watchdog释放后exit1，`FAIL: graph waits for CPU service`；0 memory errors |
| memcheck异步启动正例 | exit0、0 errors；全部4096个图节点、CPU doorbell服务及提前返回清理PASS |

据此另建`lazy-async-frozen-cache`，独立预登记一次纠正GEN1，仅追加已有的`STRATA_VERIFY_ASYNC_LAUNCH=1`。原60秒watchdog、缓存、模型、路由和内核实参未改。此开关只用于sanitizer诊断，不进入正式性能臂。

## 完整通过证据

- 真实输入16389 token、实际主块`p0=0/T=16384/stream_all=true/cpu_share_limit=4096`；C allocation与原证据严格相等。
- MTP实际范围[0,16384)，两批几何与P21原long请求完全相同。
- `DONE produced=1/input=16389/read=16389/reused=0/finish=length`；完整248320个FP32 logits均有限。
- sanitizer/native launcher实际exit0，完整错误汇总0，无不完整覆盖、OOM或application error；正常QUIT，监控在QUIT前停止。
- 两次模型启动、两次GEN1尝试：首次失败保留，纠正请求PASS。442个护栏样本，峰值71°C/23358MiB，最低MemAvailable12485MiB；两个监控abort_reason均null。

`python3 -B -m unittest discover -s docs/strata_4090_128k_lab/tests -p test_hc_memcheck.py -v`本地及29均4项PASS；29使用`-s tests`。覆盖原预算冻结、配置/借槽/分派漂移拒绝及不完整tool日志拒绝。独立审查者实际运行最初4项测试；后续helper/纠正入口为只读源码复核，没有SSH或GPU运行。

`pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build`均exit0，保留既有Phaser chunk warning。未构建或修改新的模型引擎，P21 exe SHA保持`c9cf7cf9ff5135d4a59cb4b59ce2bb448bf880c28c68fd0a78d078f205a38741`。

本结果覆盖完整本次GEN1的默认memcheck，不代表穷尽race、共享region内部子区间redzone或所有未来输入。sanitizer耗时不进入性能统计。

## 归档与后续

[阶段汇总](../workspace/combination/hc-memcheck-20261029/SUMMARY.json)、[完整通过结果](../workspace/combination/hc-memcheck-20261029/lazy-async-frozen-cache/RUN_RESULT.json)、[实际执行记录](../workspace/combination/hc-memcheck-20261029/lazy-async-frozen-cache/CAPTURE.json)、[工具日志](../workspace/combination/hc-memcheck-20261029/lazy-async-frozen-cache/sanitizer.log)、[原watchdog失败](../workspace/combination/hc-memcheck-20261029/lazy-frozen-cache/stderr.log)、[纠正预登记](../workspace/combination/hc-memcheck-20261029/lazy-async-frozen-cache/PREREGISTRATION.json)、[微型控制](../workspace/combination/hc-memcheck-20261029/graph-launch-control/PREREGISTRATION.json)、[原件清单](../workspace/combination/hc-memcheck-20261029/RAW_MANIFEST.json)、[归档回执](../workspace/combination/hc-memcheck-20261029/ARCHIVE_RECEIPT.json)。

64份原件记录长度及SHA；63份、9,392,299bytes已双端逐文件核验，两个根清单SHA相同。微型Linux二进制保留29，其身份在原件清单和控制回执中；不是未复制大模型raw的替代证明。

收口实测：13项生产保护SHA不变、服务inactive/dead、GPU1MiB且无计算进程、18089释放。使用`jssh 29`，未改生产配置、systemd、驱动或CUDA。自动续测仍PAUSED；按本次手动授权继续最多一对100K成本诊断，再决定是否进入既定正式性能门。
