# V2 支撑材料：`evidence/tqllm/helper-negative-controls.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: evidence/tqllm/helper-negative-controls.json -->
<!-- payload-sha256: 70cd1ce5b3aa22b46842e640ec91e026e8188d71bb3c336c21e5af0337109f49 -->
<!-- payload-bytes: 280 -->

<!-- payload-begin -->
````json
[
  {
    "mutation": "last4096-candidate-regression",
    "caught_by_assertion": true
  },
  {
    "mutation": "accepted-vs-committed-regression",
    "caught_by_assertion": true
  },
  {
    "mutation": "ignore-resource-budget-regression",
    "caught_by_assertion": true
  }
]
````
<!-- payload-end -->
