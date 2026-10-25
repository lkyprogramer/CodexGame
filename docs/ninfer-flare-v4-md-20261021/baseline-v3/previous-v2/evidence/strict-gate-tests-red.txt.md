# V2 支撑材料：`evidence/strict-gate-tests-red.txt`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: evidence/strict-gate-tests-red.txt -->
<!-- payload-sha256: 322e41b64d758dd17db9c51a4430b4cf10c7e8ed6b8696eed0bdb5490a3c2f68 -->
<!-- payload-bytes: 5672 -->

<!-- payload-begin -->
````text
test_check_other_commit_rejected (test_strict_gate.StrictGateTests.test_check_other_commit_rejected) ... FAIL
test_complete_synthetic_evidence_passes (test_strict_gate.StrictGateTests.test_complete_synthetic_evidence_passes) ... ok
test_duplicate_check_rejected (test_strict_gate.StrictGateTests.test_duplicate_check_rejected) ... FAIL
test_invalid_model_hash_rejected (test_strict_gate.StrictGateTests.test_invalid_model_hash_rejected) ... FAIL
test_required_check_cannot_be_renamed_away (test_strict_gate.StrictGateTests.test_required_check_cannot_be_renamed_away) ... FAIL
test_required_kind_cannot_be_downgraded (test_strict_gate.StrictGateTests.test_required_kind_cannot_be_downgraded) ... FAIL
test_required_patterns_owned_by_plan_not_report (test_strict_gate.StrictGateTests.test_required_patterns_owned_by_plan_not_report) ... ok
test_review_other_commit_rejected (test_strict_gate.StrictGateTests.test_review_other_commit_rejected) ... FAIL
test_task_commit_missing_rejected (test_strict_gate.StrictGateTests.test_task_commit_missing_rejected) ... FAIL

======================================================================
FAIL: test_check_other_commit_rejected (test_strict_gate.StrictGateTests.test_check_other_commit_rejected)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_strict_gate.py", line 30, in test_check_other_commit_rejected
    self.assertFalse(self.evaluate(lambda p,e,r:e['checks'][0].update(source_commit='c'*40))['passed'])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false

======================================================================
FAIL: test_duplicate_check_rejected (test_strict_gate.StrictGateTests.test_duplicate_check_rejected)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_strict_gate.py", line 41, in test_duplicate_check_rejected
    self.assertFalse(self.evaluate(lambda p,e,r:e['checks'].append(dict(e['checks'][0])))['passed'])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false

======================================================================
FAIL: test_invalid_model_hash_rejected (test_strict_gate.StrictGateTests.test_invalid_model_hash_rejected)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_strict_gate.py", line 39, in test_invalid_model_hash_rejected
    self.assertFalse(self.evaluate(lambda p,e,r:e['gpu'].update(model_sha256='not-a-hash'))['passed'])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false

======================================================================
FAIL: test_required_check_cannot_be_renamed_away (test_strict_gate.StrictGateTests.test_required_check_cannot_be_renamed_away)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_strict_gate.py", line 26, in test_required_check_cannot_be_renamed_away
    self.assertFalse(self.evaluate(lambda p,e,r:e['checks'][0].update(id='unrelated'))['passed'])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false

======================================================================
FAIL: test_required_kind_cannot_be_downgraded (test_strict_gate.StrictGateTests.test_required_kind_cannot_be_downgraded)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_strict_gate.py", line 28, in test_required_kind_cannot_be_downgraded
    self.assertFalse(self.evaluate(lambda p,e,r:e['checks'][0].update(kind='manual'))['passed'])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false

======================================================================
FAIL: test_review_other_commit_rejected (test_strict_gate.StrictGateTests.test_review_other_commit_rejected)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_strict_gate.py", line 24, in test_review_other_commit_rejected
    self.assertFalse(self.evaluate(lambda p,e,r:e['review'].update(reviewed_commit='c'*40))['passed'])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false

======================================================================
FAIL: test_task_commit_missing_rejected (test_strict_gate.StrictGateTests.test_task_commit_missing_rejected)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/ninfer_merge_audit/package/tests/test_strict_gate.py", line 37, in test_task_commit_missing_rejected
    self.assertFalse(self.evaluate(lambda p,e,r:e['tasks'][0].pop('commit'))['passed'])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false

----------------------------------------------------------------------
Ran 9 tests in 0.007s

FAILED (failures=7)
````
<!-- payload-end -->
