# 固定C1/W4/K3随机MTP：完整q与最小实机准备冻结

> 本冻结入口已于2026-10-24消费，当前不再是空账本。数值/native通过，Chat因阶段memset预算不足中止；详见[实机结果](ninfer-v4-sampled-q-hardware-20261024.md)。以下为原准备快照，不得据此重启。

**补丁、驱动、构建、必要CPU验证和两路集成评审已完成。唯一新窗口已冻结，账本全零；本轮GPU、模型和HTTP请求均为0。** 没有改默认分派、Target参数或Pi medium/32768，原GPU服务保持停止。

## 冻结身份与交付

- 连接：`jssh 29`，实际使用`ssh -J jump 29`。
- 隔离分支：`codex/sampled-q-hwprep-20261024`，基点树`f557ab41f68105a629344c2acb5adb6f9a38c783`，本轮树`b9d4bfb714d537e1b9a51d94d3716c9441035107`。HEAD仍为`e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`；没有新commit、push或部署。
- 唯一新入口：`/home/hhtele/ninfer-v4-sampled-q-hwprep-20261024/prepared-window-r1`。
- Freeze SHA256：`a0cef613dcd81bff75c9a6ed36f4f0aa294d42d2ab58ecd327f75b1347722d2f`。
- 状态：`FROZEN_READY_FOR_AUTHORIZED_MINIMAL_GPU_WINDOW_NOT_RUN`。`budget-ledger.json == initial-ledger.json`，全部消耗0、无reservation、无runtime目录；没有自动执行。
- 原服务STOPPED/PID0，原image/argv/cache目录身份核验不变；GPU无计算进程。模型原SHA通过相同size/mtime/inode/device复用，6个前端资源SHA本轮重核，不声称又重新读取18GB模型做hash。

[交付回执](../output/ninfer-v4-sampled-q-hwprep-20261024/remote-final/evidence/PREPARATION-DELIVERY-RECEIPT.json) · [冻结回执](../output/ninfer-v4-sampled-q-hwprep-20261024/remote-final/prepared-window-r1/freeze-receipt.json) · [源码补丁](../output/ninfer-v4-sampled-q-hwprep-20261024/remote-final/evidence/sampled-q-hwprep.patch) · [源码包](../output/ninfer-v4-sampled-q-hwprep-20261024/remote-final/source-frozen.tar.gz) · [本地核验](../output/ninfer-v4-sampled-q-hwprep-20261024/evidence/local-delivery-verification.json)。本机保留源码、工具、CPU/BO原件、失败和冻结元数据；4个冻结二进制保留远端，不把紧凑同步称为完整二进制备份。

## 完整q与native诊断

新增默认OFF的`NINFER_SAMPLED_Q_DRIVER`，复用原CUDA audit和H3控制器。`ownership.py`逐字节复用；不新建控制器框架，不绕开候选禁止cache image/session snapshot的边界。前轮算法、Target处理器和12组CPU合同输入未变。

数值驱动包含small64/128与真实131072/248320两种proposal/Target形状，各接受与拒绝场景，读取完整稀疏支持集与FP32 q。使用独立FP64参考检查实际BF16输入的排序、过滤、归一化、counter RNG、接受/bonus和残差。最后一例有重叠支持和4个正残差项，固定RNG下错误p重采样会得到8607，正确残差采样必须得到248319，从而识别实际CUDA残差分支接线错误。

数值物理布局W4/K3、逻辑extent2：第一列是预先声明的点质量q，第二列来自真实producer；不能声称数值用例已经执行3次真实MTP。完整三步条件q由native的真实模型路径观察。

native一次加载模型，依次构建Graph OFF/ON两个Program，每个执行terminal/cancel两请求。每轮保存before/pending/after的完整q、实际device ingress IDs/extent、实际device target_positions输入前缀、结果frontier，以及FP32 GDN/conv、有效KV、counts、tail hidden原始字节和SHA。检查正常许可、q promotion、取消及对应阶段direct/Graph逐bit；对比不能只依赖summary。

部分终态只在固定3轮内自然出现`produced>1`时验证，未出现则明确覆盖缺口，不增加请求找seed。真实模型采用原生产零penalty，活跃counts仍未获模型资格；合成非零penalty数值用例不能代替它。真实q诊断证明其设备绑定及流转，真实每步logits→q的独立重算不在本最小窗口。

## 已执行的无需GPU验证

| 项目 | 结果 |
|---|---|
| 前轮12组CPU合同 | 内容校验后复用，重跑0 |
| raw与sampled server、native/numeric/fixtures BO | PASS；固定BO镜像/CUDA13.2/sm89，runc、无GPU设备、无网络 |
| 新数值FP64参考 `--reference-only` | 4/4 PASS，无Device初始化 |
| native/numeric `--plan-only` | PASS，无模型加载 |
| 实际前端夹具 | 5个新fixture解析/tokenizer/RepetitionGuard检查PASS，无模型 |
| 新CPU profile及账本边界 | 5/5 PASS，一次运行；覆盖14提交/12wire、四phase聚合、0资源、超额与重复拒绝 |
| 实际消费TU与链接 | variant/round_state/native/numeric宏证明、4个binary CUDA audit符号核验PASS |
| 集成评审 | Spec和Standards，开放findings0；评审者没有代执行测试 |
| GPU数值、Graph、模型状态、性能 | 未运行 |

