# P1—P4整包对照与整轮热点：实机结果

2026-10-25通过`jssh 29`等价入口`ssh -J jump 29`执行一个冻结窗口，**全部请求已记账，未证明P1—P4整包普遍提速，并定位到P4缓存导出/发布造成的C1准入等待**。原服务保持停止，没有更改默认分派、Target采样或Pi32768预算，没有重跑旧Baseline或重开已关闭实验。

控制器北京时间10:33:51启动、10:52:57退出，共19分6.7秒；候选清理在窗口第19分钟完成，早于第27分钟清理线和30分钟硬限。8native/80decode、8Chat＋2内置warmup、14wire、18次模型提交全部完成。10个候选已停止，GPU无计算进程。测量结束不代表性能采用或生产发布通过。

状态：`COMPLETED_WITH_PERFORMANCE_REGRESSIONS_AND_DISCLOSED_LIMITATIONS`。`p95=null`，`optimization_qualification=false`，`production_release_qualified=false`。

## 整包收益

对照仍为可复现BO/O原树`6022c83a205853c65510af0b46f0dc337733cbeb`与最终P4原树`35d3dd9e4aa96b1f56f2e9c55482946bd9911cde`，包括legacy `rk4v4-e8`→midrise `rk4v4`和默认保护行为变化。不是原B29生产二进制重现，也不能归因到某一个P阶段。两端Chat使用原不可变serve，native使用独立诊断构建；完整身份与准备失败见[准备记录](ninfer-v4-p14-performance-prep-20261025.md)。

### Native完整decode轮

每端每题前2轮warmup、后8轮测量。成本为测量轮`Σ完整wall / Σ正式提交token`；没有扣除估算观测开销。

| 新输入 | BO→P4 ms/正式token | token成本变化 | BO→P4 ms/轮 | BO→P4正式token/轮 |
|---|---:|---:|---:|---:|
| Java | 8.3254→8.5018 | 增加2.12% | 22.895→23.380 | 2.750→2.750 |
| 中文推理 | 10.7059→6.4031 | 减少40.19% | 22.750→23.211 | 2.125→3.625 |

**两题单轮成本分别增加2.12%、2.03%。中文的单位token改善来自本样本每轮接受/提交更多token，不是每轮计算更快。** 两端生成序列均已分歧，中文在开头即分歧；因此不能把40.19%写成同样输出或完整编程任务快40%。这些是一个seed下的相关短窗观察，没有统计稳定收益资格。

8个native全部完成10轮，没有提前终态。随后按既定诊断协议取消，生成内容仅覆盖reasoning开头，尚无完整答案质量或完整任务时间结论。32768输出预算未变；这不是新发生的97fc7be6式输出耗尽。

### Chat端到端

下表为首个非空语义delta的客户端TTFT，包含reasoning delta；不是首个最终答案token。每项只有一次配对，正负变化均保留。

| 场景 | BO TTFT | P4 TTFT | P4成本变化 | BO→P4完整HTTP wall | 输出token BO→P4 |
|---|---:|---:|---:|---:|---:|
| 短冷 | 0.2196s | 0.9075s | 增加313.20% | 1.0242→1.2111s | 46→41 |
| 短热 | 0.1533s | 1.2838s | 增加737.31% | 0.3369→1.4726s | 26→26 |
| 长冷 | 5.0196s | 7.8709s | 增加56.80% | 6.2103→8.5015s | 91→99 |
| 长前缀L2恢复 | 0.6035s | 0.5655s | 减少6.29% | 1.5665→1.1469s | 70→91 |

四项HTTP wall合计9.1380→12.3321秒，增加34.95%。这是本次固定请求序列的观察，不是通用吞吐结论；P4异步发布可延续到响应之后，因此完整HTTP wall也不等于全部后台工作成本。不能仅用L2恢复一项的较短响应时间宣布整包胜出。

8个Chat均有完整HTTP200、单个SSE `[DONE]`、唯一响应ID与durable request_done、对应usage。4个文本回答满足`READY`，4个工具调用均是正确完整的`sha256_text`及参数。没有length/重复保护提前终止，也没有未知模型结果。这些是新夹具的有限质量检查，不扩展到历史Gson、RE003或Pi质量资格。

两侧短热都恢复L1的567tokens，仅计算26tokens。两侧长热都真实从L2恢复16991tokens，仅计算58tokens；恢复字节分别624266281与625450159，codec载荷不同。恢复时间360.586→328.308ms。P4相关长冷job6的boundary/session publication明确success后才执行私有slot erase；没有用复制完成替代发布完成。

## 热点与回退原因

### GPU整轮：Target主体约占80%

