# T13 independent review

Reviewer was not the author and did not edit the product tree.
Status: APPROVE_FOR_AUTHORIZED_RELEASE

This status allows a later explicit human authorization to start T12. It is not a completed release. G6 was not executed. G0 is not PASS.

## Blocking judgment

The temperature-0 d240 `prefix_reuse_path` split does not break the token contract and does not block a later authorized T12. `verdict.json` has an empty `token_mismatch`. `greedy_path_mismatch` has six rows, all `d240` indexes 1–6: old `full_reset`, new `restore_turn_checkpoint`. Prompt counts match calibration (index 1 is 246067, index 6 is 246532). The old rows have `hit=0`, `computed` equal to the full prompt, queue 106.384 / 107.368 / 110.250 / 112.122 / 111.828 / 110.211 seconds, and prefill about 149 seconds. The new rows have `hit` equal to the previous prompt minus 2, `computed=95`, and queue about 0.003 seconds, matching the healthy appends and the d240 temperature-1.0 lane. All four sample-lane paths match, including d240. `window.log` shows equal `pt=` on old and new, and 56 POSTs at HTTP 200. The judge recorded no `request_error`. Cold TTFT is prefill (d240 sample 149.877s vs 149.109s; prefill 145.228s vs 148.420s). Tokenize is the prepare drop (4.330s vs 0.304s).

## Other findings

G0 is not PASS. `b0-scanner` HEAD is `1dacb0f` and B0+B1 is committed. Eleven schema-20 files remain uncommitted and match `b0-evidence/http-window/overlay.patch` byte for byte, sha256 `579c0853f2ea690fd779861766f2530f213af2c990db023c3dfaeb2d01df01eb`. Dirty files outside that patch: `tests/CMakeLists.txt`, four LinearSwiGLU `return 77` propagations, plus untracked `g1_diff_main.cpp` and `Dockerfile.sm89-nobake` (sha256 `3f1fd17d…`). The six resource files and aggregate `c8afe487…` are in the fingerprint and in the G1 and CPU rows; that fingerprint file marks itself `LOCAL_BYTES_MEASURED_NOT_PRODUCTION_CERTIFIED`.

GPU numerical tests did not run and are not passes. The first ctest was 30 passed, 65 skipped, 7 failed, `CTEST_RC 8`. prefix/lora/request_log failed to load `libnvidia-ml.so.1`. The four SwiGLU tests printed `SKIP: no usable CUDA device` and then exited 1. The rerun passed `request_log` and skipped the other six with exit 77. Combined: 31 passed, 71 resource skips, 0 failed. The equivalence test skipped with 77 inside ctest because no resource directory was passed. The `/work/resources` run printed `V2-SC-06 scan_positions=49152 bytes=131072 tokens=16384`, then `EQUIV_DONE`; `classification.json` records exit 0.

G6 was not executed. `window.log` begins with `WINDOW_OPEN` and ends with `ROLLBACK_IMAGE sha256:9c2dec8b…`, `SMOKE_OK 270`, `ROLLBACK_CONFIRMED`. Candidate `e753e228…` was not left serving. There was no cutover.

The earlier HTTP window is not this ladder. `http-window/checklist.json` has `release_standard_10_6=not_met` because short index 4 changed path from `restore_turn_checkpoint` (hit 1417) to `append_frontier` (hit 1436) at equal `pt=1548`. The later frozen ladder did not reproduce that sample-lane split.

Selection and oracle isolation hold. After `merge_added_tokens_decoder`, buckets are built in ascending id order and scanned forward from `pos`; the first complete match in the bucket wins (earliest start, then lowest id). `V2-SC-01` expects `{300,99}` and `V2-SC-02` expects `{300}`. Empty content is rejected before indexing. `legacy_tokenizer.cpp` still uses `text.find` and does not call the new scanner. `legacy_encode_rendered_chat.cpp` still re-encodes the whole prefix. The simplified pre-T05 full-prefix loop is only the b0 measurement lane in `tests/.../bench_boundary_lanes.cpp`.

G1 compare passed and the mutation check failed closed. `diff-real.json` and `diff-synthetic.json` are `PASS` with `mismatches: []`, 25193 and 23613 rows. Both summaries use seed `20260925`, fuzz 20000, and resource aggregate `c8afe487…`. `mutation-sanity.txt` is `exit=1` on `FC-001#b1` field `semantic.token_ids[0]`.

Sample-lane append tokenize medians stay per depth, n=6: d32 0.914/0.039, d128 2.826/0.172, d192 4.052/0.250, d240 5.064/0.305. Cold hints are 18 and the last append is 24. CPU-lane numbers are `ANALYSIS_ONLY`, not this HTTP gate.

An authorized T12 would deploy image `sha256:e753e2283db78bbe2fe1fc92b9d45300a27fd5765b367c434c9023cbf2cb1cb3` and roll back to `sha256:9c2dec8b9ff087d178f72b68251ff7ff18c77330833eaade5b40bf4c49eb312b`. The uncommitted worktree is not a released source.
