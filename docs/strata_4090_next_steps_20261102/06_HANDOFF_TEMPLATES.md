# 交接模板与冻结基线速查

日期：2026-11-02。以下JSON都是**未执行的表单示例**，不是新实验日志；`null`表示未知或未观测，0只用于明确的“没有授权预算”。复制模板不代表批准。

## 1. 历史冻结基线速查

这些值来自固定提交中的报告，尚未现场重验。[S01、S04、S20]

| 项目 | 报告值 | 填表规则 |
|---|---|---|
| 生产A0 | v0.2.3 / `5c8dd322528cc84f68f461ad54a506b9da8fa8d4` +部署补丁 | 保护对象，不充当研究A臂 |
| 研究B | v0.2.7 /engine0.1.52 / `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d` +六文件Python port | 必须保留补丁身份 |
| B binary SHA256 | `58ffaf7f67535049baf996dd8793202b2ba4d2d7090569cfcc13019a28269f22` | 不以P24 binary或donor替代 |
| 模型来源revision | `ed59f92082b1e93c0e96d60a8b11aab089b52f09` | GSQ-RCO IQ3_XXS混合包 |
| IQ3_XXS分片1 SHA256 | `219ea929900dfa9ef091f3aa473fdba6874b65fcb36526d7d851ac9e95856d15` | 报告大小47,039,860,096 bytes |
| IQ3_XXS分片2 SHA256 | `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113` | 报告大小28,800,138,432 bytes |
| target KV | int8 /resident20480 /max-context131072 | 另保留4096 token余量 |
| MTP | spec4 /spec-min-p0.5 /默认冻结词表 | 请求sampling min_p是另一个字段 |
| session cache | 6144 MiB总预算 /4 slots | 不是每slot6144 MiB |
| 请求/控制 | reply reuse1、PT0、典型Pi xhigh、temp1/top_p0.95/top_k20 | 以实际body/渲染为准 |
| 编译 | CUDA12.3、SM89、Release；MMQ_KQUANTS OFF、Q6K_EXPERTS OFF | 新编译器属于新变量 |
| CPU/Prefill | Xeon4216，15 pool workers；CPUSHARE_MAX4096、AUTO_MAX16384、overlap | 不因为社区配置而重扫 |
| experts | auto；P6/P01B历史实际10272，P3为10290 | 不是要手工凑到的目标值 |
| 安全 | 85°C停止，MemAvailable<4096 MiB停止 | 不下调保护换取完成 |

报告中的EXACT6和显式关闭值：

```json
{
  "STRATA_DEFAULTS": "026",
  "STRATA_SIDE_MIXER": "2",
  "STRATA_ATTN_DAILY": "1",
  "STRATA_GR_UP75": "1",
  "STRATA_GU_SWIGLU": "1",
  "STRATA_QSA_ROWS": "1",
  "STRATA_B6_MMVQ_ROWS": "1",
  "STRATA_MMVQ_IL_89": "0",
  "STRATA_PROMPT_ATTN_IMMA": "0",
  "STRATA_KVA": "0",
  "STRATA_ROUTE_PRIOR": "0",
  "STRATA_DEQUANT_SIDE": "0",
  "STRATA_PLE_AUTO_RAM": "0"
}
```

这不是完整启动命令。presence-sensitive profiler变量必须删除键，不能照上面普通开关的方式设0；完整env仍需从实际身份原件取得。

## 2. IDENTITY.json 表单

```json
{
  "record_kind": "template_not_observed",
  "campaign_id": "N20261102",
  "candidate_id": null,
  "observed_at": null,
  "historical_source_commit": "b4fb53ff88df2cea58149483533cef7159fb9120",
  "role": null,
  "identity_status": "NOT_OBSERVED",
  "engine": {
    "repository": null,
    "commit": null,
    "patch_sha256": null,
    "binary_sha256": null,
    "build_flags": null,
    "cuda_compiler": null,
    "driver": null,
    "loaded_libraries": null
  },
  "assets": {
    "model_revision": null,
    "gguf_shard_sha256": [],
    "pack_manifest_sha256": null,
    "tensor_formats": null,
    "mtp_manifest_sha256": null,
    "tokenizer_sha256": null,
    "template_sha256": null,
    "draft_vocab_sha256": null
  },
  "runtime": {
    "argv": null,
    "env_present": null,
    "env_required_absent": null,
    "kv_format": null,
    "kv_resident_cells": null,
    "max_context": null,
    "session_cache_total_mib": null,
    "session_cache_slots": null,
    "actual_expert_slots": null,
    "profile_sha256": null,
    "target_tail_skip": null,
    "request_sampling": null
  },
  "hardware": {
    "gpu": null,
    "gpu_uuid": null,
    "cpu": null,
    "memory_channels": null,
    "ram_bytes": null,
    "pcie_link": null,
    "foreign_gpu_load": null
  },
  "production_current_state": "NOT_OBSERVED"
}
```

