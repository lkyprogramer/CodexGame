# V2 支撑材料：`profiles/tqllm-candidate.template.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: profiles/tqllm-candidate.template.json -->
<!-- payload-sha256: a716f41fcd4e98373433681a01e256a2564230f7a326aa78909980e56c58fed8 -->
<!-- payload-bytes: 1031 -->

<!-- payload-begin -->
````json
{
  "status": "NOT_IMPLEMENTED_NOT_FOR_OLD_BINARY",
  "target_artifact_sha256": "",
  "draft_artifact_sha256": "",
  "merged_qualified_commit": "",
  "target_kv": "rk4v4",
  "maximum_context_from_p6": true,
  "enable_new_features": false,
  "enabled_backends": [],
  "dflash2_scope": [
    "base",
    "text",
    "greedy"
  ],
  "chain_candidate_widths": [
    3,
    4,
    5
  ],
  "physical_draft_rows": "READ_FROM_FROZEN_ASSET_NOT_EQUAL_TO_K",
  "draft_archive": {
    "enabled": false,
    "layout_version": 1,
    "persistence": "in_process_only"
  },
  "selection_example": {
    "logical_page_tokens": 256,
    "representatives_per_page": 2,
    "coarse_pages": 8,
    "remote_chunks_per_head": 32,
    "chunk_tokens": 16,
    "recent_tokens": 1536,
    "anchor_tokens": 256,
    "refresh_rounds": 8
  },
  "gpu_reserve_bytes": 536870912,
  "host_reserve_bytes": 8589934592,
  "qualification": "PENDING",
  "note": "Experimental starting values; apply only after exact asset shape, budget, CUDA and task qualification."
}
````
<!-- payload-end -->
