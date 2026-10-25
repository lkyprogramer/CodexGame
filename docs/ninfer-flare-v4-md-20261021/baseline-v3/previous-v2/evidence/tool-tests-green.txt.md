# V2 支撑材料：`evidence/tool-tests-green.txt`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: evidence/tool-tests-green.txt -->
<!-- payload-sha256: 6e85f529d20646c2031f3c52ae925f9348efe0d3fa873527b842f639cc3b31ab -->
<!-- payload-bytes: 3642 -->

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

----------------------------------------------------------------------
Ran 32 tests in 0.125s

OK
````
<!-- payload-end -->
