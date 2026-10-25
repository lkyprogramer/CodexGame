# P1—P4整体性能对照与真实整轮归因：无GPU准备

2026-10-25已通过`jssh 29`等价入口`ssh -J jump 29`完成隔离源码、诊断驱动、两端BO构建、新夹具CPU预检、集成评审和空账本冻结。状态为`CPU_ONLY_PREPARED`，**没有执行GPU、模型或推理HTTP请求，尚无新的提速结论**。原服务保持停止。此前Baseline、G1、P1—P4及关闭实验不重跑。

本次要补的证据是：P1—P4集成包对当前C1 Chat路径到底改变了多少成本，以及一次真实W4 decode轮中的时间花在哪里。它不是新的优化实现，也不是完整生产验收。

## 对照基点与边界

| 项目 | BO/O端 | 最终P4端 |
|---|---|---|
| 原源码tree | `6022c83a205853c65510af0b46f0dc337733cbeb` | `35d3dd9e4aa96b1f56f2e9c55482946bd9911cde` |
| 隔离诊断tree | `fdb7e282c14a955be71ab3dd556541c0ce6b93a6` | `d002a2183d54e1562cd1f53c50cf47155b1cb38f` |
| 原服务二进制SHA | `ff5e542fef099af557a21108cd0b1359d8f68a068dd57053ddfea225965b596b` | `8884da24e63856355a2db1048c942452fe6bdd6d25aaaf517cb162f231ad8846` |
| KV codec | 原`rk4v4-e8` | P4 midrise `rk4v4` |
| 分支 | `codex/p14-perf-bo-20261025` | `codex/p14-perf-p4-20261025` |

两端同一BO镜像`sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`、SM89/Release、同一27B模型，固定C1/context与KV容量262144、prefill chunk1024、MTP W4/K3及已有optimized proposal head。Target仍为temperature1/top-p0.95/top-k20/零penalty；medium、preserve-thinking及32768输出预算保持。新对照夹具固定seed1701。

**这是BO/O→P4的整包对照，包括codec与默认保护行为差异。** BO与P4虽都存在`rk4v4`参数名，含义已经变化，不能借同名参数伪装成同codec实验。P4的`rk8v4`、`rk2v4-e8`也涉及midrise变化；不为凑桥接对照引入新codec开发或降低context。B29历史生产二进制与BO不同，因此B29只作为历史参考，不把BO重命名为原生产复现，也不据此认证B29的source→binary链。

采用最终P4原树，不采用后来包含C0、W6、随机MTP或其它已关闭实验代码的后继树。Chat直接复用原始不可变服务二进制；只有native诊断入口加入默认关闭的计时hook。原源码、原二进制和原缓存身份已在收尾复核不变。[身份与二进制](../output/ninfer-v4-p14-performance-prep-20261025/remote-evidence/inputs/source-identity.json) · [最终状态](../output/ninfer-v4-p14-performance-prep-20261025/remote-evidence/evidence/final-state.json)

## 真实整轮如何测量

复用现有natural driver的Program、Target采样、输出preview、许可resolve与commit，不用oracle制造接受率。两道新输入为Java并发实现与中文性能推理；每端各跑plain/trace，最多10轮，其中前2轮warmup、后8轮计时。第10轮后的取消是显式诊断窗口，不把模型输出上限从32768改成短输出，也不当作完整任务质量成绩。

plain的同步完整轮wall/token成本用于整包比较。trace在同一真实Graph内部记录6段：入口准备、Target主体、Target head与接受、MTP alignment、proposal head与AR、出口；Graph外另记录commit/Fold。host decode/preview/resolve/commit wall分别保留。

