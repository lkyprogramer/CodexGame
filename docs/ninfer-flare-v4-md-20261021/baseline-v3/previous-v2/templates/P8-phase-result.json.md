# V2 支撑材料：`templates/P8-phase-result.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: templates/P8-phase-result.json -->
<!-- payload-sha256: 3520352c0995196577b984e1e3e8f9af65e80760d5939fcc5ccfcebc0e1e9656 -->
<!-- payload-bytes: 2863 -->

<!-- payload-begin -->
````json
{
  "phase": "P8",
  "source_commit": "",
  "tasks": [
    {
      "id": "P8-T01",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P8-T02",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P8-T03",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P8-T04",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P8-T05",
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
      "id": "POLICY",
      "kind": "junit",
      "required_patterns": [
        "^ninfer_speculation_policy_test$",
        "^ninfer_prompt_lookup_test$"
      ],
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/policy.xml",
      "sha256": ""
    },
    {
      "id": "VERIFY",
      "kind": "junit",
      "required_patterns": [
        "^ninfer_external_draft_real_test$"
      ],
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/verify.xml",
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
      "id": "PERFORMANCE",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/performance.json",
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
        "^ninfer_external_draft_real_test$",
        "^ninfer_mtp_width_real_test$",
        "^ninfer_prompt_lookup_test$",
        "^ninfer_speculation_policy_test$"
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
  "previous_gate": "inputs/previous-gate.json"
}
````
<!-- payload-end -->
