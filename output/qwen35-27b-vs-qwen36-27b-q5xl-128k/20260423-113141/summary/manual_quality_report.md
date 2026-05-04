# Qwen3.5-27B vs Qwen3.6-27B 128K 人工质量评分
## 直接结论
本轮以 128K、coding 和 agentic 任务处理结果为主，人工复核后结论是：**Qwen3.5-27B-UD-Q4_K_XL 略优于 Qwen3.6-27B-UD-Q5_K_XL**。
Qwen3.6 的回答通常更长、更结构化，在事务边界、恢复顺序、部分脚本任务上更强；但它也出现了几处更危险的问题，包括错误的分页边界判断、retry side effect 状态污染建议、agentic TS 协议类型弱化，以及局部破碎占位代码。
## 总分
| 维度 | Qwen3.5 | Qwen3.6 | 满分 | 结论 |
|---|---:|---:|---:|---|
| 128K Coding | 187.5 | 183.0 | 220 | Qwen3.5 小幅领先 |
| 128K Agentic | 67.0 | 65.8 | 80 | Qwen3.5 小幅领先 |
| Overall | 254.5 | 248.8 | 300 | Qwen3.5 胜出 |
## 自动指标背景
- Coding：两边都是 `22/22` HTTP 成功。Qwen3.5 平均 `24657.87ms`、`42.27 tok/s`；Qwen3.6 平均 `27675.82ms`、`38.42 tok/s`。
- Agentic：两边 best validation 都是 `7/8`，parse 都是 `8/8`，共同失败项是 `agentic_ts_restore_bootstrap_patch`。Qwen3.5 平均 `11117.34ms`、`42.80 tok/s`；Qwen3.6 平均 `12823.83ms`、`38.86 tok/s`。
- 显存：Qwen3.6 Q5 比 Qwen3.5 Q4 在本轮 128K 下大约多占用 `~2.1GB` VRAM。
## Coding 人工评分
| Task | Qwen3.5 | Qwen3.6 | Winner | 评语 |
|---|---:|---:|---|---|
| `java_audit_success_on_failure` | 9.0 | 8.0 | qwen35 | Qwen3.5 removes success audit from finally and preserves failure semantics more cleanly; Qwen3.6 includes a confusing no-op finally before the cleaner fix. |
| `java_cache_stale_after_write` | 9.0 | 8.5 | qwen35 | Both identify write-side eviction; Qwen3.5 is more direct and lower-risk. |
| `java_csv_import_partial_batch` | 9.0 | 9.0 | tie | Both keep validation ahead of persistence and avoid partial batch commits. |
| `java_enum_db_compat` | 8.5 | 9.0 | qwen36 | Qwen3.6 adds clearer null/normalization handling around legacy DB values. |
| `java_idempotency_payment_callback` | 8.5 | 7.5 | qwen35 | Qwen3.5 handles callback idempotency more safely; Qwen3.6 relies too heavily on paid status and under-specifies provider transaction checks. |
| `java_null_nested_config` | 9.0 | 9.5 | qwen36 | Qwen3.6 produces cleaner local variable handling and more actionable errors. |
| `java_optimistic_lock_missing` | 8.5 | 9.0 | qwen36 | Qwen3.6 models currentVersion/nextVersion propagation more directly. |
| `java_outbox_publish_before_commit` | 7.5 | 9.0 | qwen36 | Qwen3.6 recognizes the transaction-boundary problem and moves toward after-commit/outbox semantics; Qwen3.5 is less decisive. |
| `java_pagination_boundary` | 8.0 | 6.5 | qwen35 | Qwen3.6 makes an inclusive/exclusive boundary claim that would mislead the fix; Qwen3.5 is safer. |
| `java_path_body_id_mismatch` | 9.0 | 8.5 | qwen35 | Qwen3.5 explicitly rejects mismatched/null IDs and uses the path ID as authority. |
| `java_permission_scope_trust_bug` | 9.0 | 9.5 | qwen36 | Both correct the trust boundary; Qwen3.6 gives a more polished scope guard. |
| `java_retry_duplicate_side_effect` | 8.5 | 6.0 | qwen35 | Qwen3.6 suggests marking sent before retrying email, which can create false sent state; Qwen3.5 preserves side-effect safety better. |
| `java_soft_delete_unique_email` | 7.5 | 8.0 | qwen36 | Both identify the active-only uniqueness requirement; Qwen3.6 is slightly clearer, though both remain somewhat schematic. |
| `java_transaction_partial_commit` | 9.0 | 9.0 | tie | Both use transaction boundaries appropriately. |
| `script_bash_atomic_deploy` | 9.0 | 9.0 | tie | Both cover health check and rollback semantics well. |
| `script_bash_log_triage` | 8.0 | 7.0 | qwen35 | Qwen3.6 includes a broken placeholder pipeline before the real implementation; Qwen3.5 is simpler and less risky. |
| `script_python_csv_reconcile` | 8.0 | 8.5 | qwen36 | Qwen3.6 has more coherent duplicate and primary/fallback key handling. |
| `script_python_jsonl_replay_analyzer` | 9.0 | 9.0 | tie | Both stream JSONL, tolerate malformed lines, and aggregate session-level signals. |
| `ts_boot_restore_consistency` | 7.5 | 9.0 | qwen36 | Qwen3.6 better preserves restore ordering by ensuring thread/session readiness before entering running phase. |
| `ts_build_atomic_write_guard` | 8.5 | 7.5 | qwen35 | Qwen3.5 keeps the existing tmp+rename contract and moves in-memory mutation after durable writes; Qwen3.6 is heavier and less compatible. |
| `ts_reconnect_circuit_breaker` | 8.5 | 7.5 | qwen35 | Qwen3.5 focuses on preserving the hard failure guard; Qwen3.6 over-focuses reconnect counter reset. |
| `ts_runtime_metrics_protocol` | 9.0 | 8.5 | qwen35 | Both wire protocol/runtime/client metrics; Qwen3.5 keeps the contract tighter. |
## Agentic 人工评分
| Task | Qwen3.5 | Qwen3.6 | Winner | 评语 |
|---|---:|---:|---|---|
| `agentic_bash_log_triage` | 8.5 | 9.0 | qwen36 | Both pass; Qwen3.6 normalizes key/value fields more robustly. |
| `agentic_bash_log_triage_gz` | 9.0 | 9.2 | qwen36 | Both pass gzip handling; Qwen3.6 has slightly richer status normalization. |
| `agentic_python_metrics_contract` | 9.0 | 8.8 | qwen35 | Both pass; Qwen3.5 output is cleaner and avoids minor formatting roughness. |
| `agentic_python_reconcile_pkg` | 9.0 | 9.2 | qwen36 | Both pass; Qwen3.6 catches a bit more duplicate-right detail. |
| `agentic_python_replay_analyzer_patch` | 9.0 | 8.7 | qwen35 | Qwen3.5 is simpler and closer to the dependency-light patch target; Qwen3.6 is richer but heavier. |
| `agentic_python_restore_bootstrap` | 9.0 | 8.8 | qwen35 | Both pass; Qwen3.5 has cleaner final patch formatting. |
| `agentic_ts_metrics_contract_patch` | 9.0 | 7.8 | qwen35 | Qwen3.6 weakens protocol type precision to Record<string, unknown>; Qwen3.5 preserves the schema contract better. |
| `agentic_ts_restore_bootstrap_patch` | 4.5 | 4.3 | qwen35 | Both repeats fail validation; Qwen3.5 is only marginally cleaner. |
## 采用建议
- 继续把 `Qwen3.5-27B-UD-Q4_K_XL` 作为 4090 上 coding/agentic executor 的默认候选。
- `Qwen3.6-27B-UD-Q5_K_XL` 可以作为“解释更展开、分析更丰富”的备选，但本轮不建议替换默认服务：质量没有净胜，速度更慢，显存更高。
- 如果后续要再次评估 Qwen3.6，建议单独测更高难度事务/架构分析类任务，并把“回答冗长但是否真正更正确”作为人工 rubric 的独立项。
