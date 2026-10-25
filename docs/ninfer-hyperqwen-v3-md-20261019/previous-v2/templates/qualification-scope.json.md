# V2 支撑材料：`templates/qualification-scope.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: templates/qualification-scope.json -->
<!-- payload-sha256: a5d9a1c97b57329e69e3beb634510bbf13c15cdf2c5ed5d914144a09be97709b -->
<!-- payload-bytes: 574 -->

<!-- payload-begin -->
````json
{
  "source_commit": "",
  "scope": {
    "source_full_upstream": "PENDING",
    "chat_27b_4090": "PENDING",
    "long_context_248k": "PENDING",
    "decision_text_real_adapter": "UNQUALIFIED",
    "decision_image_real_adapter": "UNQUALIFIED",
    "browser_runtime": "UNQUALIFIED",
    "35b_build": "PENDING",
    "35b_real_model": "UNQUALIFIED",
    "nvfp4_sm89_execution": "NOT_APPLICABLE"
  },
  "disabled_features": [],
  "missing_artifacts": [],
  "notes": "UNQUALIFIED必须在生产profile禁用；纯contract/op测试仍必需。NVFP4 A4不可在4090伪验收。"
}
````
<!-- payload-end -->