四组同端plain/trace的token、许可、提交及输入位置轨迹一致，真实7事件Graph节点与9个event handles见证完整，计时加总有效。观测开销分别为BO Java0.359%、P4 Java0.058%、BO中文0.122%、P4中文0.190%，均低于冻结5%门槛。

| P4阶段 | Java：占完整轮wall | 中文：占完整轮wall |
|---|---:|---:|
| Target主体 | 79.32% | 79.76% |
| proposal head＋AR | 9.51% | 9.56% |
| Target head＋接受 | 6.29% | 6.32% |
| MTP alignment | 2.35% | 2.36% |
| commit/Fold | 1.53% | 1.47% |
| 入口＋出口 | 0.086% | 0.116% |
| 未归因wall余量 | 0.916% | 0.402% |

若分母仅为已观测GPU时间，Target主体为80.06%/80.09%，proposal约9.60%，Fold约1.5%。Target主体覆盖embedding、各层与末端norm；现有粗粒度边界**不能判断主体内FFN、GDN或Attention谁最热**。wall余量包括host、driver和等待，不是纯CPU执行。

Fold的份额解释了该方向的整轮收益上界：按本次占比，即使完全消除Fold，理论完整轮时间减少也只有约1.5%。norm等Target主体内部算子的占比仍未知，不能由这份粗粒度结果推断。这是占比上界，不是新优化承诺，也不重开已关闭实验。

### Chat：导出与发布串行造成准入等待

| 场景 | BO queue | P4 queue | BO prefill | P4 prefill |
|---|---:|---:|---:|---:|
| 短冷 | 0.166ms | 684.352ms | 217.492ms | 220.725ms |
| 短热 | 0.243ms | 1091.868ms | 150.850ms | 189.704ms |
| 长冷 | 0.392ms | 3036.454ms | 5009.597ms | 4824.446ms |
| 长热 | 372.715ms | 346.174ms | 221.388ms | 209.545ms |

长冷prefill节省185.151ms（3.70%），但新增约3.036秒准入等待淹没了这点收益。短热的suffix prefill本身也慢25.76%，因此不能把所有差异都归给单一因素。frontend准备仍是毫秒级，无法解释前三项秒级回退。

`queue`定义为Engine submitted到lane admitted；包括准入前导出屏障和恢复。**restore是其组成部分，不能再与queue相加。** 源码在`admit_planned_request`记录admitted之前调用`wait_lane_export`，而`publication_loop`使用同一线程顺序执行导出、释放lane、boundary/session发布，再处理下一job。[执行器源码](../output/ninfer-v4-p14-performance-prep-20261025/source-p4/src/runtime/engine/concurrent_executor.h)（行1161–1285、2046、3628、3652）

| P4导出job | 来源 | 入队→开始 | 导出段 | lane释放→发布完成 |
|---|---|---:|---:|---:|
| 2 | startup warmup | 0.779s | 0.088s | 1.721s |
| 3 | 短冷 | 1.197s | 0.093s | 3.500s |
| 4 | 短热 | 3.124s | 0.090s | 1.683s |
| 6 | 长冷 | 0.00016s | 0.270s | 6.837s |

job3在job2 publication完成后61.85μs才开始导出，job4在job3 publication完成后51.82μs才开始。由客户端发送时间＋prepare＋queue近似推算的前三次admitted，与前序job2/3/4的lane释放分别相差−0.44ms、−0.28ms、＋2.97ms。

因此，当前有实证的机制是：**前一个CPU发布拖住后一个GPU导出，后一个导出又阻止C1复用lane。** 当前lane在自己的复制结束后已释放，但单工作线程仍形成跨job的队头阻塞。不是简单的“后台工作已经异步，所以不影响请求”。

近似admitted不是直接记录的wait span，不能宣称每一毫秒都已归因。发布路径涉及镜像复制、序列化摘要和缓存接纳；本轮没有这些内部子段计时，不能把3.5秒全部说成SHA或cache mutex。实际publication成本也不能从当前HTTP完成时间中扣掉后再声称提速。

下一步最可信的改造边界是：让受lane生命周期约束的导出不被此前已离开GPU的CPU发布挡住，采用有界交接并保留export fence、lane barrier、alias CAS/发布顺序及关闭排空合同。先针对这条已证实回退设计修复；本轮**未实施修复或启动后续实验**。不通过删除安全屏障、延迟客户端请求或重开C0等关闭实验掩盖问题。GPU方向仍需先在Target主体内定位，而不是再凭局部算子峰值选择改造。

## 失败、退出与证据限制

