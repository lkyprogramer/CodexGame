# 随机MTP最小实机结果：q与状态通过，Chat对照因预算不足中止

**完整稀疏q的数值/Graph及native状态最小验证已通过；Chat性能对比未完成，无法给出随机MTP提速结论。** 本轮在greedy对照端工具请求中触发冻结的`memset_calls`阶段上限，164.736秒完成清理。预算准备遗漏了Graph节点随replay累乘的调用成本，这是本次准备与评审失误。没有扩大上限、重发请求或修改源码。

## 完成的验证

| 项目 | 实际结果 |
|---|---|
| 数值q/接受/残差 | 4/4 PASS；8 direct Op；最大概率绝对误差2.6411775×10⁻⁸，门槛5×10⁻⁶ |
| 数值Graph | 4 capture、8 replay逐bit一致；36次算法kernel计账 |
| 非退化残差 | 大词表场景实际选择248319，独立参考匹配；直接p重采样会选择8607 |
| native | 4请求、8decode；Graph OFF/ON对应完整q和canonical状态PASS_BITWISE |
| 许可生命周期 | 两个partial terminal（产出4、许可1），正常许可4和两个cancel许可0均实际出现 |
| greedy端Chat | warmup、Java、中文推理完整PASS；工具请求中断，control未运行 |
| 随机MTP端Chat | 未启动，性能有效对数0 |

数值物理W4/K3、逻辑extent2（首列点质量、第二列实际producer）；真实完整三步q由native观察。native使用固定1027个token198的诊断输入，8轮均接受3草稿；这只证明本最小状态路径，不能代表真实Chat接受率或速度。实际device token/extent/输入前缀、结果frontier和next-q promotion均有原始证据；GDN/conv/有效KV/count及各阶段tail hidden逐bit一致。

[数值原件](../output/ninfer-v4-sampled-q-hardware-20261024/remote-final/runtime/numeric-q/numeric-summary.json) · [native比较](../output/ninfer-v4-sampled-q-hardware-20261024/remote-final/runtime/native-comparison.json) · [独立审计](../output/ninfer-v4-sampled-q-hardware-20261024/INDEPENDENT-AUDIT.md)。

## 已测到的性能数据与边界

以下仅为greedy草稿＋原Target sampling的完整请求，未与随机草稿配对；不是旧Baseline重跑。所有Target参数仍temperature1/top_p0.95/top_k20。

| greedy样本 | 实际输出tokens | Program decode ms/token | 草稿接受比例 | 客户端TTFT | 客户端wall |
|---|---:|---:|---:|---:|---:|
| java | 1088 | 6.345327 | 88.78% | 0.150496s | 7.057150s |
| reasoning | 571 | 6.102092 | 93.33% | 0.143473s | 3.629144s |

Program ms/token使用实际`completion_tokens−1`作为decode分母，首token来自prefill；其时间不含全部调度/输出/host区间，不等于完整round wall。接受比例是verifier接受草稿数/草稿数，不是提交吞吐。缺少candidate Chat，所以收益保持null；不能把greedy数据或native高接受率当随机MTP提速证据。

## 停测原因与请求终态

greedy阶段允许`memset_calls=65536`。实际已记账65477，剩59；下一次Graph所需的memset节点数超过剩余额度。审计在真实GPU调用前原子拒绝，记录`FAILED_BEFORE_GPU_CALL / GPU resource cap: memset_calls`并`_Exit(95)`。原客户端随后记录`IncompleteRead(0 bytes read)`。独立终态确认容器exit95、非OOM，原服务未受影响。

原资源推导只说明replay上限可覆盖5×2048输出，却没有证明`startup/direct + Σ(replay次数×该Graph的memset节点数)`能落在64K调用上限。split-K scratch清零等节点每轮都会重放。全局预算还有空间也不能借给已冻结的单阶段上限。此前“无需增加native/chat caps”的准备判断被本次真实证据推翻；本轮没有改这份冻结证据或绕过保护。

工具请求权威响应ID`req_8f6e368a1257c7edcb83d4710061e56d_5`，HTTP200、原始SSE5742字节，但无`[DONE]`、无`request_done/request_error`。它已随进程退出中止，没有存活请求；模型输出结果不完整、不能评分或计完整性能。保留原`FAILED_OR_UNKNOWN_NO_RETRY`及RESERVED账本，新增派生“审计封顶中断”说明，不补造终态或重发。

