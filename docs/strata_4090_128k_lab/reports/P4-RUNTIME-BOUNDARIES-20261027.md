# 当前组合运行边界补测（2026-10-27）

状态：**测试及收尾完成，存在热边界失败。** 完整配置完成了15分钟混合负载、10分钟连续冷读及热态恢复/取消续接，最高84°C；仅关闭KVRES的基线在682.70秒触发85°C保护，未完成15分钟目标。不能把本轮写成“两臂全部通过”，也不形成新的ADOPT或正式质量非劣结论。[P3既有质量失败](P3-COMBINATION-KVRES-20261027.md)继续保留。

生产配置未改。最终检查为 `inactive/dead/enabled`，13个保护文件SHA256不变，GPU 1MiB、无计算进程和本次实验驱动。最终原始回执时间为2026-10-27 16:08:38北京时间。

## 范围与冻结条件

29号机实验端口18089，单卡串行。两臂使用同一隔离树 `f615cc8d11c7f705a7c29b2884af415886c21f9c`、同一原生二进制 `819ff262a1742e8b57eedc6203b015f7c9831dd4a94ecacbb5a8b1c865fade3d`，未重新编译CUDA引擎。AUTOMAX=16384、CPUSHARE=4096、PT=0、reply reuse=1、spec=4、int8 KV、131072总上下文和6144MiB会话缓存固定；仅KVRES为0/20480。两臂同样加入实验用CUDA API追踪库。

这是一次base→cfg的有限运行边界筛查，不估计配置的热学因果效应或性能收益。环境温度未测，顺序未随机化，不能由两臂触发时间差断言KVRES改善散热。保护线始终为85°C、MemAvailable至少4096MiB；不改驱动、CUDA、生产服务或内核参数。

## 持续温度

| 负载 | 关闭KVRES | 完整配置 |
|---|---|---|
| 100K全冷读＋2048输出，目标900秒 | **失败**：682.70秒触发85°C；16个完整请求，第17个被保护中断 | **完成**：915.93秒、21个完整请求；峰值84°C |
| 上述负载开始时首个温度样本 | 63°C | 64°C |
| 收尾180秒范围；线性斜率 | 67～85°C；+0.080°C/分钟 | 67～82°C；−0.248°C/分钟 |
| 混合负载后长恢复及取消续接 | **未运行**：热保护后清理，不补跑 | **通过** |
| 短输出100K全冷读，目标600秒 | **未运行**：已触发85°C，按登记条件不重复更强升温 | **完成**：625.45秒、23个请求；峰值84°C；开始47°C；收尾180秒67～84°C、+0.048°C/分钟 |

混合负载成功请求实际读入102410/102411 token、复用0、输出2048；纯读入支路读入102396/102397、复用0、实际输出4（上限8）。均使用新的system nonce，不把热前缀复用算作冷读。请求间未主动冷却；混合负载关闭/开启的中位间隔为0.108/0.033秒，纯读入为0.074秒。最高观测功耗分别413.67/405.55/403.99W。

循环时长含少量计数和采样开销，最后一个请求完成后才结束。上述斜率按首个负载请求到实测循环时长末端的遥测窗口计算，存在小于一个采样间隔的边缘误差。温度仍在负载周期内波动；84°C距停止线仅1°C，不能推成全天运行已达到热稳态。

## 64K以上真实恢复、取消与继续

恢复使用本次模型实际回复组成历史，执行A→短B→A；下表为当前恢复请求的引擎日志回执，不用原始输入长度代替恢复量。所有已执行恢复的marker均为 `BOUNDARY_OK`，门槛为恢复至少65536 token。

| 阶段 | 关闭KVRES：68K / 100K恢复token | 完整配置：68K / 100K恢复token |
|---|---:|---:|
| 混合负载前 | 69616 / 102393 | 69627 / 102393 |
| 混合负载后 | 未运行 | 69616 / 102393 |
| 独立同阶段内存补测 | 69625 / 102402 | 69614 / 102391 |

这些marker证明生命周期续接；不证明长检索答案正确，不覆盖P3中两臂长检索错答。

