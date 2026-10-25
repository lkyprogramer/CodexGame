# K1收尾与下一项性能改造选择

K1-T01按用户要求收尾，状态为`CLOSED_NO_FURTHER_MEASUREMENT`，追加补测预算为0。保留raw默认路径，不进入K1-T02产品接入。下一项选择 **K2-T05：普通prefill卷积直接写连续Q/K/V**。本轮只做`jssh 29`只读核对、已有数据重算和文档更新；没有实施补丁、构建、产品测试、GPU或模型请求。

## K1结论与当前身份

已完成的8个数值场景继续复用。Graph补测6次capture、276次replay全部通过实际函数/几何见证及全48层逐bit检查；独立FP64参考只覆盖layer0。48 Record＋1 Fold段的五批配对中位改善：commit1为−1.0540%（0/5批更快）、commit2为−0.0714%（0/5）、commit4为＋0.1809%（3/5）。均未达到预定“至少10%且4/5批更快”，结论为`NO_SEGMENT_SIGNAL`。计时含host投递间隔，不能推出完整Verify或Chat的收益或否定其他形状的潜力。本次不再调查这些形状。

[原Graph报告](ninfer-v4-k1-graph-r2-20261023.md)、[原结果](../output/ninfer-v4-k1-graph-r2-20261023/final-summary.json)及[新收尾回执](../output/ninfer-v4-post-k1-selection-20261023/K1-closeout.json)分别保存执行事实和此次关闭决定。首轮失败的`RESERVED_UNKNOWN`、缺失的实际节点参数、所有原始账本均保留，不回填或重写。

通过`ssh -J jump 29`（本轮`jssh 29`函数）核对：分支`codex/k1-graph-witness-r2-20261023`，候选源树`41a913488b0138fe868a8321d2f6a86ce83e313f`，HEAD为`e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`。13份冻结输入及10份变更文件匹配原SHA；另12份选型源码与持久副本逐字节匹配。原容器`ninfer-4090-prod`仍exited/PID0，原镜像、argv及缓存身份未变；GPU无计算进程、独占锁可用。没有恢复服务。见[只读快照](../output/ninfer-v4-post-k1-selection-20261023/live-snapshot.json)和[源码见证](../output/ninfer-v4-post-k1-selection-20261023/source-witness.json)。

## 为什么先选这一项

普通GDN非segmented路径先把卷积结果写到完整`qkv_c`，再调用三次`extract_bf16_columns`得到连续Q/K/V。extract实际使用`cudaMemcpy2DAsync`，所以这里要消除的是**三次二维D2D拷贝及中间结果写读**，不是三个计算kernel。现有T>64卷积本身有输出及state更新两个kernel，候选保留这两个阶段。

本轮远端原容器argv确认`--prefill-chunk 1024`。27B的C为10240，Q/K/V宽度为2048/2048/6144，共48个GDN层。T1024的BF16中间payload为20MiB；省掉其一次写和一次读，理论逻辑流量减少40MiB/层、48层1.875GiB/chunk。最终Q/K/V的20MiB写仍然存在。这不是实测HBM流量，也不表示已释放20MiB工作区；首补丁保留独立池和原arena布局。

对原Baseline CSV只读重算：79个production-sampling冷core参考的prefill累计4697.09秒、decode累计377.57秒，前者占这两项之和92.56%；39条HTTP200 Pi则decode占70.51%。这些是不等权参考集合，原B29身份也不等于当前隔离树；不能当作线上负载权重或卷积热点占比。它们支持同时保留prefill与decode研究方向，尚不能估计本候选的TTFT百分比。见[重算来源与限制](../output/ninfer-v4-post-k1-selection-20261023/baseline-reaggregation.json)。

| 候选 | 本次判断 |
|---|---|
| Prefill卷积直接写Q/K/V | 明确存在冗余内存流，改动边界小，可在0模型请求下证伪，先做这一项。 |
| Request-local Lookup | Pi上仍可能有价值；缺真实token轨迹命中证据，融合前缀重验和状态合同成本更高，暂不同时实施。 |
| Q4/Q5 small-T | 已有MMA/split-K路线，缺能选出具体新配置的独立热点数据。 |
| Workspace复用、双流 | 当前没有allocator高水位或独立关键路径证据，不与本补丁捆绑。 |
| C0、K2-T01、K1-T01 | 全部收尾，追加测量预算0，不借新任务重跑。 |

既有greedy proposal＋Target精确sampling已实现；它不是本次要重新开发的功能。以上优先级是基于改动成本和可验证性的判断，并不表示已证明prefill候选的收益比Lookup更大。

## 第一份补丁范围

新增任务ID`K2-T05`，避免重开已关闭的K2-T01。profile为`SM89_GDN_PREFILL_C10240_SPLIT_QKV_T65_T128_T512_T1024_V1`。先做bench-only候选和最小驱动，复用BO依赖、原FP64卷积参考及现有构建产物；不改变产品默认dispatch。

