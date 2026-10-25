# V2 支撑材料：`data/tqllm/sources.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: data/tqllm/sources.json -->
<!-- payload-sha256: b12b9b81d1916010ece63f0034253ea6b15202ad045ab107a40ac263676e79a4 -->
<!-- payload-bytes: 12589 -->

<!-- payload-begin -->
````json
[
  {
    "id": "T01",
    "repository": "turbo-tan/tqllm",
    "commit": "4d27324a124f92b7b7dcc554e6406ab6dc645b49",
    "path": "README.md",
    "lines": [
      10,
      195
    ],
    "git_blob_sha": "ef194ddaf92c100c8a6af6dec0cf78e3d9cdcbb7",
    "url": "https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/README.md#L10-L195",
    "observed": "GGUF/TQ weight formats; 65K draft vocabulary; author-reported 3090 speed and retrieval results, not a NInfer A/B.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "T02",
    "repository": "turbo-tan/tqllm",
    "commit": "4d27324a124f92b7b7dcc554e6406ab6dc645b49",
    "path": "docs/ARCHITECTURE.md",
    "lines": [
      1,
      56
    ],
    "git_blob_sha": "9cd0ea00b11d698af4e740fd16d1c7cf4aa6c6bc",
    "url": "https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/docs/ARCHITECTURE.md#L1-L56",
    "observed": "Engine, format registries, unified attention arithmetic, memory fit and graph invariants.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "T03",
    "repository": "turbo-tan/tqllm",
    "commit": "4d27324a124f92b7b7dcc554e6406ab6dc645b49",
    "path": "src/qwen35.cpp",
    "lines": [
      2932,
      3105
    ],
    "git_blob_sha": "6451d86b623ebdbf2d82a274431dc0eb9ea26a7d",
    "url": "https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/src/qwen35.cpp#L2932-L3105",
    "observed": "DFlash2 metadata, all-layer KV projection, full-vs-ring allocation, retrieval sets ring=0; draft head rows mapping.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "T04",
    "repository": "turbo-tan/tqllm",
    "commit": "4d27324a124f92b7b7dcc554e6406ab6dc645b49",
    "path": "src/qwen35.cpp",
    "lines": [
      3194,
      3280
    ],
    "git_blob_sha": "6451d86b623ebdbf2d82a274431dc0eb9ea26a7d",
    "url": "https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/src/qwen35.cpp#L3194-L3280",
    "observed": "Target feature projection and per-layer draft K/V injection; batch path refuses ring<=0.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "T05",
    "repository": "turbo-tan/tqllm",
    "commit": "4d27324a124f92b7b7dcc554e6406ab6dc645b49",
    "path": "src/qwen35.cpp",
    "lines": [
      3422,
      3505
    ],
    "git_blob_sha": "6451d86b623ebdbf2d82a274431dc0eb9ea26a7d",
    "url": "https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/src/qwen35.cpp#L3422-L3505",
    "observed": "Single draft graph gated on ring>0 and !subset; physical block B and retrieval per layer.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "T06",
    "repository": "turbo-tan/tqllm",
    "commit": "4d27324a124f92b7b7dcc554e6406ab6dc645b49",
    "path": "kernels/qwen35.cu",
    "lines": [
      975,
      1100
    ],
    "git_blob_sha": "f50a84932d1ced84ce07871b146b8ad290fabab6",
    "url": "https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/kernels/qwen35.cu#L975-L1100",
    "observed": "RCHUNK16, last4096 remote chunks, deterministic per-head top-k, virtual-position RoPE gather.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "T07",
    "repository": "turbo-tan/tqllm",
    "commit": "4d27324a124f92b7b7dcc554e6406ab6dc645b49",
    "path": "kernels/dflash.cu",
    "lines": [
      80,
      180
    ],
    "git_blob_sha": "edac1ff8808ba5555660eb38fcd873878200a2b6",
    "url": "https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/kernels/dflash.cu#L80-L180",
    "observed": "Dynamic two-tap grouped convolution, deterministic top16 and conditioned lattice score.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "T08",
    "repository": "turbo-tan/tqllm",
    "commit": "4d27324a124f92b7b7dcc554e6406ab6dc645b49",
    "path": "README.md",
    "lines": [
      200,
      365
    ],
    "git_blob_sha": "ef194ddaf92c100c8a6af6dec0cf78e3d9cdcbb7",
    "url": "https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/README.md#L200-L365",
    "observed": "Static mtp-from threshold, lookup, effective verify maximum8, memory fit can change context/codec, sampling and performance restrictions.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "T09",
    "repository": "turbo-tan/tqllm",
    "commit": "4d27324a124f92b7b7dcc554e6406ab6dc645b49",
    "path": "tests/dflash_exact.cpp",
    "lines": [
      1,
      72
    ],
    "git_blob_sha": "f1e0a0394408330c6ce04d86c4be5511a92cde9c",
    "url": "https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/tests/dflash_exact.cpp#L1-L72",
    "observed": "Plain/tree/linear token equality test reads at most12000 source characters; context argument does not establish long actual prompt coverage.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "T10",
    "repository": "turbo-tan/tqllm",
    "commit": "4d27324a124f92b7b7dcc554e6406ab6dc645b49",
    "path": "tests/dflash_retrieve.cu",
    "lines": [
      1,
      165
    ],
    "git_blob_sha": "83f51785b102f22453bb4132f5207e26dcae021e",
    "url": "https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/tests/dflash_retrieve.cu#L1-L165",
    "observed": "pos6000 planted-chunk and RoPE tests; no coverage of retrieval candidate truncation beyond65K.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "T11",
    "repository": "turbo-tan/tqllm",
    "commit": "4d27324a124f92b7b7dcc554e6406ab6dc645b49",
    "path": "NOTICE",
    "lines": null,
    "git_blob_sha": "036b04a04cdcc1233b01bca71b9a5e4356975b39",
    "url": "https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/NOTICE",
    "observed": "Apache2.0 project, third-party MIT/public-domain notices; file-specific attribution needed.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "N01",
    "repository": "tensorninja/ninfer-4090",
    "commit": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
    "path": "src/targets/qwen3_8_27b/impl/config.h",
    "lines": [
      10,
      112
    ],
    "git_blob_sha": "12fc566958ed12eb604f6b0487fe5bdc5b33af29",
    "url": "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8_27b/impl/config.h#L10-L112",
    "observed": "27B has16 full-attention layers, KV4x256, MTPmax5, DFlash unsupported; configured1M ceiling not4090 capacity evidence.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "N02",
    "repository": "tensorninja/ninfer-4090",
    "commit": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
    "path": "src/targets/qwen3_8_27b/impl/variant.h",
    "lines": [
      16,
      48
    ],
    "git_blob_sha": "be35018217346c6bff76f9a1c80fdbf97ab1c454",
    "url": "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8_27b/impl/variant.h#L16-L48",
    "observed": "Already has131072-row optimized draft head and closed compile-time target leaves.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "N03",
    "repository": "tensorninja/ninfer-4090",
    "commit": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
    "path": "src/targets/qwen3_6_35b_a3b/impl/config.h",
    "lines": [
      60,
      120
    ],
    "git_blob_sha": "bb13a6e538b062a7d402fefa0dda4997c1cf7079",
    "url": "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_6_35b_a3b/impl/config.h#L60-L120",
    "observed": "35B DFlash supported, different geometry/features; cannot flip27B flag to reuse checkpoint.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "N04",
    "repository": "tensorninja/ninfer-4090",
    "commit": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
    "path": "src/targets/qwen3_8/impl/runtime/dflash_context.h",
    "lines": null,
    "git_blob_sha": "9482c0e7e210040985f374e21ca5b4dde0d9e81f",
    "url": "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/runtime/dflash_context.h",
    "observed": "Existing local/full DFlash state and feature buffers, not arbitrary27B DFlash2.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "N05",
    "repository": "tensorninja/ninfer-4090",
    "commit": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
    "path": "src/targets/qwen3_8/impl/runtime/schedule.h",
    "lines": [
      28,
      160
    ],
    "git_blob_sha": "509e6f9e30148b7671a78c5f331f317ca6191e66",
    "url": "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/runtime/schedule.h#L28-L160",
    "observed": "TargetVerifyFrameView, target_verify_accept, replay_records, no speculation in decision pass.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "N06",
    "repository": "tensorninja/ninfer-4090",
    "commit": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
    "path": "include/ninfer/types.h",
    "lines": [
      50,
      74
    ],
    "git_blob_sha": "94b16bab36abc759baad1c1332418c512a3968fc",
    "url": "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/include/ninfer/types.h#L50-L74",
    "observed": "Startup SpeculativeOptions supports None/Mtp/DFlash; request-level auto policy not existing.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "N07",
    "repository": "tensorninja/ninfer-4090",
    "commit": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
    "path": "src/ops/launcher/gqa_attention_decode.cu",
    "lines": [
      1,
      155
    ],
    "git_blob_sha": "bdfbe705521e2f1f77224cbc8195408ae0f11ce9",
    "url": "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/ops/launcher/gqa_attention_decode.cu#L1-L155",
    "observed": "Small-T1..6 and split envelope policy exist; not a generic add-FlashAttention problem.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "N08",
    "repository": "tensorninja/ninfer-4090",
    "commit": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
    "path": "src/targets/qwen3_8/impl/runtime/program.h",
    "lines": [
      1,
      180
    ],
    "git_blob_sha": "129dd6cc87fe9e61984f16e909b39fe7fcefcab2",
    "url": "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/runtime/program.h#L1-L180",
    "observed": "Owned lane/request plans, GDN replay, retained states and bounded entitlement.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "N09",
    "repository": "tensorninja/ninfer-4090",
    "commit": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
    "path": "LICENSE",
    "lines": [
      1,
      35
    ],
    "git_blob_sha": "261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64",
    "url": "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/LICENSE#L1-L35",
    "observed": "NInfer is Apache2.0; does not automatically license external checkpoints.",
    "evidence_level": "SOURCE_READ_NOT_EXECUTED"
  },
  {
    "id": "R01",
    "url": "https://aclanthology.org/2026.acl-long.83/",
    "observed": "Publisher abstract: LongSpec constant-sized draftKV, position indices, attention aggregation. No27B256K reproduction here.",
    "evidence_level": "PRIMARY_ABSTRACT_OR_CATALOG_NOT_REPRODUCED"
  },
  {
    "id": "R02",
    "url": "https://aclanthology.org/2026.findings-acl.2153/",
    "observed": "Publisher abstract: SpecExtend target-guided draft-context retrieval, including16K evaluation; not direct draftKV reconstruction.",
    "evidence_level": "PRIMARY_ABSTRACT_OR_CATALOG_NOT_REPRODUCED"
  },
  {
    "id": "R03",
    "url": "https://proceedings.mlr.press/v306/lee26d.html",
    "observed": "Publisher search entry: Dustin sparse verification, numerical/accuracy tradeoffs. Page open unavailable here; not an exactness authority or release dependency.",
    "evidence_level": "PRIMARY_ABSTRACT_OR_CATALOG_NOT_REPRODUCED"
  },
  {
    "id": "R04",
    "url": "https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2",
    "observed": "Model catalog existence corroborated by original DFlash project and model search. Full immutable checkpoint/tensor manifest NOT downloaded; asset gate mandatory.",
    "evidence_level": "PRIMARY_ABSTRACT_OR_CATALOG_NOT_REPRODUCED"
  }
]
````
<!-- payload-end -->
