# V2 支撑材料：`profiles/candidate-policy.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: profiles/candidate-policy.json -->
<!-- payload-sha256: b02180f2ee82e1dd43db4f864bebf3a82c2f413aa313ef5723106a728e6cf897 -->
<!-- payload-bytes: 809 -->

<!-- payload-begin -->
````json
{
  "status": "DESIGN_NOT_DEPLOYED",
  "base_profile": "production-capture.template.json",
  "before_P4": "use captured codec, only if milestone supports it",
  "P4_onwards": {
    "kv_dtype": "rk4v4",
    "codec_revision": "midrise from locked source; record actual state ABI"
  },
  "retain": [
    "reasoning_effort",
    "enable_thinking",
    "preserve_thinking",
    "max_context",
    "shared kv capacity",
    "spec/draft",
    "proxy contract"
  ],
  "new_cache_directory_required": true,
  "allow_old_codec_alias": false,
  "enable_new_decision_adapters_by_default": false,
  "enable_new_vision_decisions_by_default": false,
  "concurrency_rule": "sum of resident states and runtime overhead must fit shared KV/capacity ledger",
  "rollback": "old immutable image + old argv + old isolated cache"
}
````
<!-- payload-end -->
