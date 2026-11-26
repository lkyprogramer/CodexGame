# 34 · 缓存对象、完整状态与异步寿命合同

**以下接口均为设计，L00/L01 实现。它们扩展 [05 架构](05_architecture.md)，不替换 Atomic 的 context/stream/allocator。**

## 1. 三种对象不能混为一体

| 对象 | 内容 | 成立的声明 |
|---|---|---|
| EncodedCacheRecord | 一个具有已知原始表示、shape、有效区域的字节对象及 Codec 元数据 | 可逐 bit 恢复该对象 |
| PrefixCheckpoint | 某个精确 token 边界的完整可恢复状态及其对象目录 | 可从该边界继续同目标推理 |
| RuntimeLeaseSet | 当前 stream/event/graph/module/arena 引用的 allocation 集合 | 在最后引用完成前不回收地址 |

一个压缩 KV record 不等于完整 checkpoint。磁盘文件写完也不等于 GPU lease 已释放。共享 physical layer 权重不授权共享 logical slot 的 KV/conv。

首版完整快照只承诺同 session/request 的续接。跨请求 prefix reuse 是单独能力：只共享已证明可共享的模型计算状态，新请求重新建立 RNG、grammar、stop/parser、emit cursor、工具调用身份和权限范围；不得把另一请求的事务日志当成当前请求状态。

## 2. StateInventory 的强制逐成员登记

由真实代码和张量采样建立表，每个成员标注 `persist_exact / reconstruct_with_proof / transient_not_live / unsupported`。任意必需成员 `unsupported` 阻断该快照边界，不能把它留空后继续命中。

| 状态族 | 必填内容 | 首版处理 |
|---|---|---|
| Global K/V | 逐 logical slot、K/V、head、position range、dtype、stride、量化 scale、有效/填充区 | 按原表示精确保存；Codec 分开资格 |
| SWA K/V | ring 数据、绝对 position、first/length、环写指针、mask 所需信息 | 精确保存；不能只存最后 N 个字节 |
| Conv | 每层/循环/stream 的卷积历史和指针 | 默认 raw；不套 BF16 KV 压缩率 |
| 循环/control | 跨 token/调用仍存活的 bank、control、norm 相关状态 | 先证明寿命；瞬时 scratch 不强行持久化 |
| DSpark / 2DSD | feature visits、草稿 KV、Markov/confidence 状态、树节点与提交水位 | 首版只在无在途候选的 quiescent 边界快照 |
| Sampler/协议 | grammar、penalty、stop、EOS、token cursor、emit/commit、RNG 事件账本 | 保持原事务合同；工具副作用记录不重放 |
| 前缀身份 | 精确 token IDs、template/target/draft 指纹、位置/滑窗/循环语义 | 完整核对，不以文本近似命中 |

对于能由已保存状态重建的草稿状态，需声明确定性步骤、输入/版本和成本，并在恢复后执行；不得把“可以重算”当作已完成。恢复 TTFT 包含这些计算。

零 suffix 恢复必须闭合下一步：保存 `committed_tokens / kv_consumed_tokens / next_forward_position / last_emitted_in_kv / pending_correction_or_bonus / next_logits_recipe`。如果最后 token 已进入 KV/conv，则保存有效 next logits 或足以重建 readout 的状态；另一合法选择是保存此前完整边界并明确重算最后一步。禁止在当前完整状态上再次 forward 已处理 token。L01 同时测试“恢复后立即采样”和“有新增 suffix 后继续”。

## 3. 身份分层

1. `target_fingerprint` 保持 03 定义，包含模型资产、原始 KV 表示、loop/cache/guidance/sampler/算术语义。纯无损包装不凭空变成新目标。
2. `logical_prefix_key` 绑定 target、精确 token prefix、position、prefill 分区/语义、边界类型；这是“是否相同计算前缀”的判断。
3. `record_identity` 额外绑定 Codec 名称/版本、codebook digest、layout/endian、block/tile、K/V/slot/head、长度、checksum 和关联 snapshot manifest。
4. `capability_key` 再绑定 GPU 架构、provider、graph、budget、并发、spec/verify shape、所有构建与版本。

逻辑命中后仍需找到能被当前 decoder 解析的物理 record。可选择显式转换已支持的旧格式；未知格式、缺码本、不同 target/slot/循环策略均拒绝。格式不兼容时重算精确 token 前缀，不能尝试“差不多”的解码。

