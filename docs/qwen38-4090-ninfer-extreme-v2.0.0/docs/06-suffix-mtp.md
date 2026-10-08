# 第一条增量路线：Suffix/Lookup + 现有 MTP

## 1. 为什么先做这一条

保留同target、codec、200192容量和MTP驻留，只在可预测的输出上**延长**草稿链。无需新增DFlash2权重，是验证"我的Java/rewrite流量能否利用长重复"的最小实验。收益未知；思考链和短tool JSON未必值得，不能因一个复制题快几倍就推广。[S09]

## 2. 两个版本，先做v1

### v1：MTP链延长（零bridge，2026-09-09采纳为首版）

MTP常驻照跑：每轮仍由`mtp_bridge_and_propose`产出3个greedy草稿`d1,d2,d3`，MTP私有KV/ar_hidden照常前进。CPU侧`SuffixIndex`在`[committed…, d1, d2, d3]`之后查最长匹配，若命中则把链**延长**到K≤5（W≤6），延长部分`d4,d5`的q为one-hot，走`speculative_round.cuh`现有的exact rejection sampling。

- 零MTP状态修改、零bridge、零新kernel、零新权重；W=6在44a small-T专用路径（T=1..6）与`--draft-tokens ≤5`合同内。
- GPU侧唯一改动：每轮draft数组长度可变（`live_proposals ∈ {3,4,5}`），verify/commit按实际长度走；未命中时与现网**逐字节相同**。
- 命中时每轮最多多2个候选；`d4`的匹配条件是suffix在`d3`之后继续匹配，所以MTP拒绝`d1..d3`中任一处时延长部分自然作废，不需要额外修复逻辑。
- 上限W=6：copy类拿不到W16的3–4×，这正是T12（W16）的动机；T12依赖T07+T06，不依赖DFlash2完成。

### v2：alternating-source + MTP bridge（仅当v1命中率足够）

某轮用suffix整条替代MTP草稿（K可到5），之后MTP私有KV/hidden必须由`mtp_bridge_and_propose`消费所有已提交target hidden/token形成正确next-draft起点（§4）。它能在长复制段减少MTP draft成本，但catch-up成本可能吞掉收益；只有v1的`suffix_hit_rate`与`extra_committed_per_round`显示长重复确实存在时才做。

## 3. 首版算法：bounded n-gram/suffix chain

独立纯CPU `SuffixIndex`，不强求完整suffix tree。状态为按session隔离的已提交token ring、rolling-hash索引和位置版本：

```cpp
struct LookupCandidate { vector<TokenId> tokens; uint64_t source_begin; uint32_t matched; };
optional<LookupCandidate> lookup(span<const TokenId> committed_plus_drafts, uint32_t max_k);
void ingest_committed(span<const TokenId> delta, uint64_t frontier);
void rewind_to(uint64_t frontier);
```

- 索引ngram长度初始{4,8,16,32}；先尝试最长，hash命中后逐token确证，不用hash碰撞当真命中。
- `lookup`的查询前缀是"已提交历史 + 本轮MTP草稿"，返回的是草稿之后的继续；continuation来源必须早于当前匹配位置，不能读到未生成内容。
- v1最多返回`5 − 3 = 2`个token；v2才需要`max_k`到5。不承诺任意W32。
- 每session最多200192当前token+独立历史上限，总RAM预算初始256MiB、全局硬上限1GiB。达到上限淘汰旧位置，记录命中率，不用swap维持索引。
- 默认不跨session共享历史，避免私有代码/工具结果串漏。未来跨session需用户范围和隐私策略。
- 只索引已提交真实prompt/output；未接受draft和未来teacher答案永不ingest。

## 4. 调度与成本

v1不需要路由：命中就延长，不命中就是现网。要记录的是`suffix_lookup_us`（CPU，Xeon4216，不能照搬H100主机的12μs）、`suffix_hit_rate`、`extra_proposed / extra_accepted`、以及延长导致的verify行数变化。CPU lookup必须与GPU MTP draft并行（MTP draft kernel在跑时CPU查索引），否则2个额外候选的收益会被串行lookup吃掉。

v2才有路由：`rate = E[committed] / (lookup + proposal + verify + repair/catchup + commit)`，给新来源保守惩罚（预测rate>fallback×1.05），warmup不足走MTP；路由不看未来target输出。v2的bridge测试：每隔1/2/5轮suffix↔MTP切换，比较固定profile未来target输出/状态，日志单列`catchup_ms`。若catch-up吞掉收益，v2退化为**独立lookup-only profile**用于copy/rewrite，不伪装成普遍更快。

## 5. GPU接线

v1：不覆盖`frame.current_drafts`语义，只允许其长度在3..5之间变化；ProposalBatch带`origin`（`mtp`/`suffix_ext`）与每行q类型（NativeMtp / PointMass）进入共享verify路径；target授权与Frontend提交顺序不改。CUDA Graph按W∈{4,5,6}建立有限集合，禁止每轮capture。sampling adapter对one-hot q走fastpath，不物化全vocab q。

v2：新增family-owned ProposalBatch整条替换，需§4的bridge。

## 6. 微基准与产品门

CPU测试：空历史、重复、hash碰撞、分页边界、rewind、跨session、最大长度、内存预算、未提交token、"查询含草稿但草稿被拒"。CPU统计p95 lookup+update。GPU：W4/5/6固定随机seed、拒绝位置全覆盖（含在`d1..d3`拒绝使延长作废）、cache restore、cancel。真实：4条copy/rewrite + 4条新代码/思考负对照 + 原Java3题。

局部通过门：copy/rewrite吞吐收益95%下界≥10%、任务wall≥10%改善，负对照≤3%退化（未命中路径应与现网逐字节相同，退化只能来自lookup开销），lookup不漏记。配对≥8、A/A噪声底≤3%（docs/02 §3）。混合负载没收益就保持默认off，只交付明确场景profile；v1命中率不足则不做v2。
