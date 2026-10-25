# 随机 MTP 收尾与下一项准备：Q4 FFN 紧凑 shared 布局

**随机 MTP 就此关闭，不再追加补测。下一项优先选择 `K2-Q4-COMPACT-T4`：仅对 C1/W4 下的 Q4 FFN 融合 SwiGLU，移除无用的 Q5 高位共享内存区，并试验由此可容纳的五级预取。** 它有具体、可核对的冗余，覆盖 Target 全部 64 层，修改边界小于改变草稿分布、扩宽或引入 DFlash2。它是当前已核查的小范围候选中的优先项，**尚不能证明是所有方向中收益最大，也没有实测收益保证。**

本轮只做 jssh 29 只读核查、现有二进制静态解析、离线容量/预算推导和准备文档。没有源码修改、新构建、旧测试重跑、GPU kernel、模型或推理 HTTP 请求。原服务保持停止，默认分派、Target 采样和 Pi medium/32768 不变。

## 1. 收尾与现况

随机 MTP 状态为 `CLOSED_NOT_ADOPTED_NO_FURTHER_TESTS`。既有 q/Graph/native 最小一致性成绩继续有效；三组有效 Chat 单位 token 耗时变化为 +1.75%、+0.67%、−3.11%，没有稳定完整请求收益。旧 tool 中止、两端 control 输出耗尽、累计14模型/12wire及全部成本保持原样，不重跑或抹去。[最终结果](ninfer-v4-sampled-q-resume-20261024.md)。

2026-10-24 19:01（Asia/Shanghai）的 jssh 读回确认：原服务 Running=false、PID0、镜像和缓存目录身份不变，GPU 无计算进程，lease 可取得；后续只读校验也确认 argv SHA 未变。原模型文件 stat 与冻结回执相同，没有重新读取18GB模型。源码分支为 `codex/sampled-q-hwprep-20261024`，HEAD `e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`，内容与冻结树 `b9d4bfb714d537e1b9a51d94d3716c9441035107` 无 diff；389项既有 index 状态不是本轮修改，也不将目录称为干净 checkout。

未来候选以此树的 **greedy 默认模式**为基点，`NINFER_SAMPLED_MTP_Q` 不启用。建议分支 `codex/q4-swiglu-compact-t4-20261024` 尚未创建。本轮没有改变或运行任何已消费窗口。

[远端身份](../output/ninfer-v4-post-sampled-selection-20261024/remote-readback.json) · [11份远端源码见证与 SHA](../output/ninfer-v4-post-sampled-selection-20261024/source-witnesses.json)。

## 2. 这次为什么选这里

当前 Q4 FFN gate/up 权重形状为 `[34816,5120]`，融合输出为 `[17408,T]`。64个 Target 层都经过该算子；C1/W4 的实际 T=4 落在已有 small-T MMA 路径。MTP 层本身使用 W8，不计入这64次 Q4 工作。

按原 Q4 code 与 FP16 scale 布局，每层紧密 payload 为94,699,520字节，64层约 **6.061GB**。对比同轮 Q6 Target head约0.993GB、三个 Q4 draft head约1.070GB、64层 Q5 down约3.743GB。**这些只是源码推导的逻辑 payload，不是实测 DRAM 流量、时间占比或带宽；本改动也不会减少这些权重字节。** 它说明选择覆盖面较大的真实数学路径，比继续优先挑一个小 norm 或 logits扫描更有依据。

来源：[64层配置](../output/ninfer-v4-post-sampled-selection-20261024/source/src/targets/qwen3_8_27b/impl/config.h:12)、[Target与MTP权重绑定](../output/ninfer-v4-post-sampled-selection-20261024/source/src/targets/qwen3_8_27b/impl/load/bindings.cpp:244)、[融合调用](../output/ninfer-v4-post-sampled-selection-20261024/source/src/targets/qwen3_8_27b/impl/variant.cpp:289)、[实际T路由](../output/ninfer-v4-post-sampled-selection-20261024/source/src/ops/linear_swiglu/q4/q4_linear_swiglu_plan.cpp:32)。已有融合和P3 small-T不能再记为新成果。

具体冗余在 `SmallTMmaShape`：每个stage统一预留1024B的 Q5 high plane，scale/activation偏移跟在它后面；而 Q4 的 high 读写被 `if constexpr(Q5)` 排除。为 Q4 专用候选移除该空洞，不需要改量化格式、权重、activation精度或计算顺序。

