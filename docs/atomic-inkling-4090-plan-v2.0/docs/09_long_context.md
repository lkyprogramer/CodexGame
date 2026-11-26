# 09 · 长上下文、KV与会话续接

## 1. 128K必须定义清楚

两个不同指标分别命名：

- **C128K服务**：总context capacity=131072，输入+预留生成+必要特殊token均在其中。
- **P128K基准**：应用模板后的真实输入P=131072，再生成指定N。capacity至少P+N，不能只设 `-c 131072` 就宣称完成。

所有长度用目标tokenizer在应用正式模板后计数。日志保留送入模型的token IDs/hash、server确认的prompt_n、截断标记（必须false）及输出预留。跨模型业务比较使用同一任务内容，但不强求不同tokenizer的token数相等；报告双方实际token数。

## 2. 扩展顺序

4K → 16K → 64K → P128K；200000和262144输入作为后续独立行。每一级检查完整prefill、末尾decode、prefix续接、cancel/retry、接近容量时的spec rollback。

长输入包括真实仓库代码与工具历史、多文件符号/依赖定位、多needle与顺序约束。重复文本和随机token只用于容量/算子压力，不能代替任务能力。

官方模型卡最高1M的声明不允许跳过这些步骤，也不允许超出实际能力后静默删除历史。[S02/S03]

## 3. KV与attention

global与SWA分别计量。SWA ring必须保留绝对位置、写指针、当前窗口数据和conv状态；窗口外丢弃只能遵循模型原本语义。避免意外启用swa_full导致几十倍内存增长，也避免把global当SWA缩短。

Q8 KV为首选验证基线（若后端不支持，明确用F16建立基线），Q4/TurboQuant属于另一个数值/质量分支。其验证必须覆盖long-context检索、Java跨文件关系、spec接受率和恢复，不只测短prompt的perplexity。不同压缩codec记录group size、scale、padding、dequant kernel和actual bytes/token。[S01/S13]

## 4. Prefill与chunking

context容量与prefill microbatch不是一个数。固定目标语义下扫小范围microbatch，测TTFT、峰值workspace与吞吐，保留分块边界测试。若relative mask创建全长矩阵导致峰值，应先修正确分块，不靠截断prompt。

prefill期间生成draft feature的成本必须记录；长prompt下可能完全抵消decode加速。2DSD上游某些shared-KV模式禁止chunked prefill，不能把主线chunking协议直接套过去。[S06]

## 5. Continuation cache

借鉴现有NInfer/Strata的完整会话续接经验，但不宣称它们的实现已在Atomic存在。缓存的是继续生成所需状态，不能只存KV或最后hidden。

首版按单slot、精确前缀、显式save/restore实现。缓存清单至少含：各loop global/SWA KV、conv、位置与slot映射、模型epoch、KV codec、草稿器可恢复状态或明确重建策略、sampler/grammar/stop状态、校验和。跨深度/LoopCD/KV模式不共享缓存。

GPU→RAM→SSD分层按请求停用/恢复设计，不在每token把完整KV来回搬。比较保存/恢复耗时与重算前缀耗时，只有净收益成立才启用。SSD缓存容量、生命周期和删除策略明确；模型升级产生新namespace，不能误读旧格式。

## 6. 续接必测场景

1. 对完整prompt重算与“prefix restore + suffix”比较logits/输出/状态。
2. prefix恰好跨SWA窗口、conv长度、microbatch和loop边界。
3. 非前缀编辑：聊天中间一条消息变化，缓存必须miss或只重用真正相同的token前缀。
4. tool_call_id、工具结果与assistant continuation序列化一致，不因文本看起来一样误命中。
5. 保存时已有in-flight draft：只保存已commit状态或先结束事务。
6. 文件损坏、部分写入、旧epoch、错误codec、磁盘不足：拒绝恢复并安全重算，不输出污染结果。
7. 连续100次save/restore/cancel后资源无持续增长；回放下一个独立请求没有状态泄露。

## 7. 多子代理的服务策略

默认GPU执行并发1，2–3子代理的请求进入有界队列。测排队时间与session切换成本；长prefill不能无限饿死短请求。只有并发2在内存、状态隔离和尾延迟通过后才增加物理并发。

优先级/抢占可作为独立后续实验，不能在首版引入没有完整checkpoint的中断执行。工具有外部副作用时，在未commit模型输出前不执行工具，重试使用idempotency策略，避免重复动作。

## 8. 闲置会话的host parking候选

新增[G05](25_ghost_tasks.md)吸收Ghost“离开GPU的会话保留在host”思路。对象是完整闲置Inkling状态，不改变当前活动请求的KV策略或single active generation=1。先reserve/驱逐，再复制，最后原子发布；恢复、opening、staging、重编码权重和其他快照共用host账本。G05依赖T10/T11，仅在完整状态一致、PCIe搬运后E2E/尾延迟仍有收益且G6通过时启用。固定“五个会话”不能替代64GB容量管理。


## v2精确缓存与长context

缓存复用按34/35：只有完整checkpoint才跳过前缀，KV块内命中没有conv/controller边界时从较早完整状态重算。Tier不提高活跃GPU KV容量；Pool单独通过36/39。新增P8K/32K/200000诊断点并保留原C128K/P128K区别；P+N+lookahead与真实tokens验证不变。持久格式改变、量化改变、prefill分区或loop策略改变不得复用旧记录。

## v2.0 · 两种SSD对象不可混淆

专家权重stream是不可变模型资产的读取；会话Tier是带完整状态、版本目录和原子发布的checkpoint写入/恢复。共用预算、I/O队列和寿命规则，不共用“缓存已支持”的资格。会话存储的写量与SSD持久性成本仍需统计，不能引用权重只读路径来宣称会话缓存没有写放大。[35](35_tier_cache_design.md)与[41](41_magnitude_source_audit.md)分别定义两类对象。
