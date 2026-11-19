# 两张非性能候选卡：源码缺口与上游维护

## K-PAIR：共输入小 T 异 dtype 投影

状态：`SOURCE_BOUND_PAIR_P3_DELTA_UNBOUND`。只做 R0 源码差量检查；**不分配 kernel/GPU 实验预算**。

TensorFold `projectMany → gemvSeg → tf_lane_gemv_seg` 在一个 grid 组织多个 projection，各 member 保持自己的split-K、partial、ticket和固定归约。可借的是组织方式，不是MLX-affine4权重kernel。

固定 NInfer b0 中已核实：

| 路径 | 实际现状 | 边界 |
|---|---|---|
| `attn_input_proj/q4_q5/*_small_t.cu` | 同 x 的 Q4 query/key 与 Q5 gate/value 两次 dispatch | 不是未做QKV融合；不同dtype/几何不能简单concat |
| `gdn_input_proj/q4_q5/*_independent.cu` | small-T Q4/Q5 pair；T4函数名含PDL | sm89构建定义NINFER_SM86，实际普通同stream launch |
| GDN大T | 已有Mixed grouped MMA | 不列重复“首次分组” |
| gate/up、控制a/b | 已融合/paired | 不再泛化合并 |
| MTP某query/gate pair | 位于prefill末chunk，不是每轮decode | 不将冷路径放大为decode热点 |

**源码任务：**取得 P3 最终隔离树和当前二进制对应源码；逐一绑定实际shape、codec、路由条件、宏与launch。输出`pair_gap.json`，状态只可为`ALREADY_COVERED`、`NOT_HOT_PATH`、`SOURCE_UNBOUND`或`UNRESOLVED_MECHANISM_GAP`。后者也不自动获得候选资格。

只有在新授权下，确认当前仍有pair且关键路径瓶颈为launch/资源组织、可保原member算术，才另立提案。两个host wrapper合一不等于减少GPU launch；共享input也不证明权重只读一次。禁止顺势扫旧Q4layout/prefetch/tile。没有真实P3源码就到此停止。

固定路径和PDLguard链接见 [源码地图](02_EVIDENCE_AND_SOURCE_MAP.md) 与 [历史台账](01_HISTORY_AND_NO_REPEAT.md)。

## M0：Strata 末轮输入提交边界

状态：`UPSTREAM_IMPLEMENTED_DEPLOYMENT_UNBOUND`。上游HEAD `13eedf552417a6a791a7d13c6597e24300ee3a09` 已将stop-bound用于CUDA；不是需要重写的算法。release/control版本号不能证明运行二进制已有此改动。

### 正确理解边界

`serve_stop_bound(accepted, remaining, outputs, is_eos)` 限制的是**committed input rows**：每一行对应可曝光输出，最后一个已曝光output仍是下次未消费token。实际serve loop先`a=bound(a+1,...)-1`再`commit(a+1)`；不要误写成“只裁输出文本”或少commit一列。

merged首窗含prompt rows，不能按输出预算裁掉它们。末轮不再draft时，DF2还需把最终committed rows/context更新到ring。已有CPU helper测试覆盖accepted1..16、remaining1..18、EOS位置与零预算；本包不复制一套穷举测试冒充新增能力。

### 真正待绑定的回归序列

| 序列 | 必须观测 | 对照 |
|---|---|---|
| remaining小于accepted窗，随后同session追加 | committed input frontier、next unconsumed token、cache命中原因 | 标量终止语义参考 |
| 首EOS在窗内，随后允许的新请求/会话续用 | 不提交client不可见尾token；MTP/DF2 history不留洞 | 原协议允许的EOS处理 |
| 两条件同时成立 | 两边界取正确最早者，不多/少一行 | 同输入/同token trajectory |
| 保存→恢复→追加 | KV/GDN/conv/hidden/drafter/token-prefix身份一致 | 原engine支持的save/restore合同 |
| merged prompt首窗 / context边界 / cancel | 不误裁prompt，不破坏旧终止/撤销事务 | 已有回归复用 |

跨engine恢复仅在原产品已经支持且许可的版本兼容合同内测试，不由本包新增。HTTP成功/输出相同不够：须绑定fallback/re-prefill reason，不能把cache miss隐藏在速度均值里。

### 停止/结果

未绑定部署→只交回归卡。已含修复且精确原件已通过→`ALREADY_VERIFIED`，不重跑。尚不含修复→给出维护升级/最小backport方案，先获授权；不能为了M0顺便升级全部模型/量化。修复后只可声称正确性/恢复稳定性，除非另外获得同合同净益证据。

NInfer `resolve_pending_batch` 已有partial terminal hidden纠正、按committed列Fold、KVtrim，因此不向NInfer移植一个“首次终止窗口修复”。