取消只关闭本次拥有的HTTP socket。prefill在进度事件显示 `processed=16384`、`cache=0`、尚未读完约100K且没有输出事件时断连；decode在64个非空SSE事件时断连。**64事件不是64 token**。通过条件为30秒内 `/v1/status.activity.in_flight=0` 且 `/slots.is_processing=false` 连续三次，同一引擎PID仍存活，然后重发或带真实部分输出继续。

| 阶段 | 关闭KVRES：prefill / decode到idle秒数 | 完整配置：prefill / decode到idle秒数 |
|---|---:|---:|
| 混合负载前 | 4.673 / 0.610 | 5.090 / 0.610 |
| 混合负载后 | 未运行 | 4.877 / 0.610 |
| 独立内存补测 | 4.674 / 0.610 | 4.881 / 0.609 |

所有上述取消均真实触发、PID未换、继续请求通过。idle时延含三次轮询确认。独立内存补测中，prefill取消后服务最终记录只读入32768、生成0；说明取消会等待当前chunk边界，不是收到断连就立即停止GPU工作。decode最终记录生成66，而客户端只接收64个非空事件；部分输出、SSE、触发事件、idle轮询及继续请求均保留。

## RAM与锁页内存：同阶段构成

进程内存以下列独立 `memory-pair/` 为准：两臂各14请求全部通过，14组请求body SHA256逐一相同。显式包含GPU审计确认的引擎PID及所有服务线程的子进程；loaded阶段缺少引擎smaps即失败。关闭/开启引擎PID为1398155/1399938，分别有217/236份含引擎的周期样本。完整快照耗时约0.4～0.54秒，系统与进程读取不具原子性。

下表单位GiB，单元格均为 **关闭 / 开启**。RSS/PSS来自引擎smaps_rollup，Swap为该口径；服务进程另存，不将共享页RSS相加当物理总量。

| 引擎构成 | loaded | 100K恢复后 | 缓存填充后idle30秒 |
|---|---:|---:|---:|
| RSS | 42.478 / 42.445 | 47.059 / 48.356 | 47.855 / 49.161 |
| PSS | 42.474 / 42.442 | 47.056 / 48.353 | 47.852 / 49.158 |
| PSS_Anon | 41.860 / 41.847 | 46.365 / 46.360 | 47.161 / 47.164 |
| PSS_File | 0.262 / 0.243 | 0.260 / 0.250 | 0.261 / 0.251 |
| PSS_Shmem | 0.352 / 0.352 | 0.430 / 1.743 | 0.431 / 1.743 |
| Swap | 0.440 / 0.432 | 0.384 / 0.378 | 0.381 / 0.375 |

| 系统构成 | loaded | 100K恢复后 | 缓存填充后idle30秒 |
|---|---:|---:|---:|
| AnonPages | 41.983 / 41.969 | 46.513 / 46.498 | 47.316 / 47.314 |
| Cached−Shmem（避免重复计入Shmem） | 14.671 / 13.024 | 9.373 / 7.638 | 8.994 / 7.296 |
| Shmem | 0.616 / 2.291 | 0.694 / 2.370 | 0.694 / 2.370 |
| SReclaimable | 0.215 / 0.219 | 0.215 / 0.219 | 0.215 / 0.219 |
| SUnreclaim | 0.401 / 0.414 | 0.403 / 0.416 | 0.403 / 0.417 |
| PageTables | 0.092 / 0.095 | 0.101 / 0.104 | 0.102 / 0.105 |
| MemFree | 0.500 / 0.452 | 1.158 / 1.199 | 0.716 / 0.724 |
| MemAvailable | 14.716 / 13.020 | 10.075 / 8.382 | 9.254 / 7.567 |
| Swap使用量 | 0.850 / 0.844 | 0.778 / 0.781 | 0.773 / 0.775 |

两臂的匿名页在历史及缓存填充期间都增长约5.3GiB，不能把loaded到末端的全部增长归给KVRES。开启臂持续多出的系统Shmem约1.676GiB，同时可回收文件缓存更少；这比两次MemAvailable相减更能说明内存去向。其他系统项、PSI、vmstat和完整映射在原始数据中。

### 1.55GiB差额的归因

