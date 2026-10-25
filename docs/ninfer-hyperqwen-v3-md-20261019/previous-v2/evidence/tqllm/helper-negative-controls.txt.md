# V2 支撑材料：`evidence/tqllm/helper-negative-controls.txt`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: evidence/tqllm/helper-negative-controls.txt -->
<!-- payload-sha256: 3093c95b57283ce4c78c953be508c852ef36fd18dbba8e87a76b1859b605408b -->
<!-- payload-bytes: 2444 -->

<!-- payload-begin -->
````text
last4096-candidate-regression
test_262k_includes_oldest_not_only_4096 (tqtests.RetrievalOracleTests.test_262k_includes_oldest_not_only_4096) ... FAIL

======================================================================
FAIL: test_262k_includes_oldest_not_only_4096 (tqtests.RetrievalOracleTests.test_262k_includes_oldest_not_only_4096)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/work/ninfer-upstream-merge-20261015/tests/test_tqllm_tools.py", line 73, in test_262k_includes_oldest_not_only_4096
    self.assertEqual(ids[0],0);self.assertEqual(len(ids),16288)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^
AssertionError: 12192 != 0

----------------------------------------------------------------------
Ran 1 test in 0.001s

FAILED (failures=1)

accepted-vs-committed-regression
test_uses_committed_including_bonus (tqtests.RoundCostTests.test_uses_committed_including_bonus) ... FAIL

======================================================================
FAIL: test_uses_committed_including_bonus (tqtests.RoundCostTests.test_uses_committed_including_bonus)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/work/ninfer-upstream-merge-20261015/tests/test_tqllm_tools.py", line 92, in test_uses_committed_including_bonus
    r=summarize_rounds(self.rows());self.assertEqual(r["effective_tokens_per_second"],100.0)
                                    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 60.0 != 100.0

----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (failures=1)

ignore-resource-budget-regression
test_reserve_enforced (tqtests.BudgetTests.test_reserve_enforced) ... FAIL

======================================================================
FAIL: test_reserve_enforced (tqtests.BudgetTests.test_reserve_enforced)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/mnt/data/work/ninfer-upstream-merge-20261015/tests/test_tqllm_tools.py", line 46, in test_reserve_enforced
    self.assertFalse(estimate_budget(b)["fits_with_reserve"])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: True is not false

----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (failures=1)
````
<!-- payload-end -->
