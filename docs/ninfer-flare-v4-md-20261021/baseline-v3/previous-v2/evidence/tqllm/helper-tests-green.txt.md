# V2 支撑材料：`evidence/tqllm/helper-tests-green.txt`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: evidence/tqllm/helper-tests-green.txt -->
<!-- payload-sha256: 14398237c5f5ec6b33a170e96009526b22a49afa5ccc457ad91353ba57b16688 -->
<!-- payload-bytes: 6816 -->

<!-- payload-begin -->
````text
test_git_probe_isolated_and_conflict_is_reported (test_merge_tools.UtilityTests.test_git_probe_isolated_and_conflict_is_reported) ... ok
test_junit_duplicate_rejected (test_merge_tools.UtilityTests.test_junit_duplicate_rejected) ... ok
test_junit_failure_is_not_pass (test_merge_tools.UtilityTests.test_junit_failure_is_not_pass) ... ok
test_junit_missing_required_is_not_pass (test_merge_tools.UtilityTests.test_junit_missing_required_is_not_pass) ... ok
test_junit_no_tests_is_not_pass (test_merge_tools.UtilityTests.test_junit_no_tests_is_not_pass) ... ok
test_junit_optional_skip_allowed (test_merge_tools.UtilityTests.test_junit_optional_skip_allowed) ... ok
test_junit_pass (test_merge_tools.UtilityTests.test_junit_pass) ... ok
test_junit_required_skip_is_not_pass (test_merge_tools.UtilityTests.test_junit_required_skip_is_not_pass) ... ok
test_metrics_detects_latency_regression (test_merge_tools.UtilityTests.test_metrics_detects_latency_regression) ... ok
test_metrics_duplicate_is_rejected (test_merge_tools.UtilityTests.test_metrics_duplicate_is_rejected) ... ok
test_metrics_good_samples_pass (test_merge_tools.UtilityTests.test_metrics_good_samples_pass) ... ok
test_metrics_mismatched_cases_rejected (test_merge_tools.UtilityTests.test_metrics_mismatched_cases_rejected) ... ok
test_metrics_nan_rejected (test_merge_tools.UtilityTests.test_metrics_nan_rejected) ... ok
test_metrics_underpowered_is_blocked (test_merge_tools.UtilityTests.test_metrics_underpowered_is_blocked) ... ok
test_metrics_zero_prepare_uses_absolute_budget (test_merge_tools.UtilityTests.test_metrics_zero_prepare_uses_absolute_budget) ... ok
test_phase_evidence_pending_rejected (test_merge_tools.UtilityTests.test_phase_evidence_pending_rejected) ... ok
test_phase_evidence_requires_real_files (test_merge_tools.UtilityTests.test_phase_evidence_requires_real_files) ... ok
test_plan_accepts_dag (test_merge_tools.UtilityTests.test_plan_accepts_dag) ... ok
test_plan_rejects_cycle (test_merge_tools.UtilityTests.test_plan_rejects_cycle) ... ok
test_plan_rejects_duplicate_id (test_merge_tools.UtilityTests.test_plan_rejects_duplicate_id) ... ok
test_plan_rejects_missing_dependency (test_merge_tools.UtilityTests.test_plan_rejects_missing_dependency) ... ok
test_redaction_preserves_token_count_configuration (test_merge_tools.UtilityTests.test_redaction_preserves_token_count_configuration) ... ok
test_redacts_both_argument_styles (test_merge_tools.UtilityTests.test_redacts_both_argument_styles) ... ok
test_check_other_commit_rejected (test_strict_gate.StrictGateTests.test_check_other_commit_rejected) ... ok
test_complete_synthetic_evidence_passes (test_strict_gate.StrictGateTests.test_complete_synthetic_evidence_passes) ... ok
test_duplicate_check_rejected (test_strict_gate.StrictGateTests.test_duplicate_check_rejected) ... ok
test_invalid_model_hash_rejected (test_strict_gate.StrictGateTests.test_invalid_model_hash_rejected) ... ok
test_required_check_cannot_be_renamed_away (test_strict_gate.StrictGateTests.test_required_check_cannot_be_renamed_away) ... ok
test_required_kind_cannot_be_downgraded (test_strict_gate.StrictGateTests.test_required_kind_cannot_be_downgraded) ... ok
test_required_patterns_owned_by_plan_not_report (test_strict_gate.StrictGateTests.test_required_patterns_owned_by_plan_not_report) ... ok
test_review_other_commit_rejected (test_strict_gate.StrictGateTests.test_review_other_commit_rejected) ... ok
test_task_commit_missing_rejected (test_strict_gate.StrictGateTests.test_task_commit_missing_rejected) ... ok
test_archive_scales_with_aggregate_tokens (test_tqllm_tools.BudgetTests.test_archive_scales_with_aggregate_tokens) ... ok
test_bool_rejected_as_integer (test_tqllm_tools.BudgetTests.test_bool_rejected_as_integer) ... ok
test_full_draft_kv_is_five_gib (test_tqllm_tools.BudgetTests.test_full_draft_kv_is_five_gib) ... ok
test_host_budget_enforced (test_tqllm_tools.BudgetTests.test_host_budget_enforced) ... ok
test_illustrative_never_qualified (test_tqllm_tools.BudgetTests.test_illustrative_never_qualified) ... ok
test_measured_fit_is_only_budget_go (test_tqllm_tools.BudgetTests.test_measured_fit_is_only_budget_go) ... ok
test_missing_size_rejected (test_tqllm_tools.BudgetTests.test_missing_size_rejected) ... ok
test_negative_rejected (test_tqllm_tools.BudgetTests.test_negative_rejected) ... ok
test_projected_archive_is_two_point_five_gib (test_tqllm_tools.BudgetTests.test_projected_archive_is_two_point_five_gib) ... ok
test_raw_features_are_not_free (test_tqllm_tools.BudgetTests.test_raw_features_are_not_free) ... ok
test_reclaim_cannot_exceed_baseline (test_tqllm_tools.BudgetTests.test_reclaim_cannot_exceed_baseline) ... ok
test_reclaim_requires_evidence (test_tqllm_tools.BudgetTests.test_reclaim_requires_evidence) ... ok
test_reserve_enforced (test_tqllm_tools.BudgetTests.test_reserve_enforced) ... ok
test_ring_scales_with_lanes_not_context (test_tqllm_tools.BudgetTests.test_ring_scales_with_lanes_not_context) ... ok
test_unknown_archive_rejected (test_tqllm_tools.BudgetTests.test_unknown_archive_rejected) ... ok
test_262k_includes_oldest_not_only_4096 (test_tqllm_tools.RetrievalOracleTests.test_262k_includes_oldest_not_only_4096) ... ok
test_empty_prefix (test_tqllm_tools.RetrievalOracleTests.test_empty_prefix) ... ok
test_nan_score_rejected (test_tqllm_tools.RetrievalOracleTests.test_nan_score_rejected) ... ok
test_negative_recent_rejected (test_tqllm_tools.RetrievalOracleTests.test_negative_recent_rejected) ... ok
test_page_ties_stable (test_tqllm_tools.RetrievalOracleTests.test_page_ties_stable) ... ok
test_partial_chunk_not_out_of_bounds (test_tqllm_tools.RetrievalOracleTests.test_partial_chunk_not_out_of_bounds) ... ok
test_zero_chunk_rejected (test_tqllm_tools.RetrievalOracleTests.test_zero_chunk_rejected) ... ok
test_zero_page_budget (test_tqllm_tools.RetrievalOracleTests.test_zero_page_budget) ... ok
test_cancelled_zero_commit_allowed (test_tqllm_tools.RoundCostTests.test_cancelled_zero_commit_allowed) ... ok
test_empty_rejected (test_tqllm_tools.RoundCostTests.test_empty_rejected) ... ok
test_more_accepted_than_proposed_rejected (test_tqllm_tools.RoundCostTests.test_more_accepted_than_proposed_rejected) ... ok
test_no_drafts (test_tqllm_tools.RoundCostTests.test_no_drafts) ... ok
test_nonpositive_time_rejected (test_tqllm_tools.RoundCostTests.test_nonpositive_time_rejected) ... ok
test_too_many_committed_rejected (test_tqllm_tools.RoundCostTests.test_too_many_committed_rejected) ... ok
test_uses_committed_including_bonus (test_tqllm_tools.RoundCostTests.test_uses_committed_including_bonus) ... ok
test_zero_acceptance_can_commit_one (test_tqllm_tools.RoundCostTests.test_zero_acceptance_can_commit_one) ... ok

----------------------------------------------------------------------
Ran 63 tests in 0.174s

OK
````
<!-- payload-end -->