[审计失败](../output/ninfer-v4-sampled-q-hardware-20261024/remote-final/runtime/chat-raw/audit.json) · [客户端失败](../output/ninfer-v4-sampled-q-hardware-20261024/remote-final/runtime/chat-raw/tool.failure.json) · [原始SSE](../output/ninfer-v4-sampled-q-hardware-20261024/remote-final/runtime/chat-raw/tool.raw) · [最终进程读回](../output/ninfer-v4-sampled-q-hardware-20261024/remote-final/execution/final-readback.json)。

## 计账、安全与保全

| 项目 | 使用/授权 |
|---|---:|
| 数值场景/direct/capture/replay | 4/8/4/8，全部完成 |
| native请求/decode | 4/8（上限4/12） |
| 正式Chat请求 | 3/8发出，其中2完整、1中断 |
| warmup | 1/2完整 |
| wire | 5/12发出，其中4完整 |
| 总模型提交 | 8/14发出，其中7完整 |
| GPU窗口清理 | 164.736202秒；硬20分钟、第17分钟清理约束未触及 |

原ledger仍为RUNNING，raw phase与tool为RESERVED；此状态保留未知/失败成本，不代表进程还运行。三个候选均Pid0，controller/guardian已退出、lease释放、GPU无计算进程；原生产服务STOPPED且image/argv/cache身份不变。没有默认分派、Target采样、Pi medium/32768调整，未重跑旧任务。

下表将numeric/native完成阶段与raw中断阶段的审计计数合并；它们是调用前预留/已发起工作的计账，不一概等于已同步完成的GPU工作。原`GPU_actual_completed`只包含完整阶段，未被回填。

| GPU资源 | 本窗口计账 | 全窗口冻结上限 |
|---|---:|---:|
| `algorithm_kernels` | 417,199 | 34,603,044 |
| `captured_copy_calls` | 2,421 | 1,572,864 |
| `captured_kernel_calls` | 14,520 | 2,621,452 |
| `captures` | 22 | 196 |
| `d2d_bytes` | 5,567,102,976 | 4,466,765,987,840 |
| `d2d_calls` | 3,720 | 2,162,688 |
| `d2h_bytes` | 4,169,308,704 | 51,556,384,768 |
| `d2h_calls` | 4,892 | 327,708 |
| `direct_kernels` | 23,847 | 2,621,452 |
| `h2d_bytes` | 35,811,789,828 | 206,175,207,424 |
| `h2d_calls` | 2,884 | 327,712 |
| `memset_bytes` | 2,809,246,752 | 206,158,430,208 |
| `memset_calls` | 68,229 | 163,840 |
| `replays` | 496 | 69,640 |

全部阶段实际计账均未越过阶段或全局上限；触顶请求在下一次预留时停止。没有追加GPU操作。

完整原始状态1610文件、4,161,477,660字节保留在远端持久目录，另有只读归档`/home/hhtele/ninfer-v4-sampled-q-hwprep-20261024/execution-r1/full-runtime.tar`，归档4,165,847,040字节、SHA256`85acfb09f7133b174fa1f19dbe6c240c795af312037926c406f0768840ebb683`。本机同步98份metadata、wire、失败、账本和终态并逐项核验SHA；未把远端原始bin描述为已下载本地。冻结24个文件SHA保持，唯一入口已消费，不得重启。

[机器结果](../output/ninfer-v4-sampled-q-hardware-20261024/final-summary.json) · [原始文件清单](../output/ninfer-v4-sampled-q-hardware-20261024/remote-final/execution/artifact-manifest.json) · [本地核验](../output/ninfer-v4-sampled-q-hardware-20261024/local-verification.json) · [离线分析脚本](../output/ninfer-v4-sampled-q-hardware-20261024/analyze_finished.py)。

## 未完成与缺口

raw tool完整响应、raw control及candidate四项Chat均未完成；实际性能收益、采样统计分布、活跃penalty模型状态、缓存恢复和生产资格未通过。native真实逐步logits→q独立重算不在本窗口。没有真实逐token ITL、round wall或allocator高水位，继续null+原因。p95=null、optimization_qualification=false。Baseline缺口、18处G1差异、C1附件缺口及所有历史失败继续保留。

本轮结论为最小验收未完成。已通过数值/native证据可复用，不能再次重跑来修复预算；未启动的新请求不自动补发，剩余额度不构成新窗口授权。后续若续测，先根据实际Graph节点成本重新设计有限预算和新账本，当前冻结工具保持不变。
