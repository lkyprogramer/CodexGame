# P19 · HC真实4096/16384块验证

结论：**真实4096块的同路径数值门PASS；自然C完成真实16384块，但其独立HC对照因额外显存不足而在主计算前拒绝。16K等价性仍未建立，按预登记首失败停止。** 本轮4次GEN1尝试、3次完整完成、零重试，正式性能样本0。没有观察到16K数值不一致，也不能把未完成的对照写成PASS。

## 范围与方法

用户授权按“真实边界及生命周期→一对长请求成本信号→有信号才做正式配对性能”的阶段门继续，并要求通过`jssh 29`访问。本轮先执行边界门，未启动后两阶段。生产配置不改、服务继续停机，自动续测保持PAUSED。

复用P18的4090块数值证据，不重跑A/B或原六个失败任务。仍为P6冻结commit `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`、原权重、EXACT6、KV int8/resident20480、spec4/minp0.5、15 workers＋host、CPUshare MAX4096、AUTO MAX16384及原checkpoint规则。`--vram-reserve-mib 974`、专家缓存和采样配置均未调整。

4096恰是实际分派边界：更小的块允许CPUshare；达到4096的块进入streamed路径。旧oracle明确拒绝该路径。因此在新的隔离树扩展诊断记录，保留原kernel、规约、分组和CPUshare规则，增加实际streamed/fused判定、驻留映射及fused行映射记录。实测两种块的48层均为`stream_all=true, fused_l=false`；fused记录分支只有源码/补丁检查，未取得GPU动态覆盖。

在原4095-token fixture的末尾assistant turn之前补普通token13，分别冻结4101和16389个输入token，最后turn边界位于4096和16384。没有关闭checkpoint来制造覆盖。实际chunk、48层FFN、MTP计算区间、HC/下一half缓存、完整chunk R、logits及有效SAVE分别验收；分配T不能代替计算T。

独立HC控制在C的借区及驻留已经确定后，仅将`xn16/lo/lo16/gated`改用四份独立cudaMalloc，按实际分配T保留垫片；借槽、resident和实际分派保持C路径。对照逐字段读取参考并重新计算，容差仍为0。所需额外显存不足时拒绝，不减缓存或改reserve。

## 实测结果

| 阶段 | 真实计算/捕获 | 数值验收 |
|---|---|---|
| `c-4096` | 单块T4096、48 FFN，3887条raw，完整DONE/SAVE/正常退出 | CAPTURE_VALID |
| `control-4096` | 同C借槽/分派，四份独立HC分配额外259,523,584 bytes；完整完成 | 3887条/1,123,191,816 bytes全部逐字节一致 |
| 4096配对 | 248,320个有限FP32 logits，实际MTP范围[0,4096) | logits零bit差；298,726,276 bytes有效终态全部一致，完整文件checksum通过；排除77,200个无效/非数值字节 |
| `c-16384` | 单块T16384、48 FFN，4019条/4,136,034,468 bytes raw；完整DONE/SAVE/正常退出；logits全有限 | CAPTURE_VALID，实际MTP范围[0,16384)；单臂运行不建立HC等价性 |
| `control-16384` | 初始化完成后、请求主chunk计算前拒绝 | RUN_RESULT=FAIL，PAIR-16384=FAIL；16K数值对照NOT_PROVEN |

16K失败日志明确记录：

```text
P19_CONTROL_MEMORY {"free_bytes":539492352,"required_bytes":1038091264}
P15_ORACLE REJECT private HC control VRAM headroom
```

即实际剩余**514.5 MiB**，对照需要**990.00098 MiB**，差**475.50098 MiB**。该phase没有完成主chunk、没有logits元素、没有SAVE或oracle COMPLETE。runner原错误`NATIVE_PROTOCOL: None`和两个FAIL状态原样保留，资源原因单列在BOUNDARY_SUMMARY中；不是将执行失败改成数值PASS，也不是HC候选已经被证明数值错误。

