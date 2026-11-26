# 35 · Tier：完整状态的 RAM / SSD 无损存取

**所属任务 L03；前置 L00–L02、T05/T10 的对应状态能力。当前未实现。**

## 1. 目标与边界

Tier 首先解决闲置 Agent 会话和精确前缀被驱逐后重复 prefill。活跃请求仍使用已经资格化的原 GPU KV 表示和 Attention。它不会直接压缩 GPU KV，也不默认增加活跃生成并发。

本文不是把现有 NInfer 参数换成 Atomic 参数。NInfer/Strata 私有分支未在本包审计；旧服务仅作为业务/回退对照。Atomic 的状态导出与持有权必须按 [34](34_cache_state_contracts.md) 实现。

LoomKV 借鉴点是 exact-length record、GPU 并行解码、直接写入分散页、长度回读移出关键路径，以及传输/解码流水线。其论文实现使用 LMCache/vLLM、128-token chunk 与不同硬件预算，不能照搬整套缓存服务。[论文 §V、VII](https://arxiv.org/html/2611.32954v1)

## 2. 分三个可独立验收的版本

| 版本 | 操作 | 实验必须对照 |
|---|---|---|
| Tier-0 | raw 完整 checkpoint 放入 RAM/SSD 并恢复 | 无缓存重算；验证“缓存本身”的价值 |
| Tier-1 | 已资格对象采用 lossless Codec，其他成员 raw | 同容量/策略的 raw Tier；验证压缩的增量价值 |
| Tier-2 | 直接分页恢复、小缓冲异步流水、长度回读分离 | 相同 Codec 的连续解码再 scatter 对照 |

三者使用同一 StateInventory、target/prefix key、eviction policy 和工作负载。不能把 Tier-0 避免整段 prefill 的收益全部归因于 Codec。

## 3. 存储布局

首版使用进程内 CacheManager；Atomic 的 allocator 与事件所有权保持。RAM cache 保存不可变对象，SSD 保存版本化对象和完整快照清单。可以混合 codec，例如 global BF16 KV 编码、SWA/conv/Q8 raw；一个 snapshot 的所有必需成员必须整体可恢复。

数据对象共享与命中以精确前缀和状态语义为前提：逐 block KV 可共享不意味着在任意 block 末尾都有卷积与控制状态 checkpoint。先允许命中已保存的完整安全边界；命中中间 KV block 但无完整状态时，从最近完整 checkpoint 重算剩余前缀，并把重算记入 TTFT。不得为追求命中率凭 KV 单独跳过计算。

SSD 容量同时记录 logical bytes、文件实际占用、filesystem 分配粒度、临时写副本、索引/日志和保留量。若 RAM 与 SSD write-through 双写，同一个对象在两个介质上各计一次容量，不能把两级名义容量简单相加成独立工作集容量。通过实际淘汰/复制策略与命中曲线计算 raw-equivalent capacity。

## 4. 有界异步数据路径

Store：在提交边界取得 snapshot lease → 申请编码预算 → GPU 编码/生成长度 → completion event → 后台取得长度 → 拷贝精确 payload 到 pinned 区 → 迁入 pageable RAM/写 SSD → 校验并发布目录 → event/引用清理。

Load：验证目录与所有格式 → 为完整目标状态和 scratch 准入 → SSD 读入可复用 host buffer → H2D 传输 encoded payload → GPU 按显式 destination descriptors 直接恢复 → 校验完成与状态完整 → 原子发布恢复状态。

双缓冲是可测试选择，三重/大 ring 不能默认更好。初始候选总 device staging envelope 为 32/64/128 MiB 中**实际容纳至少一个最大 record 的最小值**；host pinned 单独计费。若记录放不下，要定义分块格式并重新验证，或拒绝该 profile，不能越界。候选值是实验起点，不是已验证配置。与 expert streaming 共用预算时必须记录真实同时在途峰值。

上述envelope是所有同时存活的encode输出、load/store buffer、length metadata与codec scratch的合计上限，不是每个buffer各32/64/128 MiB。按34的typed subrecord计算单条最大值，并按真实流水阶段的live allocation并集计算峰值；完整目标state另计。一个record能放下只是必要条件，不能证明整个pipeline准入。

## 5. 直接分页恢复的接口

拟在 NEW `common/atomic-cache-codec.h` 声明：

~~~cpp
struct CacheRecordView;      // validated immutable bytes + identity
struct CacheDestinations;    // bounded scatter spans + layout + valid ranges
struct CacheOpTicket;        // completion event and retained leases
Result<CacheOpTicket> decode_cache_record(
    const CacheRecordView&, const CacheDestinations&, CacheExecutionContext&);
~~~

目标 spans 不允许重叠写，不能指向已经被另一个 active context 使用的页；有效长度、dtype、slot 与绝对位置必须一致。任意偏移/长度不合法都在 launch 前拒绝。GPU kernel 只读/写被合同声明的范围；不自行发布状态。

## 6. 什么时候缓存值得保存

以 trace 估计复用概率，不在初版引入学习型策略。优先 baseline LRU + 明确 byte cost，再比较按完整 checkpoint 的复用价值。估算：

`expected_saved_time = P(reuse_before_eviction) × (recompute_cost - restore_cost) - foreground_store_interference`。

Store 可以异步，但其 SM、显存带宽、PCIe 和 host 开销仍会干扰当前请求；不能把后台耗时自动当成零。没有复用时可跳过压缩或低价值 store，保留可解释原因。

对压缩传输本身，收益上界来自减少 `(raw_bytes - encoded_bytes)/effective_link_bandwidth` 的时间；需扣去不可重叠的编解码、同步、scatter、额外对象管理与状态重建。用实测有效 PCIe/I/O 带宽，不用链路理论数字。

## 7. 拥塞和背压

优先级建议：当前请求必须的 target/专家数据 > 恢复当前请求的完整 checkpoint > 当前已提交块的 store > 推测性 prefetch/冷压缩。执行器仍应避免长传输阻塞高优先级工作；按有界 chunk 与完成事件调度，不能假设 CUDA stream priority 能抢占所有 DMA 或长 kernel。

队列、pinned buffer、文件句柄、未提交对象数均有上限。达到上限时暂停/放弃低价值 store，不扩容到内存耗尽。SSD 满、文件截断、校验失败、codebook 缺失等都使相应对象 miss；完整原始前缀可重算时才回退，不能忽略错误继续恢复。

## 8. 验收

Tier-E 要求 source representation 逐 bit 往返、完整状态一致，以及相同 Attention/执行路径下 teacher-forced 状态与输出通过 E 合同。首个不同 kernel 或数值路径必须另按 N 资格，不能沿用 Tier-E 标签。

性能实验覆盖 no-reuse、RAM hit、真实 SSD hit、冷 miss、LRU 临界、容量充分六类；区分 OS page cache 命中与物理 SSD I/O。记录 restore TTFT、首 token 后 stall、有效请求吞吐、完整 Agent 时间、GPU/host/SSD allocated bytes、传输量和 raw fallback。单并发场景没有 GPU admission queue 时，不沿用论文并发 goodput 结论。

每个能力行沿原 G2–G6；容量扩展单独通过 G4，不要求短请求变快，但须公开代价。活跃请求逐 token 的 host/SSD KV demand paging 继续 DEFERRED，另有设计与授权后才扩展。
