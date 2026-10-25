# V2 支撑材料：`templates/P12-phase-result.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: templates/P12-phase-result.json -->
<!-- payload-sha256: e85b47db41d7fc2862ce98e5f138a0ae6a39cd2553f0b3a15306feee31964953 -->
<!-- payload-bytes: 4194 -->

<!-- payload-begin -->
````json
{
  "phase": "P12",
  "source_commit": "",
  "tasks": [
    {
      "id": "P12-T01",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P12-T02",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P12-T03",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P12-T04",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P12-T05",
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
      "id": "SOURCE_AND_LICENSE_RETENTION",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/source_and_license_retention.json",
      "sha256": ""
    },
    {
      "id": "BUILD_MATRIX",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/build_matrix.json",
      "sha256": ""
    },
    {
      "id": "FINAL_QUALITY",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/final_quality.json",
      "sha256": ""
    },
    {
      "id": "PERFORMANCE",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/performance.json",
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
      "id": "CANARY",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/canary.json",
      "sha256": ""
    },
    {
      "id": "ROLLBACK",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/rollback.json",
      "sha256": ""
    },
    {
      "id": "QUALIFICATION_SCOPE",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/qualification_scope.json",
      "sha256": ""
    },
    {
      "id": "REVIEW",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/review.json",
      "sha256": ""
    },
    {
      "id": "FINAL_NATIVE_REGRESSION",
      "kind": "junit",
      "required_patterns": [
        "^ninfer_dflash2_artifact_test$",
        "^ninfer_dflash2_graph_test$",
        "^ninfer_dflash2_long_context_real_test$",
        "^ninfer_dflash2_ops_test$",
        "^ninfer_dflash2_real_test$",
        "^ninfer_dflash2_state_test$",
        "^ninfer_draft_archive_test$",
        "^ninfer_draft_cache_lifecycle_real_test$",
        "^ninfer_draft_page_index_test$",
        "^ninfer_draft_refresh_test$",
        "^ninfer_draft_retrieval_test$",
        "^ninfer_external_draft_real_test$",
        "^ninfer_gqa_attention_test$",
        "^ninfer_mtp_width_real_test$",
        "^ninfer_prompt_lookup_test$",
        "^ninfer_qwen3_8_boundary_encoding_test$",
        "^ninfer_qwen3_8_encoding_restart_test$",
        "^ninfer_qwen3_8_frontend_test$",
        "^ninfer_qwen3_8_legacy_oracle_test$",
        "^ninfer_qwen3_8_tokenization_equivalence_test$",
        "^ninfer_qwen3_8_tokenizer_work_test$",
        "^ninfer_selective_draft_policy_test$",
        "^ninfer_spec_perf_log_test$",
        "^ninfer_speculation_policy_test$",
        "^ninfer_verify_envelope_test$"
      ],
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/final_native_regression.xml",
      "sha256": ""
    }
  ],
  "gpu": {
    "executed": false,
    "uuid": "",
    "model_sha256": "",
    "draft_model_sha256": "",
    "raw_evidence": ""
  },
  "qualification_scope": {
    "source": "PENDING",
    "mtp_policy": "UNQUALIFIED",
    "lookup": "UNQUALIFIED",
    "dflash2_ring": "UNQUALIFIED",
    "dflash2_global": "UNQUALIFIED"
  },
  "notes": "模板不是运行结果。保留前一gate复本，所有证据必须指向相同集成source；预算计算不等于GPU资格。",
  "previous_gate": "inputs/previous-gate.json"
}
````
<!-- payload-end -->
