# V2 支撑材料：`data/fork-files.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: data/fork-files.json -->
<!-- payload-sha256: 664dfdedfa9e5d8eb1a2426ca0697611a5d947ca2b59c1fd4bc7640dd67e4e79 -->
<!-- payload-bytes: 16628 -->

<!-- payload-begin -->
````json
[
  {
    "path": "Dockerfile.sm89-nobake",
    "status": "A",
    "additions": 43,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Keep weightless/no-dashboard image; add reproducible build labels and separate test stage",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/Dockerfile.sm89-nobake"
  },
  {
    "path": "evidence/b0/t00/base-check.json",
    "status": "A",
    "additions": 14,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Preserve immutable historical evidence; do not treat as current deployment proof",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/base-check.json"
  },
  {
    "path": "evidence/b0/t00/image_identity.json",
    "status": "A",
    "additions": 39,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Preserve immutable historical evidence; do not treat as current deployment proof",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/image_identity.json"
  },
  {
    "path": "evidence/b0/t00/overlay.patch",
    "status": "A",
    "additions": 347,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Preserve immutable historical evidence; do not treat as current deployment proof",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/overlay.patch"
  },
  {
    "path": "evidence/b0/t00/overlay.patch.sha256",
    "status": "A",
    "additions": 1,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Preserve immutable historical evidence; do not treat as current deployment proof",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/overlay.patch.sha256"
  },
  {
    "path": "evidence/b0/t00/resources-fingerprint.json",
    "status": "A",
    "additions": 31,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Preserve immutable historical evidence; do not treat as current deployment proof",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/resources-fingerprint.json"
  },
  {
    "path": "evidence/b0/t00/resources-manifest.json",
    "status": "A",
    "additions": 56,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Preserve immutable historical evidence; do not treat as current deployment proof",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/resources-manifest.json"
  },
  {
    "path": "evidence/b0/t00/source-audit.md",
    "status": "A",
    "additions": 31,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Preserve immutable historical evidence; do not treat as current deployment proof",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/source-audit.md"
  },
  {
    "path": "evidence/b0/t00/task-result.md",
    "status": "A",
    "additions": 17,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Preserve immutable historical evidence; do not treat as current deployment proof",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/task-result.md"
  },
  {
    "path": "evidence/b0/t00/untracked.txt",
    "status": "A",
    "additions": 1,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Preserve immutable historical evidence; do not treat as current deployment proof",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/untracked.txt"
  },
  {
    "path": "evidence/b0/t00/worktree-status.txt",
    "status": "A",
    "additions": 12,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Preserve immutable historical evidence; do not treat as current deployment proof",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/worktree-status.txt"
  },
  {
    "path": "include/ninfer/types.h",
    "status": "M",
    "additions": 11,
    "deletions": 0,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/include/ninfer/types.h"
  },
  {
    "path": "src/serve/generation_service.cpp",
    "status": "M",
    "additions": 22,
    "deletions": 3,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/generation_service.cpp"
  },
  {
    "path": "src/serve/generation_service.h",
    "status": "M",
    "additions": 14,
    "deletions": 0,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/generation_service.h"
  },
  {
    "path": "src/serve/http_server.cpp",
    "status": "M",
    "additions": 4,
    "deletions": 2,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/http_server.cpp"
  },
  {
    "path": "src/serve/request.h",
    "status": "M",
    "additions": 3,
    "deletions": 0,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/request.h"
  },
  {
    "path": "src/serve/request_log.cpp",
    "status": "M",
    "additions": 27,
    "deletions": 1,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/request_log.cpp"
  },
  {
    "path": "src/serve/request_log.h",
    "status": "M",
    "additions": 5,
    "deletions": 1,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/request_log.h"
  },
  {
    "path": "src/serve/responses_http.cpp",
    "status": "M",
    "additions": 3,
    "deletions": 2,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/responses_http.cpp"
  },
  {
    "path": "src/targets/qwen3_8/export/ninfer/targets/qwen3_8/prepared_prompt.h",
    "status": "M",
    "additions": 5,
    "deletions": 0,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/export/ninfer/targets/qwen3_8/prepared_prompt.h"
  },
  {
    "path": "src/targets/qwen3_8/impl/frontend/frontend.cpp",
    "status": "M",
    "additions": 25,
    "deletions": 2,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/frontend.cpp"
  },
  {
    "path": "src/targets/qwen3_8/impl/frontend/processor.cpp",
    "status": "M",
    "additions": 100,
    "deletions": 17,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/processor.cpp"
  },
  {
    "path": "src/targets/qwen3_8/impl/frontend/processor.h",
    "status": "M",
    "additions": 29,
    "deletions": 0,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/processor.h"
  },
  {
    "path": "src/targets/qwen3_8/impl/frontend/tokenizer.cpp",
    "status": "M",
    "additions": 52,
    "deletions": 7,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/tokenizer.cpp"
  },
  {
    "path": "src/targets/qwen3_8/impl/frontend/tokenizer.h",
    "status": "M",
    "additions": 33,
    "deletions": 0,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/tokenizer.h"
  },
  {
    "path": "tests/CMakeLists.txt",
    "status": "M",
    "additions": 60,
    "deletions": 0,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/CMakeLists.txt"
  },
  {
    "path": "tests/ops/linear_swiglu/test_nvfp4.cpp",
    "status": "M",
    "additions": 8,
    "deletions": 4,
    "both_sides_touched": false,
    "action": "Keep return77; mandatory sm89 tests may not skip",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/ops/linear_swiglu/test_nvfp4.cpp"
  },
  {
    "path": "tests/ops/linear_swiglu/test_q4_a16.cpp",
    "status": "M",
    "additions": 1,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Keep return77; mandatory sm89 tests may not skip",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/ops/linear_swiglu/test_q4_a16.cpp"
  },
  {
    "path": "tests/ops/linear_swiglu/test_q4_a8.cpp",
    "status": "M",
    "additions": 1,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Keep return77; mandatory sm89 tests may not skip",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/ops/linear_swiglu/test_q4_a8.cpp"
  },
  {
    "path": "tests/ops/linear_swiglu/test_w8_a16.cpp",
    "status": "M",
    "additions": 1,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Keep return77; mandatory sm89 tests may not skip",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/ops/linear_swiglu/test_w8_a16.cpp"
  },
  {
    "path": "tests/targets/qwen3_8/bench_boundary_lanes.cpp",
    "status": "A",
    "additions": 987,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/bench_boundary_lanes.cpp"
  },
  {
    "path": "tests/targets/qwen3_8/g1_diff_main.cpp",
    "status": "A",
    "additions": 1319,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/g1_diff_main.cpp"
  },
  {
    "path": "tests/targets/qwen3_8/legacy_oracle_main.cpp",
    "status": "A",
    "additions": 346,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/legacy_oracle_main.cpp"
  },
  {
    "path": "tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.cpp",
    "status": "A",
    "additions": 69,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Freeze tokenizer algorithm; isolate old boundary DTOs from new production headers",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.cpp"
  },
  {
    "path": "tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.h",
    "status": "A",
    "additions": 18,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Freeze tokenizer algorithm; isolate old boundary DTOs from new production headers",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.h"
  },
  {
    "path": "tests/targets/qwen3_8/reference/legacy_tokenizer.cpp",
    "status": "A",
    "additions": 738,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Freeze tokenizer algorithm; isolate old boundary DTOs from new production headers",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/reference/legacy_tokenizer.cpp"
  },
  {
    "path": "tests/targets/qwen3_8/reference/legacy_tokenizer.h",
    "status": "A",
    "additions": 63,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Freeze tokenizer algorithm; isolate old boundary DTOs from new production headers",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/reference/legacy_tokenizer.h"
  },
  {
    "path": "tests/targets/qwen3_8/test_boundary_encoding.cpp",
    "status": "A",
    "additions": 303,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/test_boundary_encoding.cpp"
  },
  {
    "path": "tests/targets/qwen3_8/test_encoding_restart.cpp",
    "status": "A",
    "additions": 357,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/test_encoding_restart.cpp"
  },
  {
    "path": "tests/targets/qwen3_8/test_legacy_oracle.cpp",
    "status": "A",
    "additions": 185,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/test_legacy_oracle.cpp"
  },
  {
    "path": "tests/targets/qwen3_8/test_tokenization_equivalence.cpp",
    "status": "A",
    "additions": 284,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/test_tokenization_equivalence.cpp"
  },
  {
    "path": "tests/targets/qwen3_8/test_tokenizer_work.cpp",
    "status": "A",
    "additions": 186,
    "deletions": 0,
    "both_sides_touched": false,
    "action": "Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/test_tokenizer_work.cpp"
  },
  {
    "path": "tests/test_request_log.cpp",
    "status": "M",
    "additions": 6,
    "deletions": 0,
    "both_sides_touched": true,
    "action": "Manual semantic review required; see conflict catalogue",
    "source": "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/test_request_log.cpp"
  }
]
````
<!-- payload-end -->