论文的 per-head codebook 是参考，不意味着 Inkling 同一物理层不同 pass 必须共享。L02比较 `physical-layer+K/V+head` 与 `logical-slot+K/V+head`，连同码本 bytes、escape、校准成本一起评估。码本未命中的值须 exact escape/raw fallback，不能截断或饱和。[LoomKV §IV](https://arxiv.org/html/2611.32954v1)

## 4. RecordHeader 设计

L00冻结显式版本化wire协议，L01在 NEW `common/atomic-cache-record.h` 实现；不用 C++ struct 原始内存作为磁盘格式。至少保存：

本地首版明确使用 **typed subrecord + checkpoint directory**：一个 subrecord 只覆盖一个已声明 component/slot/KV-kind/head range/token span，独立格式、长度和checksum；目录列出所有必要成员及其依赖。可以把多个 subrecord 聚合为一个传输 container，但container只提供索引，不改变子记录身份。它不是论文跨所有层的 TileStream record，格式命名不得冒称二进制兼容。`max_record_bytes` 指单个subrecord，容器与同时在途数据另按预算计费。

`magic, format_version, byte_order, codec_id, codec_revision, source_representation_id, shape, strides_or_layout_id, target_fingerprint, logical_slot, physical_layer, loop_pass, kv_kind, head_range, token_start, valid_tokens, raw_length, encoded_length, codebook_digest, payload_checksum, raw_checksum, owning_checkpoint_id, prior_checkpoint_digest, publication_epoch`。

所有 length/offset 使用可检查的无符号宽度，先检查乘加溢出、文件长度和目标容量，再分配/launch。稀疏 offset、超过 2GiB/4GiB 的对象/目录必须测试。NaN payload、±0、Inf、subnormal 及量化 block 的 scale/padding 按原 bits 保存；禁止 decode 经 float 运算“还原”位模式。只允许读取初始化且被合同声明的字节；未初始化 padding 不能随意校验或泄露。

## 5. 发布与恢复状态机

~~~mermaid
stateDiagram-v2
  [*] --> Mutable
  Mutable --> Sealed: 已提交边界且写入完成
  Sealed --> Encoding: 预算预留与读 lease
  Encoding --> Published: 完整校验和目录原子提交
  Encoding --> Aborted: 失败或取消
  Published --> Restoring: 身份核验与目标预留
  Restoring --> Ready: 全部成员与完成事件核验
  Restoring --> Aborted: 解码或校验失败
  Ready --> Retiring: 引用归零
  Published --> Retiring: 驱逐
  Aborted --> Retiring: 在途工作已排空
  Retiring --> [*]: 最后事件与图引用结束
~~~

`Published` 指完整目录可见；每个对象的 publish 必须晚于生产它的 GPU event。快照目录最后发布，读取方不得观察到只有 KV、缺 conv 的半份状态。SSD 推荐临时对象 + 校验 + 提交清单；是否要求 fsync 由“跨进程恢复”或“崩溃持久”能力行分别指定，不能把 OS page cache 完成称为落盘持久。

恢复先预留所有目标与 scratch，逐对象解码到隔离目的地。数据/元信息全部通过，且 GPU event 完成后，才原子切换请求到新状态。任何失败都不部分发布：释放未被引用的新资源、将对象标为无效；在新的合法 context 上重算或明确失败。

## 6. 撤销、取消与投机

只压缩已封口且提交的 block；未提交 token、开放尾块、SWA 正在覆盖的数据不得原地被 codec 读写。可用 COW/sealed copy，但副本计入峰值。首版在 speculation 完全 settle 后保存完整 checkpoint；如果后续要持久化在途 tree，另建能力行，不扩张 L03 的承诺。

Pool 的提交与压缩是两件事：token 一旦 emit/commit 不因容量失败撤销。已提交 raw sealed block 保留到新压缩记录完整、map原子发布、最后raw读者完成；同时新open tail也占预算。未完成压缩积压有界，初版至多一个逻辑token block（覆盖全部相关slot）的pending set；满时背压后续推进，不无限分配。正常容量失败可保留原raw表示，或在已预留/已资格的raw profile重建；无法容纳则明确终止请求，不重复压缩同一不可压数据。异步设备错误另按context退役处理。

取消停止新工作和提交，保留 lease 到最后相关 event。CUDA 异步错误标记 sticky；停止 token/tool commit，drain 或隔离 context；不能在已污染 context 中切到 raw Attention 然后继续。只有 launch 前的干净 `NoMatch` 可以直接使用已资格的 raw path。

## 7. Graph 与 Codec 生命周期

图捕获涉及 page table、record map、原始尾块、codebook、scratch、kernel module 与 arena generation。图对象要持有这些资源的 lease。指针不变但 layout/codebook/有效长度语义改变仍需正确更新或失效；不能仅按 shape 查图。

Host 的长度回读只异步等待自己的 completion event，在后台推进队列；服务主循环禁止因该对象使用 device-wide synchronize。固定容量 GPU 元数据表可以在图外更新，图内 grid/参数布局按捕获合同固定。队列满时施加背压或放弃低价值 cache store，不能无限追加 pinned 内存。

页表/record map的内容也有寿命：必须建立 `last_reader_event → metadata_update_complete → next_replay_wait`，读者包括decode、export/import及校验kernel。也可用双缓冲表与generation切换，旧表等所有读者完成后复用。固定地址和图外更新本身不构成同步证明。

## 8. 必须可观察的输出

每次 cache operation 记录 operation/snapshot ID、状态转移、source/target fingerprints、raw/encoded/allocated bytes、每层级驻留与实际传输、所有 event/lease generation、命中/回退/拒绝原因、部分恢复与重算时间。日志不写私有提示词全文；fixture 和原始 tensor 的存储按用户工程环境权限处理。

本篇契约由 LX01–LX10、LX15–LX19、LX27–LX32 验证；详见 [39 测试](39_cache_validation.md)。

## 9. 续接归属、资源身份和状态词汇的规范化

`request_continuation_checkpoint`在VALIDATED/PUBLISHED时必须包含continuation_binding：owner_session_id、logical_request_id、resume_generation、committed_output_tokens、effect_journal_watermark和authoritative_journal_ref。logical_request_id标识可续接的逻辑请求，重连的HTTP传输ID另记。恢复发布前由当前协调器核对归属、允许的resume generation以及权威emit/tool提交高水位；同target/前缀/权限不代表同请求。老checkpoint只允许按已提交token进行模型重算，不重发输出、不重执行完成的副作用，否则拒绝。新的CUDA/context/ticket epoch在恢复时重新分配，不能把持久逻辑归属当GPU句柄复活。

`model_prefix_checkpoint.continuation_binding`必须为null；请求RNG、grammar、stop/parser、提交日志、工具身份等不得随模型前缀导入。LX13/LX22/LX32覆盖同前缀A/B误配、同A的过期提交水位和合法同owner续接。

唯一物理分配key为`physical_store_id + allocation_id + allocation_generation + medium`。`resource_id + view_generation`标识对该物理分配的某个range/view；ResourceAdmissionPlan负责唯一映射及offset/length。实际副本是不同物理key，多个view共享key只计一次。arena_id/arena_generation另记；同arena内子范围重用必须增加view_generation，即使物理allocation不变。ticket同时绑定物理key、view及arena代际，晚event不得回收新view。representation.location_domain必须等于physical_allocation.medium；其资源字段只是生产证据，恢复时建立新的runtime binding。

图中的Mutable/Sealed/Encoding/Restoring/Ready/Retiring/Aborted是操作与lease状态；JSON的PLANNED/BUILDING/VALIDATED/PUBLISHED/RETIRED/QUARANTINED是持久目录状态，不能机械逐个转换。StateInventory的persist_exact→PERSIST、reconstruct_with_proof→REBUILD、transient_not_live→有证据的ABSENT_AT_BOUNDARY；unsupported会阻塞发布，不能编造成ABSENT。DO_NOT_SERIALIZE_RUNTIME_HANDLE只排除运行句柄，不证明必要模型状态不存在。

哈希方向无环：每个record记录预先分配的owning_checkpoint_id；目录最后包含成员record的完整checksum。prior_checkpoint_digest若存在只指向更早的不可变checkpoint，不指当前拥有它的目录。最终目录hash在成员全部完成后计算，不能让header与owning directory互相包含最终hash。序列化字节顺序与hash覆盖范围由L00冻结、L01实现。
