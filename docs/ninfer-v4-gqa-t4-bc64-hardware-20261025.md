# T4 GQA Bc64：数值与Graph通过，性能首筛未通过，配置关闭

**本次授权的一次实测已完成，状态为`CLOSED_PERFORMANCE_GATE_FAILED`。不采用Bc64，不追加调参、32K专测、模型请求或完整decode集成。** 32K存在局部收益，但8K明显回退，128K未达到预定采用门槛。原服务保持停止；默认分派、Target采样、Pi medium/32768、模型、codec和生产缓存目录不变。

## 实测结果

同一冻结二进制比较原Bc32/8warps与候选Bc64/16warps。C1/T4、24 query heads、4 KV heads、head256、rk4v4；CPU预填cache，`Masked=true`、非零页表行、`writes_cache=false`。每个长度32对AB/BA交替计时，使用CUDA events测量partial＋reduce整段；256MiB冷缓存清扫在events之外，两路一致。

| visible keys | 原路径中位数 | Bc64中位数 | 耗时变化 | 候选更快配对 | 判定 |
|---|---:|---:|---:|---:|---|
| 8,192 | 63.488 μs | 72.704 μs | 增加14.516% | 7/32 | 超过2%回退上限 |
| 32,768 | 151.552 μs | 129.024 μs | 减少14.865% | 32/32 | 局部收益，保留观察 |
| 131,072 | 411.008 μs | 411.648 μs | 增加0.156% | 10/32 | 未达到长上下文门槛 |

128K预定要求同时满足耗时减少≥15%、绝对节省≥60μs、≥24/32对更快；实际绝对变化为增加0.640μs。8K和32K各自要求回退≤2%。门槛在实测前冻结，没有根据结果重新选择长度或修改采用标准。

编译spill本身不能否决性能，32K的结果也说明资源指标不能简单等同实测快慢。但本轮真实数据仍否决该固定配置的采用条件。没有动态spill流量或stall归因，不能把8K回退直接归因于spill，也不据此否定其它Attention实现。

这些数据只覆盖**预填cache的masked GQA partial＋reduce**。未覆盖真实append、Target状态链、完整decode、TTFT、Chat或质量，不能换算为整机推理提速。`p95=null`，`optimization_qualification=false`。

## 数值、Graph与证据范围

- 3长度×2查询输入，共6个数值场景；原/候选共12次direct均满足原FP64 checker及原容差：relative_l2=0.00315、gross_absolute=0.0011、gross_relative_to_max_reference=0.0022，保留原组合判据。
- 6次Graph capture均通过函数、参数、拓扑与可驻留资源见证。12次Graph正确性replay均满足FP64判据，并与对应route的direct BF16输出逐字节相同。
- **Graph正确性范围为每个长度/route的query0重复两次，共6个唯一输入/route组合；query1只做了direct，未做Graph。** 不将12次检查说成12个不同输入的Graph覆盖。也不要求或声称新旧route逐bit一致。
- 三种长度的cache、输入和guard均未改写。24份数值输出及判定、6份Graph见证、192条原始计时事件完整保留。
- 根代理离线复算计时、核对BF16字节和SHA；独立评审复核原始事件、预算求和和门槛，没有新增阻塞。没有重跑任何已完成GPU工作。

## 冻结身份与准入修订

复用[原实现、BO构建与失败证据](ninfer-v4-gqa-t4-bc64-20261024.md)。源码树仍为`b361766a8072943b2cde700ae12263efd16423db`，probe SHA为`ebc3642f9f7d079876caac396d640263c25f61770dabafa6188a3b6e41cc942d`；本轮没有修改kernel、probe或重新构建。

用户明确授权后，只对该固定源码、二进制、原资源证据和单一窗口版本化调整spill准入。原`FAIL_NEW_SPILL`文件逐字节保留，SHA为`e4b4308e9508aaf649c092fbc86c64f38596c21e41846a0f773b3d8ab9a8915d`，没有改写成资源PASS；新授权理由单独写入回执。数值、Graph、预算和清理门槛不变。

