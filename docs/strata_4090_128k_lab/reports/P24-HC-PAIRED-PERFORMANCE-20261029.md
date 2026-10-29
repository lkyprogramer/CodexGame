# P24 · HC-only正式配对性能验证

结论：**PERFORMANCE_GATE_NOT_MET，当前HC候选不采用。** 已完成原登记的20个fresh engine、24个工作请求；全部请求验收PASS，零失败、零替补、零重试。100K冷读TTFT改善0.824%，95% CI[-0.035%,1.804%]，未达到改善≥4%且CI下界>0的门。完整decode用时增加4.428%，C/A时间比CI上界1.068783，超过非劣门1.02。

P22完整memcheck和P23真实保留专家成本门均PASS；P20同C路径数值与P21生命周期证据直接复用，没有重跑。601个保留专家和约8.19GB传输减少并未转化为本次所需请求收益。原六个任务FAIL保持，任务质量采用门未通过；未改生产、未部署。

## 主指标：六个完整配对轮次

按原AC/CA/CA/AC/AC/CA顺序执行。同body、102400输入、固定2048输出、read102400/reused0；每次使用独立引擎。每个完整A/C轮次为重采样单位，穷举6^6=46656组log-ratio bootstrap，不按token或同一引擎内请求重采样。wall和decode分别验收，没有用tokens/s或窗口外推代替完整请求。

| 指标 | A中位数(s) | C中位数(s) | C/A几何比 | 改善率及95% CI | C/A 95% CI | 门 |
|---|---:|---:|---:|---|---|---|
| 冷读TTFT | 27.099109 | 27.108883 | 0.991756 | 0.824% [-0.035%, 1.804%] | [0.981959, 1.000352] | FAIL：改善不足4%，CI跨零 |
| 完整wall | 42.841070 | 43.362313 | 1.009464 | -0.946% [-1.749%, -0.146%] | [1.001461, 1.017491] | PASS：CI上界≤1.02 |
| 完整decode | 15.512050 | 16.235100 | 1.044275 | -4.428% [-6.878%, -2.087%] | [1.020868, 1.068783] | FAIL：CI上界>1.02 |

负改善率表示C耗时更长。完整wall虽满足≤2%的非劣边界，不能据此宣称更快；主TTFT与decode两项门均未通过。

| 配对轮次 | 顺序 | A TTFT(s) | C TTFT(s) | wall C/A | decode C/A |
|---|---|---:|---:|---:|---:|
| 1 | A/C | 26.835087 | 26.357183 | 0.992953 | 1.016080 |
| 2 | C/A | 27.033022 | 26.247437 | 1.011271 | 1.085804 |
| 3 | C/A | 27.143054 | 27.197287 | 1.002187 | 1.004540 |
| 4 | A/C | 27.055164 | 27.146337 | 1.021240 | 1.057923 |
| 5 | A/C | 27.264838 | 27.175944 | 1.007586 | 1.027378 |
| 6 | C/A | 27.188236 | 27.071428 | 1.021853 | 1.076610 |

## 支持性结果：只描述，不并入主统计

4K为原冻结4095-token请求，两对均输出2048、read4095/reused0。

| 4K配对 | A TTFT(s) | C TTFT(s) | A wall(s) | C wall(s) |
|---|---:|---:|---:|---:|
| 1 | 3.549938 | 3.418559 | 19.467206 | 18.773014 |
| 2 | 3.452379 | 3.525917 | 18.792385 | 18.679856 |

prime→append沿用原body及exact评分，不根据生成文本改写历史。四个引擎均精确回答ACK/1730；prime输入32771、输出2、reused0；append输入35993、输出5、实际复用32764、新读3229。max_tokens32为上限，没有要求输出恰好32。本项是真实warm append，不是真实compaction回放。

| 配对/臂 | prime TTFT(s) | append TTFT(s) | append wall(s) | 评分 |
|---|---:|---:|---:|---|
| 1/A | 8.259454 | 2.988993 | 3.067696 | ACK/1730 PASS |
| 1/C | 8.234853 | 3.083677 | 3.165162 | ACK/1730 PASS |
| 2/A | 8.373404 | 3.115941 | 3.194347 | ACK/1730 PASS |
| 2/C | 8.214232 | 3.113701 | 3.183163 | ACK/1730 PASS |

## 构建、测量和验证边界