每个trace进程9个timing event handles，每张MTP Graph有7个真实event-record节点。capture内采用`cudaEventRecordExternal`，已有同步后读取；没有新增阶段同步、算法kernel或tensor搬运。不能用仅在capture时执行的host timer冒充replay阶段成本。[CUDA事件API](https://docs.nvidia.com/cuda/archive/12.8.1/cuda-runtime-api/group__CUDART__EVENT.html)

归因资格要求同端plain/trace token和许可轨迹一致、8个测量轮完整、Graph事件见证正确、时间有限有效，且观测开销不超过5%。不满足时保留原数，阶段占比无资格；plain数据不扣除估算观测开销。`wall − Graph span − Fold`仅称未归因wall余量，不能等同纯CPU成本。

## Chat、缓存与前端准备

每端只做短前缀冷/热和长工具前缀冷/恢复四个Chat。两端独立新缓存目录，原缓存不挂载；不引入其它协议。复用既有响应ID、完整SSE、已知HTTP错误终态、unknown禁止重发和候选清理合同。

已使用模型内原有六份frontend资源，实际运行两端各6个新夹具的CPU前端路径。六对token IDs与positions摘要全部相同：native输入120/125 token，短Chat569/593 token，长Chat16993/17049 token；长前缀共有16992 token。BO checkpoint hints与P4 typed boundaries的差异原样保留，不能据CPU预检宣称实机已经恢复L2。[真实预检与原生边界](../output/ninfer-v4-p14-performance-prep-20261025/remote-evidence/inputs/frontend-preflight.json)

P4只有相关boundary publication明确success，才允许清除私有slot并发恢复请求。BO缺少请求级export job/digest字段，其证据限制明确记录；实际是否恢复及恢复深度，以request_done中的来源、恢复token/字节为准。short-warm未实际命中、long-warm未实际L2恢复或输出不合格时，保留整包行为观察，但不生成对应缓存路径的提速资格。两端恢复深度不同必须报告，不能把它说成同工作量下某个kernel的加速。

客户端TTFT以首个非空语义delta计，role元数据、首HTTP字节和server durable TTFT另列；HTTP时长固定到EOF。完整进程身份检查放在计时外，fsync、证据落盘和日志读回另计。输出耗尽、保护截断、输出长度、P/O/cache及实际x-request-id均保留，不把提前终止当作胜出。

## 最小实机预算与耗时

| 项目 | 冻结上限 |
|---|---:|
| 新native请求 | 8 |
| 请求内decode | 80，含16轮warmup、最多64轮测量 |
| 新Chat | 8 |
| 默认内置startup warmup | 2，无额外warmup POST |
| 全部模型提交计账 | 18 |
| HTTP wire | 14：8 Chat＋2 readiness＋2 erase＋2 telemetry |
| native capture / replay | 72 / 152，含profile warmup |
| native算法kernel | 1,376,256 |
| trace event handles | 同时最多9，累计36 |
| trace captured / ordinary / replayed records | 252 / 148 / 532 |
| 窗口 | 硬限30分钟，第27分钟停止准入并清理候选 |

native完整辅助上限：H2D 16384次/192GiB，D2D 32768次/32GiB，D2H 16384次/512MiB，memset 65536次/32GiB，device allocation 32768次/累计512GiB；每Graph节点上限8192。以上是累计调用/请求字节的保守准入包络，不是实际使用量或峰值显存。算法预算为每请求`16384 + 19×8192`，capture为9个既有W4 profiles，replay为9个启动warmup加10轮。实际均待执行。

**上述逐kernel/辅助计数只覆盖native。** HTTP复用原服务二进制，没有逐kernel拦截，采用请求、输出、context、独占进程与窗口限制，不能将其GPU实际计数填0或声称纳入native精确包络。[完整plan](../output/ninfer-v4-p14-performance-prep-20261025/remote-evidence/inputs/plan.json)

预计实机12–20分钟；30分钟是失败时也必须执行的硬限，不延长、不自动加请求。依据是已有8-native窗口约5分钟，加两次服务加载、startup和缓存流程的余量，属于工程估计。实测结束后离线核对和归因整理预计另20–40分钟；没有预设提速百分比。

## 无GPU验证、失败与评审

- 两端最终BO诊断构建通过，真实`variant.cpp`编译命令具有opt-in宏；产品默认选项仍关闭。Chat服务原SHA保持。
- 两端各8个新native CPU合同、两端各6个新frontend预检通过；6个静态接线检查通过。HTTP工具15个合同及新增warm-miss定向合同通过；控制器7个合同通过。这些不是GPU数值或性能PASS。
- r1保留BO旧3参API适配错误、P4边界字段适配错误。另保留P4首轮CPU入口exit2：增量同步保留旧mtime导致对象未更新。修复同步时间戳后，两端r3定向构建及最终CPU绑定通过。最初BO预检结果也保留；最终重验是为关闭已发现的构建身份问题，不重跑历史模型任务。
- 独立只读集成评审发现并修复了HTTP计时污染、EOF边界、publication终态、缺附件仍READY及warm-miss资格问题。静态评审无剩余阻塞；评审代理没有自行运行测试或GPU。

原始构建/预检失败、修复构建、最终消费TU命令和patch在[远端证据副本](../output/ninfer-v4-p14-performance-prep-20261025/remote-evidence/evidence)。旧18处G1差异、C1附件缺口、Baseline坏raw/CLI与评分附件缺口、97fc7be6输出耗尽和全部已关闭实验结果继续保留；本轮没有修复或覆盖这些原结论。

文档定向检查通过：新增链接可达，当前MANIFEST的416项size/SHA一致，注册表机器JSON与本轮修改前相同。旧全量文档检查器仍硬编码23个节点，注册表此前已包含第24项K2-T05，因此报`unexpected_or_missing_active_node`。该既有校验器差异单独保留，没有改旧任务图或把本次定向通过写成全量通过；它不参与本次独立控制器的冻结验证。[检查结果](../output/ninfer-v4-p14-performance-prep-20261025/evidence/document-validation-targeted.json)

## 冻结入口与停止边界

远端隔离根：`/home/hhtele/ninfer-v4-p14-performance-prep-20261025`。

窗口：`prepared-window-r1`；freeze SHA：`0712e94eb92bd65a70897c0024e80e1384a3acd846aef4d73946a9ffa7aef6ab`。账本为`PRISTINE`，所有used/completed均0，runtime目录不存在；GPU/模型/HTTP实际执行0。freeze验证绑定新工具、两端二进制、六个活跃夹具、十二项真实前端结果及预算。[回执](../output/ninfer-v4-p14-performance-prep-20261025/remote-evidence/prepared-window-r1/freeze-receipt.json) · [空账本](../output/ninfer-v4-p14-performance-prep-20261025/remote-evidence/prepared-window-r1/budget-ledger.json)

当前只授权准备。控制器必须有新的明确GPU执行授权及精确freeze SHA才可进入执行；没有自动启动。仅提供当前可安全执行的只读检查：

```bash
ssh -J jump 29 'python3 /home/hhtele/ninfer-v4-p14-performance-prep-20261025/prepared-window-r1/tools/controller.py --root /home/hhtele/ninfer-v4-p14-performance-prep-20261025/prepared-window-r1 --plan-only --freeze-sha 0712e94eb92bd65a70897c0024e80e1384a3acd846aef4d73946a9ffa7aef6ab'
```

后续实机只回答两个新问题：当前C1整包Chat成本差异与两个短上下文自然decode样本的阶段份额。它不覆盖P2多lane吞吐、长上下文质量、广泛负载稳定性或发布门禁；p95=null、optimization_qualification=false。BO实机加载、Graph event/update、trace开销和真实缓存命中仍需该新窗口验证，失败不降context、不改采样、不缩Pi预算，不恢复原GPU服务，不重开关闭实验。