新工具4项定向CPU回归通过；最终补强fixture SHA库存后仅重跑受影响2项，通过。首轮macOS临时路径规范化测试失败已保存。6个CPU参考场景由原二进制在无GPU的runc容器生成，耗时92.408秒，完整15个数据文件及manifest在冻结和启动前检查库存、状态、布局、尺寸及SHA。

远端窗口：`/home/hhtele/ninfer-v4-gqa-t4-bc64-hardware-20261025/prepared-window-r1`。

冻结回执SHA：`2070cbd7b8f6c034728b3b9347c25bc028bba2d4f8a6950384be35c3624ac35f`。启动前账本PRISTINE、全部用量0，无旧进程或未知attempt；原服务镜像、argv和缓存设备/inode与旧回执一致。

## 实际消耗与清理

| 项目 | 冻结上限 | 实际 |
|---|---:|---:|
| 数值场景 / direct Op | 6 / 12 | 6 / 12 |
| capture / replay（含warmup） | 6 / 240 | 6 / 240 |
| 算法kernel执行 / capture内节点 | 504 / 12 | 504 / 12 |
| H2D | 12次 / 386,363,648B | 同上限 |
| D2H | 27次 / 387,100,928B | 同上限 |
| memset，含cold flush | 276次 / 67,646,914,560B | 同上限 |
| 显式device allocation | 6次 / 累计1,191,227,648B | 同上限 |
| D2D / 辅助compute / 模型 / HTTP | 0 | 0 |

585条reservation均为COMPLETED，无未结束操作。600秒硬限、420秒开始清理；实际从控制器窗口建立至候选清理完成为**37.319秒**，包含初始化、数值/CPU字节检查和清理，不是GPU kernel总耗时。候选退出码0、stderr为空；GPU compute进程为空，原服务`STOPPED_IDENTITY_UNCHANGED`。未恢复原服务。

## 可复现交付与保留的限制

- [结构化结果](../output/ninfer-v4-gqa-t4-bc64-hardware-20261025/result-summary.json)、[离线核验](../output/ninfer-v4-gqa-t4-bc64-hardware-20261025/validation.json)、[独立评审](../output/ninfer-v4-gqa-t4-bc64-hardware-20261025/review.json)。
- [原始summary](../output/ninfer-v4-gqa-t4-bc64-hardware-20261025/remote/prepared-window-r1/native-summary.json)、[预算账本](../output/ninfer-v4-gqa-t4-bc64-hardware-20261025/remote/prepared-window-r1/budget-ledger.json)、[清理回执](../output/ninfer-v4-gqa-t4-bc64-hardware-20261025/remote/prepared-window-r1/runtime/cleanup.json)。
- [冻结回执](../output/ninfer-v4-gqa-t4-bc64-hardware-20261025/remote/prepared-window-r1/freeze-receipt.json)、[原spill证据](../output/ninfer-v4-gqa-t4-bc64-hardware-20261025/remote/prepared-window-r1/resource-assessment.json)、[归档回执](../output/ninfer-v4-gqa-t4-bc64-hardware-20261025/archive-receipt.json)。

本机紧凑归档3,485,150B，SHA为`e34967edced75cc499e6bf21e592bab939f6697115e632b559753fe31adac7a5`，已验证131份清单内文件。大probe和原/冻结两份共6个arena.bin保存在29持久目录，并由远端完整SHA校验和清单绑定；没有声称它们已传回本机。原始输出、参考、日志、请求授权、工具和所有回执在本机归档中。

首次离线审计曾误假定query1也经过Graph而失败；已保留[该审计失败与更正说明](../output/ninfer-v4-gqa-t4-bc64-hardware-20261025/offline-audit-first-failure.json)。更正的是对实际覆盖的描述，没有改动GPU断言、容差或原始结果。

复现离线核验，不发远端/GPU请求：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B output/ninfer-v4-gqa-t4-bc64-hardware-20261025/analyze.py
```

真实CPU准备、freeze和GPU启动的精确argv分别保存在`remote/evidence/cpu-fixture-launch.json`、`freeze-result.json`、`gpu-launch.json`。窗口已消耗，禁止再次执行原启动命令。18处G1差异、C1/旧Baseline附件缺口及所有历史失败保持原状；本次结果不授予其它实验或生产发布资格。
