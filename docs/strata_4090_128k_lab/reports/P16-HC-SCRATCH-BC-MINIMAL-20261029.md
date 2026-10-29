# P16 · HC-only scratch B/C 最小验证

结论：**B运行护栏FAIL，按用户要求在首个失败处停止；C未运行，未重试。** 本轮仅新增1个GEN1请求。B已完成的原始数值和有效终态与A逐字节相同，但运行FAIL及AB门FAIL保持，不能将离线数值证据改写为B整体通过。

## 范围与身份

用户授权仅运行一次B；B通过才运行一次C；最多新增两个GEN1，遇到失败就停。不运行后续边界、生命周期、sanitizer、成本链或性能测试，不改生产，测完保持生产停机。

复用[P14/P15](P14-P15-NUMERICAL-REPLAY-ORACLE-20261029.md)的完整请求A/A，不重跑A。仍为冻结4095-token输入（SHA256 `3c4f5016a093346a0c6f8aaeec401592c15f9326c044fe89051ba7b2f168367d`）、原完整配置及实际4090-token主prefill、48层FFN、GEN1。引擎SHA256仍为`0070efba6dc1196bdf5963f61686fa7e53686763c991042d901c104c49f4cde9`；源码及原有执行工具均未改。

本轮补充登记在首B请求前写入，限制B/C各一次、零重试、首失败停止。执行前核验原oracle的7459份文件、A/A PASS、工具/源码/二进制、权重文件元数据及生产保护hash；取得原GPU串行锁并确认无计算进程。旧登记和旧完成回执不覆盖。

## B实际结果

| 检查 | 实际结果 |
|---|---|
| 请求数 | B=1、C=0；输入4095、`max_new=1`；实际完成1块4090、48层FFN |
| 布局 | `xn16/lo/lo16/gated`实际放入共享region，保留A的借区容量；启动T16384时cap=7,656,345,600、carve=6,441,848,576、region=3,907,494,912 bytes |
| 实际relayout | 分配T4096，cap=2,814,156,800、carve=2,503,544,576、region=976,905,216 bytes；这是分配尺寸，实际计算仍为T4090，不构成4096边界测试 |
| raw记录 | 3329字段、1,121,573,360 bytes；实际执行逐字段memcmp，与A参考全部一致，完成标记确认3329条参考全部消费 |
| 最终logits | 248,320个FP32，全有限；0 bit差异、max abs=0 |
| 有效状态 | SAVE完整文件298,682,028 bytes；checksum核验后比较298,656,148 bytes，全相同，按原合同排除25,168无效/非数值字节 |
| MTP及标量 | 实际有效MTP范围[0,4090)，batch、GEN1未调用后续draft、终态PLE标量均与A一致 |
| 运行状态 | `NATIVE_EXIT=0: [Errno 2] No such file or directory: '/proc/2266238/exe'`；RUN_RESULT=FAIL，AB_ANALYSIS=FAIL |
| C | NOT_RUN_B_FAILED；没有启动C、没有更换phase重试 |

引擎已正常exit0，并完成DONE、SAVE及oracle COMPLETE；监控器在退出窗口读取已消失的`/proc/<pid>/exe`失败。现有护栏只在“进程已退出且再次查询GPU已无计算进程”同时成立时放行；该修复未覆盖本次退出窗口。记录中的最后一次GPU采样仍列出本轮PID及`[No data]`；最终资源核查已无该PID。没有发现数值差异，但本轮仍按执行失败停止，不在本轮修护栏或重跑B。

正常AB分析因B运行FAIL而拒绝验收，问题为`CAPTURE_NOT_VALID: replay-b`。随后只离线读取已经产生的文件：检查完整raw覆盖、实际reference memcmp记录、logits、有效SAVE及执行元数据；结果单列为`NUMERIC_BYTES_EQUAL_BUT_RUN_FAIL`，没有改RUN_RESULT或AB门，也未启动额外引擎。

## 证据与收尾

- [补充登记](../workspace/combination/oracle-replay-20261029/bc-minimal-20261029/PREREGISTRATION.json)、[B运行回执](../workspace/combination/oracle-replay-20261029/full-request/replay-b/RUN_RESULT.json)、[AB门结果](../workspace/combination/oracle-replay-20261029/full-request/AB_ANALYSIS.json)。
- [离线字节对账](../workspace/combination/oracle-replay-20261029/bc-minimal-20261029/OFFLINE_BYTE_INSPECTION.json)、[本轮完成回执](../workspace/combination/oracle-replay-20261029/bc-minimal-20261029/COMPLETION.json)、[生产/资源保护](../workspace/combination/oracle-replay-20261029/bc-minimal-20261029/FINAL_PROTECTION.json)、[新增文件清单](../workspace/combination/oracle-replay-20261029/bc-minimal-20261029/RAW_MANIFEST.json)。
- 本轮3356份新增证据文件登记长度和SHA256；raw二进制及SAVE保留在29的`/home/hhtele/strata-lab-4090/workspace/combination/oracle-replay-20261029/full-request/replay-b`。本地导出26份元数据、日志、logits小文件和对账结果，逐项长度与SHA256匹配远端清单；大raw/SAVE留在29，不声称完成双端同步。
- 原oracle7459份文件及P13原187份raw hash不变，生产13个保护文件hash不变。权重仅复核既有身份对应的文件元数据，没有重做全权重内容hash。
- 本轮PID2266238退出；GPU最终1MiB、44°C、无计算进程；18089可用；生产`inactive/dead/enabled`，自动续测保持PAUSED。
- 39份监控样本中峰值52°C、显存23618MiB、最低MemAvailable11008MiB。它们只用于本次资源护栏核查，不构成性能测量。

原六FAIL保留。未执行C及后续边界、生命周期、sanitizer、成本链或性能；正式性能样本0。未改引擎、运行工具或生产配置；没有提交、推送或部署。复用上轮工具单测及仓库五项pnpm检查证据，本轮未重复运行。

本次给出了固定分派下HC地址复用的正向数值证据；C的实际少借槽路径仍无计算验证。继续前应先处理退出护栏竞态，并另行授权后续请求；本次范围到此停止。
