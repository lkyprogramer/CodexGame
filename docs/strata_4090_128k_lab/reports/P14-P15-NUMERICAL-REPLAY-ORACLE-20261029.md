# P14/P15 · 数值回放 oracle

结论：**冻结 4095-token GEN1 fixture 的局部 FFN 及完整请求 A/A 数值回放通过。按用户最新指令在此收口，未执行 HC 候选 B/C 或后续探索验证。** 原六项任务 FAIL 保留。本结果建立固定分派下的诊断 oracle，不代表生产自然分派确定性、候选正确性、性能或质量采用通过。

## 实际范围和结果

同 P6 v0.2.7 `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`、原完整配置、冻结 IQ3_XXS native pack、EXACT6、KV int8/resident20480、spec4/minp0.5、15 workers＋host、CPUshare MAX4096、AUTO MAX16384。没有关闭 CPUshare、替换权重、修改评分或放宽容差。输入文件 SHA256 为 `3c4f5016a093346a0c6f8aaeec401592c15f9326c044fe89051ba7b2f168367d`。

| 检查 | 实际证据 | 结果 |
|---|---|---|
| 局部同进程 FFN A/A | `p0=0,T=4090,layer=3,half=1`；第二遍固定第一遍实际 CPU 专家集合和行映射；86 个字段、1,139,717,436 bytes | 全部逐字节相同 |
| 输入负控制 | 改变实际 mixed 输入，拒绝于输入字节检查 | PASS |
| 分派负控制 | 改变实际 on_cpu 集合，在计算前拒绝 | PASS |
| 行映射负控制 | 改变真实 slot 映射，在上传/计算前拒绝 | PASS |
| 完整请求 A/A | 两个 fresh engine；A 自然录制，第二个 A 使用其实际 CPU 分派；实际主 prefill 为一个4090块、48层 FFN | PASS |
| 完整请求 raw | 初态、路由、驻留、专家集合、row/scatter、MMQ groups、目标 HC／half／下一 half norm 缓存、完整 FP32 chunk R；3329字段，1,121,573,360 bytes | 全部逐字节相同 |
| 最终 logits | 248,320 个 FP32，全部有限 | 0 bit差异，max abs=0 |
| 有效终态 | 298,656,148 bytes；GDN、PLE、indexer、main KV、实际有效 MTP KV | 全部逐字节相同 |

完整请求的 SAVE 为298,682,028 bytes、live长度4095、13组KV（12 main＋1 MTP）。比较器核验完整文件checksum后，按字段做实际字节比较；checksum不代替逐字节证明。排除25,168 bytes的LRU元数据、无效KV页尾和未使用indexer tail等；其范围由冻结源码及实际token位置决定。

MTP由成功调用和实际batch日志确定有效范围为 **[0,4090)**；GEN1达到输出上限后未调用后续draft，不能把live长度4095当成MTP全部已计算。另行核对实际MTP batch及终态PLE标量，弥补SAVE不记录它们的限制。main/CPU resident及分派在独立transcript中核对；SAVE仅证明权威逻辑KV，不代表全部物理VRAM槽生命周期已验收。

## 失败记录及归因边界

局部阶段共6次native请求，其中2次执行故障均保留：

- `aa-1`：远端旧版runner预建输出目录，与探针要求冲突，目标FFN未执行；同步正确runner后修复。
- `aa-2`：引擎正常exit0，监控器读取已消失的`/proc/<pid>/exe`触发退出竞态。该运行仍为FAIL；独立补充比较显示1,125,163,924 bytes相同。修复只允许“owner已退出且重新查询GPU为空”的正常退出，其他异常保持失败；4项回归测试通过。随后`aa-3`完整通过。
- 三个负控制的native协议退出是预期拒绝，必须同时满足对应精确REJECT与完整前置记录，不能以任意进程失败判PASS。旧局部探针在拒绝时可能未flush小文件，相关分析明确保留此限制。

完整请求阶段只执行A录制、A回放两次，共8次native请求，正式性能样本为0。旧P13失败和本轮故障未删除、未替换。此前P13中相同HC输入而FFN输出不同，与动态CPU/GPU分派有关；本次固定实际分派后，局部及完整请求均可复现，显著加强该解释。但只覆盖这一个fixture，不宣称所有来源均已排除。

## 冻结产物与复现

- 局部登记 SHA256：`b1743b11cf6c51119dc79362fdb77eb60b201c504ad019d78c146e18431839c7`。
- 完整请求登记 SHA256：`1173183f45244ad0161a7839b496bf2fccad958ffd4ca6cf2e09bf762b62c689`。
- 局部引擎 SHA256：`c0a80685335011314195b7f892322ec9090ad485b0c7b1349aa3f40f732b29ea`。
- 完整请求引擎 SHA256：`0070efba6dc1196bdf5963f61686fa7e53686763c991042d901c104c49f4cde9`。
- [完整A/A分析](../workspace/combination/oracle-replay-20261029/full-request/AA_ANALYSIS.json)、[局部A/A分析](../workspace/combination/oracle-replay-20261029/aa-3/ANALYSIS.json)、[完成回执](../workspace/combination/oracle-replay-20261029/COMPLETION.json)、[资源与生产保护](../workspace/combination/oracle-replay-20261029/FINAL_PROTECTION.json)、[完整文件清单](../workspace/combination/oracle-replay-20261029/RAW_MANIFEST.json)。
- 原始字节、SAVE和两版二进制保留于29的`/home/hhtele/strata-lab-4090/workspace/combination/oracle-replay-20261029`。本地导出元数据、分析、日志和源码；清单记录全部远端原件的长度与SHA256。
- 工具：[tools/oracle_replay](../tools/oracle_replay)。原始source-read未改；补丁只应用于29隔离树`workspace/trees/oracle-replay-20261029`。

复算不启动GPU：

```bash
python -B tools/oracle_replay/analyze.py workspace/combination/oracle-replay-20261029/aa-3
python -B tools/oracle_replay/full_request.py analyze --name replay-a
```

## 停止范围与验证

用户明确要求“完成数值回放 oracle后进行汇报，停止后续探索验证”。因此B/C、真实4096/16K边界、生命周期/redzone/sanitizer、成本链和性能、GROUP_SCRATCH及IMMA均未运行；不能沿用原续测合同自动继续。定时续测`29-gpu-strata`已确认PAUSED。

独立只读审查发现并修复验收中的自然C分派与数值混淆、HC目标覆盖漏检及indexer block尺寸校验问题；审查者未代替主代理运行GPU。定向Python测试44项oracle＋4项退出护栏均通过；仓库要求的`pnpm typecheck / lint / test / test:integration / build`均exit0，build保留既有Phaser大chunk警告。本地166个导出文件逐项长度与SHA256匹配远端清单；实验包267文件完整性校验通过。

最终回执确认：生产13个保护文件hash不变、服务inactive/dead（开机自启仍enabled）；P13原187个raw文件不变；本轮8个PID全部退出；GPU显存1MiB、无计算进程；18089已释放。未提交、推送或部署。
