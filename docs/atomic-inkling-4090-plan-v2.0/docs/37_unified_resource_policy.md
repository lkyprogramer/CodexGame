# 37 · 统一资源预算与缓存、专家、投机的协同

## 1. 统一账目，不强制统一 allocator

Atomic 保持各模块既有拥有权。新增 ResourceLedger 汇总 `physical_store_id, allocation_id, allocation_generation, medium`及`resource_id/view_generation → physical key + range`映射；另记`arena_id/arena_generation, owner, role, reserved_bytes, allocated_bytes, live_leases, retirement_event`。每个物理分配计一次；多个 view 只记录引用，不重复加总。

GPU 包含权重、packed/expert cache、全部 KV/conv/loop、草稿、verify/tree、图池、staging、codec/codebook/map/overflow、allocator padding 和 driver 未跟踪量。Host 包含匿名副本、mmap 实际驻留、page cache、pinned、快照、服务/代理与 OS。SSD 包含双写、临时对象、索引、文件系统占用和持久性成本。保留 [04](04_hardware_memory.md) 的余量规则。

## 2. 净收益怎么算

在**相同目标、上下文、投机宽度、并发、图与业务语料**下：

`net_gpu_freed = raw_profile_peak_allocated - candidate_profile_peak_allocated`。

诊断公式 `raw_KV - encoded_KV - extra_overhead` 只有在其他项相同且没有重复计费时成立。报告稳态与峰值两个结果；容量准入用峰值。raw source 仍是同一 allocation 时不重复计入，但新旧 arena 并存或 migration copy 是不同 allocation，必须计费。

### 只作算术演示

若原 KV 为 6 GiB、payload ratio=0.71，payload 节省 1.74 GiB。若新增加的页/尾块/码本/图/缓冲等总峰值为 0.25 GiB，则净收益只剩 1.49 GiB。所有数字是假设，不是 Inkling 或 4090 实测。

更关键的比较：GGML Q8_0 每 32 标量约 34 bytes，而 BF16 为 64 bytes。忽略其他开销时，`0.71 × BF16 = 45.44 bytes/32`，仍大于 Q8_0 的 34 bytes。因此，把已有 Q8 KV 改成 BF16 再无损压缩不能自动增加容量；它最多是另一条精度/容量取舍，必须作为独立 profile 比较。[GGML 类型依据见 04 的固定源码索引]

## 3. 三种预算层级

| 层级 | 运行时职责 | 不承担的事情 |
|---|---|---|
| Static profile envelope | 启动时预留完整 worst-case 所需/已资格上界与 reserve | 不靠未来平均压缩率准入 |
| Safe-boundary reallocation | 新请求或 quiescent 边界重新分配可用预算 | 不挪用仍有 event/graph lease 的地址 |
| Offline policy selection | 用同 workload 比较预算分配候选并冻结赢家 | 不在生产在线搜索、改阈值或随意升级 codebook |

Pool 对不可压数据要有有界 raw 路径或明确拒绝；不能假定每个 block 都达平均比例。未知或超上界的数据先拒绝/重新准入，不能超卖显存后依赖 OOM 回收。

## 4. 节省字节只能分配一次

L06 分别测以下完整 profile：

1. 所有节省保留为 headroom：检验稳定性及缓存收益本身。
2. 分配给更长合法上下文：检验新增能力及延迟，输出 reserve 不变。
3. 分配给专家驻留：仅当原路径存在真实专家搬运时；记录 H2D bytes、stall 和命中。
4. 分配给已资格 DSpark/verify buffer：记录 draft 额外工作、接受长度、完整请求时间。

上述不是同时兑现的承诺。若权重已经全驻留，给 expert cache 增加预算没有必然收益。若 GPU active=1，更多可驻留会话也不等于更高活跃并发吞吐；可能只减少顺序请求恢复成本。

## 5. PCIe 与 SM 干扰同样计费

缓存 restore、专家 fetch、DSpark feature copy、日志/长度回读会竞争同一链路；编码/解码与 attention/GEMM 竞争 SM、寄存器和带宽。记录每类 H2D/D2H、真正重叠和串行关键路径，不把总 kernel 时间相加冒充 wall time。

后台 store 可能推迟下个 Agent turn；只有完整 trace 能发现。无独占测试条件则不做速度结论。CPU Xeon/DDR4/PCIe Gen3 属历史记录，现场 T00 确认后再选择实际并行度、NUMA/pinned 策略。

## 6. 交互实验

只对各自已资格的因素做有界组合。两因素 A=cache、B=DSpark 或 residency，跑 00/10/01/11 四格；保持目标、输出长度、上下文和其余条件，AB/BA 随机化与时间分块沿 14。

用 log latency 定义交互项 `I = log(t11) - log(t10) - log(t01) + log(t00)`，并报告区间与各格原始时延。这是分析工具，不是验收新阈值。I<0 是超出该乘法参考的协同线索，不改变原 ≥5%/≥10% 请求收益门。

若 A 改变 capacity，不能同时声称四格服务的是同一资源问题；分别做等工作负载比较与等硬预算的新容量比较。质量变化、量化变化和 last-loop/LoopCD 变化单列，不混入 E 类开关矩阵。

## 7. 长上下文矩阵

增加诊断点 8192、32768、65536、131072、200000 **实际输入 token**，保留既有 4096/16384 和 C128K 总容量口径。每行容量需容纳 `P + N + lookahead + alignment`，模板应用后再计算 P；200000 不等于 200 Ki tokens。

不支持或装不下的行写 UNSUPPORTED/DOES_NOT_FIT 并保留原始错误，不能静默截断、减少输出或缩短循环。它们不阻断较短行的真实资格，也不能被较短 PASS 覆盖。并发矩阵首先是 active=1，active=2/3 仅作独立可选资格。

## 8. 立项和结案

优先实施能减少真实关键路径或解除已确认容量缺口的项。任何来源只改变候选列表，不自动重开旧 CPU pool、launch overlap 或 DFlash2 的 no-benefit 结论。需要新 trace、可证伪机制和单变量对照。

最终发布冻结整个组合：target + source representation + Codec/码本/格式 + pool/tier + residency + draft/schedule + kernels/toolchains + graph + budget + 任务数据。局部最优不能替代完整组合验收。

## 9. Magnitude机制如何落在同一账本上

BudgetSnapshot绑定物理store、OS采样与ledger epoch；reserved / allocated / retiring分别记录但采用不重复计费的物理集合。AdvanceReservation先覆盖下一advance所需的KV、conv、loop、verify空间再launch，不能用平均接受率或平均压缩率借未来容量。实现与L01共用，M00只补缺失字段和MGX测试。

TransferTicket的退休条件是DMA完成且最后读者完成；已发出hint取消仍需等待，source/destination任何generation变化都不得由晚到event复活。需求工作保留staging份额，可取消的只有尚未发出的hint。显式冻结调度顺序并用aging或有界工作量防止后台必需checkpoint长期饥饿；不得为了释放内存驱逐当前请求马上需要的专家形成来回搬运。

先记录真实RouteTrace，再离线比较因果LRU/frequency/reuse与Bélády miss下界（可避免驱逐miss的改进上界）。后者使用未来信息，只衡量替换/驻留的miss空间，不能作为在线算法成绩或stall/预取时延上界。仅当真实expert miss/SSD stall主导时启动M01预取实验；all-resident可结案NO_BENEFIT。Pool节省、驻留策略或图改变会使CostEpoch失效，重测M02合法draft宽度与plain，不照搬旧接受率/verify时间。全部接口和MGX01–16在[42](42_magnitude_integration.md)。
