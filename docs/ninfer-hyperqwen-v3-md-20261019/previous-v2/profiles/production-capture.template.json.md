# V2 支撑材料：`profiles/production-capture.template.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: profiles/production-capture.template.json -->
<!-- payload-sha256: 2892c03d6c915e87e75dad54e87f0f3bc11de9999ce82eb7cd7ccc3d5ac788a8 -->
<!-- payload-bytes: 1023 -->

<!-- payload-begin -->
````json
{
  "status": "TEMPLATE_NOT_RUNNABLE",
  "capture_from_current_production": true,
  "image_digest": "",
  "source_commit": "",
  "gpu_uuid": "",
  "model_path": "",
  "model_sha256": "",
  "model_mount_read_only": true,
  "frontend_resources_sha256": {},
  "argv": [],
  "settings": {
    "max_context": null,
    "kv_capacity_shared": null,
    "max_concurrency": null,
    "max_pending_requests": null,
    "prefill_chunk": null,
    "kv_dtype": null,
    "codec_revision": null,
    "spec": null,
    "draft_tokens": null,
    "reasoning_effort": null,
    "enable_thinking": null,
    "preserve_thinking": null,
    "prefix_checkpoint_policy": null,
    "lora_pool_manifest_sha256": null,
    "vision_enabled": null
  },
  "cache": {
    "directory": "",
    "namespace": "",
    "l1_mib": null,
    "l2_mib": null,
    "l3_mib": null
  },
  "proxy": {
    "version": "",
    "routing": "",
    "reasoning_override": null
  },
  "provenance": "P0 captures actual current values; historical records are not defaults."
}
````
<!-- payload-end -->
