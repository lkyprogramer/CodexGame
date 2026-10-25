# V2 支撑材料：`profiles/tqllm-budget-example.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: profiles/tqllm-budget-example.json -->
<!-- payload-sha256: dc150a041743bcd40be97b90b43812048c8253e2a93d09ce40dd12514144c14c -->
<!-- payload-bytes: 801 -->

<!-- payload-begin -->
````json
{
  "total_gpu_bytes": 25769803776,
  "baseline_gpu_peak_bytes": 23622320128,
  "total_host_bytes": 68719476736,
  "baseline_host_peak_bytes": 25769803776,
  "draft_weights_bytes": 536870912,
  "draft_layers": 5,
  "draft_kv_heads": 8,
  "draft_head_dim": 128,
  "draft_hidden": 5120,
  "target_feature_layers": 5,
  "aggregate_archive_tokens": 262144,
  "gpu_ring_rows": 2176,
  "resident_draft_lanes": 1,
  "staging_bytes": 67108864,
  "index_bytes": 20971520,
  "scratch_bytes": 67108864,
  "graph_bytes": 67108864,
  "draft_head_extra_bytes": 0,
  "checkpoint_bytes": 0,
  "pinned_transfer_bytes": 33554432,
  "gpu_reserve_bytes": 536870912,
  "host_reserve_bytes": 8589934592,
  "archive_kind": "projected_bf16",
  "inputs_measured": false,
  "reclaimed_gpu_bytes": 0,
  "reclaim_evidence": ""
}
````
<!-- payload-end -->
