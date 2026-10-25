# V2 支撑材料：`data/fork-commits.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: data/fork-commits.json -->
<!-- payload-sha256: ae39b1b9063a1401876dec34eca3f0e0755f6c255afd6c9a739053dd1387e48b -->
<!-- payload-bytes: 3223 -->

<!-- payload-begin -->
````json
[
  {
    "sha": "d5d2e17fb9d0256b06249291f5d2714b92014952",
    "title": "Baseline identity evidence",
    "disposition": "Preserve as historical, remeasure production in P0",
    "source": "https://github.com/lkyprogramer/ninfer-4090/commit/d5d2e17fb9d0256b06249291f5d2714b92014952"
  },
  {
    "sha": "e924cc2c08d7523d0b58672fbb98511ecd7e664f",
    "title": "Request-local work counters",
    "disposition": "Retain optional instrumentation, no prompt identity impact",
    "source": "https://github.com/lkyprogramer/ninfer-4090/commit/e924cc2c08d7523d0b58672fbb98511ecd7e664f"
  },
  {
    "sha": "c782577eb536608160e73f4c3b59ee89b6180198",
    "title": "Frozen complete 44a2c6c reference",
    "disposition": "Preserve core algorithm, decouple DTOs",
    "source": "https://github.com/lkyprogramer/ninfer-4090/commit/c782577eb536608160e73f4c3b59ee89b6180198"
  },
  {
    "sha": "6b4286de451411b19d75051376b0ede6d461c936",
    "title": "B0 monotonic first-byte scanner",
    "disposition": "Retain single scanner with added-token order priority",
    "source": "https://github.com/lkyprogramer/ninfer-4090/commit/6b4286de451411b19d75051376b0ede6d461c936"
  },
  {
    "sha": "1d05441bafdb89a254f9e592de53d19c1de4e765",
    "title": "Selected-token restart trace",
    "disposition": "Retain via same scanner metadata, no second full encoding",
    "source": "https://github.com/lkyprogramer/ninfer-4090/commit/1d05441bafdb89a254f9e592de53d19c1de4e765"
  },
  {
    "sha": "a5128f058c13c32affa6e40e80dfa1774ca16482",
    "title": "B1 boundary validation and memo",
    "disposition": "Migrate behavior to segmented prefix API, retain memo/counters",
    "source": "https://github.com/lkyprogramer/ninfer-4090/commit/a5128f058c13c32affa6e40e80dfa1774ca16482"
  },
  {
    "sha": "1dacb0f21e8397ce41f7790b3bb3468811e91876",
    "title": "Legacy/B0/B1 benchmark lanes",
    "disposition": "Keep legacy lane and add upstream/merged lane comparison",
    "source": "https://github.com/lkyprogramer/ninfer-4090/commit/1dacb0f21e8397ce41f7790b3bb3468811e91876"
  },
  {
    "sha": "f3b231db68542f01568216711d4fda485fa62799",
    "title": "Prepare-detail timers and sizes",
    "disposition": "Keep fields with explicit extension discriminator",
    "source": "https://github.com/lkyprogramer/ninfer-4090/commit/f3b231db68542f01568216711d4fda485fa62799"
  },
  {
    "sha": "46320bd0b70e73330c9ee88db2ccc0b7259c19de",
    "title": "Weightless serving image",
    "disposition": "Keep runtime read-only model mount",
    "source": "https://github.com/lkyprogramer/ninfer-4090/commit/46320bd0b70e73330c9ee88db2ccc0b7259c19de"
  },
  {
    "sha": "7c9d9591ffca158f197a175c8bfe5e77a7f848ec",
    "title": "Linear SwiGLU skip77",
    "disposition": "Keep correct skip semantics, enforce GPU required tests",
    "source": "https://github.com/lkyprogramer/ninfer-4090/commit/7c9d9591ffca158f197a175c8bfe5e77a7f848ec"
  },
  {
    "sha": "e0b05f7cb46adae2787be2ccbe605e1b0c9b3923",
    "title": "G1 differential driver",
    "disposition": "Preserve original real53/synthetic74 routing, materialize external fixtures",
    "source": "https://github.com/lkyprogramer/ninfer-4090/commit/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923"
  }
]
````
<!-- payload-end -->
