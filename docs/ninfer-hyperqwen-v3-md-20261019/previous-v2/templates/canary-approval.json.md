# V2 支撑材料：`templates/canary-approval.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: templates/canary-approval.json -->
<!-- payload-sha256: 8aea1c6d573a11ab8b4614ec3f5a5ee8981d829b9180a2e970fa03f7e7a652b5 -->
<!-- payload-bytes: 346 -->

<!-- payload-begin -->
````json
{
  "status": "NOT_APPROVED",
  "target_host": "",
  "container": "",
  "candidate_image_digest": "",
  "source_commit": "",
  "maintenance_window": "",
  "allowed_interruption": false,
  "approved_by": "",
  "rollback_trigger_ids": [],
  "notes": "此模板不构成授权。用户允许部署测试不等于任意生产目标均可重启。"
}
````
<!-- payload-end -->
