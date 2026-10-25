# V2 支撑材料：`evidence/tqllm/helper-tests-red.txt`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: evidence/tqllm/helper-tests-red.txt -->
<!-- payload-sha256: 96ef48e8c92f3abd7341c807bde43ff99641f9fe53a345b6dc7a95cc6ab460d8 -->
<!-- payload-bytes: 999 -->

<!-- payload-begin -->
````text
test_tqllm_tools (unittest.loader._FailedTest.test_tqllm_tools) ... ERROR

======================================================================
ERROR: test_tqllm_tools (unittest.loader._FailedTest.test_tqllm_tools)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_tqllm_tools
Traceback (most recent call last):
  File "/usr/lib/python3.13/unittest/loader.py", line 396, in _find_test_path
    module = self._get_module_from_name(name)
  File "/usr/lib/python3.13/unittest/loader.py", line 339, in _get_module_from_name
    __import__(name)
    ~~~~~~~~~~^^^^^^
  File "/mnt/data/work/ninfer-upstream-merge-20261015/tests/test_tqllm_tools.py", line 6, in <module>
    from tqllm_tools import estimate_budget, eligible_remote_chunks, select_pages, summarize_rounds
ModuleNotFoundError: No module named 'tqllm_tools'


----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)
````
<!-- payload-end -->