- BO最终telemetry记录`publication_failures=2`、`publication_successes=2`；P4为0/8。BO schema20缺少逐job失败终态与原因，无法确定具体请求或失败类别。原始失败保留，不将其冒充模型质量失败，也不因为Chat PASS而删除。
- 8native进程exit0；两端HTTP候选按冻结`docker stop -t 2`停止，最终exit137、OOMKilled=false。候选确已停止，但**不是优雅关闭/后台发布排空PASS**。
- P4最后一个模型请求engine5已完整done，关联job7没有publication终态。其背景发布结果保留缺口，不能用scheduler idle证明缓存工作也已结束。长热所依赖的job6发布成功已有证据，不受这项未知终态替代。
- 18处G1差异、C1附件缺口、Baseline损坏raw与CLI/评分附件缺口及全部历史失败继续保留；没有补造或重测。
- native精确GPU计数不覆盖原始不可变HTTP服务；HTTP kernel、辅助传输实际计数为不可观测，不能填0。allocator真实高水位、统计p95和生产资格未建立。单seed短窗和四个Chat配对不能推广到多lane吞吐、长上下文质量或真实编程闭环完成时间。
- BO缺Engine request ID、逐job publication和retained digest观测。此次使用原有canonical x-request-id/request ID/instance关联，不声称补齐旧接口的全部可观测性。

## 预算、完整性与可复现材料

| 项目 | 实际 | 冻结上限 |
|---|---:|---:|
| native / decode | 8 / 80 | 8 / 80 |
| Chat / 内置warmup | 8 / 2 | 8 / 2 |
| wire / 模型提交总数 | 14 / 18 | 14 / 18 |
| native capture / replay | 72 / 88 | 72 / 152 |
| native算法kernel | 99780 | 1376256 |
| native direct / captured kernel | 25200 / 61020 | 131072 / 589824 |
| trace handles / captured records | 36 / 252 | 36 / 252 |
| trace ordinary / replayed records | 148 / 308 | 148 / 532 |

辅助累计实际/上限：H2D8776/16384次、143214704512/206158430208字节；D2D3312/32768次、2197389312/34359738368字节；D2H120/16384次、43168/536870912字节；memset12232/65536次、7434204992/34359738368字节；device allocation24/32768次、186088933376/549755813888累计请求字节。不是同时占用量或allocator高水位。各native单项资源也逐一核验未越限。

freeze SHA为`0712e94eb92bd65a70897c0024e80e1384a3acd846aef4d73946a9ffa7aef6ab`，运行前确认空账本和GPU独占。冻结plan、原二进制与冻结工具在导出前重新核验。账本used/completed相等；本轮没有模型重试。

217个文件已下载到持久工作区并逐文件校验size/SHA，归档SHA为`4594ac099b6742c388db252b5e1e2fafbbf264cb290f71d32b2e9253acff2f69`。远端私有cache/slot payload及二进制仍留远端，明确不声称已包含在此小型归档。控制器在finally完成清理后，将原始runtime/summary的`cleanup_readback_pending`置为false并附上cleanup；后续独立container状态回读补充了exit137和非优雅排空边界。下载后的原始文件保持未修改。

- [最终结构化结果](../output/ninfer-v4-p14-performance-hardware-20261025/final-summary.json) · [指标CSV](../output/ninfer-v4-p14-performance-hardware-20261025/metrics.csv)
- [原始回执与217文件清单](../output/ninfer-v4-p14-performance-hardware-20261025/execution-20261025-export.json) · [归档核验](../output/ninfer-v4-p14-performance-hardware-20261025/evidence/export-verification.json)
- [原始测量汇总](../output/ninfer-v4-p14-performance-hardware-20261025/remote-evidence/prepared-window-r1/runtime/summary.json) · [最终账本](../output/ninfer-v4-p14-performance-hardware-20261025/remote-evidence/prepared-window-r1/budget-ledger.json)
- [P4请求/导出原始日志](../output/ninfer-v4-p14-performance-hardware-20261025/remote-evidence/prepared-window-r1/runtime/http-p4/server-requests.jsonl) · [最终容器状态](../output/ninfer-v4-p14-performance-hardware-20261025/evidence/final-container-states.json)
- [候选清理回执](../output/ninfer-v4-p14-performance-hardware-20261025/remote-evidence/prepared-window-r1/runtime/cleanup.json) · [独立结果与源码评审](../output/ninfer-v4-p14-performance-hardware-20261025/evidence/result-review.md)

实际执行：冻结控制器`--execute --authorized-profile P14_BO_P4_W4_WHOLE_PACKAGE_AND_ROUND_TRACE_V1 --freeze-sha 0712e94…`一次；之后仅只读监控、终态证据导出和离线核算。独立评审分别核对native/Chat原始结果和源码/事件因果，没有再次发GPU或模型请求。当前窗口已消耗完毕，不可用原账本重新执行。