1. 限普通非segmented Prefill、BF16、C10240、T>64且本profile不超过1024、指针4B对齐。沿用pairs kernel四tap累加、SiLU及`__floats2bfloat162_rn`，只改最终store地址，将结果直接写到独立连续Q/K/V。
2. 独立state更新kernel及同stream顺序保持原样。这里的conv state为BF16，FP32仅描述累加。覆盖state输入输出精确同址与分离；Q/K/V互不重叠，也不得覆盖输入、权重或state。Q/K/V分界均偶数，不跨BF162 pair。
3. 从现有`tests/ops/test_causal_conv1d_silu.cpp`提取或共享唯一FP64 oracle，保留原误差准则；不另写迁就候选的参考。额外要求全部Q/K/V和最终conv state逐bit相同、非零历史和finite输入、输入不变及guard完整。
4. 候选从真实launch TU导出函数身份和几何合同；probe不重新实例化生产kernel来充当地址见证。CPU冻结预期拓扑与预算，实机capture后才验证实际节点类型、函数、几何和copy参数，异常即停。

decode、T≤64、Verify/snapshot、segmented、MTP、Target采样、缓存格式及arena复用均不在首补丁范围。源树复用不等于候选资格；18处G1差异、C1附件缺口及全部旧失败保留。

关键源码：[普通路径](../output/ninfer-v4-post-k1-selection-20261023/source-witnesses/src/targets/qwen3_8/impl/runtime/text_context_impl.h:995)、[三次D2D实现](../output/ninfer-v4-post-k1-selection-20261023/source-witnesses/src/ops/wrapper/scatter.cpp:90)、[原prefill launcher](../output/ninfer-v4-post-k1-selection-20261023/source-witnesses/src/ops/launcher/causal_conv1d.cu:42)、[pairs数值顺序](../output/ninfer-v4-post-k1-selection-20261023/source-witnesses/src/ops/kernel/causal_conv1d.cuh:53)、[独立参考](../output/ninfer-v4-post-k1-selection-20261023/source-witnesses/tests/ops/test_causal_conv1d_silu.cpp:89)。

## 最小验证与耗时

以下为**未来拟议上限**，此次没有执行或消耗。CPU实现、构建和独立集成评审预计8–16工程小时，新增定向CPU合同最多16场景；不运行旧Baseline或已通过旧矩阵。

| 新验证项目 | 最小首筛上限 |
|---|---:|
| 数值场景 | 4：T65/128/512/1024，两路线各执行一次 |
| direct Op | 20＝8次conv＋baseline 12次extract |
| direct算法kernel | 16＝8次conv×2 |
| Graph capture | 4：仅T512/1024×raw/split |
| correctness / warmup / timing replay | 8 / 16 / 160 |
| replay合计 | 184＝4图×（2＋4＋5批×8） |
| 算法kernel总执行 | 384＝16＋184×2 |
| 预期baseline Graph拷贝操作 | 276＝两张raw图×46 replay×3；候选为0 |
| 模型提交 / HTTP | 0 / 0 |
| GPU预计 / 硬限 / 开始清理 | 2–5分钟 / 10分钟 / 第7分钟 |

276是预期copy操作执行量，实际CUDA图可能采用内部实现，不能预先冒充已观察到276个Memcpy节点。helper的H2D/D2D/D2H复位、canary及结果导出次数和字节尚未枚举，为`null+原因`；驱动完成后必须逐项冻结，方可安排GPU窗口。不得加入隐藏compute kernel或扩大迭代。

计时比较**卷积输出＋state更新＋baseline三次拷贝**的整个段与候选两kernel段。使用CUDA events、同等初态和AB/BA五批配对；reset、guard、结果传输放计时区间外，host wall单列。replay之间host投递间隔仍可能影响event时间，不能把含gap的结果写成纯kernel latency；不稳定则为INCONCLUSIVE，不自动追加循环。

全部逐bit/oracle/guard/实际Graph见证通过，且段级配对中位改善至少10%、至少4/5批更快，才得到`SEGMENT_SIGNAL_NOT_K4`。没有信号或有数值/资源回退就停止、保留原实现。当前完整prefill占比、实际route-hit及端到端收益均未知，不承诺TTFT或tokens/s提升。

有段级信号后才单独准备真实27B完整prefill/Chat驱动，枚举其capture/replay/提交预算，再由用户授权；不将这一步作为CPU开工前置，也不从本次20Op预算推导模型额度。候选资格与生产发布门禁独立。采样、context和Pi medium/32768保持不变，原GPU服务持续停止。

本次范围及预算真源为[selection.json](../output/ninfer-v4-post-k1-selection-20261023/selection.json)。V4入口和任务注册表只登记这一项新选型，不启动其余路线。`p95=null`，`optimization_qualification=false`。

## 文档与证据检查

已执行`python3 output/ninfer-v4-post-k1-selection-20261023/validate_documentation.py docs/ninfer-flare-v4-md-20261021`，结果`PASS_DOCUMENTS_ONLY`：417份Markdown、20任务/4门禁/80断言、31个可选scope的依赖/断言/链接/INDEX/MANIFEST一致；29个负例被拒绝。288份继承文档、3份Baseline交付及4份K1原始结果哈希未变，12份新源码见证通过。初次文档检查因注册表收尾记录多一个报告链接而触发严格对象不等检查，原错误已保存；校验器明确接受这个链接字段后通过，没有改动原结果或放宽产品断言。

独立只读评审无实质finding；评审未运行产品测试或重复文档校验。结果见[文档检查](../output/ninfer-v4-post-k1-selection-20261023/document-validation.json)。原文归档、索引归档、只读快照与所有缺口均保留在[本轮交付目录](../output/ninfer-v4-post-k1-selection-20261023)。本轮不需要运行CodexGame的应用测试；没有修改其runtime、协议或客户端。