`role`最终只填A0/B/A1/C之一；不能把统计臂名A映射到历史生产。现场UUID等敏感标识保留在私有原件，对外总结只提供必要匿名信息。

## 3. ARTIFACT_INDEX.json 表单

```json
{
  "record_kind": "template",
  "artifact_status": "MISSING",
  "warm_probe_status": "BLOCKED_EVIDENCE",
  "items": [
    {
      "logical_name": "P01B_REQUESTS",
      "reported_relative_path": "docs/strata_4090_128k_lab/workspace/frontier/p01b-20261031/run/REQUESTS.jsonl",
      "actual_accessible_path": null,
      "sha256": null,
      "evidence_level": "REPORT_ONLY",
      "verified_original": false
    }
  ],
  "missing_required_items": [
    "P01B_REQUESTS_ANALYSIS_TOKEN_MANIFESTS",
    "P00_IDENTITY_ASSET_MANIFESTS",
    "P24_PREREGISTRATION_ANALYSIS",
    "F03_LIFECYCLE_LEDGER",
    "QUALIFIED_WARM_FIXED2048_ORIGINALS"
  ],
  "rerun_to_fill_gaps_authorized": false
}
```

原件路径仅表示用户/报告所指位置，本轮没有该目录；不把它变成虚假的GitHub blob链接。只需用户定向提供已有原件或脱敏导出，不索要凭据，不扫描无关文件。

## 4. 单候选卡

```text
候选ID：
路线：F / T / Q / P（只选一个）
基线B与候选C的身份：
唯一允许差量：
旧研究/旧负结果：
相对于旧实现的新机制：
真实任务覆盖证据：
暴露成本与计时区间：
可信可消除量及依据：
新增计算/搬运/内存/启动/维护成本：
完整请求预计净省的推导（未知就写未知）：
为什么可能达到准入门，而非只快一个kernel：
数值/target/采样/状态语义级别：
原六FAIL与新增质量风险：
资源可容纳性：
最小验证及负控制：
明确停止条件：
缺证清单：
独立审查结论：BLOCKED / NO_QUALIFIED_MECHANISM / ELIGIBLE_FOR_AUTHORIZATION
```

`ELIGIBLE_FOR_AUTHORIZATION`仅指可以请求授权，不是已经获准运行。不得把0.5GiB理论节省填成“预计10%速度提升”。

## 5. AUTHORIZATION.json 表单

```json
{
  "record_kind": "template_not_authorized",
  "campaign_id": "N20261102",
  "candidate_id": null,
  "approved": false,
  "approval_reference": null,
  "approved_at": null,
  "host_access_authorized": false,
  "numeric_tradeoff_authorized": false,
  "allowed_source_changes": [],
  "allowed_env_changes": [],
  "allowed_asset_changes": [],
  "allowed_bind_address": null,
  "allowed_port": null,
  "gpu_seconds_max": 0,
  "engine_starts_max": 0,
  "requests_max": 0,
  "quality_task_pairs_max": 0,
  "download_bytes_max": 0,
  "production_changes_max": 0,
  "temperature_stop_c": 85,
  "mem_available_stop_mib": 4096,
  "stop_on_foreign_gpu_load": true,
  "stop_on_identity_mismatch": true,
  "stop_on_oom": true,
  "failure_replacement_allowed": false,
  "retry_until_significant_allowed": false,
  "cleanup_scope": [],
  "rollback_reference": null
}
```

如需批准，必须引用真实用户授权且填写有限预算；不能把 `approved` 自行改成true。GPU预算和质量预算分别列出，不能用“研究”二字绕过。

## 6. PREREGISTRATION.json 表单

```json
{
  "record_kind": "template",
  "candidate_id": null,
  "admission_status": "BLOCKED_EVIDENCE",
  "route": null,
  "workload_contract": null,
  "baseline_identity_sha256": null,
  "candidate_identity_sha256": null,
  "allowed_delta": null,
  "warm_probe_status": "BLOCKED_EVIDENCE",
  "actual_request_identity_policy": "BODY_AND_RENDERED_TOKENS",
  "primary_metric": null,
  "non_target_metrics": [],
  "aa_evidence_sha256": null,
  "aa_noise_definition": "median(abs(paired_time_ratio - 1))",
  "aa_noise_observed": null,
  "minimum_improvement_m": null,
  "primary_ci_upper_limit": null,
  "non_target_ci_upper_limit": 1.02,
  "fixed_probe_pair_order_if_applicable": ["AC", "CA", "CA", "AC", "AC", "CA"],
  "fixed_probe_bootstrap_resamples_if_applicable": 46656,
  "confidence_level": 0.95,
  "support_scenarios_authorized": false,
  "selection_set_sha256": null,
  "holdout_set_sha256": null,
  "task_budget_seconds": null,
  "relative_quality_margin": 0.02,
  "absolute_quality_gate": "ORIGINAL_SIX_FAILS_REMAIN_UNRESOLVED",
  "numeric_tolerance_contract": null,
  "critical_failure_policy": null,
  "initial_temperature_policy": null,
  "cooldown_policy": null,
  "posthoc_metric_switch_allowed": false,
  "registered_before_candidate_results": false
}
```

