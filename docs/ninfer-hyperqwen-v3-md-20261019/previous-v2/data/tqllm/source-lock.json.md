# V2 支撑材料：`data/tqllm/source-lock.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: data/tqllm/source-lock.json -->
<!-- payload-sha256: 0e4f44b8ad390c834e55c05d3128252cd8d0fa8564e358ee3a9ad209d077470d -->
<!-- payload-bytes: 982 -->

<!-- payload-begin -->
````json
{
  "as_of": "2026-10-15",
  "original_package_sha256": "2c98ff7ba7b9fbd8c1b79dacb3ddcc76e42b6223f4d534dfb7708b6d236ff89f",
  "baseline": {
    "B": "44a2c6c3392c9d51e76a895ed97bf1867530d252",
    "O": "e0b05f7cb46adae2787be2ccbe605e1b0c9b3923",
    "U": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
    "merged_qualified_commit": null,
    "required_gate": "P6-GATE"
  },
  "donor": {
    "repository": "turbo-tan/tqllm",
    "branch": "main",
    "commit": "4d27324a124f92b7b7dcc554e6406ab6dc645b49",
    "method": "semantic_port_not_git_merge"
  },
  "asset": {
    "repository": "z-lab/Qwen3.8-27B-DFlash2",
    "immutable_revision": null,
    "tensor_manifest_sha256": null,
    "license_review": "PENDING"
  },
  "user_input_sha256": "d088d227b5da769659adbcf487bada545444a1a124e8b41f277d9635bba9b0d2",
  "limitations": [
    "No full local donor clone",
    "No NInfer or tqLLM CUDA build",
    "No model downloaded",
    "No4090 execution",
    "No production mutation"
  ]
}
````
<!-- payload-end -->
