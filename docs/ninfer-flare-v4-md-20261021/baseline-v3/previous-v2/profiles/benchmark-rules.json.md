# V2 支撑材料：`profiles/benchmark-rules.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: profiles/benchmark-rules.json -->
<!-- payload-sha256: f807ad2b85a5c07692d243251acab85d9c5deb177abfbdeff6f27dcf12391f52 -->
<!-- payload-bytes: 397 -->

<!-- payload-begin -->
````json
{
  "ttft_seconds": {
    "direction": "lower",
    "p50_relative": 0.05,
    "p90_relative": 0.1,
    "absolute_floor": 0.005
  },
  "decode_tok_s": {
    "direction": "higher",
    "p50_relative": 0.03,
    "p10_relative": 0.05,
    "absolute_floor": 0.0
  },
  "prepare_seconds": {
    "direction": "lower",
    "p50_relative": 0.05,
    "p90_relative": 0.1,
    "absolute_floor": 0.0005
  }
}
````
<!-- payload-end -->