复用P13纯HC二进制，SHA256为`9a6b441da4933d4de8c9ba88e0cdfc83d755c90ed99b184a1b0ae712f2fc00bb`，prefill源码SHA为`9deeead6286f8a1d47a6e8e77a41f2100f73cf66f5485dba057680d582293fd5`。六份Python port、原generate.cpp、源码和二进制在每次启动前核对；A/C只改变HC_REGION。原EAGER、auto10272槽、profile、KV int8/resident20480、CPUshare MAX4096、AUTO MAX16384、MTP和采样保持。

最终配置通过ready.common.env的None真正移除prefill/decode计时变量；设为0仍会启用的STRATA_PREFILL_TIMING没有残留。实际/proc环境逐引擎核对。正式臂不带P23成本、raw oracle、managed HC、生命周期dump、profiler或异步graph控制。每个请求记录原始SSE、最终usage/timing；启动、冷却和退出/端口回收不计入请求耗时。

GPU时钟及实际native PID的RSS/PSS/Swap、fault与系统内存按请求前后及约1Hz采样。所有20个引擎均有完整native内存及clock记录，无已退出进程样本；共600条采样和边界记录。SM时钟范围2520–2775MHz；不是锁频实验，没有做时钟归一化。

峰值GPU 71°C/23708MiB，最低MemAvailable 10247MiB，1284个资源护栏样本，无护栏终止。native最大RSS 46198.879MiB、最大PSS 46200.078MiB；各引擎最大VmSwap范围330.867–572.168MiB。全部20个引擎运行均观测到major fault及系统swap活动，未剔除或补替样本。这些数据不能证明变化由HC单独造成，也不能声称零swap或无内存扰动。

本结果限于同一台29号机、本次窗口、原冻结请求及六对样本；不推广为所有上下文、负载或新模型的结论。资源护栏通过不代表没有内存噪声。系统swap计数覆盖整机，不能专属归因于该引擎。模型在本阶段复核冻结资产元数据和小文件SHA，未重新全内容hash大模型；前后资产记录完全相同。

本地及29执行`python -B -m unittest discover -s tests -p test_hc_perf.py -v`：5项PASS，覆盖固定20/24顺序、46656整对重采样、TTFT与wall/decode分离门、失败/短输出/错hash/热缓存拒绝、真正删除继承计时开关，以及完整主指标与失败支持层的分别报告。独立代码审查者实际运行本地5项测试，未SSH/GPU。P23的11项测试和P22的4项证据复用。

本轮此前的`pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build`均exit0；后续仅Python实验工具和文档变化，未重复运行。已解析本次7份Python新源码并检查本次入口文件diff。全包diff检查仍提示工作区既有`lab/statistics.py:205`末尾空行，本次未改该文件。

## 归档与停机交还

[完整统计](../workspace/combination/hc-perf-20261029/ANALYSIS.json)、[预登记](../workspace/combination/hc-perf-20261029/PREREGISTRATION.json)、[实际计数](../workspace/combination/hc-perf-20261029/COMPLETION.json)、[逐引擎资源](../workspace/combination/hc-perf-20261029/RESOURCES.json)、[最终保护](../workspace/combination/hc-perf-20261029/FINAL_PROTECTION.json)、[归还复核](../workspace/combination/hc-perf-20261029/HAND_BACK.json)、[原件清单](../workspace/combination/hc-perf-20261029/RAW_MANIFEST.json)、[双端校验回执](../workspace/combination/hc-perf-20261029/ARCHIVE_RECEIPT.json)。

429份、49725277bytes原件已导出并逐一核对长度与SHA。清单SHA为`e977dad4a24d4c1430debef010aafc758f87e2440b9ec3161f3ccd3b6eefda30`。首次解压早于传输完成，待传输exit0后对同一原件包重新解压并核验；没有新增GPU请求。临时私有配置不导出，退出后key已移除；纯HC二进制留29，归档保存其hash、两份C++及六份Python port源码。

独立验收者在本地逐一复核429份原件，重新计算全部统计并与ANALYSIS完全一致；另核对24条原始请求/响应/评分/SSE结束、20个唯一native PID和实际资源记录。未执行SSH/GPU或重跑CPU测试。

最终13项生产保护SHA不变、服务inactive/dead且enabled；GPU1MiB且无计算进程，18089释放，全部本轮拥有的PID已退出。使用jssh 29，未改生产配置、systemd、驱动或CUDA；自动续测保持PAUSED。当前HC性能筛查收口，不自动扩大到其他候选。
