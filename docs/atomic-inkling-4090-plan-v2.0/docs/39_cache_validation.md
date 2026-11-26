# 39 · 缓存、资源协同与上游变更测试合同

**全部模型/GPU/业务测试为NOT_RUN。本文新增LX01–LX32与UX01–UX04，保留原96项；外部源码审查和本包自检不勾选这些测试。**

## 1. LX32项

| ID | 场景 | 可判定断言 |
|---|---|---|
| LX01 | 身份/源码/码本失效：codec/source/dictionary/layout/stateinventory changed with stale cache | identity mismatch refuses reuse and never transfers old qualification |
| LX02 | 真实表示与错误dtype：Q8_0 compressed record mislabeled BF16 or paper ratio applied to Q8 budget | format mismatch and unmeasured budget rejected; same-target claim fails |
| LX03 | 全部位型与量化block：all raw bit patterns, signed zero, subnormal, nonfinite payload, scale/quant blocks and tails | byte-identical lossless roundtrip independent of model numerical validity; model-validity checks still reject invalid active values |
| LX04 | 不可压数据与输出上界：incompressible/random/high-entropy blocks and maximum encoded size | bounded output and raw fallback fit reserved peak; average ratio never used as hard bound |
| LX05 | 长度/offset/截断/恶意记录：length/offset/index overflow, malformed symbol table, truncated chunk and expansion bomb | host/device range guards reject before unsafe read/write; no partial model state publication |
| LX06 | 缺块/乱序/错slot：checksum collision candidate, reordered/missing/duplicated chunk and wrong slot/range | complete manifest validation and exact content/domain checks reject; hash lookup alone not a prefix proof |
| LX07 | 完整StateInventory：StateInventory omits conv/controller/draft member or lacks rebuild proof | qualification BLOCKED; independent prompt recompute catches later state drift |
| LX08 | 块内prefix边界：prefix ends inside cached block with only end-of-block conv snapshot | use earlier complete checkpoint and replay suffix or miss; never crop KV and reuse later conv |
| LX09 | 精确token与模板身份：same text but different token IDs/template/tool serialization/position/scope | refuse prefix reuse except exact legal token prefix and identity |
| LX10 | emit/KV/next-logit游标：resume last emitted token already/ not yet in KV; pending correction or bonus | cursor contract prevents duplication/skip; next logits and AR64 continuation match |
| LX11 | SWA/conv/page联合边界：SWA, conv, codec block, page and prefill boundaries crossed together | valid spans, absolute positions, write cursors and complete state match independent oracle |
| LX12 | last-loop的prefill分区：last-loop cache saved under one prefill partition restored under another or B>1 | target/policy mismatch rejected; storage block cannot silently change semantic partition |
| LX13 | 跨请求私有状态隔离：cross-request model prefix sharing with source RNG/grammar/tool state attached | only permitted model state is shared; new request states are independently rebuilt and isolated |
| LX14 | 在途草稿与安全快照点：save during in-flight draft, partial pass or uncommitted branch | quiesce/rollback to complete committed boundary or refuse save; unpublished suffix never leaks |
| LX15 | 存取各阶段故障注入：cancel/short-read/OOM/disk-full at each save, encode, publish, restore phase | atomic visibility, reservation release and safe retained source; no partially restored session |
| LX16 | raw/encoded并存峰值：raw and encoded representations retained together with metadata/scratch/staging | unique allocation ledger counts real duplicates and alias once; observed GPU/host peaks within reserves |
| LX17 | pinned/mmap/PSS计费：host pinning in place versus separate pinned copy, mmap/page cache and anonymous repack | physical-memory accounting avoids doublecount and omission; pinned is charged in host domain |
| LX18 | 碎片/页内空洞/延迟回收：small compressed objects, page slack, fragmentation, metadata and delayed reclamation | allocated ratio and peak reported separately from payload ratio; steady ratio not used for admission |
| LX19 | 恢复和fallback暂态准入：restore fits steady state but not transient old/new state plus raw decode target | reject before copy or make safe eviction/checkpoint choice; fallback must fit same budget |
| LX20 | 压缩发布与raw尾块：Pool seal/unseal with raw tail, speculative writes and shared prefix readers | COW/private writes, commit watermark and reader leases preserved; no unverified block published |
| LX21 | 图表内容与地址generation：graph replay while pool page/metadata/module/arena generation changes | old resources remain leased; graph invalidated or qualified indirect update; no stale address/function |
| LX22 | 迟到event与sticky故障：late encoder/decoder/DMA completion or error after request cancel/epoch rotation | sticky fault stops commit; late result retires only, cannot publish to new epoch |
| LX23 | PCIe竞争/背压：Tier restore plus foreground expert fetch plus background flush under PCIe pressure | bounded tickets/pinned/chunks, priority applied, foreground and tail latency measured; no claimed free overlap |
| LX24 | CPU/内存/工具干扰：codec CPU/DRAM contention with CPU experts, tokenizer and Java tools | record actual shared-resource workload and Agent makespan; standalone codec GB/s cannot grant E2E PASS |
| LX25 | 完整Attention参数矩阵：Pool global/SWA/sink/relative-bias/softcap/head geometry/stride and tails | every dispatch explicitly supported or clean fallback; same decoded inputs compared to raw reference |
| LX26 | E Codec与N Attention：byte-exact codec with changed attention reduction/accumulation and near-tie routes | E codec and N attention separately qualified; frozen tolerance and required QC cannot be bypassed |
| LX27 | native DSpark组合：Pool plus each qualified native k/B, rejection position, EOS/stop/max_new/cancel | full state/RNG/cursor after restore and AR64 continuation correct; actual q and final target unchanged |
| LX28 | 2DSD tree组合：2DSD tree depth/frozen/fork with compressed sealed prefix and private branch state | actual proposal ledger, finalized watermark and all rejected branch state isolated; experimental source is not qualification |
| LX29 | LoopCD目标组合：LoopCD reference/final coda states with cache restore | guided target and readonly reference preserved; unguided p cannot masquerade as guided verifier |
| LX30 | 冷热命中与长context：warm/cold/partial hit/miss/invalidation/eviction/churn at 64K C128K P128K | actual input/reused/computed tokens and all costs saved; no truncation or selected fastest-only report |
| LX31 | 假PASS/缺原始证据：schema-only PASS, missing artifact, zero GPU launches, synthetic ratio and omitted paired failures | semantic validator rejects; source/CPU/GPU/model/business evidence remain distinct |
| LX32 | 续接循环/soak/回退：A-B-C-A switching, >=100 repeated save/restore/cancel, original 8h service soak | active generation=1, no leakage/swap/OOM/tool duplication, original 200 request and context coverage unchanged |

