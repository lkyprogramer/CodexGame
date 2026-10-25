# V2 支撑材料：`data/fork-files.csv`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: data/fork-files.csv -->
<!-- payload-sha256: 9b0025946d594fc0e469d856494121f7d9cad44bb7366c67e6a209ac673335ac -->
<!-- payload-bytes: 10843 -->

<!-- payload-begin -->
````csv
path,status,additions,deletions,both_sides_touched,action,source
Dockerfile.sm89-nobake,A,43,0,False,Keep weightless/no-dashboard image; add reproducible build labels and separate test stage,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/Dockerfile.sm89-nobake
evidence/b0/t00/base-check.json,A,14,0,False,Preserve immutable historical evidence; do not treat as current deployment proof,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/base-check.json
evidence/b0/t00/image_identity.json,A,39,0,False,Preserve immutable historical evidence; do not treat as current deployment proof,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/image_identity.json
evidence/b0/t00/overlay.patch,A,347,0,False,Preserve immutable historical evidence; do not treat as current deployment proof,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/overlay.patch
evidence/b0/t00/overlay.patch.sha256,A,1,0,False,Preserve immutable historical evidence; do not treat as current deployment proof,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/overlay.patch.sha256
evidence/b0/t00/resources-fingerprint.json,A,31,0,False,Preserve immutable historical evidence; do not treat as current deployment proof,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/resources-fingerprint.json
evidence/b0/t00/resources-manifest.json,A,56,0,False,Preserve immutable historical evidence; do not treat as current deployment proof,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/resources-manifest.json
evidence/b0/t00/source-audit.md,A,31,0,False,Preserve immutable historical evidence; do not treat as current deployment proof,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/source-audit.md
evidence/b0/t00/task-result.md,A,17,0,False,Preserve immutable historical evidence; do not treat as current deployment proof,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/task-result.md
evidence/b0/t00/untracked.txt,A,1,0,False,Preserve immutable historical evidence; do not treat as current deployment proof,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/untracked.txt
evidence/b0/t00/worktree-status.txt,A,12,0,False,Preserve immutable historical evidence; do not treat as current deployment proof,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/worktree-status.txt
include/ninfer/types.h,M,11,0,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/include/ninfer/types.h
src/serve/generation_service.cpp,M,22,3,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/generation_service.cpp
src/serve/generation_service.h,M,14,0,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/generation_service.h
src/serve/http_server.cpp,M,4,2,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/http_server.cpp
src/serve/request.h,M,3,0,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/request.h
src/serve/request_log.cpp,M,27,1,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/request_log.cpp
src/serve/request_log.h,M,5,1,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/request_log.h
src/serve/responses_http.cpp,M,3,2,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/responses_http.cpp
src/targets/qwen3_8/export/ninfer/targets/qwen3_8/prepared_prompt.h,M,5,0,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/export/ninfer/targets/qwen3_8/prepared_prompt.h
src/targets/qwen3_8/impl/frontend/frontend.cpp,M,25,2,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/frontend.cpp
src/targets/qwen3_8/impl/frontend/processor.cpp,M,100,17,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/processor.cpp
src/targets/qwen3_8/impl/frontend/processor.h,M,29,0,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/processor.h
src/targets/qwen3_8/impl/frontend/tokenizer.cpp,M,52,7,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/tokenizer.cpp
src/targets/qwen3_8/impl/frontend/tokenizer.h,M,33,0,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/tokenizer.h
tests/CMakeLists.txt,M,60,0,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/CMakeLists.txt
tests/ops/linear_swiglu/test_nvfp4.cpp,M,8,4,False,Keep return77; mandatory sm89 tests may not skip,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/ops/linear_swiglu/test_nvfp4.cpp
tests/ops/linear_swiglu/test_q4_a16.cpp,M,1,0,False,Keep return77; mandatory sm89 tests may not skip,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/ops/linear_swiglu/test_q4_a16.cpp
tests/ops/linear_swiglu/test_q4_a8.cpp,M,1,0,False,Keep return77; mandatory sm89 tests may not skip,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/ops/linear_swiglu/test_q4_a8.cpp
tests/ops/linear_swiglu/test_w8_a16.cpp,M,1,0,False,Keep return77; mandatory sm89 tests may not skip,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/ops/linear_swiglu/test_w8_a16.cpp
tests/targets/qwen3_8/bench_boundary_lanes.cpp,A,987,0,False,Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/bench_boundary_lanes.cpp
tests/targets/qwen3_8/g1_diff_main.cpp,A,1319,0,False,Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/g1_diff_main.cpp
tests/targets/qwen3_8/legacy_oracle_main.cpp,A,346,0,False,Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/legacy_oracle_main.cpp
tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.cpp,A,69,0,False,Freeze tokenizer algorithm; isolate old boundary DTOs from new production headers,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.cpp
tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.h,A,18,0,False,Freeze tokenizer algorithm; isolate old boundary DTOs from new production headers,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.h
tests/targets/qwen3_8/reference/legacy_tokenizer.cpp,A,738,0,False,Freeze tokenizer algorithm; isolate old boundary DTOs from new production headers,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/reference/legacy_tokenizer.cpp
tests/targets/qwen3_8/reference/legacy_tokenizer.h,A,63,0,False,Freeze tokenizer algorithm; isolate old boundary DTOs from new production headers,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/reference/legacy_tokenizer.h
tests/targets/qwen3_8/test_boundary_encoding.cpp,A,303,0,False,Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/test_boundary_encoding.cpp
tests/targets/qwen3_8/test_encoding_restart.cpp,A,357,0,False,Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/test_encoding_restart.cpp
tests/targets/qwen3_8/test_legacy_oracle.cpp,A,185,0,False,Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/test_legacy_oracle.cpp
tests/targets/qwen3_8/test_tokenization_equivalence.cpp,A,284,0,False,Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/test_tokenization_equivalence.cpp
tests/targets/qwen3_8/test_tokenizer_work.cpp,A,186,0,False,Retain and adapt to new boundary DTOs; run outside CTest drivers explicitly,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/test_tokenizer_work.cpp
tests/test_request_log.cpp,M,6,0,True,Manual semantic review required; see conflict catalogue,https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/test_request_log.cpp
````
<!-- payload-end -->