1. 两臂共同的 `cudaHostRegister` 当前量为42,915,302,400字节（39.967990GiB），日志确认expert arena注册成功。开启KVRES额外出现 **13次各138,413,056字节的cudaHostAlloc**；其他live分配组一致。loaded与qualified阶段的allocation差额均为 **1,799,369,728字节＝1.675794GiB**。
2. `layer.cpp:903–919` 的每层公式为 `pages × kv_block_bytes + 4×256`，本次为 `32768×4224+1024`。12层主状态合计1,660,956,672字节＝**1.546886GiB**，对应日志四舍五入的1.55；MTP再初始化一份同尺寸状态，增加**0.128907GiB**。`generate.cpp:5227` 的日志先于 `mtp.load`（5472）输出。13次调用的共同返回点 `0x136c5c` 只能符号化到 `host_alloc_guarded`，没有逐层栈；“12主层＋1 MTP”是分配字节、初始化顺序和源码共同支持的归因。
3. 13个指针分别落在 `/dev/zero (deleted)` 的共享映射，每个大小135172KiB。加载时13块Rss/Pss/Locked全部为0；两臂系统Shmem差额恰为 **1,757,236KiB＝13×135172KiB**，与按4KiB页取整后的1.675831GiB完全一致。比API请求多39KiB，是13块各取整增加3072字节。
4. 100K恢复后，这13块已有1,376,128KiB（1.312378GiB）计入Rss/Pss，余下约0.363GiB仍未体现在这些映射的RSS/PSS；系统Shmem差额仍为1,757,236KiB。因此RSS差额会随阶段改变，不能用RSS或VmLck/VmPin的零值否定CUDA锁页。

