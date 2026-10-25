# 技术吸收账本与 NInfer 冲突图

所有 proposed 路径都是未来实施文件，不是声称源码已有。现有路径以 U 树为依据，实际执行以 P6 合格集成树重定位。

| 能力 | donor 位置 | NInfer 现状/落点 | 保留与替换 | 阶段 |
|---|---|---|---|---|
| request-local suffix Lookup | HQ02 `_suffix_lookup_kernel` | 新 `runtime/generation/prompt_lookup.*`；使用已有 tokenized prompt | 不重新 tokenizer、不读取别的 session；CPU index 先做基线 | H1 |
| head/tail 条件融合 | HQ02 `_fuse_draft_kernel` | 新 `hybrid_proposal.*` | 取代 V2 只选单一 backend；不是无条件尾拼 | H1/H4 |
| neural/verify 解耦 | HQ02 draft_block/num_speculative_steps | 新 `ChainVerifyState`，共同 `target_verify_accept` | MTP maximum5 不等于 verify maximum15 | H3/H4 |
| 延迟信号与 Sticky | HQ02 `next_num_draft_tokens` | 新 per-lane `hybrid_policy.*` | 不搬全batch共享 sticky；用 epoch/round/event | H4 |
| drafter-free copy run | HQ03 `_chain_should_engage` | gated hybrid schedule | 保留 MTP alignment；拒绝后恢复 neural 需要 ready | H4 |
| 词表重新校准 | HQ06 | 独立 `.ninfer` proposal-head companion，启动期 closed profile | Target 全词表不变；不改变主模型权重文件 | H2 |
| Split-KV 扩宽 | HQ01/HQ04 | `ops/launcher/gqa_attention_decode.cu`、实际 i8/BF16 kernels | 既有 W≤6 不变；W8/W16 各自新增资格 | H3/H4 |
| scratch token 行数 | HQ05 | `layouts_impl.h`、`workspace_recipe.h`、ReplaySSM layout | 容量从物理 row×width 推导，不能按 request_count 分配 | H0/H3/H4 |
| 动态卷积、selector、ring | V2 T03—T07 | 新 typed 27B DFlash2 companion 和 target family 实例化 seam | 不复用 35B DFlashConfig 数值；不运行时 GGUF 重打包 | H6 |
| selective drafting | V2 T06/T08 | 独立 ProjectedG archive/全局页索引/staging | 不把 Target L2 当 Draft KV；不限制仅最近65K | H7 |
| 相同算术资格 | tqLLM T02/T09；HQ02/HQ05 反例 | 普通/verify/replay、eager/graph、不同宽度 differential | 单元数值通过不是 greedy exact 的替代品 | 全程 |
| W4A8、量化 embedding/head | HQ01 | 现有 groupwise-int/INT8 prefill/131K drafthead | 首轮只审计，不重复宣称节约2.6GB | 不单独立项 |
| GDN fp16、KVarN、vLLM block864 | HQ01/HQ04 | FP32 recurrence、合格 rk4v4、NInfer page policy | 不纳入默认路线 | 延后/拒绝 |

## 源码级冲突不是文本 merge 冲突

HyperQwen 是 vLLM 补丁系列，tqLLM 是另一个 C++ 引擎；二者均不是 NInfer 的 Git parent。这里的“冲突”包括：运行时所有权、采样语义、资源布局、状态frontier、前端词表、缓存 identity 和测量口径。只有原 U 合入 O 才做真实 Git merge。

`mtp_impl.h` 的原流程是 verify→accept→alignment→proposal next round，且这些在同一个图体中。新 Lookup-only 提案或 W16 必须在 gate 控制的 hybrid 入口拆开 proposal 选择与 verify shape；不要在旧分支外另建独立 KV、GDN、输出发布者。旧 `--spec` 未启用 hybrid 时保持原 graph 和执行顺序。[NI03/NI04]

V2 提议将 `PromptLookup` 加入 `SpeculativeBackend`；V3 改为 **backend 表示 resident 神经运行时，source 表示每个候选来自哪里**。Lookup 没有模型权重，不应迫使 MTP 状态退出。旧 enum 原值不变；DFlash2 的新值只在 H6 落地，不能把旧 DFlash 重新解释为 DFlash2。