## 验证及冻结身份

- `python3 -B -m unittest discover -s docs/strata_4090_128k_lab/tests -p test_hc_boundary_patch.py -v`：本地6项PASS；29在包根目录以`-s tests`执行同一6项PASS。覆盖源码漂移、原专家调用保留、FFN/记录缺失、错误实际几何及前序FAIL阻止启动。
- 独立只读审查未发现阻断问题。审查者运行的是初版2项补丁测试，没有编译、SSH或运行GPU；后补4项负例由主代理在本地及29运行。
- CUDA12.3/sm89隔离构建161步完成、exit0；编译警告保留。新引擎SHA256为`e8d7f969884381d04e4146ded31bec6b00fc783cab3ef2e3efa6eec8594036f1`，prefill源码为`0f33677020ef6f9b57de74b961f12a1380a6bbee4ac56dd813b22069c624b2a3`。
- 本轮实际执行`pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build`，均exit0，保留既有Phaser chunk警告。此后更新了Python验收器、负例和文档，相关Python测试已在两端通过，没有重复运行无关的仓库检查。

全包`git diff --check`提示现有`lab/statistics.py`末尾多一个空行；该文件未由本轮修改。已改为核验本轮文件的diff及新文件空白。

[预登记](../workspace/combination/hc-boundary-20261029/PREREGISTRATION.json)、[冻结输入](../workspace/combination/hc-boundary-20261029/inputs.json)、[4096配对](../workspace/combination/hc-boundary-20261029/PAIR-4096.json)、[16K自然C](../workspace/combination/hc-boundary-20261029/c-16384/RUN_RESULT.json)、[16K失败原日志](../workspace/combination/hc-boundary-20261029/control-16384/stderr.log)、[汇总](../workspace/combination/hc-boundary-20261029/BOUNDARY_SUMMARY.json)、[资源及生产保护](../workspace/combination/hc-boundary-20261029/FINAL_PROTECTION.json)。

## 归档与停止边界

11,897份远端原件、7,597,298,137 bytes逐项登记长度和完整SHA256。81份导出内容文件共8,015,831 bytes在本地核验长度及SHA256，两个清单根文件也核对远端SHA。大raw、SAVE和引擎留29，未声称大文件双端同步。归档根为29的`/home/hhtele/strata-lab-4090/workspace/combination/hc-boundary-20261029`，独立源码/二进制留`workspace/trees/hc-boundary-20261029`；见[归档回执](../workspace/combination/hc-boundary-20261029/ARCHIVE_RECEIPT.json)。

首次归档脚本误要求失败phase不存在logits路径；runner其实会预建0-byte文件。修正为“无SAVE且logits长度0”后完成归档，保留`FINALIZE_ATTEMPT_1.json`；未重跑GPU或修改任何producer结果。

P13/P14/P18旧清单hash、P13/P18旧源码及二进制身份一致；旧raw内容hash复用前轮证据，本轮未再次遍历。权重核对既有身份的三项文件元数据，未重做全权重hash。生产13个保护文件hash不变，服务保持`inactive/dead/enabled`。四个本轮PID均退出，18089释放；收尾GPU1MiB、43°C、无计算进程。148个护栏样本中峰值63°C、显存23872MiB、最低MemAvailable11376MiB；这些插桩样本不作性能测量。

原六FAIL、P18自然A/C差异及旧退出失败全部保留。本轮没有运行候选短→长→短、恢复、取消、sanitizer/redzone、长请求成本链、正式配对性能或任务质量采用；没有提交、推送、部署或修改生产。

后续首先需要一个**不额外占约990MiB峰值显存、仍保持同驻留/同实际数值路径的16K匹配oracle**，通过后才能恢复生命周期和成本门。本轮未设计或实现这一替代。现有证据支持保留容量方向与4096正确性结果，尚不支持提速或上线结论。
