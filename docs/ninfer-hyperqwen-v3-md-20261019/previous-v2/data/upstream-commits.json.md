# V2 支撑材料：`data/upstream-commits.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: data/upstream-commits.json -->
<!-- payload-sha256: 419bd9f24ff4c3c3ef448d90305d46fbd91292c7b74c87d90319538cdf7ce974 -->
<!-- payload-bytes: 13969 -->

<!-- payload-begin -->
````json
[
  {
    "id": "U01",
    "sha": "68da38efea0a8c08071e1f11b3aefdc1f8ee7692",
    "date_utc": "2026-09-07",
    "title": "Responses prefill progress",
    "phase": "P1",
    "scope": "SSE progress; OutputSink/StreamSink forwarding",
    "resolution": "Keep prepare timers and add progress callbacks; no fake token deltas",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/68da38efea0a8c08071e1f11b3aefdc1f8ee7692"
  },
  {
    "id": "U02",
    "sha": "8921981617fc96b2b26ff8d099608bc008239b26",
    "date_utc": "2026-09-08",
    "title": "Hermes tool-call dialect",
    "phase": "P1",
    "scope": "Parser object/string/null arguments",
    "resolution": "Preserve correctness, later streaming parser supersedes implementation",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/8921981617fc96b2b26ff8d099608bc008239b26"
  },
  {
    "id": "U03",
    "sha": "c55dcf359730c0d2e6c310f670966c25cf67870b",
    "date_utc": "2026-09-08",
    "title": "Unclosed think tool recovery",
    "phase": "P1",
    "scope": "Output terminalization",
    "resolution": "Do not flush tool region to reasoning too early",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/c55dcf359730c0d2e6c310f670966c25cf67870b"
  },
  {
    "id": "U04",
    "sha": "4040222bf1396fea9102ecd994e9c6d22b32beff",
    "date_utc": "2026-09-10",
    "title": "Committed-token repetition guard",
    "phase": "P1",
    "scope": "Generation policy and finish reasons",
    "resolution": "Import together with 995f4a2 and 15fd064; parity can disable guard",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/4040222bf1396fea9102ecd994e9c6d22b32beff"
  },
  {
    "id": "U05",
    "sha": "995f4a25804316d974f16cfc31259aed5ee2d120",
    "date_utc": "2026-09-10",
    "title": "Round-scoped fault recovery",
    "phase": "P1",
    "scope": "Executor and row-commit contract",
    "resolution": "Fail all affected round lanes, not queue or entire healthy engine",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/995f4a25804316d974f16cfc31259aed5ee2d120"
  },
  {
    "id": "U06",
    "sha": "c406bc0d9333f200e3529ff399765648f21fe50d",
    "date_utc": "2026-09-16",
    "title": "Explicit alias kind and atomic publication",
    "phase": "P1",
    "scope": "L2/L3 alias ownership",
    "resolution": "Do not restore name-prefix based kind detection",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/c406bc0d9333f200e3529ff399765648f21fe50d"
  },
  {
    "id": "U07",
    "sha": "3c3904a49b7e269521711d7c49c7c030af0dc014",
    "date_utc": "2026-09-16",
    "title": "Explicit prompt-cache breakpoints",
    "phase": "P1",
    "scope": "Template/processor/runtime/HTTP boundary model",
    "resolution": "Use ordered boundaries and explicit-cut LCP semantics",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/3c3904a49b7e269521711d7c49c7c030af0dc014"
  },
  {
    "id": "U08",
    "sha": "c02acc999a85155f46ab26294c17afb5b15de4b1",
    "date_utc": "2026-09-16",
    "title": "Frontier and session payload deduplication",
    "phase": "P1",
    "scope": "Publication parent identity",
    "resolution": "Same payload parent for both aliases",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/c02acc999a85155f46ab26294c17afb5b15de4b1"
  },
  {
    "id": "U09",
    "sha": "15fd064b86721f038124e8b89f9fe4628af6c369",
    "date_utc": "2026-09-16",
    "title": "Accept repetition-cycle decoder limit",
    "phase": "P1",
    "scope": "Output licensing",
    "resolution": "Mandatory companion to guard",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/15fd064b86721f038124e8b89f9fe4628af6c369"
  },
  {
    "id": "U10",
    "sha": "94cdb5a975e514935ed4be214ee7f776a8683635",
    "date_utc": "2026-09-17",
    "title": "One segmented prompt encoding",
    "phase": "P1",
    "scope": "Tokenizer/processor/custom B0+B1 conflict",
    "resolution": "Keep segmented API; integrate B0 scanner, memo and counters",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/94cdb5a975e514935ed4be214ee7f776a8683635"
  },
  {
    "id": "U11",
    "sha": "4d3366e5b9a959627a6db1f0eb36932be0482def",
    "date_utc": "2026-09-17",
    "title": "Prefill admission and asynchronous exports",
    "phase": "P2",
    "scope": "Scheduler, lane lifetime, CUDA streams",
    "resolution": "Keep export fencing and measure total export cost separately",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/4d3366e5b9a959627a6db1f0eb36932be0482def"
  },
  {
    "id": "U12",
    "sha": "16d4318a20048d6f9af3ce890849741570b26bbe",
    "date_utc": "2026-09-17",
    "title": "Admission/decode/swarm benchmark drivers",
    "phase": "P3",
    "scope": "Benchmarks; LoRA split-K cap",
    "resolution": "Keep benchmark creation signatures coherent",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/16d4318a20048d6f9af3ce890849741570b26bbe"
  },
  {
    "id": "U13",
    "sha": "53ca151f2b986b2eda1643884e230acf59b71346",
    "date_utc": "2026-09-17",
    "title": "Q5 residual small-T tensor-core route",
    "phase": "P3",
    "scope": "Shared row-split MMA; linear_add",
    "resolution": "Import kernel, plan, tests and CMake as a bundle",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/53ca151f2b986b2eda1643884e230acf59b71346"
  },
  {
    "id": "U14",
    "sha": "ec52a2434bade0fa64ed6c3b9668928c6bebcb32",
    "date_utc": "2026-09-17",
    "title": "Q4 SwiGLU small-T tensor-core route",
    "phase": "P3",
    "scope": "linear_swiglu",
    "resolution": "Preserve fork skip77 while enforcing real GPU gates",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/ec52a2434bade0fa64ed6c3b9668928c6bebcb32"
  },
  {
    "id": "U15",
    "sha": "16a586ec4dcc594978a0cc6f3e010a90d7610dcc",
    "date_utc": "2026-09-17",
    "title": "Q4/Q5 attention/GDN small-T routes",
    "phase": "P3",
    "scope": "Projection plans and composed convolution",
    "resolution": "Do not keep deleted fused snapshot scheduling alive",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/16a586ec4dcc594978a0cc6f3e010a90d7610dcc"
  },
  {
    "id": "U16",
    "sha": "3b6e5c4d769410a4fe15a220e541e3f55794de7c",
    "date_utc": "2026-09-17",
    "title": "Small-T performance documentation",
    "phase": "P3",
    "scope": "Performance methodology",
    "resolution": "Treat upstream timings as upstream observations, not local claims",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/3b6e5c4d769410a4fe15a220e541e3f55794de7c"
  },
  {
    "id": "U17",
    "sha": "f4089901fa17b83ecbb21bd2bde17bf614c3bf03",
    "date_utc": "2026-09-23",
    "title": "Incremental tool calls across protocols",
    "phase": "P3",
    "scope": "Serving interfaces; upstream log schema20",
    "resolution": "Preserve fork prepare_detail without reverting stream lifecycle",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/f4089901fa17b83ecbb21bd2bde17bf614c3bf03"
  },
  {
    "id": "U18",
    "sha": "0669b29b67e3e0965e980af9ad74d2cc02448ca3",
    "date_utc": "2026-09-30",
    "title": "Segmented mixers and pointer head",
    "phase": "P4",
    "scope": "A4, conv/GDN, gather, pointer-head Ops",
    "resolution": "Keep branch isolation and independent numeric oracle",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/0669b29b67e3e0965e980af9ad74d2cc02448ca3"
  },
  {
    "id": "U19",
    "sha": "ab221dc13cc856fb006df928d16390ba7de73723",
    "date_utc": "2026-09-30",
    "title": "System One decisions on shared runtime",
    "phase": "P4",
    "scope": "Decision adapters, A16 phase, API schema21",
    "resolution": "Code integrated; production decision adapters remain opt-in",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/ab221dc13cc856fb006df928d16390ba7de73723"
  },
  {
    "id": "U20",
    "sha": "772b88117867862d9669f4d970929242872bfabe",
    "date_utc": "2026-09-30",
    "title": "Midrise 4-bit KV and BF16 own branches",
    "phase": "P4",
    "scope": "KV ABI and startup codec change",
    "resolution": "Explicit rk4v4 migration; old image/cache retained for rollback",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/772b88117867862d9669f4d970929242872bfabe"
  },
  {
    "id": "U21",
    "sha": "a120e983938959019d215bb3085604160717c304",
    "date_utc": "2026-09-30",
    "title": "Restore 35B-A3B package build",
    "phase": "P4",
    "scope": "Artifact identity and variant workspace",
    "resolution": "Both-package compile gate; no fake 35B GPU qualification",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/a120e983938959019d215bb3085604160717c304"
  },
  {
    "id": "U22",
    "sha": "a0fd3285ac6833cb2072442813c4686b6b67ff5e",
    "date_utc": "2026-09-30",
    "title": "Schema22 and non-starving telemetry",
    "phase": "P4",
    "scope": "Snapshots, adapter residency and decision counters",
    "resolution": "Extend upstream fields; do not reintroduce execution-mutex reads",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/a0fd3285ac6833cb2072442813c4686b6b67ff5e"
  },
  {
    "id": "U23",
    "sha": "a4575864a290b40d01c30961e9b4f9dc6e937792",
    "date_utc": "2026-09-30",
    "title": "Correct LoRA negative restore fixture",
    "phase": "P4",
    "scope": "L2 test isolation",
    "resolution": "Separate legitimate cache hit from adapter identity leak",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/a4575864a290b40d01c30961e9b4f9dc6e937792"
  },
  {
    "id": "U24",
    "sha": "efec0fdc586dfa4ef0baa78e142527df154a3f9a",
    "date_utc": "2026-09-30",
    "title": "Dual-system dashboard",
    "phase": "P4",
    "scope": "Web records, derive and panels",
    "resolution": "Preserve historical-log parsing and fork timer visibility",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/efec0fdc586dfa4ef0baa78e142527df154a3f9a"
  },
  {
    "id": "U25",
    "sha": "5942a8249b2394bd3a4e9be5a303d61dfecded9a",
    "date_utc": "2026-09-30",
    "title": "Mixed chat/decision benchmark",
    "phase": "P4",
    "scope": "Shared-thread interference measurement",
    "resolution": "Use client output rate, not only per-round rate",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/5942a8249b2394bd3a4e9be5a303d61dfecded9a"
  },
  {
    "id": "U26",
    "sha": "f1b32f91ed7b933515fd00c8dd86d716275ef722",
    "date_utc": "2026-09-30",
    "title": "Two-system README",
    "phase": "P4",
    "scope": "Documentation",
    "resolution": "Keep local deployment profile distinct from upstream example",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/f1b32f91ed7b933515fd00c8dd86d716275ef722"
  },
  {
    "id": "U27",
    "sha": "29d13e3d99491ed82e7be4edc801d92a59643cea",
    "date_utc": "2026-09-30",
    "title": "Replace malformed generated UTF-8",
    "phase": "P4",
    "scope": "Incremental output decoder",
    "resolution": "Do not relax strict input tokenizer validation",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/29d13e3d99491ed82e7be4edc801d92a59643cea"
  },
  {
    "id": "U28",
    "sha": "897652a368312d8e2dd5028c0fbcd19428f3d5f0",
    "date_utc": "2026-09-30",
    "title": "TypeSafe answer shapes documentation",
    "phase": "P5",
    "scope": "Protocol docs",
    "resolution": "Preserve protocol-owned answer shapes and confidence semantics",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/897652a368312d8e2dd5028c0fbcd19428f3d5f0"
  },
  {
    "id": "U29",
    "sha": "ed8e548b1fafa97421218bf3a348db3a7dd54d7a",
    "date_utc": "2026-09-30",
    "title": "TypeSafe prefix renamed to /typesafe",
    "phase": "P5",
    "scope": "Routes, smoke clients and docs",
    "resolution": "Old /systemone returns404; no implicit alias",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/ed8e548b1fafa97421218bf3a348db3a7dd54d7a"
  },
  {
    "id": "U30",
    "sha": "9570a58d87182e4a5ff1ee165a8018e8ac20fad1",
    "date_utc": "2026-09-30",
    "title": "System One playground",
    "phase": "P5",
    "scope": "Web application",
    "resolution": "No dashboard required in weightless production image",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/9570a58d87182e4a5ff1ee165a8018e8ac20fad1"
  },
  {
    "id": "U31",
    "sha": "13aabb7bcb3302b4c7e3bebd9722063fe56f3b33",
    "date_utc": "2026-10-01",
    "title": "Structured primitive presets",
    "phase": "P5",
    "scope": "Playground fixtures",
    "resolution": "Preserve ordered data and large integer text",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/13aabb7bcb3302b4c7e3bebd9722063fe56f3b33"
  },
  {
    "id": "U32",
    "sha": "4e570b79230f032c5531a196023c9c066501ac5c",
    "date_utc": "2026-10-07",
    "title": "a human is still here",
    "phase": "P5",
    "scope": "Repository documentation",
    "resolution": "Carry as upstream history; no performance claim",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/4e570b79230f032c5531a196023c9c066501ac5c"
  },
  {
    "id": "U33",
    "sha": "ab7ada97c4a28b9b26bad0c0cdacb282fe8ca2fc",
    "date_utc": "2026-10-07",
    "title": "OpenAI Decisions and dual protocols",
    "phase": "P5",
    "scope": "Native schemas and discovery; schema23",
    "resolution": "Do not implement OpenAI by lossy TypeSafe translation",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/ab7ada97c4a28b9b26bad0c0cdacb282fe8ca2fc"
  },
  {
    "id": "U34",
    "sha": "5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
    "date_utc": "2026-10-07",
    "title": "Image decisions and image-aware playground",
    "phase": "P5",
    "scope": "Vision preprocessing, state identity; schema24",
    "resolution": "Final snapshot6/continuation5/decision-alias2; image feature gated",
    "source": "https://github.com/tensorninja/ninfer-4090/commit/5b99996bc7c1fe6ff27f271a205eb605302ec8bb"
  }
]
````
<!-- payload-end -->
