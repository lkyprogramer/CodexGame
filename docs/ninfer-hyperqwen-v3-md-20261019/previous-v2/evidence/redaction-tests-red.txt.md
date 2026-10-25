# V2 支撑材料：`evidence/redaction-tests-red.txt`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: evidence/redaction-tests-red.txt -->
<!-- payload-sha256: bfba1809641a5d034cb8a6fd77cfaed5a39be3ea3095584b540daedeaf74d245 -->
<!-- payload-bytes: 3650 -->

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
test_redaction_preserves_token_count_configuration (test_merge_tools.UtilityTests.test_redaction_preserves_token_count_configuration) ... FAIL
test_redacts_both_argument_styles (test_merge_tools.UtilityTests.test_redacts_both_argument_styles) ... ok

======================================================================
FAIL: test_redaction_preserves_token_count_configuration (test_merge_tools.UtilityTests.test_redaction_preserves_token_count_configuration)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 52, in test_redaction_preserves_token_count_configuration
    self.assertEqual(self.m.redact_argv(argv),argv[:-1]+['<redacted>'])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Lists differ: ['ser[19 chars]s', '<redacted>', '--max-tokens=<redacted>', '[57 chars]ed>'] != ['ser[19 chars]s', '3', '--max-tokens=32768', '--tokenizer-js[43 chars]ed>']

First differing element 2:
'<redacted>'
'3'

  ['serve',
   '--draft-tokens',
-  '<redacted>',
-  '--max-tokens=<redacted>',
+  '3',
+  '--max-tokens=32768',
   '--tokenizer-json',
-  '<redacted>',
+  'vocab.json',
   '--auth-token',
   '<redacted>']

----------------------------------------------------------------------
Ran 23 tests in 0.106s

FAILED (failures=1)
````
<!-- payload-end -->
