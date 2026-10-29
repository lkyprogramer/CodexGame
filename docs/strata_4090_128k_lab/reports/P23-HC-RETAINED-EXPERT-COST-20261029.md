# P23 · HC保留专家的真实成本诊断

结论：**PASS_MECHANISM_SIGNAL**。唯一一对冻结100K请求确认，C少借的601个槽保留了真实路由命中的专家，并减少实际专家传输。满足进入既定性能测试的成本门；本对含诊断日志和原有GPU事件计时，不计作正式性能样本，不代表可采用。

P20同C路径的16K逐字节数值、P21八请求生命周期、P22完整memcheck证据直接复用，没有重跑。原六个任务FAIL保持。

## 冻结配置与覆盖

通过`jssh 29`，A→C各一个fresh engine、各一个工作请求，无重试。恢复原EAGER加载、`--expert-cache auto`、实际10272槽/17055MiB、冻结profile、int8 KV/resident20480、MAX4096/AUTO16384、MTP及原采样。未带入P22专用异步graph启动、managed HC、raw oracle或生命周期dump；生产配置未改。

两臂均为102400输入、2048输出、reused0、read102400。原body SHA为`70bca1817c37adeacd59038f25b6a5d622efa3163497ee54b0719cddb3f9c563`，token文件SHA为`89110d268d1dea535a776a4f5aba2178ec43780c3448deed2f3935bc6e59cac7`；原模板重新渲染的102400 IDs完全相同。

每臂实际执行6个16384块加一个4091块，共102395个batched prefill token、336条FFN层记录。其余5个token没有冒充batched覆盖。所有记录为有效ordinary路径，按每层`cnt`、实际驻留mask和CPU选择核对，不使用fused路径中未更新的计数。缓存初始全映射和变长slot_offsets两臂相同；唯一loan均完成实际H2D回填和同步。

## 实际收益信号

| 指标 | A | C | A减C |
|---|---:|---:|---:|
| prefill专家H2D bytes | 225085056000 | 217935795200 | 7149260800 |
| 借槽回填bytes | 7656345600 | 6618342400 | 1038003200 |
| 两项专家传输合计bytes | 232741401600 | 224554137600 | **8187264000** |
| 原compute流暴露copy等待ms | 2207.179006 | 2090.346880 | **116.832126** |
| 回填wall ms，单独列示 | 631.451215 | 546.126102 | 85.325113 |

601个实际专家ID对应1038003200bytes（约990.001MiB）变长槽。每个16K块实际命中其中581–597个专家，C路由行数为181181–191126；最后4091块命中591个、47401行。六个16K块的实际H2D减少量分别严格等于这601个专家的真实blob bytes。短块按有效路由和CPU分派复算，未套用全量stream规则。完整ID、slot、blob长度、逐块命中及传输差值保存在`ANALYSIS.json`。

H2D记录来自原六处`cudaMemcpyAsync`的真实长度参数，issuer计数只有一个写线程，原join后才读取；回填按底层blob/parts实际提交字节记录。未新增CUDA调用、同步、timer fold、数学或分派操作。传输字节需要无错误请求及原有同步完成才验收。

暴露等待使用原`pt.fold()`后的`kPfWaitCopy`，按完整`run_impl`范围核对。没有把所有kernel/copy累计时间当成关键路径，也没有把host等待、GPU等待和回填wall相加。A/C自然路由与CPU分派允许按原算法变化；尾块已观测到少量差异，因此不把全部差值归因为单一算子的加速。

## 检查、审查与归档

首个GPU请求前固定原登记、验证补充、驱动/分析器/测试SHA。独立审查发现分析器误把单卡`PfPart.dev=-1`要求为0；发送请求前已按冻结源码修复，并加入错误设备负例。未因此消耗或重跑GPU样本。

`python3 -B -m unittest discover -s tests -p 'test_hc_cost*.py' -v`本地和29均**11项PASS**，包括保留原CUDA操作及顺序、去插桩逐字恢复、真实计数/loan/refill/覆盖缺失拒绝。独立审查实际运行本地11项测试并只读核对源码；没有执行SSH或GPU。同步时29无rsync，改用scp；早期7项及修正前11项CPU日志均保留，没有充当最终验收。

[完整分析](../workspace/combination/hc-cost-20261029/ANALYSIS.json)、[预登记](../workspace/combination/hc-cost-20261029/PREREGISTRATION.json)、[验证合同](../workspace/combination/hc-cost-20261029/VALIDATION_ADDENDUM.json)、[A覆盖](../workspace/combination/hc-cost-20261029/A/COVERAGE.json)、[C覆盖](../workspace/combination/hc-cost-20261029/C/COVERAGE.json)、[收口保护](../workspace/combination/hc-cost-20261029/FINAL_PROTECTION.json)、[原件清单](../workspace/combination/hc-cost-20261029/RAW_MANIFEST.json)、[归档回执](../workspace/combination/hc-cost-20261029/ARCHIVE_RECEIPT.json)。

69份、13101388bytes原件已复制本地并逐一核对长度与SHA；清单SHA为`6544f4d8d9e7f2ec6b31e2e0b0782982e9e96460fd98228042db253d7b955416`。临时私有server配置没有导出，退出后其key已移除。隔离构建二进制留29，身份记录于`BUILD_COMPLETE.json`。

152个护栏样本，峰值69°C/23680MiB，最低MemAvailable10564MiB，两个abort_reason均null。收口时生产13项保护SHA不变、服务inactive/dead，GPU1MiB且无计算进程、18089释放。随后按已授权阶段进入P24，仍保持原六FAIL和独立任务质量门。
