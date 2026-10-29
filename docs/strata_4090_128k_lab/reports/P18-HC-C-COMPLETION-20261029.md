# P18 · C退出修复与同路径HC数值验证

结论：**C运行和同驻留、同实际分派的HC独立缓冲区对照均PASS。** 本轮两个GEN1均完成计算、SAVE、退出及资源释放，监控没有再误报；3325条原始记录、完整logits和有效终态均逐字节一致。自然A/C仍不逐bit，保留为`NATURAL_C_NUMERICAL_DIFFERENCE`，没有改写旧失败或宣称任务质量通过。

## 退出顺序的修复

此前仅在`FileNotFoundError`后检查`poll()`和GPU残留PID，仍让监控线程跨过主动`QUIT`的退出边界。29的CPython源码确认，另一个线程持有waitpid锁时，`poll()`可以暂时返回None；旧日志未记录异常瞬间的poll值，不能断言旧失败必然命中这个分支。

这次在真实`run_native`协议路径改为：GEN/DONE及SAVE完成后，调用`Guard.finish()`停止并join监控线程，确认线程结束且无既有护栏错误，再发送QUIT并检查退出码。监控未停、既有资源/归属错误、非零退出仍失败；`wait_released`继续检查GPU与18089释放。无需根据退出过程中`/proc`和NVML快照的相对先后猜测正常结束。

新增退出顺序用例在旧代码上实际失败：QUIT发生时监控尚未停止。修复后10项护栏测试在本地和29通过，包括监控未停止、已有护栏失败、运行中身份错误及外来PID拒绝。两个真实请求均生成`guard-finished.json`，确认监控在QUIT前停止；最终telemetry的两个abort_reason均为null。旧P16/P17失败保持原状态。

## C的数值对照

P17中的自然C改变了驻留和CPU/GPU分派，与自然A的最终数值不同，不能仅凭这个差异判断HC复用损坏。用户本次要求修复C并完成测试；首个新请求前登记本轮对照：

1. 运行一次自然C，保留其实际驻留、CPU专家集合、路由、行映射、分组、MMQ参数、MTP batch及有效状态。
2. 用同一引擎运行一次独立HC缓冲区对照：保留C的少借槽、驻留和实际CPU分派，只把四个HC临时数组改为独立cudaMalloc。路由、状态等由引擎重新计算，逐字段与C比较，不注入C的数值结果。
3. 同路径原始字节、最终logits和有效状态必须全部相同；容差仍为0。直接A/C另存诊断，不以其代替同路径对照，也不把其差异改成PASS。

控制分支在缓存与借区已初始化、实际4090块开始时分配四个数组，按原分配容量4096保留垫片，额外259,523,584 bytes（约248MiB）。不改C的借区容量或缓存配置，不支持其他shape的自动回退。结束时同步相关流、恢复原指针并释放四份分配。实际执行标记及精确bytes是捕获验收的必需条件，旧二进制或未进入控制分支不能冒充有效对照。

这是一项诊断控制，额外显存不计作候选收益。HC共享布局、权重、CPU/GPU计算kernel、分组及浮点规约均保持；没有关闭CPUshare、修改gold或放宽数值容差。

| 检查 | 实测结果 |
|---|---|
| 输入/配置 | 冻结4095-token GEN1，实际主prefill4090、48层FFN；原完整配置保持 |
| 运行次数 | 自然C一次、同C分派独立HC对照一次；共2个新GEN1，无额外重试 |
| 原生退出/捕获 | 两次exit0、CAPTURE_VALID；监控均在QUIT前停止 |
| raw覆盖 | 3325条、1,121,572,804 bytes；初态、实际分派/路由/驻留/分组、目标HC/下一half缓存及完整chunk R逐字节一致 |
| 最终logits | 248,320个有限FP32；0 bit差异，max abs=0 |
| 有效终态 | 298,656,148 bytes全部一致；完整文件checksum通过，按既有合同排除25,168无效/非数值字节 |
| MTP | 实际有效范围[0,4090)，batch及终态PLE标量一致；GEN1没有执行后续draft |
| 同路径数值门 | `CC_CONTROL_ANALYSIS.json: PASS`，无raw、metadata或state差异 |
| 自然A/C | 42层on_cpu记录变化；全部248320个logits值bit不同，max abs=1.0783228874206543；有效状态首个登记差异字段live.gdn；原差异结果保留 |

