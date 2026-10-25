# H3-T01 Stage A：实机窗口因驱动初始化错误停止

**本轮最小验收未完成。6个独立Op数值/Graph场景通过，第7个GDN链场景在驱动初始化时退出；native与Chat均未启动，完整逐bit与W4→W6 decode净收益没有结果。** 失败不能归为模型质量或W6性能退化。未重发、未补测、未修改冻结工具或产品源码。

## 实际执行结果

| 项目 | 实际结果 |
|---|---|
| Q5 residual K6144/K17408 | 2场景PASS，2 direct Op、2capture/4replay |
| Q4 SwiGLU、Q6全Target head、Attention输入投影、GDN输入投影 | 4场景PASS，4 direct Op、4capture/8replay |
| GDN projection-conv Record＋recurrent Record＋Fold | 初始化FAIL；从报错和控制流确认未到3个Op/Graph入口 |
| native 4请求/≤16decode | NOT_RUN，0提交/0decode |
| 6 Chat＋2warmup、10wire | NOT_RUN，全部0 |
| 完整FP32 state/conv/KV逐bit | NOT_RUN |
| W4→W6完整decode、TTFT收益 | null，无成对样本 |

前6项复用原独立数值参考、误差判据、guard及两次Graph replay检查。Graph通过不等于全Engine或状态逐bit通过；Q6仍为完整形状执行＋原sampled FP64参考，并非全词表FP64穷举。旧P4 GQA T6证据复用，本轮没有重跑。CPU/BO证据复用，没有新构建或CPU测试。

## 精确原因与证据边界

原始错误为`DeviceArena capacity must be nonzero`，候选ExitCode1、OOMKilled=false。[原stderr](../output/ninfer-v4-h3-w6-hardware-20261024/remote/prepared-window-r1/runtime/numeric-chain/container.stderr)与[退出状态](../output/ninfer-v4-h3-w6-hardware-20261024/remote/prepared-window-r1/runtime/numeric-chain/exit-readback.json)保留。

冻结[新驱动第37行](../output/ninfer-v4-h3-w6-hardware-20261024/remote/hardware-run-r1/source-evidence/tests/h3_w6/numeric_chain.cpp:37)把`gdn_input_proj_conv_record_workspace_capacity_bytes(2048,2048,6144,1,6,6)`直接交给`WorkspaceArena`。已注册的Q4/Q5路径[合法返回0](../output/ninfer-v4-h3-w6-hardware-20261024/remote/hardware-run-r1/source-evidence/src/ops/wrapper/gdn_input_proj.cpp:691)，而[Arena构造要求非零](../output/ninfer-v4-h3-w6-hardware-20261024/remote/hardware-run-r1/source-evidence/src/core/arena.cu:134)。现有产品路径已用`max(kMinimumLeafWorkspaceBytes, query)`处理，原Op测试也有正容量下限。此次遗漏在新测试驱动，不需要修改kernel或产品分派。之前plan-only、16具名CPU合同及构建未实例化此GPU Arena，评审未覆盖到该调用约束；先前“准备通过”不等于实机合同通过。

初始化前已发生buffer分配和输入传输；[异常出口](../output/ninfer-v4-h3-w6-hardware-20261024/remote/hardware-run-r1/source-evidence/tests/h3_w6/numeric_chain.cpp:74)只写stderr并返回1，没有调用`audit_checkpoint`，故该阶段`audit.json`与`numeric-summary.json`不存在。**失败阶段的完整资源实际计数不可恢复，全窗口实际总量保留null，不能将已完成阶段的计数冒充全窗口总量。** 冻结资源检查仍在调用前执行；本轮未见资源超限退出，但由于最终审计缺失，不签发完整资源账本PASS。

原账本保留`RUNNING`及`numeric-chain: RESERVED`原值，不伪造COMPLETED；容器已确定Exit1、控制器已退出，派生终态单列`KNOWN_EXIT_1_CLEANED_NO_RETRY`。这是逻辑账本未收口，不是仍在运行或存在未知模型请求。

## 身份、窗口与资源

连接`jssh 29`（`ssh -J jump 29`）。冻结SHA `4cce84aa7a8b3093a2162a1df17b47f42cfb41a96cf8167a661bb3e14d52dcdc`，源树`49bee647112ee171de35529028fc271494260751`，执行前后均核验冻结payload（含8个二进制）。入口`/home/hhtele/ninfer-v4-h3-w6-20261024/prepared-window-r1`；新窗口08:26:29 UTC派发，控制器30.184秒退出，从runtime计时到候选清理完成**24.560秒**，早于17分钟清理/20分钟硬限。

| 应用CUDA资源 | 已完成5进程/6场景的实际小计 | 冻结全窗口上限 |
|---|---:|---:|
| `algorithm_kernels` | 18 | 34,652,160 |
| `captured_copy_calls` | 2 | 1,622,016 |
| `captured_kernel_calls` | 6 | 2,646,016 |
| `captures` | 6 | 199 |
| `d2d_bytes` | 0 | 4,518,305,595,392 |
| `d2d_calls` | 0 | 2,211,840 |
| `d2h_bytes` | 1,276,186,624 | 154,618,822,656 |
| `d2h_calls` | 140 | 376,832 |
| `direct_kernels` | 6 | 2,646,016 |
| `h2d_bytes` | 1,264,021,504 | 257,698,037,760 |
| `h2d_calls` | 20 | 376,832 |
| `memset_bytes` | 188,540,800 | 309,237,645,312 |
| `memset_calls` | 46 | 212,992 |
| `replays` | 12 | 69,646 |

失败链进程有独立预留额度，但实际尾部审计缺失，既不记0也不退款。高层模型加载/提交/native/Chat/warmup/wire均0。6个候选进程已退出，controller/guardian/launcher均不存在，GPU idle、lease free，原GPU服务Running=false/PID0，镜像、argv和缓存目录身份不变。[最终读回](../output/ninfer-v4-h3-w6-hardware-20261024/remote/hardware-run-r1/final-readback.json)。

## 交付与剩余缺口

原始日志、失败、退出状态、账本、冻结元数据与相关源码已归档到29持久目录，并完整镜像本地；95个清单文件逐个SHA核验。新包不重复携带准备期8个二进制，完整二进制仍在原CPU准备持久归档。归档SHA `53c1b97679a8d99e2a2890a694f7877f1ea37858a29132a7295a177df8e9ad6a`。[归档回执](../output/ninfer-v4-h3-w6-hardware-20261024/archive-receipt.json) · [结构化结果](../output/ninfer-v4-h3-w6-hardware-20261024/analysis.json)。采集过程中一次源码附件路径写错已保留为[采集失败记录](../output/ninfer-v4-h3-w6-hardware-20261024/collection-r1-failure.json)，修正读取路径后归档成功，没有重跑测试。

后续修复应仅覆盖新驱动的零工作区构造及异常资源审计，另行版本化冻结接续账本；已通过6个场景不再执行。剩余范围为1个链场景/3 direct Op/1capture/2replay，加未执行的4 native/≤16decode及6Chat＋2warmup/10wire。当前单次入口已消费，不可重启或把未用额度自动转成新窗口；本报告不新增执行预算。

本轮未改默认分派、Target采样、Pi medium/32768，没有开发W8。18处G1差异、C1附件缺口、全部历史失败保留。候选资格与发布均未通过，`p95=null`、`optimization_qualification=false`。
