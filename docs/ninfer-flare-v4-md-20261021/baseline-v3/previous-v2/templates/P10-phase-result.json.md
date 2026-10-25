# V2 支撑材料：`templates/P10-phase-result.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: templates/P10-phase-result.json -->
<!-- payload-sha256: 519d62936dbd305aae6e71e6699396c3f393d62c0ad1b32c47580e60f3a44411 -->
<!-- payload-bytes: 3849 -->

<!-- payload-begin -->
````json
{
  "phase": "P10",
  "source_commit": "",
  "tasks": [
    {
      "id": "P10-T01",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P10-T02",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P10-T03",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P10-T04",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P10-T05",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P10-T06",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P10-T07",
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
      "id": "ASSET_BINDING",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/asset_binding.json",
      "sha256": ""
    },
    {
      "id": "DRAFT_OPS",
      "kind": "junit",
      "required_patterns": [
        "^ninfer_dflash2_ops_test$",
        "^ninfer_dflash2_artifact_test$"
      ],
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/draft_ops.xml",
      "sha256": ""
    },
    {
      "id": "DRAFT_REAL",
      "kind": "junit",
      "required_patterns": [
        "^ninfer_dflash2_real_test$",
        "^ninfer_external_draft_real_test$"
      ],
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/draft_real.xml",
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
      "id": "LEGACY_REGRESSION",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/legacy_regression.json",
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
      "id": "INDEPENDENT_REFERENCE",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/independent_reference.json",
      "sha256": ""
    },
    {
      "id": "ALL_PHASE_TARGETS",
      "kind": "junit",
      "required_patterns": [
        "^ninfer_dflash2_artifact_test$",
        "^ninfer_dflash2_graph_test$",
        "^ninfer_dflash2_ops_test$",
        "^ninfer_dflash2_real_test$",
        "^ninfer_dflash2_state_test$",
        "^ninfer_external_draft_real_test$"
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