因此，在这个冻结fixture和实际C执行路径下，HC地址复用没有产生相对独立缓冲区实现的新增数值差异。直接A/C的差异同时存在于独立HC缓冲区的C路径，不能将其作为HC共享区损坏的证据。该结果不建立自然A/C全局确定性、不修复原六个任务FAIL，也不覆盖生命周期或所有physical cache槽的安全性。

## 冻结产物与验证

同一P6 v0.2.7 `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`、原权重和原4095-token输入，输入SHA256仍为`3c4f5016a093346a0c6f8aaeec401592c15f9326c044fe89051ba7b2f168367d`。复用P17的B PASS，不重跑A/B。

新隔离树为29的`/home/hhtele/strata-lab-4090/workspace/trees/hc-c-complete-20261029`；新引擎SHA256为`06acae93fce0d690074a76695f5aedea6b2593f80a5ad225217e7bb99ba52f67`。两个对照使用同一二进制；新增C++代码仅为受冻结geometry约束的独立HC诊断控制，不是生产引擎修改。原P15树的源码和二进制hash仍匹配旧回执。

- `python3 -B -m unittest discover -s docs/strata_4090_128k_lab/tests -p test_reference_guard.py -v`：10项PASS，本地/29均执行。
- `python3 -B -m unittest discover -s docs/strata_4090_128k_lab/tests -p test_oracle_full_driver.py -v`：6项PASS，本地/29均执行；覆盖独立分配标记必需和同路径分派必须严格相同。
- 隔离CUDA12.3/sm89引擎161项构建完成、exit0；编译警告保留原始日志。
- `pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build`均exit0，保留既有Phaser大chunk警告。

[预登记](../workspace/combination/hc-c-complete-20261029/full-request/PREREGISTRATION.json)、[C运行](../workspace/combination/hc-c-complete-20261029/full-request/natural-c/RUN_RESULT.json)、[独立缓冲区运行](../workspace/combination/hc-c-complete-20261029/full-request/replay-control/RUN_RESULT.json)、[严格同路径比较](../workspace/combination/hc-c-complete-20261029/full-request/CC_CONTROL_ANALYSIS.json)、[自然A/C诊断](../workspace/combination/hc-c-complete-20261029/full-request/AC_ANALYSIS.json)、[完成回执](../workspace/combination/hc-c-complete-20261029/COMPLETION.json)、[资源/生产保护](../workspace/combination/hc-c-complete-20261029/FINAL_PROTECTION.json)。

## 归档和停止边界

6740份原件、2,979,436,197 bytes登记长度与SHA256；87份本地导出文件逐项匹配远端清单。大raw、SAVE和二进制保留29的`/home/hhtele/strata-lab-4090/workspace/combination/hc-c-complete-20261029`，不声称完成大文件双端同步。旧运行未覆盖；旧清单hash和原源码/引擎身份已核验，旧raw全内容hash复用前轮证据，本轮未重复遍历。

生产13个保护文件hash不变，服务保持`inactive/dead/enabled`。本轮两PID退出，GPU最终1MiB、44°C、无计算进程，18089释放，自动续测PAUSED。73份资源样本中峰值53°C、显存23872MiB、最低MemAvailable10940MiB，两个abort_reason均为null；这些数值只作护栏证据，不作性能测量。

本轮C运行及同路径HC等价验证已完成。真实4096/16K边界、生命周期、sanitizer、成本链、性能和质量采用均未运行；原六FAIL及旧退出失败保留，正式性能样本0。没有提交、推送、部署或修改生产配置。
