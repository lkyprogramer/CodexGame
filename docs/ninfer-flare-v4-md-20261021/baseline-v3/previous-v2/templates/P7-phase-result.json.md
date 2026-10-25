# V2 支撑材料：`templates/P7-phase-result.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: templates/P7-phase-result.json -->
<!-- payload-sha256: c89fa7a58fc832949f5c64b2a7edb864fa0b0171ec67577dae9877602f2c6c7e -->
<!-- payload-bytes: 2529 -->

<!-- payload-begin -->
````json
{
  "phase": "P7",
  "source_commit": "",
  "tasks": [
    {
      "id": "P7-T01",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P7-T02",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P7-T03",
      "status": "PENDING",
      "commit": "",
      "evidence": []
    },
    {
      "id": "P7-T04",
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
      "id": "SOURCE_ASSET_LOCK",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/source_asset_lock.json",
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
      "id": "SPEC_TELEMETRY",
      "kind": "junit",
      "required_patterns": [
        "^ninfer_spec_perf_log_test$"
      ],
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/spec_telemetry.xml",
      "sha256": ""
    },
    {
      "id": "GPU_PROFILE",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/gpu_profile.json",
      "sha256": ""
    },
    {
      "id": "BUDGET",
      "kind": "manual",
      "status": "PENDING",
      "source_commit": "",
      "evidence": "raw/budget.json",
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
        "^ninfer_spec_perf_log_test$"
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
