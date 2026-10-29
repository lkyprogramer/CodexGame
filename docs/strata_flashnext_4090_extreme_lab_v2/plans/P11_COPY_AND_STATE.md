# P11 — 拷贝、状态快照与资源竞争

覆盖O13/O30/O37/O41–43/O45/O51。目标是在24GB显存和64GBRAM内，减少必要数据传输与多余状态复制；同等状态合同优先。

## 1. 源码锚与基本合同

[conversation_snapshot.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/conversation_snapshot.cpp)、[conversation_state.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/conversation_state.cpp)、[conversation_copy.hpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/conversation_copy.hpp)、[conversation_file.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/conversation_file.cpp)、[conversation_snapshot.hpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/include/strata/core/conversation_snapshot.hpp)、[expert_cache.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/expert_cache.cpp)、[verify.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/verify.cpp)。donor具体来源见07/08审计；不能只凭同名机制推断兼容。

一个会话事务至少涉及KV、GDN递推state、conv history、hidden/位置、draft/MTP状态、sampler及prefix身份。任一局部优化不能只保存attention KV就假定可正确恢复。共享blob只能在引用计数、immutable区间和最后读者完成后复用。

## P11-01 拷贝ledger与选择器

记录每类copy src/dst、字节、mapped/pinned/pageable、生命周期、stream依赖、队列、相邻计算、DDR竞争。实际4090连接的PCIe negotiated链路以inventory/测量为准，不能使用显卡标称x16带宽直接估计。

为O30比较两条路径：GPU mapped读取专家blob；CPU整理到固定pinned staging再cudaMemcpyAsync/DMA并GPU算。总成本包含CPU memcpy/quant、pin管理、等待、host唤醒及cache污染。用实际大小（约1.31/1.87MB专家，仅为历史布局例）和真实nt/路由；coldpage、多个copy、CPU pool并发分别测。

拟新增选择器按大小/连续性/当前队列选路径，先离线表，默认旧策略；任何地址别名/host memory lifetime检查失败回退旧路径。没有PCIe stall或当前share极低就不继续投入。

## P11-02 单GPU snapshot shuttle复用

[PR4002](https://github.com/Niko1221/Strata/pull/4002)针对多GPU并行stage copy。单GPU只考虑复用固定shuttle、减少分配和序列化开销；不能宣称获得4卡并行收益。限额pinned staging，完成event后才能复用；取消/失败必须join自有copy再释放。

测试0/1/manysegments、末尾非整段、空state、host/GPU分配失败、copy中取消、restore失败、engine重启；恢复后的state bytes/teacher-forced logits对照fresh recompute。测park/restorewall、CPU/DDR占用、RSS和active请求尾延迟。

## P11-03 增量snapshot与无损压缩

先沿用现有ConversationBuffer单owner、16MiB分段和unchanged-prefix复用，实测剩余copy量；没有剩余热点就停止。只有append-only immutable前缀才可进一步跨snapshot共享；GDN当前state不是简单追加数组。若确有价值，将segment version/refcount与dirty map列为独立、默认关闭候选，分离stable KV pages、当前递推state、draft scratch、metadata。按照模型/tokenizer/template/量化布局/位置版本生成key；编辑prefix触发正确失效。

压缩优先仅cold snapshot、低优先级CPU线程、限额buffer；解压和校验完成前不提交restore。目标quant KV已经低比特，但熵和可压缩比未知，先采样压缩率与CPU成本。还要计入压缩线程与CPU专家争DDR；仅节省空间但拖慢当前任务不能过性能门。

测试随机页/全零页/损坏checksum/截断/版本不符/重复页引用/evict共享页/cancel同时restore。state事务完整才可发布，错误不静默重用。

## P11-04 SSD冷层

SSD snapshot可改善可容纳会话数，但读写时间不保证比re-prefill小。PR3341仅作为待重新核验的候选源；执行前必须读取当前固定diff、写入源锁并核对是否已上游，本包未将其加入可自动prepare注册表。

使用独立有界目录，文件头记录source/model/state format/hash、atomic写入/rename、checksum、磁盘quota与LRU；不存密钥；不删除不属于实验的文件。先测SSD实际顺序/随机吞吐和可用空间；不能把权重盘pagecache被快照污染的成本忽略。

判定比较`restore_from_SSD + decode`与`re-prefill + decode`、swap/OOM风险、写放大和disk busy；没有真实长冷会话复用就暂缓。

## P11-05 ReplaySSM与推测回滚

NInfer/SGLang的ReplaySSM是设计来源；先测当前verify checkpoint/rollback占比，若很小就停止。探索从最近完整checkpoint按真实transition重放，禁止数值不稳定的“逆矩阵撤销”冒充exact。保留主state、conv、hidden、KV append位置和MTP一致提交。

测试accept0/1/all、不同T、reject后立刻cancel、EOS/工具边界、chunk边界、prefill后spec、restore后spec。E轨道要求同状态同token逐位；改变reduction顺序降N并走长teacher-forced。比较节省的copy bytes与新增compute、graph和scratch；replay更贵标NO_GAIN。

## P11-06 统一后台copy配额

active KV和本轮必要专家高优先级；预测预取/SSD写/冷snapshot压缩低优先级且可取消。仅单独stream不保证硬件隔离；需有显式inflight字节/任务上限，避免把DDR/PCIe填满。所有copy带owner epoch，旧epoch不能写入新会话状态。

先重放trace离线模拟再实现拟新增budgeter；burst和压力恢复要无饥饿、无无限队列。回归context8/64/122K、decode+restore、prefill+prefetch。若配额只推迟必需copy而无降低关键路径，结束。

## P11-07 编辑前缀与多级循环状态checkpoint（O51）

普通KV页的共享不能自动恢复GDN/conv的历史状态。先记录实际Pi编辑发生位置、从最近合法checkpoint重放的token量和时间；若绝大多数是追加，或最近checkpoint已足够，标NOT_APPLICABLE/NO_GAIN。目标不是默认增加每token快照。

拟新增有界checkpoint目录，key包含model/tokenizer/template/格式版本、完整prefix token hash与token位置，value是该位置一致的KV边界、GDN/conv、hidden与MTP状态。周期边界与热点工具/文件边界是两类候选，先trace模拟内存—重放成本曲线，再选少量位置；所有层状态在同一commit时点发布，不能拼不同轮的checkpoint。

编辑发生在位置p时，选择严格不越过最长匹配前缀的最近合法checkpoint，恢复后重放剩余真实token。失效的后缀页与所有依赖循环状态一起回收；shared/pinned/donor保护仍生效。prefix文本相同但tokenizer/template不同不命中；重放过程中取消不提交半状态。

拟新增测试：编辑首/中/尾、恰在checkpoint边界与前后1token、4token page/conv窗口边界、相同prefix不同后续、删改tool结果、连续回退、checkpoint损坏、内存预算满时淘汰、restore失败重算。对照从头prefill的state和teacher-forced logits；E不成立则降N走质量门。至少同时记录保存开销、存储bytes、重放token、避免prefill wall和active decode影响。

完整会话cache与增量checkpoint共享RAM预算，不得在6144MiB会话预算外偷偷再分配无界目录。组合O39/O40/O41后重测压力与guard。恢复成本不低于重新prefill、命中率低或副本挤出更有价值会话时停止；默认关闭并可丢弃实验checkpoint后回到fresh recompute。

## 统一验收

输出状态事务图、每buffer owner/last-reader表、copy ledger、kernel/state测试、注入失败记录、paired多会话性能与资源余量。默认关闭候选；不能通过缩小128K、削弱RAM floor或隐藏fallback获得PASS。
