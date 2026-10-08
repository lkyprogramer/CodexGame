# 长Agent缓存验证

核心问题不是“同一个prompt重复发有多快”，而是“上一轮实际生成+tool结果回灌后，还能否复用完整旧历史”。Kern已有checkpoint/retire/lease_from/park/wake基元，但GDN只有在正确state frontier才可截断/恢复。[S01]

## P0必过

- 一份20K Java/日志内容读入一次，连续10个短追问，不再次read全文。
- 历史从约48K增长到64K，加入多个真实tool_call/tool_result，记录每轮实际LCP、被restore长度和新算token。
- 对有效append历史，旧内容大部分复用；computed_prefill应接近真实新增尾巴+有解释的模板replay，不应反复吞掉20K大文件。
- exact resend可因checkpoint长于prompt而miss；这不是状态错误。输出必须正确，日志必须解释路径。
- 不共享不同模型hash/模板/state layout的cache；session id仅查找提示，不是真实前缀证明。

## 近期rewrite（P1性能，P0正确性）

改变最近user reminder或tool_result：不能误命中旧state。没有合适checkpoint时允许冷算，不允许错误复用。后续可加最近两个真实消息边界anchor。

**边界checkpoint不能追溯创造。** 若当前GDN state已在64K，无法仅复制它并标成50K。必须在prefill经过50K时保存，或从更早合法checkpoint重放到50K再保存；最后再回到正确执行点。前缀哈希/模板版本/weight digest/position/state layout都绑定该位置。

KV整页可共享、末页COW；GDN新slot复制也计入GPU预算。host64GB不代表GPU checkpoint无费用。P0默认host tier关闭，让一个主session尽量留在卡上；host park/wake做独立生命周期测试，不套用GB300的C2C速度到4090 PCIe。

## 每轮日志

`request_id, session_id_hash, prompt_tokens, exact_lcp_tokens, reused_tokens, computed_prefill_tokens, replayed_tokens, checkpoint_frontier, state_frontier, cache_source, restore_ms, snapshot_ms, prefill_ms, decode_ms, target_tokens`。

原始tools/system/rendered-token SHA用于定位变化；不要在公共日志写入私密代码/令牌。真实read同一文件第二次产生一份新tool_result时仍是新tokens，不期待引擎按路径自动复用非前缀KV。