LX04/LX15/LX20必须包含raw overflow空、只剩一个slot和完全耗尽；确认失败不写slot0、不发布坏map、不撤销已emit前缀，并且停止/回退有界。LX05增加2GiB/4GiB整数宽度与8191/8192/8193字节尾块。LX10包括零suffix恢复；LX13区分同会话与跨请求；LX21检查metadata内容reader/update/replay事件边。

## 2. 上游更新回归UX

| ID | 场景 | 验收 |
|---|---|---|
| UX01 | 2DSD runner_check prefix-equal but output lengths differ; empty result set; returncode0 with mismatch | qualification wrapper rejects every mismatch/empty set; compare full state and exact lengths, not only first_divergence |
| UX02 | 2DSD native exact/served, Atomic quant oracle, formal/varloop and pinned revisions mixed | reject incompatible comparison; native FP64/served Hopper rounding is a diagnostic reference, not automatically Atomic oracle |
| UX03 | 2DSD lagged read sharing with static graph full planes and Humming import without actual SM89 launch | measure actual allocated bytes; no capacity grant from sharing; compile/launch/output evidence mandatory |
| UX04 | cuda-oxide reverse writes, prior trapping assertion, 2D writes_all_elems and stale proof artifact | pin f35d6ccc revision; reject unsupported2D coverage and stale witnesses; prove scope then independently test GPU numerical behavior |

## 3. 必需实验矩阵

1. Source representation：真实Q8_0 baseline；实际支持时才纳入F16/BF16/FP8；Q4为单独质量目标。
2. Mode：无缓存重算、raw Tier、compressed Tier、限定Pool、完整所选Pool。先单项后组合。
3. Prefix：不复用、RAM hit、物理SSD hit、部分命中、miss、错误epoch、容量临界、容量充分。
4. Context：实际P=8192/32768/65536/131072/200000，并保留4K/16K及C128K；按P+N+lookahead准入。失败/不支持不截断冒充。
5. Spec：none→已资格native DSpark各k/B→单独资格的2DSD。active generation=1；并发2/3另立行。
6. Data：真实Java/工具trace、均匀随机、极端escape、全位型、长位置漂移；校准/探索/确认/质量holdout分离。

## 4. 指标与原始证据

保存TTFT、ITL/TPOT、request/Agent耗时、p50/p95/p99、失败/超时、实际输入与生成tokens、完整prefix命中与重算tokens、payload/stored/allocated/全引擎峰值、raw尾块和pending、metadata/codebook/overflow/graph/scratch、host pinned/PSS、物理SSD I/O、H2D/D2H、codec与attention时间、foreground stall。p99只在足够样本时给出，不能用小样本精确尾延迟承诺。

同一合法表示、同一目标的raw reference作Codec/Pool对照；Q8与BF16压缩是另一个精度/容量比较。性能测试不带profiler，另采诊断trace。原5%/10%、CI、p95、质量、8h/200请求条件全部继续有效。

## 5. 现在能运行的包检查与未来命令

包内preflight/helper测试只检查工程包和统计工具；详见[tools](../tools/README.md)。L00之后才存在`lab.py cache-run`，具体命令见38。CUDA sanitizer、kernel launch、Lean证明、模型和服务尚未运行；机器状态与空测量保持NOT_RUN/null。

任何schema-only成功、上游CI成功、architecture skip、编译PTX/cubin或论文reported结果都不能通过本测试表。新原始记录的语义验证器由L01实现；JSON Schema不检查磁盘文件真实性、真实GPU执行或因果收益。

## 6. 身份与条件覆盖补充

LX13/LX22/LX32加入相同prompt/target/权限的不同逻辑请求A/B、A已推进后的过期checkpoint，以及合法同owner恢复；校验resume generation和权威提交/副作用日志，不能回拨已提交输出。LX16/17/19/22加入不同physical store的同本地allocation ID、同arena内子view复用与晚ticket，确认物理块只计一次但真实副本不漏计。

LX31同时拒绝config.cache_profile旧扁平别名、PASS已选cache却缺artifact，以及hash合法但capability不匹配的资源计划。计划null实例继续有效，不构成资格。

LX27只适用于native_dspark，LX28只适用于2dsd，LX29只适用于LoopCD guidance；serial Pool不等待这些未选研究。适用性由冻结profile机器求值，记录不适用不能授予该feature资格。LX32的功能子集用于L03，完整soak仅在T11后由L07/T12消费。
