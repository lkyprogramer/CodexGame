# V2 支撑材料：`evidence/tqllm/budget-example-output.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: evidence/tqllm/budget-example-output.json -->
<!-- payload-sha256: a5f875014bbe68255d7ffcd1c5fddb11ab913624b7570b75b39dc3ef2badaa25 -->
<!-- payload-bytes: 517 -->

<!-- payload-begin -->
````json
{
  "scope": "CPU_ESTIMATE_NOT_INFERENCE_TEST",
  "verdict": "ILLUSTRATIVE_ONLY",
  "fits_with_reserve": true,
  "draft_kv_bytes_per_token": 20480,
  "hypothetical_full_draft_kv_bytes": 5368709120,
  "host_archive_bytes": 2684354560,
  "gpu_ring_bytes": 44564480,
  "gpu_incremental_bytes": 803733504,
  "projected_gpu_peak_bytes": 24426053632,
  "projected_host_peak_bytes": 28487712768,
  "gpu_headroom_after_reserve_bytes": 806879232,
  "host_headroom_after_reserve_bytes": 31641829376,
  "reclaim_evidence": ""
}
````
<!-- payload-end -->