追踪库通过动态libcudart拦截成功的host allocation/register/free/unregister，并记录当前量、峰值、指针和调用点。24MiB探针实际产生4个事件，峰值25,165,824字节，释放后0；当时VmLck/VmPin也都是0。CUDA API的page-locked语义见 [NVIDIA CUDA 12.3文档](https://docs.nvidia.com/cuda/archive/12.3.0/cuda-runtime-api/group__CUDART__MEMORY.html)。

### 峰值与卸载

| 观测口径 | 关闭KVRES | 完整配置 |
|---|---:|---:|
| 同阶段补测：最大观测内核VmHWM | 48.179GiB | 49.480GiB |
| 同阶段补测：周期RSS / PSS峰值 | 48.074 / 48.071GiB | 49.375 / 49.372GiB |
| 同阶段补测：CUDA API outstanding峰值 | 40.651118GiB | 42.326912GiB |
| 其中allocation / registration各自峰值 | 0.683128 / 39.967990GiB | 2.358922 / 39.967990GiB |
| 同阶段补测：最低系统MemAvailable | 9.042GiB | 7.372GiB |
| 同阶段补测：系统Swap最大使用量 | 0.886GiB | 0.885GiB |
| 混合负载的CUDA API峰值 | 40.651137GiB | 42.326931GiB |
| 纯读入支路：VmHWM / CUDA API峰值 | 未运行 | 49.461 / 42.326864GiB |

上述各字段峰值不一定同一时刻。registration范围与RSS有重叠，**不能相加**当总RAM；API峰值是应用可见请求范围，不是CUPTI/驱动内部全部物理锁页量。周期RSS不能保证捕捉亚秒峰值；VmHWM是仍可读取时观测到的内核高水位。混合负载旧主采样遗漏了引擎，不能据此补造它的RSS峰值。

实际存在换页。包含加载和卸载的独立内存窗口，系统swap in为235.13/230.96MiB，swap out为803.11/680.12MiB，major faults为31319/30301；均为系统范围累计增量，不能全部归因模型，也不能宣称无换页。本轮未观察到OOM、CUDA分配失败或内存保护中止。

卸载15秒后两臂引擎均不存在，系统Shmem均回到384KiB、MemAvailable约57.86/57.90GiB。追踪文件末尾仍有随进程存活的KV指针：进程退出不会为所有指针逐一发出free事件，不能把末尾计数当作退出后泄漏；以进程退出、GPU释放和系统内存回落共同确认收尾。

## 执行修订、原始证据与复放

原始目录在29为 `/home/hhtele/strata-lab-4090/workspace/combination/boundaries-20261027`；本地镜像为 [workspace/combination/boundaries-20261027](../workspace/combination/boundaries-20261027/ARTIFACTS.md)。固定采集清单 `RAW_MANIFEST.json` 的984份输入、源码、日志和原始记录全部完成本地SHA256复核。另附 `ANALYSIS.json`、`MAPPING_ANALYSIS.json` 及其生成脚本，不改写原始结果。

- `run/`：适配器误用状态接口结构，在第一个prefill取消触发后出现KeyError。此前8条评分记录通过；取消原始SSE及请求保留，没有补造该条评分。初始源码在 `source-initial/`。
- `run-v2/`：修正源码尚未成功上传时提前启动，已在加载阶段中断。日志和错误修订元数据保留，不计通过。
- `run-v3/`：正式边界尝试，关闭28/29记录通过，唯一失败为热保护中断；开启43/43通过。两臂系统内存、CUDA事件、GPU遥测有效，但主进程枚举只读主线程children，遗漏加载线程创建的引擎；其primary进程快照**不用于引擎RSS/PSS归因**。另有一份显式引擎快照仅为未配对辅助观察。
- `pure-prefill-cfg/`：按登记条件只执行开启臂，含qualification共24/24通过。
- `memory-pair/`：修正为显式引擎PID＋所有线程children，两臂14/14通过。GPU执行源码版本分别冻结于 `SOURCE_MANIFEST.json`、`SOURCE_MANIFEST.supplement.json`；测试从7项增至8项的版本也分开保留。
- 收尾后将同一PID修正合入交付版主boundary runner，memory runner复用该实现；本机和29的8项定向测试再次通过。此版本保存在 `source-package-final/`，**没有用它重跑GPU或替换旧采样**。

使用与当时阶段相应的冻结源码；下列为实际成功推进的三条GPU命令，输出目录需要换成不存在的新路径。原始失败命令及完整参数在各 `console*.log`、plan和修订记录中。

```bash
cd /home/hhtele/strata-lab-4090
LAB_PYTHON=/home/hhtele/strata-0.1.43.1/.venv/bin/python
BOUNDARY_TASK=workspace/combination/boundaries-20261027
COMBO_TASK=workspace/combination/kvres-20261027
COMBO_TREE=workspace/trees/combo-kvres-20261027
$LAB_PYTHON -B tools/combination/run_boundaries.py --config "$BOUNDARY_TASK/config.json" --tree "$COMBO_TREE" --corpus "$COMBO_TASK/corpus.json" --performance-corpus "$COMBO_TASK/performance-corpus.json" --out "$BOUNDARY_TASK/run-v3" --heat-seconds 900 --execute
$LAB_PYTHON -B tools/combination/run_prefill_stress.py --config "$BOUNDARY_TASK/config.json" --tree "$COMBO_TREE" --corpus "$COMBO_TASK/corpus.json" --out "$BOUNDARY_TASK/pure-prefill-cfg" --arm cfg --execute
$LAB_PYTHON -B tools/combination/run_memory_pair.py --config "$BOUNDARY_TASK/config.json" --tree "$COMBO_TREE" --corpus "$COMBO_TASK/corpus.json" --out "$BOUNDARY_TASK/memory-pair" --execute
```

## 工具验证与剩余限制

本机执行 `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_boundaries -q`；29使用 `/home/hhtele/strata-0.1.43.1/.venv/bin/python -B -m unittest tests.test_boundaries -q`，最终均8项通过，含真实本地socket断连、状态接口、预算/usage、loader线程和显式引擎PID覆盖。只编译观测库及可信探针；未重编原生引擎。本轮根仓库 `pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build` 均exit0，日志在原始目录 `local-verification/`。包完整性与范围检查见 [VALIDATION](../VALIDATION.md)。

仍未验证：全天热稳态、完整128K边界、并发客户端取消/服务崩溃/主机重启、生产流量，以及驱动内部全部物理锁页峰值。base热态后续和纯读入支路按保护条件未运行。当前既有质量非劣缺口仍在，不自动修改或恢复生产。