| 配置 | 每级 shared | 每CTA shared | 3 CTA加每块1KiB保留 | 目的 |
|---|---:|---:|---:|---|
| 原4级 / MinBlocks3 | 7,424B | 29,696B | 92,160B | 原对照 |
| 紧凑4级 / MinBlocks3 | 6,400B | 25,600B | 79,872B | 隔离布局因素 |
| 紧凑5级 / MinBlocks3 | 6,400B | 32,000B | 99,072B | 尝试多一级预取 |

Ada 每SM的100KiB shared、每块1KiB保留等限制见 [NVIDIA Ada Tuning Guide](https://docs.nvidia.com/cuda/ada-tuning-guide/index.html#unified-shared-memory-l1-texture-cache)。未压紧的五级流水加保留需要114,432B/三CTA，超过此容量；压紧后99,072B在 shared 容量上可行。**这不证明实际驻留三个CTA或会变快**，寄存器、carveout与编译结果仍需核查。紧凑四级也不能宣称可驻留四CTA：含保留需106,496B，仍超限。

同一 BO 镜像对原 server-raw 做静态 `cuobjdump --dump-resource-usage`，匹配 Q4/SwiGLU/Tile8/S4/MinBlocks3 的已构建函数：**REG78、SHARED29696、STACK0、LOCAL0**。因此先保持 MinBlocks3，不把降低stage并强压四CTA的寄存器变量一起引入。宿主 cuobjdump 首次报 `Invalid fatbin header`，失败保留；换用已冻结 BO 内工具后成功，未构建或执行 CUDA。

[二进制资源证据](../output/ninfer-v4-post-sampled-selection-20261024/binary-resources-bo-r2.json) · [首次工具失败](../output/ninfer-v4-post-sampled-selection-20261024/binary-resources.json) · [公共布局](../output/ninfer-v4-post-sampled-selection-20261024/source/src/ops/common/small_t_rowsplit_mma.h:42) · [Q4不读high的实现](../output/ninfer-v4-post-sampled-selection-20261024/source/src/ops/common/small_t_rowsplit_mma.cuh:168)。

## 3. 实施范围与不可扩大边界

首次补丁先限制为 bench-only 候选：公共布局/内核与现有 bench profile，必要时增加同作用域布局事实定义；不新建 controller 或通用调优框架。真实decode接入是首筛有效后的条件工作，不能用“只改两个文件”承诺掩盖执行阶段边界。

1. `small_t_rowsplit_mma.cuh`：显式默认关闭的 Q4/SwiGLU 紧凑布局。外层 shared 数组分配、内部 stage stride、scale/activation offset必须取同一布局；不能直接改所有调用者共用的默认 `SmallTMmaShape`，也不能按 `!Q5` 普遍启用而影响 Mixed。
2. 先在 bench 的显式候选入口按精确 `[34816,5120]`、输出17408、**实际T=4**调用候选，原 `q4_linear_swiglu_small_t_mma.cu` 默认入口保持。后续若接真实decode，还必须由既有 `Variant::post_mixer` 的 `TextPhase::Verify` 上下文限界。仅检查Tile8会扩大到其它T，仅检查T4也会误覆盖prefill尾块；`A16Only`还覆盖其它语义，不能拿它代替phase身份。若不能小范围传达现有上下文，就停在bench，不偷改prefill。
3. 复用已注册 `q4_linear_swiglu_variants_bench`、`TimedGraph` 和现有 owner/audit/deadline工具，增加明确 small-T profile。该 bench 当前默认是large-T预填充扫描，**不能直接执行默认扫描**来替代本实验。

保持 Q5、Mixed、其它T、prefill、vision、MTP/W8、head、采样与缓存格式不变。不改 split-K、MMA、scale-FMA、phase归并、SiLU或BF16舍入顺序，不增加全局 workspace。候选共享内存属于CTA片上空间，不是显存或allocator优化。

紧凑scale offset4096、activation offset4352及stage6400符合原拷贝对齐；阶段结束已有 `cp_wait<0>` 与barrier，再复用空间做4096B phase reduction。现有 SwiGLU split-K=1，不进入partials/counter路径。上述是可行性依据，**不是逐bit实测结果**。评审发现并补清了上述T4/prefill阶段隔离要求；准备合同已修正，未发生产品修改。源码注释已有150.7/155.6µs历史调优，不能把原路线当作未优化，也不能把注释当本轮归因数据。

## 4. 最小验证预算与止损

先完成无需GPU的候选/BO/CPU准备，再单独冻结实机工具和新账本。以下是**拟议有限预算，不是空账本、已冻结回执或执行授权**。

| 阶段 | 范围 | 预算/预计耗时 |
|---|---|---|
| 实现可行性检查点 | 默认关闭布局、真实消费TU、编译资源；若需要改数学/格式或扩到其它Op则停止 | 最多先投入4工程小时 |
| CPU、BO、驱动与评审 | ≤8个新增布局/范围合同，复用原FP64 oracle和未改动P3证据；保留register/shared/local数据 | 补丁至构建评审约6–10工程小时；驱动冻结另1–2小时 |
| 独立Op首筛 | 4个新输入 × 原路径/两候选；全输出、guard与Graph逐bit | 12 direct、3 capture、126 replay；0模型/HTTP；通常2–5分钟，硬10分钟、第7分钟清理 |
| 只有首筛有效才考虑完整decode | 胜出候选与greedy对照，4个新native/≤16decode，4个新Chat＋2warmup | ≤10模型提交、8wire；拟议硬20分钟、第17分钟清理；此时才推导完整kernel/transfer/capture上限 |

每图126/3=42次replay，分为 **4 correctness＋6 warmup＋32 timing**。四种输入均覆盖三配置的direct/Graph；算法执行总数12＋126=**138**，capture记录的3个kernel节点另计。计时按32组平衡轮换三配置，避免先测完一组再测另一组的固定顺序偏差。完整decode阶段需冻结新的配对输入/RNG与输出工作量合同；若不能保证可比，不把随机输出长度变化当加速。只复用现有native诊断，Chat正式计时不开profiler。

首筛辅助成本也计入：每次cold flush256MiB，含direct/全部replay最多138次，预留总memset≤144次/36GiB；H2D≤40次/128MiB、D2H≤24次/4MiB、D2D=0、helper compute=0。计划显式buffer合计363,315,712B，封顶384MiB；不把它称为CUDA context/Graph allocator实测高水位。资源公式和传输设计在[拟议预算](../output/ninfer-v4-post-sampled-selection-20261024/proposed-budget.json)。驱动冻结前必须逐项对照实际代码，不能照搬旧65536 memset cap或只算计时阶段。

推进条件：逐bit与guard全部通过，无新增未解释spill；至少一个候选cold Graph中位耗时下降≥10%、每Op绝对节省≥12µs，且32个配对计时组中至少24个改善。它们只是首筛门槛，不是统计或发布资格。12µs×64≈0.768ms；相对既有样本约23.2ms的Program归一化轮时间，仅是约3.3%的**条件量级**，不是实测完整round收益。无局部信号即关闭，不自动增加配置、模型请求或补测。

## 5. 收益预期与其它方向

实际收益预测仍为null。若该Op占完整decode的20%/30%/40%，并减少自身耗时10%/15%/20%，相同工作量下完整decode条件节时分别约 **2%/4.5%/8%**。这不是可达区间，实际份额未测；更深预取若不能隐藏延迟，或增加寄存器压力，收益可能为零或负值。后续只在胜出候选的native完整链中观察64次路线命中与实际耗时，避免再把局部百分比直接当整体提升。

| 其它方向 | 当前不优先的原因 |
|---|---|
| Q5 down / Q6 head | 有成本，但Q5真实需要high区且split-K合并风险更高；Q6 head覆盖字节较少，没有更具体的新冗余 |
| 再裁draft词表 | 已有131072行优化head，进一步裁剪涉及资产、覆盖率和接受率，不是相同数学的小改 |
| W6、Lookup、随机MTP再试 | 保留旧结果与缺口，本轮不重新打开旧窗口或补测 |
| 物理proposal-skip / 自适应K | 可直接少算，但当前Graph/stride/MTP状态固定，范围明显更大 |
| DFlash2 | 可能有更大上限，但新增draft模型与状态适配、显存压力，不满足当前小范围要求 |
| workspace / utility / 小norm、Fold | 当前缺容量或关键路径收益依据；已收尾方向不再轮回试验 |

独立源码与证据评审支持本选择的可准备性，未发现阻塞准备的明确缺陷；没有任何GPU性能结论。所有旧失败、18处G1差异、C1附件缺口、原Baseline证据继续保留。完整候选资格和生产发布门禁独立，原服务继续停止。

[机器准备包](../output/ninfer-v4-post-sampled-selection-20261024/preparation.json) · [离线推导与条件情景](../output/ninfer-v4-post-sampled-selection-20261024/static-analysis.json) · [评审结论](../output/ninfer-v4-post-sampled-selection-20261024/REVIEW.md)。
