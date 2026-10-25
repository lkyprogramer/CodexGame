# V2 支撑材料：`templates/P11-phase-result.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: templates/P11-phase-result.json -->
<!-- payload-sha256: 0cf8d36732144baadf2f8b86c69d0150b255296183097996300ceb816fcc429b -->
<!-- payload-bytes: 3809 -->

<!-- payload-begin -->
````json
{
  "phase": "P11",
  "source_commit": "",
  "tasks": [
    {
      "id": "P11-T01",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P11-T02",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P11-T03",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P11-T04",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P11-T05",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P11-T06",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P11-T07",
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
      "id": "BUILD",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/build.json",
      "sha256": ""
    },
    {
      "id": "ARCHIVE_AND_INDEX",
      "kind": "junit",
      "required_patterns": [
        "^ninfer_draft_archive_test$",
        "^ninfer_draft_page_index_test$"
      ],
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/archive_and_index.xml",
      "sha256": ""
    },
    {
      "id": "RETRIEVAL",
      "kind": "junit",
      "required_patterns": [
        "^ninfer_draft_retrieval_test$",
        "^ninfer_draft_refresh_test$"
      ],
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/retrieval.xml",
      "sha256": ""
    },
    {
      "id": "LONG_REAL",
      "kind": "junit",
      "required_patterns": [
        "^ninfer_dflash2_long_context_real_test$"
      ],
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/long_real.xml",
      "sha256": ""
    },
    {
      "id": "CACHE_LIFECYCLE",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/cache_lifecycle.json",
      "sha256": ""
    },
    {
      "id": "BUDGET_AND_PERFORMANCE",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/budget_and_performance.json",
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
      "id": "ALL_PHASE_TARGETS",
      "kind": "junit",
      "required_patterns": [
        "^ninfer_dflash2_long_context_real_test$",
        "^ninfer_draft_archive_test$",
        "^ninfer_draft_cache_lifecycle_real_test$",
        "^ninfer_draft_page_index_test$",
        "^ninfer_draft_refresh_test$",
        "^ninfer_draft_retrieval_test$",
        "^ninfer_selective_draft_policy_test$"
      ],
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/all_phase_targets.xml",
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
  "previous_gate": "inputs/previous-gate.json",
  "research_and_promotion": {
    "implementation": "PENDING",
    "correctness": "PENDING",
    "resource": "PENDING",
    "measurement": "PENDING",
    "promotion": "UNQUALIFIED",
    "enabled_by_default": false,
    "decision_evidence": ""
  }
}
````
<!-- payload-end -->
