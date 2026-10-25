# V2 支撑材料：`templates/P0-phase-result.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: templates/P0-phase-result.json -->
<!-- payload-sha256: eb7c506bac58a1fa0290ca4236352503675585e88e08587a68c5b20649c70454 -->
<!-- payload-bytes: 2778 -->

<!-- payload-begin -->
````json
{
  "phase": "P0",
  "source_commit": "",
  "tasks": [
    {
      "id": "P0-T01",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P0-T02",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P0-T03",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P0-T04",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    }
  ],
  "review": {
    "status": "PENDING",
    "reviewer": "",
    "reviewed_commit": "",
    "blocking_findings": []
  },
  "checks": [
    {
      "id": "SOURCE_AUDIT",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/source_audit.json",
      "sha256": ""
    },
    {
      "id": "PROD_PROFILE",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/prod_profile.json",
      "sha256": ""
    },
    {
      "id": "BUILD",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/build.json",
      "sha256": ""
    },
    {
      "id": "FRONTEND",
      "kind": "junit",
      "required_patterns": [
        "^ninfer_qwen3_8_frontend_test$",
        "^ninfer_qwen3_8_tokenizer_work_test$",
        "^ninfer_qwen3_8_tokenization_equivalence_test$",
        "^ninfer_qwen3_8_encoding_restart_test$",
        "^ninfer_qwen3_8_boundary_encoding_test$",
        "^ninfer_qwen3_8_legacy_oracle_test$"
      ],
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/frontend.xml",
      "sha256": ""
    },
    {
      "id": "ORACLE_G1",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/oracle_g1.json",
      "sha256": ""
    },
    {
      "id": "BASELINE",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/baseline.json",
      "sha256": ""
    },
    {
      "id": "GPU_RAW",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/gpu_raw.json",
      "sha256": ""
    },
    {
      "id": "REVIEW",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/review.json",
      "sha256": ""
    }
  ],
  "gpu": {
    "executed": false,
    "uuid": "",
    "model_sha256": "",
    "raw_evidence": ""
  },
  "qualification_scope": {
    "source": "PENDING",
    "chat": "PENDING",
    "decision_text": "UNQUALIFIED",
    "decision_image": "UNQUALIFIED",
    "browser": "PENDING"
  },
  "notes": "模板不是运行结果。checks示例见evidence-check.example.json。前一gate的复本和所有raw文件必须位于本phase evidence根目录内。"
}
````
<!-- payload-end -->