[CPU/BO原件目录](../output/ninfer-v4-sampled-q-hwprep-20261024/remote-final/evidence/) · [CPU日志](../output/ninfer-v4-sampled-q-hwprep-20261024/remote-final/evidence/CPU-tools-r1.log) · [FP64参考](../output/ninfer-v4-sampled-q-hwprep-20261024/remote-final/evidence/numeric-reference-r1.json) · [评审与修复](../output/ninfer-v4-sampled-q-hwprep-20261024/remote-final/evidence/INTEGRATION-REVIEW.md)。精确容器命令记录于对应BO/CPU JSON回执。

保留的本轮失败：BO r1诊断把DeviceSpan传给Tensor reader，已改为受审计的U8 view；原失败log和overlay未覆盖。首次冻结diff检查误比较HEAD，触发历史C0文件已有尾空行；修正为本轮冻结基点比较，未修改旧文件，失败另记。评审还修正pending tail hidden生命周期、已被复用的device frontier及拒绝夹具盲点，没有改采样算法或放宽逐bit要求。

## 唯一冻结的最小实机预算

| 项目 | 上限 |
|---|---:|
| 新数值 | 4场景、8 direct Op、4 capture、8 replay（含warmup） |
| native | 4请求、≤12 decode/verify |
| 正式Chat | Java/中文推理/工具/开放控制各raw→sampled一对，共8 |
| HTTP warmup / wire | 2 / 12（10模型HTTP＋2readiness） |
| 总模型提交 | ≤14 |
| 窗口 | 硬20分钟，第17分钟停止准入并清理候选 |

所有请求fresh/cache off，两端固定C1/W4/K3、context262144、prefill1024、temperature1/top_p0.95/top_k20；请求不覆盖Target采样。Chat新夹具max_tokens2048与native/Pi32768是独立预算。未知请求不重发，旧入口不恢复，不补测旧任务。原GPU服务保持停止。

下表是**全窗口硬上限**，包括numeric、native和两套Chat的模型加载、startup、warmup、Graph、kernel、辅助传输与清理；不是预计用量。独立数值的4/8不是全窗口capture/replay总量。

| GPU计数 | 全窗口上限 |
|---|---:|
| `algorithm_kernels` | 34,603,044 |
| `captured_copy_calls` | 1,572,864 |
| `captured_kernel_calls` | 2,621,452 |
| `captures` | 196 |
| `d2d_bytes` | 4,466,765,987,840 |
| `d2d_calls` | 2,162,688 |
| `d2h_bytes` | 51,556,384,768 |
| `d2h_calls` | 327,708 |
| `direct_kernels` | 2,621,452 |
| `h2d_bytes` | 206,175,207,424 |
| `h2d_calls` | 327,712 |
| `memset_bytes` | 206,158,430,208 |
| `memset_calls` | 163,840 |
| `replays` | 69,640 |

[逐阶段机器预算](../output/ninfer-v4-sampled-q-hwprep-20261024/remote-final/prepared-window-r1/plan.json) · [资源推导](../output/ninfer-v4-sampled-q-hwprep-20261024/remote-final/evidence/GPU-RESOURCE-DERIVATION.md)。源码预计每个Graph ON Program有9个MTP profile；native36份状态快照保守约6.188GiB，低于16GiB D2H阶段上限。kernel等大额度沿用已验证audit的有限停止界，不保证所有输出必能完成。GPU allocation/allocator高水位不在14项计数内；容量不足停止，不缩context。

预计实际窗口10–20分钟，20分钟硬限不顺延；结果归档与分析约30–60分钟。该时间是预算，不是已测随机MTP运行耗时。

## 性能判读与仍未覆盖范围

正式Chat不导出native重型状态。分别报告实际接受位置/rounds、生成token数、TTFT、client wall、service total及Program累计decode/fold时间/token。后者未包含全部host提交、调度与输出，**不能称完整decode净收益**；round wall及完整decode净收益保持null。raw与随机proposal文本/长度可能不同，四对新样本只提供筛选信号，不证明质量等价或分布资格。开放控制只评分结构，实际低接受尚未观察。

GPU数值、Graph与状态逐bit、真实模型q、速度是否更快全部等待执行；缓存恢复、活跃penalty、统计分布、性能采用和生产发布仍是独立门禁。`p95=null`、`optimization_qualification=false`。全部历史失败、18处G1差异、C1附件缺口及Baseline缺口保留，不重跑旧Baseline或已通过任务。
