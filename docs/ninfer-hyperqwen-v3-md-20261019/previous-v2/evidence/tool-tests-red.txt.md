# V2 支撑材料：`evidence/tool-tests-red.txt`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: evidence/tool-tests-red.txt -->
<!-- payload-sha256: cdd562d2411ab915f144c00a65f926d86c20f2a463543e35588466484f851992 -->
<!-- payload-bytes: 20269 -->

<!-- payload-begin -->
````text
test_git_probe_isolated_and_conflict_is_reported (test_merge_tools.UtilityTests.test_git_probe_isolated_and_conflict_is_reported) ... FAIL
test_junit_duplicate_rejected (test_merge_tools.UtilityTests.test_junit_duplicate_rejected) ... FAIL
test_junit_failure_is_not_pass (test_merge_tools.UtilityTests.test_junit_failure_is_not_pass) ... FAIL
test_junit_missing_required_is_not_pass (test_merge_tools.UtilityTests.test_junit_missing_required_is_not_pass) ... FAIL
test_junit_no_tests_is_not_pass (test_merge_tools.UtilityTests.test_junit_no_tests_is_not_pass) ... FAIL
test_junit_optional_skip_allowed (test_merge_tools.UtilityTests.test_junit_optional_skip_allowed) ... FAIL
test_junit_pass (test_merge_tools.UtilityTests.test_junit_pass) ... FAIL
test_junit_required_skip_is_not_pass (test_merge_tools.UtilityTests.test_junit_required_skip_is_not_pass) ... FAIL
test_metrics_detects_latency_regression (test_merge_tools.UtilityTests.test_metrics_detects_latency_regression) ... FAIL
test_metrics_duplicate_is_rejected (test_merge_tools.UtilityTests.test_metrics_duplicate_is_rejected) ... FAIL
test_metrics_good_samples_pass (test_merge_tools.UtilityTests.test_metrics_good_samples_pass) ... FAIL
test_metrics_mismatched_cases_rejected (test_merge_tools.UtilityTests.test_metrics_mismatched_cases_rejected) ... FAIL
test_metrics_nan_rejected (test_merge_tools.UtilityTests.test_metrics_nan_rejected) ... FAIL
test_metrics_underpowered_is_blocked (test_merge_tools.UtilityTests.test_metrics_underpowered_is_blocked) ... FAIL
test_metrics_zero_prepare_uses_absolute_budget (test_merge_tools.UtilityTests.test_metrics_zero_prepare_uses_absolute_budget) ... FAIL
test_phase_evidence_pending_rejected (test_merge_tools.UtilityTests.test_phase_evidence_pending_rejected) ... FAIL
test_phase_evidence_requires_real_files (test_merge_tools.UtilityTests.test_phase_evidence_requires_real_files) ... FAIL
test_plan_accepts_dag (test_merge_tools.UtilityTests.test_plan_accepts_dag) ... FAIL
test_plan_rejects_cycle (test_merge_tools.UtilityTests.test_plan_rejects_cycle) ... FAIL
test_plan_rejects_duplicate_id (test_merge_tools.UtilityTests.test_plan_rejects_duplicate_id) ... FAIL
test_plan_rejects_missing_dependency (test_merge_tools.UtilityTests.test_plan_rejects_missing_dependency) ... FAIL
test_redacts_both_argument_styles (test_merge_tools.UtilityTests.test_redacts_both_argument_styles) ... FAIL

======================================================================
FAIL: test_git_probe_isolated_and_conflict_is_reported (test_merge_tools.UtilityTests.test_git_probe_isolated_and_conflict_is_reported)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_junit_duplicate_rejected (test_merge_tools.UtilityTests.test_junit_duplicate_rejected)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_junit_failure_is_not_pass (test_merge_tools.UtilityTests.test_junit_failure_is_not_pass)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_junit_missing_required_is_not_pass (test_merge_tools.UtilityTests.test_junit_missing_required_is_not_pass)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_junit_no_tests_is_not_pass (test_merge_tools.UtilityTests.test_junit_no_tests_is_not_pass)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_junit_optional_skip_allowed (test_merge_tools.UtilityTests.test_junit_optional_skip_allowed)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_junit_pass (test_merge_tools.UtilityTests.test_junit_pass)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_junit_required_skip_is_not_pass (test_merge_tools.UtilityTests.test_junit_required_skip_is_not_pass)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_metrics_detects_latency_regression (test_merge_tools.UtilityTests.test_metrics_detects_latency_regression)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_metrics_duplicate_is_rejected (test_merge_tools.UtilityTests.test_metrics_duplicate_is_rejected)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_metrics_good_samples_pass (test_merge_tools.UtilityTests.test_metrics_good_samples_pass)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_metrics_mismatched_cases_rejected (test_merge_tools.UtilityTests.test_metrics_mismatched_cases_rejected)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_metrics_nan_rejected (test_merge_tools.UtilityTests.test_metrics_nan_rejected)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_metrics_underpowered_is_blocked (test_merge_tools.UtilityTests.test_metrics_underpowered_is_blocked)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_metrics_zero_prepare_uses_absolute_budget (test_merge_tools.UtilityTests.test_metrics_zero_prepare_uses_absolute_budget)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_phase_evidence_pending_rejected (test_merge_tools.UtilityTests.test_phase_evidence_pending_rejected)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_phase_evidence_requires_real_files (test_merge_tools.UtilityTests.test_phase_evidence_requires_real_files)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_plan_accepts_dag (test_merge_tools.UtilityTests.test_plan_accepts_dag)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_plan_rejects_cycle (test_merge_tools.UtilityTests.test_plan_rejects_cycle)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_plan_rejects_duplicate_id (test_merge_tools.UtilityTests.test_plan_rejects_duplicate_id)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_plan_rejects_missing_dependency (test_merge_tools.UtilityTests.test_plan_rejects_missing_dependency)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

======================================================================
FAIL: test_redacts_both_argument_styles (test_merge_tools.UtilityTests.test_redacts_both_argument_styles)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 20, in setUp
    def setUp(self): self.m = load_tools(self)
                              ~~~~~~~~~~^^^^^^
  File "/mnt/data/ninfer_merge_audit/package/tests/test_merge_tools.py", line 13, in load_tools
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : audit utilities have not been implemented

----------------------------------------------------------------------
Ran 22 tests in 0.005s

FAILED (failures=22)
````
<!-- payload-end -->
