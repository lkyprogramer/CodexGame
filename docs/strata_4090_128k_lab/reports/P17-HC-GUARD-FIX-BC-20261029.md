# P17 · 退出护栏修复与B/C限额重跑

结论：**本轮B运行及AB门通过；C完成计算后再次触发退出护栏FAIL，AC门FAIL，按用户要求停止。护栏修复仍不完整。** 本轮新增B/C各1个GEN1，共2个，未追加请求或重跑。C已产生文件的离线对账还显示logits及有效状态与A不同；C不能验收通过，也不能将差异直接归因于HC复用。

## 护栏变更与回归

只修改实验工具`tools/v027/run_reference_logits.py`的`Guard.loop`：遇到`FileNotFoundError`且Popen已观察到进程退出时，重新读取GPU列表；新列表为空或只残留该自有PID可结束监控，出现其他PID仍失败。`wait_released`仍须确认GPU和实验端口最终释放；原生非零退出、协议或数值错误的失败逻辑保持。

新增两个回归：已退出的自有PID仍被NVML列出；该残留PID与外来PID同时出现。前者在修复前稳定失败，其余5项通过；修复后6项在本地及29均通过。覆盖仍在运行时的身份错误、外来PID、其他ownership异常等既有拒绝行为，没有削弱断言。

本轮实际C再次出现`/proc/<pid>/exe`读取失败，证明上述修复仅覆盖一类退出窗口。C最后GPU采样仍列出自有PID及`[No data]`，原生引擎随后确认exit0。日志没有记录异常捕获瞬间的`poll()`结果和二次GPU快照，不能唯一确定剩余窗口；不声称退出竞态已彻底解决。按首失败停止要求，没有继续修改护栏或增加测试请求。

## 冻结输入与实际运行

复用已通过的[P14/P15 oracle](P14-P15-NUMERICAL-REPLAY-ORACLE-20261029.md)。输入仍为冻结4095个token（SHA256 `3c4f5016a093346a0c6f8aaeec401592c15f9326c044fe89051ba7b2f168367d`），GEN1实际主prefill为4090、48层FFN。原完整配置及引擎不变，二进制SHA256仍为`0070efba6dc1196bdf5963f61686fa7e53686763c991042d901c104c49f4cde9`。

新登记和运行位于`workspace/combination/oracle-replay-20261029/bc-guardfix-20261029`；以已有A捕获目录作为参考。B/C各一次、首失败停止、零额外重试在运行前登记。旧[P16 B失败](P16-HC-SCRATCH-BC-MINIMAL-20261029.md)、旧登记、原始数据和验收状态均保留。没有重建引擎或重跑A。

| 检查 | B：相同借槽和固定分派 | C：实际少借槽和自然分派 |
|---|---|---|
| GEN1次数 | 1 | 1，仅在本轮AB PASS后启动 |
| 原生结果 | 完成DONE/SAVE/exit0 | 完成DONE/SAVE/exit0 |
| 运行护栏 | 正常，`CAPTURE_VALID` | FAIL：`NATIVE_EXIT=0: [Errno 2] No such file or directory: '/proc/2267846/exe'` |
| 正式验收 | AB PASS | AC FAIL：`CAPTURE_NOT_VALID: natural-c` |
| raw | 3329字段、1,121,573,360 bytes与A逐字节一致 | 捕获3533条记录，无A参考回放；记录数变化不等于数值损坏 |
| logits | 248,320个有限FP32，零bit差异 | 离线比较：248,319个值bit不同，全部有限，max abs=0.734858512878418 |
| 有效终态 | 298,656,148 bytes全部相同 | 离线比较不同，首个登记差异字段`live.gdn` |
| CPU专家分派 | 与A逐字节一致 | 43层`on_cpu`记录与A不同 |

对C的额外处理仅为读取已生成文件，结果单列`DIAGNOSTIC_ONLY_RUN_FAIL`，不修改运行或AC门FAIL，不启动额外引擎。比较使用相同的实际MTP有效范围[0,4090)，按原合同排除无效页尾等字节；状态文件checksum先核验，再比较有效区域。43层分派差异支持“执行数值路径发生变化”的解释，不足以证明差异只来自调度，也不足以证明是HC复用错误；没有同输入同实际执行路径的C归因对照。

C启动T16384的借区cap为6,618,342,400 bytes，原布局/保留借槽B为7,656,345,600 bytes，少1,038,003,200 bytes；共享region仍为3,907,494,912 bytes。实际请求relayout分配T4096时，B/C的cap分别为2,814,156,800/2,554,240,000 bytes。分配尺寸不代替实际计算块，本轮不构成真实4096或16K边界验证。

## 验证、证据和收尾

- 最小回归：`python3 -B -m unittest discover -s docs/strata_4090_128k_lab/tests -p test_reference_guard.py -v`，6项PASS；29执行同一组6项PASS。修复前失败和修复后结果均归档。
- 仓库要求：`pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build`均exit0；保留既有Phaser大chunk警告。这些检查不构成护栏所有退出窗口已覆盖的证明。
- [补充登记](../workspace/combination/oracle-replay-20261029/bc-guardfix-20261029/PREREGISTRATION.json)、[AB结果](../workspace/combination/oracle-replay-20261029/bc-guardfix-20261029/AB_ANALYSIS.json)、[C运行结果](../workspace/combination/oracle-replay-20261029/bc-guardfix-20261029/natural-c/RUN_RESULT.json)、[C离线对账](../workspace/combination/oracle-replay-20261029/bc-guardfix-20261029/OFFLINE_C_INSPECTION_NOT_GATE.json)。
- [完成回执](../workspace/combination/oracle-replay-20261029/bc-guardfix-20261029/COMPLETION.json)、[最终保护回执](../workspace/combination/oracle-replay-20261029/bc-guardfix-20261029/FINAL_PROTECTION.json)、[原件清单](../workspace/combination/oracle-replay-20261029/bc-guardfix-20261029/RAW_MANIFEST.json)。原始raw和SAVE留29，本地56份小文件逐项长度和SHA256匹配远端清单；不声称大文件双端同步。
- 原oracle7459文件、P16新增3356文件及P13原187份raw hash不变；生产13个保护文件hash不变，原引擎及其C++源码不变。权重仅核对既有身份对应的文件元数据，没有重新全内容hash。
- 最终自有PID均退出，GPU1MiB、45°C、无计算进程，18089释放；生产仍`inactive/dead/enabled`，自动续测PAUSED。
- 76份监控样本中峰值53°C、显存23618MiB、最低MemAvailable11028MiB；只作为资源护栏证据，不作为性能样本。

原六项FAIL保留。边界、生命周期、sanitizer、成本链和性能均未运行，正式性能样本0。只修改实验护栏及其回归测试，没有修改生产配置，没有提交、推送或部署。后续仍需解决残余退出竞态，并单独归因C的数值/状态差异；本轮范围已停止。
