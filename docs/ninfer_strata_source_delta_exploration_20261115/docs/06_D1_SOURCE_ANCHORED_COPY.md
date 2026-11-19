# D1：来源锚定的复制/编辑草稿

状态：`NEW_MECHANISM_CONDITIONAL`。这是相对旧 H1 的**局部机制差量**，不是新的 lookup 算法家族、不是 W16 方案，也不自动取得硬件资格。

## 1. 原因与来源

旧 H1 用请求内 8192 ring、4-gram、K3 整包替换，mandatory MTP 仍执行；命中但 ms/token 变慢。OSAKANA 的 `common_speculative_impl_copy` 增加了 source anchor、冷启动长匹配、编辑后恢复、复制证据与失败让路；dispatcher 在 copy 有结果后不再让后面的 DFlash 产生无用候选。源码见 [证据地图](02_EVIDENCE_AND_SOURCE_MAP.md)。

NInfer 的 MTP 与 Target / next-proposal 状态关系不同，不能照抄 DF2 skip。Strata 已有 `skip_draft_for_lookup`、suffix 与 DF2 context 维护；“命中后不生成 DF2”在 Strata 不是新发现。

## 2. 明确分开三种假说

| 假说 | 同一 W 下可验证什么 | 不得混入 |
|---|---|---|
| D1-P，planner 差量 | 同来源集合，anchor/repair 能否减少错误定位和重搜成本、改善可接受跨度 | 把 ring 扩全文的收益全部记给 anchor |
| D1-S，避免无效 proposal | 相同 copy 选择/accepted 轨迹，真实省掉神经 proposal 后净成本是否下降 | 不计 catch-up、仅看 CPU 分支或 graph capture |
| D1-W，更宽 verifier | **旧 W8/W16 规划，非本包实施项** | 作为 D1-P/S 的共同处理偷偷打开 |

离线对照：`B0=现 baseline`；`B1=相同 prompt-source 集合，无 anchor/repair`；`B2=B1+anchor/repair`；`B3=B2+可证明的 proposal skip`。B1/B2 首先只回放记录。硬件阶段只比较预先选中的一个 C 对 B0，不扫描四组组合。若 B3 不可保持状态或只能扩大 W 才有意义，本包停止，另提旧宽窗接续合同。

## 3. 使用范围

优先：已有完整 Java 文件/JSONL 的局部修改、重命名、复制编辑后回吐。普通自然生成、短问答和推理不是默认目标。保持当前 W/K、context capacity、模型、tokenizer、KV、功耗及采样合同。

首版只索引本请求已授权 prompt 与 committed output，不索引私人其他请求、磁盘代码库或未提交草稿。prompt-source 与 output-source 必须分开，后者不因短重复取得更宽许可；本包两者都不超过原 W。

## 4. 拟新增接口（未实现）

目标目录：NInfer `src/targets/qwen3_8/impl/runtime/source_copy_plan.h`；若现场已有等价 H7 实现，改为 adapter 并记录实际路径。

| 接口 | 输入/输出 | 约束 |
|---|---|---|
| `reset(identity, prompt_token_ids)` | 初始化一次有界 token 索引 | 固定 tokenizer/model/request generation，记建立时间和内存 |
| `propose(committed_suffix, anchor, max_drafts)` | `CopyProposal` 或无提议 | 返回 source_kind/start/end、exact-match长度、token IDs、reason；不得变 Target 状态 |
| `observe(accepted_prefix, verifier_result)` | 更新 anchor/proven source/失败状态 | 只用已提交事实；acceptance 与 commit 截断不可混用 |
| `invalidate(reason)` | 清除来源身份 | reset/取消/换前缀/恢复不匹配必失效 |

`CopyProposal` 至少包含 `identity_hash/source_generation/source_kind/source_token_begin/proposal_token_ids/match_tokens/planner_reason`。hash 只加速桶查找，实际 token IDs 相等才算匹配；hash 碰撞不可产生错误的“证明”。

OSAKANA 的 3-gram、16-token cold-match、[-8,+64] 搜索、编辑恢复范围、EMA 和退避是来源事实，不是本机最优值。首版固定一套来源有据的参数并锁 hash，不扫描 n-gram/阈值。max_drafts 始终由原 W−1、剩余上下文和真实预算三者限制。

