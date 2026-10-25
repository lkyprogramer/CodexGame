# V2 支撑材料：`templates/evidence-check.example.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: templates/evidence-check.example.json -->
<!-- payload-sha256: d666678f066f8247aa9e16febdee93d305bb19ed90e4e3accf2c1e00c6c22224 -->
<!-- payload-bytes: 595 -->

<!-- payload-begin -->
````json
{
  "id": "FRONTEND",
  "kind": "junit",
  "status": "PENDING",
  "source_commit": "",
  "evidence": "raw/frontend.xml",
  "sha256": "",
  "required_patterns": [
    "^ninfer_qwen3_8_frontend_test$",
    "^ninfer_qwen3_8_tokenizer_work_test$",
    "^ninfer_qwen3_8_tokenization_equivalence_test$",
    "^ninfer_qwen3_8_encoding_restart_test$",
    "^ninfer_qwen3_8_boundary_encoding_test$",
    "^ninfer_qwen3_8_legacy_oracle_test$"
  ],
  "notes": "由计划required_checks约束，不能把kind改manual或删required来规避缺测；每个阶段FRONTEND之外必需检查见tasks.json。"
}
````
<!-- payload-end -->
