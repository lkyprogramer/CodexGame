# P04 — 投机窗口、lookup 与草稿成本 Implementation Plan

> **For agentic workers:** 执行时使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans`，逐任务审阅再扩大试验。本文是未来实施计划；未在 RTX 4090 目标机运行，不含已实现承诺。

**Goal:** 改善每单位真实请求时间完成的目标 token 与任务数；先校准和扩展现有 DraftPolicy，再评估长 lookup 窗口和更便宜的 draft。保持目标 sampler、停止语义和完整 hybrid state 的一致性。

**Architecture:** 现有 MTP/SuffixDrafter → 只观察的 round 账本 → 本机成本与候选选择 → Verifier 校验 → 原子 commit。先保持 `--spec 4 --spec-min-p .5`，只改一个预注册变量；树状 draft 是独立研究子项目。

**Tech Stack:** C++/CUDA `sm_89`，固定 Strata main `41cf05a06a25dd29103b7b27a2279a3f60c21876`。实际 Flash-Next hybrid MoE 与 GDN/QSA/conv 状态；dense 27B 的权重、树 mask 或测量结果不可直接代用。

**Spec:** 包内数值、benchmark、统计和组合协议。覆盖 O23、O26、O33–O36、O38。O37 ReplaySSM/完整 checkpoint 的实现归 P11；本计划定义它应满足的 draft/verify/rollback 合同。

## Freshness：审计锚与执行锁

2026-10-25 最后刷新：实验执行锁为 [`4b9e05a2a806a3fe24f7b2560d98626c37dade35`](https://github.com/Niko1221/Strata/commit/4b9e05a2a806a3fe24f7b2560d98626c37dade35)，release v0.2.6；本文保留41cf的固定源码引用。项目已核对两锁之间`src/core`、`include/strata/core`、CPU/CUDA kernels与prefill的git对象相同；Qwen generate只有spec-split非bitexact说明增量，serve还有空消息400/one-token rate修正，CMake版本变化。执行时保留新锁的API修正，不用旧固定引用误称当前入口完全未变。相关新diff仍须随实验manifest记录。这个刷新不是本机性能验证。

## 1. Global Constraints 与已存在能力

- `--spec-min-p .5` 是 **draft 概率截断阈值**，不是请求 sampler 的 `min_p`。manifest 必须分别记录 `spec_min_p` 与 sampling 参数。[S1]
- `DraftPolicy` 已实现按窗口宽度的 EMA 成本、3 个 context bucket、MTP 概率校准、lookup match 统计、stale 探测、`keep_draft` 和 `chain`。O33 是对其未覆盖成本的增量研究；不是从零实现 adaptive spec。[S2][S3]
- 当前 `DraftPolicy::kMaxT=8`；`SuffixDrafter` 已用 trigram、最近 4 个位置和有界索引。不能把“加哈希 lookup”当新成果。扩大到 16 需要核对所有数组、pool MAXT、图/状态和接口，而不只改一个常量。[S2][S4]
- MTP 已有 `make_q4_head/make_q4_dense`、draft vocab、coupled/probabilistic draft 路径。先核对实际 effective 模式；MTPQ4 和 LOOKUP2 的既有边缘/无收益结果不重复包装。[S5]
- 当前 baseline overlap=1 排除 autoasync；P04 比较中保持它，避免把迁移策略变化归给 spec。
- 任何 proposal 变化只有在目标验证和采样协议完整保持时才可能保持目标分布。greedy 的 identity 不能证明随机采样；相同 seed 下输出不同也不自动证明分布错误。按包内 E/N/Q 规则分层审查。
- GDN/conv 是 recurrent state，不能把 dense attention 的树扩展只套在 KV mask 上。拒绝 draft 后，所有状态必须回到已接受前缀。

## 2. 源码入口与不可破坏的合同

| 现有文件/符号 | 本计划关注的合同 |
|---|---|
| `src/spec/draft_policy.cpp::choose / observe / keep_draft / observe_probs / chain / set_context` | 成本单位、接受计数、bucket/冷启动、探测和策略状态 |
| `include/strata/spec/draft_policy.hpp::DraftPolicy` | `t=1+drafts`，kMaxT=8，现有 context bucket 范围 |
| `src/spec/suffix_drafter.cpp` 与 `SuffixDrafter::append/propose/propose_after/reset` | 只索引已合法接受的历史；未接受 proposal 不污染后续检索 |
| `src/core/mtp.cpp::MtpDrafter::load/bind/make_q4_head/set_draft_sampling/draft` | draft vocab token 映射、q 分布与抽样、私有 state/graph |
| `src/program/generate.cpp` spec 主循环 | 实际 round 起止、EOS/tool stop、max_new_tokens、sampled/greedy 分支 |
| `src/core/verify.cpp::Verifier::run/commit/copy_logits` | 接受前缀提交、state 与 target 输出的一致性 |
| `include/strata/core/spec_prob.hpp`、`coupled_draft.hpp` | probabilistic acceptance/correction 与 coupling 的真实合同 |

固定链接 [S1]–[S7]。修改之前应从调用点确认实际走到哪个分支；存在代码不等于本机已启用。

## 3. 必须先修正的计量口径

### 3.1 Round ledger

**拟新增** `SpecRoundLedger` 最少包含：`request_id, round_id, context_start, proposal_kind, target_rows, draft_count, accepted_draft_count, committed_target_tokens, correction_tokens, bonus_tokens, eos, stop_reason, round_start_ns, round_end_ns, lookup_ns, draft_ns, verify_ns, commit_ns, graph_capture_ns, cpu_miss_count/bytes, migration_epoch, effective_tier, graph_bytes, expert_cache_bytes`。

真实主指标是：

\[
R=\frac{\sum committed\_target\_tokens}{\sum round\_wall\_seconds}.
\]

`committed_target_tokens` 以实际输出/推进的 token 账本为准，包含真实提交的 correction/bonus，不能无条件用 `accepted+1` 处理 EOS、取消和长度边界。accepted draft 数是诊断量；spec=0 仍能提交 target token。

Round wall 的起止必须覆盖本轮真实经历的 draft/lookup/verify/commit 及必要等待。流水执行用真实时间区间，不把重叠阶段相加。verify 内若已包含 CPU stall，不再加一次 stall；不得平均“每轮 token/s”代替总 token/总时间。graph 首次 capture 冷成本单列，同时仍进入请求 TTFT/总 wall，不能从总体结果删除。

### 3.2 离线策略的可辨认范围

旧策略只观察被选中的宽度，未执行宽度没有真实反事实成本。回放可验证计数、规则稳定性、资源约束和有观测支撑的选择；用估计填补的结果必须标 model estimate。正式比较需要有限、预注册的 exploration 或独立同输入 replay，计入探索开销，不能声称仅凭离线 replay 已证明新控制器更快。

### 3.3 首先测的 workload

真实 Pi sampled/thinking、Java 修复/测试、工具轮次、无重复自由生成、copy/edit、重复前缀但后缀错误；短/中/长 context 分开，最长样本预留输出和模板空间。固定 tokenizer/template/system/tools 后，输入+输出预算+4096余量不得超131072。

控制器按总体 workload 权重选择；copy/edit 成功不自动代表生成、推理或工具任务。质量统计保留合法模型失败，time-to-success 给失败预先声明的预算值，不能只对成功样本平均。

## 4. 拟新增接口/开关

| 拟新增名称，当前 main 不存在 | 默认与限制 |
|---|---|
| `STRATA_LAB_SPEC_LEDGER` | 默认关闭；预分配、抽样；最终性能轮关闭重观测 |
| `STRATA_LAB_SPEC_POLICY=baseline|shadow|cost_v2` | 默认 baseline，shadow 不改变宽度/候选来源 |
| `STRATA_LAB_SPEC_COST_MANIFEST` | 指纹包括机器、权重、KV、CPU内核、placement、graph 集；不匹配拒绝 |
| `STRATA_LAB_SPEC_GRAPH_BUDGET_MIB` | 有界额外图预算，与 P08 lease 协商；无空间沿用当前宽度 |
| `STRATA_LAB_DRAFT_HEAD_VARIANT` | 默认原 head；量化/词表版本显式记录，不改变 target head |

PR #4040 的 `--lookup-max-t` 属 **PR 候选参数**，不宣称当前 main 支持。迁入后才可暴露。不要新增与现有 `STRATA_SPEC_COST` 功能重叠的公开开关；cost_v2 先作为内部 shadow，只有正式证据支持才决定接口。

## 5. 任务清单

### P04-01 — 列清现有策略与 round 计数

- [ ] 保存 `spec/lookup/lookup-chain/spec-min-p/STRATA_SPEC_COST`、coupled/prob 模式及 sampler 的 requested/effective 值。
- [ ] 在 serve 与非 serve 两个 spec loop 核对 `policy.observe` 传入 `accepted` 与 `round_ms` 的意义，检查异步流水分支计时。
- [ ] ledger 与实际 token 输出、state 位置交叉核对；专测 accepted=0、partial、all、EOS、tool stop、max_new=1、取消。
- [ ] 用 spec 关闭或宽度1作为控制，确认 accepted_draft=0 不会让有效吞吐错误归零。

**验收：** 所有 round 计数可解释，无重复输出/丢失，时间区间不双计。**Stop：** 指标不守恒或不同执行分支分母不同，先修计量，停止策略比较。

### P04-02 — O33：现有 DraftPolicy 的本机校准与归因

- [ ] 先测现有 `STRATA_SPEC_COST` on/off 的资格和本机表现；既有 bucket `<6K/<24K/>=24K` 并未把 32K/64K/128K 或 tier 变化显式区分。[S3]
- [ ] 在 shadow 中加入 CPU miss bytes/nt、tier/migration 状态、graph 是否已捕获和额外 graph bytes。先小维度 bucket/线性修正，不把每个 expert ID 变成高维在线模型。
- [ ] 对候选宽度记录：预计提交量、整轮 wall、决策费用、graph capture 冷费用、挤出 expert 后新增 miss。缓存机会成本经 P03/P08 的实际预算估计，不能只看多分配了几 MiB。
- [ ] 新 bucket/滞回/探测预算在校准集冻结；状态重置、会话切换、长 context 过渡都有明确策略。保留现有先验/冷启动 fallback。
- [ ] 优先比较 spec4 附近已支持的宽度，且考虑 `spec_min_p=.5` 本身已经截短窗口，不按配置上限当每轮实际宽度。

**指标：** ledger 总 token/总wall、任务时间、接受长度分布、decision cost、宽度切换次数、graph bytes、CPU miss、成本预测残差。**测试：** 无历史、新 context bucket、成本突变、stale 再探测、cancel 后 reset、异常时间样本、T 边界。**Stop：** 更复杂的状态不比现有政策稳；只校准题赢；graph/CPU nt 成本抵消接受提升。

### P04-03 — O34：长 lookup 与 MTP 深度分离

- [ ] 审阅 PR #4040 固定 head `4dd7b4812d7f15b6d6a49e6ba7961f154183ee94`，逐项 diff 当前 main；作者同 GSQ-RCO IQ3_XXS/2060 Super 的数据只作资格线索。[P1]
- [ ] 保持 MTP spec4，分别资格 lookup8/16。明确 `T` 是总 verify rows 还是 draft tokens，给每个 CLI/内部数组写映射；不能有 +1 off-by-one。
- [ ] 审计 pool MAXT、ExpertJobMulti、router plan、MTP cache、Verifier graph、QSA/GDN/conv scratch、accepted 状态快照和 memory guards。只捕获确实需要的有限宽度。
- [ ] 增加 graph lease admission：预算不足或捕获失败时在安全点回落已支持宽度，不释放 live graph 地址。

**测试：** T=1/4/8/16 的边界、0/全部/中间拒绝、page/ring 边界、长重复错误后缀、EOS 位于窗口中部、16 行专家聚合上限、A→B→A恢复。**Stop：** PR 在当前结构无法保持 state 合同；新宽度让 CPU 工作和图显存大于有效接受收益；目标任务 copy/edit 占比不足。不得把作者百分比写成本机预期。

### P04-04 — O35：现有 suffix 索引的费用与门控

- [ ] 测 `SuffixDrafter::append/propose/propose_after` 在真实长 history 的 CPU 时间、索引占用、hash 冲突和候选命中；已有 trigram 表不重复实现。[S4]
- [ ] 仅在发现真实瓶颈时优化重置/增量 append/缓存候选；匹配必须核对真实 token，不能凭 hash 直接接受。
- [ ] history 只含合法 prefix 和已接受输出；`propose_after` 的未接受草稿不得写回 permanent history。
- [ ] gate 使用本任务真实成功率与费用；探索预算显式限制，零重复文本应迅速回到 MTP/target。

**测试：** 相同 trigram 不同后缀、超长周期、词表边界 token、容量上限、恢复后索引、取消后的 history 长度。**Stop：** lookup 已只占微小份额；收益仅来自自复述训练文本；新索引内存抢走 expert/RAM headroom。

### P04-05 — O23：已有 draft head 量化/词表的增量

- [ ] 用 `MtpDrafter::make_q4_head/bind` 核对已有 Q4/vocab 行为，先重现实机既有 MTPQ4 边缘结果。
- [ ] 若 head 在关键路径占比足够，才试新的 draft-only quant、紧凑词表或低秩候选。target embedding/head/最终 sampler 保持原版本。
- [ ] token ID 映射必须双向验证；候选词表漏掉 token 只影响 proposal，不能无声截断 target 分布。
- [ ] sampled 分支若 acceptance/correction 依赖 q，必须获得完整、定义一致的 proposal 概率；低秩 shortlist 不提供 q 时不得冒称精确 rejection sampling。

**测试：** 每个 vocab ID 映射、OOV proposal、head logits/prob 数值、greedy 与 sampled 分开、penalty/history、temperature/top-p/min_p。**Stop：** draft 变快但接受下降使总 wall 不降；需要量化 target 才获得结果则转 P08/P10 Q 轨。

### P04-06 — O26：accept/commit 设备端 bookkeeping

- [ ] profile 确认真实 D2H、小 kernel、host decision 或同步占比；现有图空隙低时先做 Amdahl 上界，不能为小片段重写协议。
- [ ] 只融合原本多余的计数/flag，保持 correction/bonus 与 state commit 的顺序及取消响应边界。
- [ ] 明确 host 可观察 `accepted_count`、输出内容、下一轮位置、GDN/conv/KV/MTP commit 的 happens-before。

**测试：** accept0/1/all、EOS/tool stop、截断输出、copy error、用户取消、下一请求继续、不同 stream/event 延迟。**Stop：** 份额太小，或融合让取消/错误回收不可解释；保留原 commit。

### P04-07 — O36：Flash-Next 匹配的更强 draft 资格

- [ ] 在代码之前提交 qualification card：target 模型 hash、tokenizer、hidden 层/维度、所需 feature、训练数据/预算、draft 权重来源/许可、推理 adapter、显存和 cache 需求。
- [ ] HyperQwen 的 dense 27B DFlash 与 EAGLE-4 的现成 draft 不能因同属 Qwen 就直接用于 hybrid Flash-Next。[D1][D2]
- [ ] EAGLE-4 固定 SHA 的成本模型/低秩 head 源码使用 `LicenseRef-Eagle-4-Source-Available`，不作为普通 MIT/Apache donor 直接复制。可依据公开算法独立实现，或选已核对许可的实现；实质复制须先满足该具体授权。[D3]
- [ ] 先小 context/小 draft 证明接口、state 和采样协议，再评估完整128K与CPU专家流量。训练/权重不存在就标 BLOCKED，不写伪速度。

**Stop：** 无匹配 draft 或训练预算、draft 占用挤掉过多 resident expert、接受质量不足、代码许可不支持拟议复制。此研究失败不阻塞 P04-01至06。

### P04-08 — O38：树验证研究，先证明父状态

- [ ] 只在匹配 draft 已资格后建 tiny tree oracle。每个 node 显式有 parent、token、position、attention visibility、GDN/conv parent state。
- [ ] 同一父节点的不同子节点从相同父状态开始；不同分支不能共用线性更新后的 GDN 状态。accepted path 之外的状态全部丢弃。
- [ ] 比较 tree 与串行逐路径 reference，覆盖 parent permutation、非连续 node index、共享 prefix、拒绝、EOS、rollback；N 轨数值不能简写成逐 bit。
- [ ] 树节点使 CPU expert、多份 state、KV/graph scratch 增长，全部计入 wall 和内存，不只报 target forward 次数减少。

**Stop：** tiny oracle 不成立、Flash-Next parent state 没有完整设计、4090/RAM预算不足、分支 expert 工作膨胀。没有完成这些前，状态为 research，不进入默认候选组合。

### P04-09 — 统计决策与回退

- [ ] 正式 holdout 前冻结 workload 权重、task budget/retry、样本数、主指标和非劣界。模型失败进入配对4格表；infra错误单列，不丢弃有效慢结果。
- [ ] ABBA/BAAB macroblock 为重采样单位，独立进程、相同 warmup/history 初态；控制器热身和冷启动结果分别报。
- [ ] 长任务使用冻结的 time-to-success/失败封顶规则；质量 delta 的配对下置信界与预设门比较。30个任务只作筛选；零discordance时不能直接用退化bootstrap的[0,0]宣布非劣。
- [ ] 恢复旧 binary、所有 policy 状态、draft 格式、图集和配置；不可只恢复 `--spec 4` 却保留新图预算/学习表或不同 draft 权重。

任何 state 污染、丢 token、sampled 分布协议错误、OOM 或质量门失败立即停止性能测试。无可重复总体收益则保留计量改进和结论，不强行交付新控制器。

## 6. 必测目标与交付

已有目标：`draft_policy_test`、`suffix_drafter_test`、`controller_test`、`spec_start_test`、`draft_kv_plan_test`、`coupled_draft_test`、`spec_prob_test`、`draft_cap_test`、`spec_verify_parity`。先从固定 CMake/`ctest -N`确认当前 build 的可用目标与所需 GPU/模型。[S8]

拟新增：`tests/spec/spec_round_ledger_test.cpp`、`tests/spec/spec_cost_shadow_replay.cpp`、`tests/core/lookup_wide_state_parity.cpp`、`tests/core/tree_parent_state_oracle.cpp`。仅前两个是常规增量所需；后两个分别由长lookup/树分支启用，不为了凑覆盖提前实现整套树。

交付：真实入口图、ledger schema、policy diff、旧/新资格清单、model/draft/tokenizer指纹、状态测试、配对原始数据、有效提交量和任务统计、失败/退出记录、可恢复旧图集。所有 benchmark 数值标明“本机实测/上游作者实测/模型估算/待测”。

## 7. 一手来源

[S1]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/program/generate.cpp
[S2]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/include/strata/spec/draft_policy.hpp
[S3]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/spec/draft_policy.cpp
[S4]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/include/strata/spec/suffix_drafter.hpp
[S5]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/mtp.cpp
[S6]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/verify.cpp
[S7]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/include/strata/core/spec_prob.hpp
[S8]: https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt
[P1]: https://github.com/Niko1221/Strata/commit/4dd7b4812d7f15b6d6a49e6ba7961f154183ee94
[D1]: https://github.com/syv-ai/HyperQwen/blob/ce9615c4f2309be727407918a6c979bd67968069/patches/dflash2-lookup-drafting.patch
[D2]: https://github.com/eagle-hq/EAGLE-4/blob/60bab6b469e795d47bda82b16243b82bb7b6206f/docs/architecture.md
[D3]: https://github.com/eagle-hq/EAGLE-4/blob/60bab6b469e795d47bda82b16243b82bb7b6206f/LICENSE

可参考的宽度成本与候选边界实现：[FLARE rounds.rs，固定 SHA](https://github.com/NVIDIA/flare-local-inference/blob/bce032c014bae34502ba22d3304fa084d5b40afe/helios/src/scheduler/rounds.rs)。其官方设备范围与本机不同，移植控制思想不等于迁入 SM120/121 内核；实质复制 Apache-2.0 代码保留对应 NOTICE。EAGLE-4 的算法启发、代码复制许可与匹配 draft 权重资格必须分开记录。