首版拟定边界：仅索引当前合同允许的完整请求token范围，index peak上限64MiB/请求；达到cap则给`INDEX_CAP`并关闭本请求copy，回baseline，不能静默截短后仍宣称相同来源集合。此64MiB是待R0审核的安全cap，不是实际内存测量。索引建立是O(prompt tokens)的一次请求成本，append只索引新committed后缀；分别计TTFT和整任务摊销，不能全部当“预热免费”。

B1/B2共享同一index、cold-match门、候选数cap和确定性tie规则。B1无anchor，按最长exact match、再按源位置固定顺序选；B2只增anchor优先与edit恢复。共同输入的可检索来源token宇宙/索引范围必须相同；anchor/edit可以改变实际返回的候选位置。若实现扩大来源宇宙，报告为单独source机制，不能混算anchor收益。no-match/backoff时仍计查询成本。

## 5. 草稿状态事务与 skip 门

必须画出当前 `mtp_bridge_and_propose`、`mtp_decode_batch_body`、`proposal_argmax`、`target_verify_accept`、`resolve_pending_batch` 的依赖。回答：

1. 哪段仅为“本轮没采用的候选”而做，可以不执行？哪段是下轮 hidden/KV/position 必需维护？
2. copy 连续命中后转 MTP，缺失的 history/taps 能否有界追平？追平是每次 commit 做还是第一次 fallback 做？
3. cancel/EOS/预算结束时是否需要最后一次 context 更新？restore/next turn 会否产生空洞或重复位置？
4. skip 后 Graph 地址/形状是否仍合格？省掉的是实际 kernel/bytes 还是仅没消费输出？

不支持时选择原 MTP 路径；不能用 stale MTP hidden 续跑。`catchup_rows`、`catchup_ns` 与 `neural_draft_executed` 必须有执行证据。纯 planner 可先保留 mandatory MTP，但不能宣传“避免神经草稿”的收益。

## 6. 离线最小验证

使用现有且获准处理的真实轨迹，三类各至少 20 个不同任务：copy-edit、普通非 copy Java、相似片段/多 token 编辑干扰。按任务划分开发/holdout，先冻结清单，不从运行结果挑选。没有这批轨迹就 `BLOCKED_TRACE`，不生成看似真实的合成收益。

回放的是**已发生的 Target token 轨迹**：只能估计该轨迹上的 proposal 匹配和 planner 成本，不能证明改变 proposal 后的未来分布、MTP 状态、GPU 时间或自然任务 wall。

输出：来源位于旧 ring 外的增量比例、B1/B2差异、错误源率、连续复制跨度分布、edit 后重命中距离、lookup/build CPU p50/p95、索引 peak bytes、match 后预计省掉/新增工作的有界估计。含输入散列、split、source hash 与所有失败项。

## 7. 必须测试的反例

- 相同 3-gram/哈希碰撞但后缀不同；重复相似函数；同名字段不同值。
- 单 token 替换、插入、删除、多 token 编辑；锚点前/后漂移；源结束转自然生成。
- prompt/output 边界，token ID 与字节相似不一致，tokenizer 或 template 变化。
- commit 小于 verify accepted；拒绝首/中/末；EOS 在窗口内；remaining < W；cancel；恢复后 generation 变化。
- 多次成功后失败让路；无 copy 时不新增无界 CPU 开销；所有索引有 cap 和越界拒绝。

这些是 planner CPU 合同测试，不证明 model quality。state、sampler、observer-off 正式门见 [测试协议](10_TEST_PROTOCOL_AND_GATES.md)。

## 8. 立即停止条件

真实 workload 几乎无 prompt-source 增量；B2 相对 B1 没有可见差量；skip 不能保持原状态/Graph；catch-up 吞掉节省；收益只来自扩大 W/换量化；当前可证净耗时下降不足正式门＋余量；非 copy 组退化。关闭 `D1_THIS_CONTRACT`，不删除旧 H1，不补参数组或新增请求直到显著为止。