W-T不适用固定输出/六对工具时，明确将不适用字段置null并使用已批准任务统计合同；不得保留46656就假装变长任务分析已实现。`m`与CI门由合格A/A在候选结果前确定，禁止事后选择。

## 7. 请求与事件最小字段

这是一条**结构示例**，不是可以作为现场证据的 `REQUESTS.jsonl` 数据。实际格式优先兼容原工具；若需映射，保留原文件和无损映射说明。

```json
{
  "record_kind": "schema_example_not_a_measurement",
  "run_id": null,
  "pair_id": null,
  "arm": null,
  "phase": null,
  "engine_identity_sha256": null,
  "actual_request_sha256": null,
  "rendered_tokens_sha256": null,
  "prime_history_sha256": null,
  "started_at": null,
  "completed_at": null,
  "input_tokens": null,
  "read_tokens": null,
  "reused_tokens": null,
  "committed_tokens": null,
  "thinking_tokens": null,
  "text_tokens": null,
  "proposed_tokens": null,
  "accepted_draft_tokens": null,
  "draft_ms": null,
  "verify_ms": null,
  "native_decode_ms": null,
  "ttft_thinking_ms": null,
  "ttft_visible_ms": null,
  "request_wall_ms": null,
  "restore_ms": null,
  "park_ms": null,
  "peak_vram_mib": null,
  "min_mem_available_mib": null,
  "max_gpu_temperature_c": null,
  "major_faults_delta": null,
  "swap_in_bytes_delta": null,
  "swap_out_bytes_delta": null,
  "stop_reason": null,
  "task_success": null,
  "task_budget_seconds": null,
  "restricted_time_seconds": null,
  "failure_class": null
}
```

`EVENTS.jsonl`须能追踪身份检查、prime完成、append前hash检查、decode起终点、park/restore、预算累计和停止事件。开销区间有重叠时不能相加当完整wall；每项注明计时源、同步方式和是否仅诊断。

## 8. RESULT.json 表单

```json
{
  "record_kind": "template_not_run",
  "campaign_id": "N20261102",
  "candidate_id": null,
  "mechanism_status": "NOT_RUN",
  "bridge_status": "NOT_RUN",
  "numeric_status": "NOT_RUN",
  "resource_status": "NOT_RUN",
  "lifecycle_status": "NOT_RUN",
  "performance_status": "NOT_RUN",
  "relative_quality_status": "NOT_RUN",
  "absolute_quality_status": "BLOCKED_QUALITY",
  "thermal_status": "NOT_RUN",
  "primary_time_ratio": null,
  "primary_ratio_ci95": null,
  "independent_quality_task_pairs": null,
  "quality_discordant_b": null,
  "quality_discordant_c": null,
  "original_six_fail_status": "UNRESOLVED",
  "consumed_engine_starts": 0,
  "consumed_requests": 0,
  "consumed_gpu_seconds": 0,
  "production_state_changed": false,
  "production_current_state": "NOT_OBSERVED",
  "overall_decision": "DOCUMENTATION_ONLY",
  "stop_reason": null,
  "evidence_manifest_sha256": null,
  "reviewer_receipt": null
}
```

候选运行后，即使 `performance_status=PASS_RESEARCH_GATE`，仍必须保留其他分项真实状态。只有原六FAIL未解决时的收口结论，应使用 `RESEARCH_RESULT_ONLY / BLOCKED_QUALITY`，不写READY。

## 9. 可直接交给下一位执行者的指令

> 阅读本包README、01、02、03、04和06及05所需来源。仅执行N0离线身份/原件整理，使用我已经提供且可访问的材料，不连接目标机、不停服务、不发模型请求、不改配置、不下载权重。原件缺失时给缺件表，不重新测速。保留冻结合同收口结论；任何Q/T/P候选都先提交单候选卡和有限预算供我另行批准。不得以我批准生成文档作为硬件执行许可。

若用户之后授权某个硬件阶段，应另给出明确候选ID、允许差量、任务合同、目标机/端口、样本与总耗时上限、质量取舍及退出方式。没有这些字段，就只交付阻塞原因。
