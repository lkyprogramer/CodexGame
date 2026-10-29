# P03 — 驻留价值、专家分流与预取 Implementation Plan

> **For agentic workers:** 执行时使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans`，按独立任务实施并在扩大实验前审阅。本文是实施计划；拟新增接口、实验开关和结果文件均不表示已经实现或在目标机跑过。

**Goal:** 在完整保留实际 router 选择、专家权重与模型计算的前提下，减少暴露在关键路径上的 CPU miss 和迁移等待。优先改善已有策略的成本依据，不重复实现已经存在的缓存、lookahead 或多 token expert 分组。

**Architecture:** 真实路由 trace → 本机成本表与离线筛选 → 只观察的影子决策 → 有界、可回退的在线驻留/分流。决策与执行分离；槽位 epoch、在途 GPU 读者和 host 源数据所有权继续由已有执行层管理。

**Tech Stack:** Strata C++/CUDA，RTX 4090 `sm_89`，Xeon Silver 4216；本机 CUDA 12.3 与现有编译配置。固定主线 `41cf05a06a25dd29103b7b27a2279a3f60c21876`。生产 A0/EXACT6 与新主线基线必须分别冻结。

**Spec:** 包内 `docs/01_MACHINE_AND_PROGRESS.md`、`03_ARCHITECTURE_AND_CRITICAL_PATH.md`、`12_NUMERICS_AND_QUALITY.md`、`13_BENCHMARK_PROTOCOL.md`、`14_STATISTICS_AND_SELECTION.md`、`config/directions.json`。覆盖 O07–O12、O14；O13 的跨业务拷贝仲裁归 P11，本计划仅提供专家 copy 的优先级与预算接口。

## Freshness：审计锚与执行锁

2026-10-25 最后刷新：实验执行锁为 [`4b9e05a2a806a3fe24f7b2560d98626c37dade35`](https://github.com/Niko1221/Strata/commit/4b9e05a2a806a3fe24f7b2560d98626c37dade35)，release v0.2.6；本文保留41cf的固定源码引用。项目已核对两锁之间`src/core`、`include/strata/core`、CPU/CUDA kernels与prefill的git对象相同；Qwen generate只有spec-split非bitexact说明增量，serve还有空消息400/one-token rate修正，CMake版本变化。执行时保留新锁的API修正，不用旧固定引用误称当前入口完全未变。相关新diff仍须随实验manifest记录。这个刷新不是本机性能验证。

## 1. Global Constraints 与当前代码事实

1. 当前基线已设 `STRATA_ADAPT_OVERLAP=1`；`adapt_async_self_decides()` 对 overlap 明确返回不适用。不得把本机 baseline 写成会自动混用新 async 策略。改变策略只在预先声明的实验 arm 中进行。[S3]
2. `expert_pool_dispatch_multi()` 已按 expert 合并多 token，并区分 resident、PCIe 与 CPU 工作；O12 先查剩余重复开销，没有缺口就关闭该方向。[S2]
3. `RouterLookahead`、`ForesightSwap`、`FileExpertSource::prefetch/prefetch_pairs` 已存在。O11 的新工作是预测质量、预算与现有路径适配，不是首次添加预取。[S2]
4. `ExpertCache` 已支持分层槽位、分段 VMM、`shrink/grow`。统一的 KV/graph/scratch 预算归 P08，不在这里重建 allocator。[S1]
5. 移动计算到 CPU/GPU 可能改变舍入与后续路由，通常归 N；只有同一 placement、同一算术与输出逐 bit 相同的元数据/所有权改动可归 E。不能用“真实 router 没改”推断整体 bitwise。
6. 实际 CPU GU/down 格式按 tensor inventory：偶数层 IQ2_XS/IQ4_NL，奇数层 IQ2_XXS/Q2_0；不要用 IQ3_XXS 包名索引成本。单 token 偶数层已接近实际 DDR 带宽上限，增加线程不能创造带宽。P01/P06 的 pool/ISA 改动必须单独冻结后重新校准。
7. 仅在隔离 worktree 和实验进程中实施。生产端口 18343/28343 不属于自动实验对象；实验端口沿用 18089，持有单 GPU 锁，不与 CPU 带宽微基准同时跑。

## 2. 源码锚点与责任

| 现有文件/符号 | 本计划使用的合同 |
|---|---|
| `src/core/expert_cache.cpp::read_expert_profile / ExpertCache::open_sized / layer_slot_range / fill_slot_queued_parts / sync_queued / verify_slot` | profile 与实际槽位、变长 blob、copy 完成验证；不得在 DMA 尚未完成时发布 resident |
| `src/core/expert_source.cpp::expert_pool_dispatch_multi` | 合法窗口内按 expert 聚合；保留每 token activation、weight 和输出位置 |
| 同文件 `FileExpertSource::blob_parts / tier_of / commit_copies / note_async_read` | 数据实际来源、分片 bytes、迁移和在途读取的生命周期 |
| 同文件 `RouterLookahead::submit / stats_score / run` | 已有预测输入、命中统计与 worker；先核对运行资格和是否实际启用 |
| 同文件 `ForesightSwap::take / hold / unhold / predict / request_locked` | 已有有界暂存与读者占用；错误预测不能代替真实选中 expert |
| `src/program/generate.cpp::adapt_overlap / resident_stage_swaps` 与 adaptive 主循环 | 迁移发生在哪个 window、对当前 request 生效的时点 |
| `include/strata/core/adapt_async_default.hpp::adapt_async_self_decides / AdaptAsyncSelf` | existing blocking/async 资格、测量状态与回退 |
| `src/core/verify.cpp::Verifier::run / commit` | CPU/GPU 工作最终 join 与已接受前缀的 state commit |

固定文件来源见 [S1]–[S4]。所有新策略先通过已有入口注入，不把 `generate.cpp` 再扩成另一套调度系统。

## 3. 首先测什么：trace 与成本单位

**拟新增** `ExpertDecisionTrace`：`request_id, round_id, layer_id, expert_id, nt, gu_type, down_type, actual_blob_bytes, source_tier, selected_route, slot_epoch, route_weight_summary, queue_submit_ns, ready_ns, compute_done_ns, reader_exit_ns, critical_wait_ns`。时间戳使用一致的 host 时钟；GPU 时间通过关联 event 单独记录，不能直接与 host 时间作未经校准的减法。

分开记录 `copy_bytes_requested`、`copy_bytes_completed`、`prefetch_bytes_used`、`evicted_future_hit_bytes`、CPU 读取估计与硬件计数器实测。`76 misses × 1.59 MB / 6.2 ms` 只能是粗略推算，不能标成真实逐 tensor DDR 流量。

成本表以 `(phase, layer-shape, GU/down dtype, nt, source tier, queue bucket)` 为键。decode 与 prefill 分开；使用真实 pool 路径修复后的 Q2_0 微基准，不沿用走错 ggml 路径的旧数值。记录当前 GPU cache 容量、KV 长度、graph 集和 CPU placement，才能解释成本变化。

对 expert e 的驻留启发式可用 `预计复用次数 × 避开的边际关键路径时间 − 迁移/驱逐成本`，再除以 `bytes(e)`。这里的“边际时间”由实测 DAG/重叠关系估计，不等于 CPU phase 的全部时间。H2D→cold GPU compute 是串行依赖，resident 与 cold GPU compute 还竞争同一 GPU，不能简单把三个时间取 max 后宣称精确模型。

离线同路由 replay 只用于筛选；placement 改变后的真实路由、CPU/GPU 排队、prefetch 争用需要在线 A/B。无 counterfactual 测量的候选成本必须标“估计”，不得变成实测收益。

## 4. 拟新增接口与开关

以下名称均为**本计划拟新增**，不是当前上游可运行 CLI。

| 拟新增项 | 默认与边界 |
|---|---|
| `STRATA_LAB_EXPERT_POLICY=baseline|shadow|value` | 默认 `baseline`；shadow 只记录决策，不更改 placement |
| `STRATA_LAB_EXPERT_COST_FILE` | 带模型/tensor/ISA/机器/主线指纹；不匹配则拒绝加载并回退 |
| `STRATA_LAB_EXPERT_TRACE_RATE` | 默认 0；固定上界的预分配 ring，drop 有计数，不阻塞热路径 |
| `STRATA_LAB_PREFETCH_BUDGET_BYTES` | 默认 0，未授权本分支时不开启新增预取；不得挤占 live KV/graph/state |
| `STRATA_LAB_PREFETCH_MAX_INFLIGHT` | 有界；必须接 P11 的必要 copy 优先级，不与 adaptive 各自无限排队 |
| `STRATA_LAB_RESIDENCY_HYSTERESIS` | 默认使用现有策略；实验数值在校准集冻结 |

拟新增纯策略模块 `include/strata/core/expert_cost_policy.hpp`、`src/core/expert_cost_policy.cpp`，输入 immutable snapshot，输出有限长 `ExpertDecision`；执行层在 epoch 安全点重新验证决定。先实现 shadow，无证据不必实现全部开关。

## 5. 任务清单

### P03-01 — 冻结配置并证明 trace 不扰动

- [ ] 保存实际 `--expert-profile`、adaptive 周期、swap 数、overlap/async effective 值、cache bytes、PCIe share、模型清单与 EXACT6 状态。
- [ ] 在 `expert_pool_dispatch_multi`、copy submit/complete、window join 周围加入抽样 trace；不得在每个 spin 或 claim 中增加共享原子计数。
- [ ] 选择固定 teacher-forced 路由回放和正常请求，比较 trace on/off 输出、wall、trace drop 与时间排序。

**验收：** 观测开销落在预先冻结的 A/A 噪声预算内，真实路由和 bytes 可关联。**Stop：** 当前 trace 无法分辨 CPU 暴露等待与已隐藏工作，先修观测，不算缓存价值。

### P03-02 — O07：成本/字节的驻留价值

- [ ] 在固定路由 trace 上比较现有 frequency profile、按 bytes 归一、按边际等待价值三种策略；相同 VRAM bytes 上限，不固定槽位数冒充相同容量。
- [ ] 对变长 IQ2_XS/IQ4_NL 与 IQ2_XXS/Q2_0 blob 使用实际大小、decode 成本和 nt 分布。
- [ ] 先生成可审阅的新 profile 与 shadow 决策，再接在线增量 swaps；保持原 profile 可一键恢复。
- [ ] 把迁移 bytes、驱逐代价、最小驻留时长、滞回和老化写进 manifest。策略只使用当前及过去信息。

**指标：** 总 request wall、CPU critical wait、每层 miss bytes、eviction 后再 miss、GPU hit、迁移成本、有效提交 token/s。**测试：** 相同 size 的并列分数确定性、0 容量、仅能容纳一个 blob、不整除层容量、迁移失败与旧 profile 读取。**Stop：** hit 增加而 wall 不降；收益靠挤掉 KV/graph 或训练任务 profile 过拟合。

### P03-03 — O08：三路成本分流

- [ ] 使用 resident GPU、CPU 原位、H2D 后 GPU 三路的当前排队完工时间估计；已有分流为回退 oracle。
- [ ] 先固定 cache 与 route，仅把一个明确的 miss 子集作为 treatment；保留真实 top-k 和 combine weights。
- [ ] 采用有界贪心/有限候选比较，避免复制 Fiddler 对小 Mixtral 的指数枚举。为本机建立 CPU/GPU/PCIe 竞争惩罚，不能只用理想 bandwidth。[D1][D2][D3]
- [ ] 决策必须在原 GPU plan 发布合同允许的时点完成，避免为更复杂估计丢失 overlap。

**测试：** 全 resident、全 CPU、全 transfer、三路混合、无 CPU miss、copy 失败、队列过载、同 expert 多 token；N 轨 teacher-forced logits/路由/GDN 和自由生成非劣。**Stop：** 决策本身或 DDR↔PCIe 争用吞掉省时；动态策略预测误差使尾延迟失控；只有离线估算好看。

### P03-04 — O09：已有 overlap/async 的明确资格与成本

- [ ] 给启动日志记录 `requested/effective/reason`，基线保留 overlap=1 且 autoasync 不适用的原因。
- [ ] 分离三个 arm：生产 overlap；显式 blocking；显式 async。后两者仅在合法资格下测试，并把关闭 overlap 本身列为 treatment，不把它隐藏到候选配置中。
- [ ] 保留同一 prompt、warm 状态和 adaptive 观察历史；记录 `AdaptAsyncSelf` 的测量/试验/完成状态与实际窗口数。
- [ ] 若修改控制器，只改观察量和滞回；不要同时改 cache selection、CPU pool 和 spec 深度。

**指标：** migration critical stall、host memcopy 与 CPU expert 争用、相同 token 数下 wall；长阶段和任务切换分别报告。**Stop：** async 在 64 窗附近的偶然阶段获胜而完整请求退化，或目标配置本来不具备资格。

### P03-05 — O10：已搬入 expert 的驻留晋升资格

**当前生产形态为 NOT_APPLICABLE。** PR #2964 固定 head [`f8184f25c169f6459b2e2a1524731055f54c5d90`](https://github.com/sergqwer/Strata-pr/commit/f8184f25c169f6459b2e2a1524731055f54c5d90) 明确排除 overlap 等模式；实际PCIe share很低。以下是未来配置变化时的资格清单，不为使PR可运行而关闭当前overlap或人为提高PCIe share。已有guard必须保留；另一个配置实验需要作为单独treatment和基线评估。

- [ ] 先统计当前 PCIe share 下可晋升候选 bytes、未来复用和还需 copy 的比例。无候选则归档 no-op。
- [ ] 对在途 staging blob 明确 `(slot, epoch, reader set, copy completion)`；晋升不得覆写仍被 graph/compute 使用的数据。
- [ ] 用原始 PR 思路作为候选，逐函数重接当前 main。若要求关闭生产 overlap 才可工作，先比较总代价再决定是否继续。

**测试：** 读者延迟、slot 重用、迁移失败、相同专家多 consumer、epoch 变化、取消/下一请求。**Stop：** 需要破坏当前 overlap 或晋升收益不足；只保存分析和安全测试，不强行引入 promotion。

### P03-06 — O11：已有 lookahead/foresight 的有界改进

- [ ] 先列当前 `RouterLookahead/ForesightSwap` 的 enable 条件、预测输入、线程、上限和是否实际命中；先优化已有路径的观测与预算。
- [ ] 对历史路由或 residual-based predictor 分别做 shadow，记录 precision、recall、提前量、完成但未使用 bytes、污染的热集。DALI/HybriMoE 的机制用于提出假设，不把论文设备上的收益移植成 4090 数据。[D1][D4]
- [ ] 执行时只提前复制预测专家；真实路由出现后，全部实际选中专家照常计算。错预测是多余带宽/缓存成本，不允许跳过真实 expert。
- [ ] 以必要 KV/expert copy 优先，限制预取 bytes、inflight 和 residency lease；无空闲预算则放弃本次预取。

**测试：** 0% 命中、100% 命中、突变任务、误预测热集冲突、长 context host-KV、restore 同时发生、取消后预测不泄漏到下一会话。**Stop：** 预测计算或 copy 竞争增加关键路径；需要少算 expert 才有收益时转 P10 Q 分支。

### P03-07 — O12：现有聚合后的剩余去重

- [ ] 对照 `expert_pool_dispatch_multi` 已有分组，定位仍重复的 metadata、host blob 分片获取或 queue entries。
- [ ] 仅处理同一合法 verify 窗口中相同输入来源的可共享读取；不把 nt=4 改为四个 nt=1，也不合并不同 activation 或跨层状态依赖。
- [ ] 若唯一剩余成本是已经被 overlap 隐藏的小元数据工作，直接归档不实施。

**测试：** duplicate expert、token 顺序变化、weight 不同、重复 route 的输出位置与累加顺序、所有 nt 边界。**Stop：** 现有代码已完成所提去重；新 grouping 成本比所省成本大。

### P03-08 — O14：会话热集与切换

- [ ] 先观察真实 Java/工具任务的会话间 route divergence 和切换频率；没有分布差异就保留全局热度。
- [ ] 候选采用全局主 profile + 有界会话修正，记录生命周期与版本，不把每会话分成固定显存小岛。
- [ ] A→B→A、冷启动、新任务和长期同任务分别测试；校准集不含留出任务。

**Stop：** 容量分割降低总命中、warm profile 已足够、切换成本大于复用价值。旧 profile 和 cold 行为必须保留。

### P03-09 — 端到端判定与回退

- [ ] 独立进程组成 ABBA/BAAB macroblock，四个 `process_instance_id` 共享一个 `paired_block_id`；warmup、profile reset、case order 固定。
- [ ] 先筛选，再冻结正式 holdout 的样本数、主要指标和 stopping 规则。按照包内统计协议判断，不能看一次有利 CI 就停。
- [ ] 每个 arm 输出实际算法/格式/placement。模型任务失败计有效结果；infra/config/log 错误单列，不删除慢的有效失败。
- [ ] 保存旧二进制/config/profile/hash；候选关闭后只在安全窗口结束或重启自己的实验进程恢复。不得只改 resident metadata 而留下旧 slot 内容/epoch。

**必须回退：** 错权重、UAF/epoch 污染、任何 hang、非有限输出、显存/RAM 越界、N 轨质量门失败。**无收益退出：** wall/time-to-success 的预注册收益门未通过，或关键场景退化门未通过；保存 trace 和失败归因即可，不以“命中率变高”强留 patch。

## 6. 最小验证与交付

已有 CMake targets：`expert_cache_per_layer_test`、`expert_cache_segmented_test`、`expert_cache_slot_guard_test`、`conversation_validation_test`；是否可运行受测试构建与 GPU 条件限制。先 `ctest --test-dir "$STRATA_TEST_BUILD" -N` 核对，不把缺 CUDA/模型的 skip 记 PASS。[S5]

拟新增：`tests/core/expert_cost_policy_test.cpp`（纯决策和容量）；`tests/core/expert_policy_replay.cpp`（trace replay）；`tests/core/expert_epoch_transition_test.cpp`（延迟读者/迁移失败）。新 targets 只在实现并接入 CMake 后调用。真实 GPU integration 必须另跑，host mock 无法证明 DMA 正确。

交付至少包括策略小 diff、成本表版本、trace schema、effective config、正确性报告、原始配对日志、预注册统计和 no-benefit 记录。先保留最小有效策略，再与 P01/P04/P08 做组合；组合增益按组合实测，不能相加。

## 7. 一手来源与移植边界

[S1]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/expert_cache.cpp
[S2]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/expert_source.cpp
[S3]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/include/strata/core/adapt_async_default.hpp
[S4]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/program/generate.cpp
[S5]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt
[D1]: https://arxiv.org/html/2602.03495v1
[D2]: https://arxiv.org/html/2411.15715v1
[D3]: https://github.com/efeslab/fiddler/blob/227715bfd6e8c731b29548eab01d9919c4fe9564/src/fiddler/mixtral.py
[D4]: https://github.com/PKU-SEC-Lab/HybriMoE/blob/508a85b9a43dff37124370d8816e411e74827803/ktransformers/operators/experts.py

补充 donor：tqLLM `MixedExpertCache::prefetch/prefetch_released/reserve_staging` 的 [固定源码](https://github.com/turbo-tan/tqllm/blob/c2163c2da408603331a5814f62fd1f287f54370b/src/experts/tq3_expert_cache.hpp)，用于预算和 bank 生命周期对照。Fiddler/HybriMoE/tqLLM 若实质复制代码，按各固定 SHA 的 Apache-2.0 LICENSE/NOTICE 保留出处；论文机制独立实现不意味着复制代码。DALI/ScheInfer 此次未确认可直接移植的官方仓库，不虚构函数或实现状态。
