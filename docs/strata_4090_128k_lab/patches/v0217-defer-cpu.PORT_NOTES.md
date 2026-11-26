# Port of upstream Strata PR #2690 (STRATA_VERIFY_DEFER_CPU) onto v0.2.17 + STRATA_VERIFY_ECAP

Base: `a/` (v0.2.17, engine 0.1.63, ECAP patch applied). Result: `b/`. Patch: `v0217-defer-cpu.patch`
(`diff -ruN a b`, timestamps stripped; checked: `patch -p1 -F0 -N --batch` on a fresh copy of `a/` reproduces `b/`,
`diff -r` clean). Nothing was compiled or run (no CUDA here; see the test plan).

Line numbers below are in `b/`.

2026-11-25: the patch no longer carries the PR's `docs/DETAILS.md` hunk (documentation only). `upgrade_gate.py prepare` exports only `engine/` and `terminal/`, so that hunk made the zero-fuzz dry run fail. The first 4090 build also failed: `defer_ok` named `kVerifyMaxT` unqualified (it lives in `strata::kernels`); it now uses `strata::kernels::kVerifyMaxT`, as the rest of verify.cpp does.

## 1. PR hunks

| PR file / hunk | Status | Where in b/ | Note |
|---|---|---|---|
| expert_source.hpp GpuPlanSink weights/heavy/partial | applied | include/strata/core/expert_source.hpp:416-421 | context drift only |
| peer_experts.hpp/.cpp set_pool_gpu_helper / pool_gpu_helper | applied | peer_experts.hpp:35-39, peer_experts.cpp:26-28 | |
| verify.hpp members, raise_partial, defer_ok, heavy_layer | adapted (rejected: `groups_` is `[kVerifyLongT + 1]` in v0.2.17) | include/strata/core/verify.hpp:753, 758-772 | same text |
| verify_kernels.hpp decls | applied | include/strata/kernels/verify_kernels.hpp:119-132 | |
| verify_kernels.cu defer_add_rows / fill_zero / copy_rows_by_weight | applied | src/kernels/cuda/verify_kernels.cu:1736-1814 | arithmetic re-checked against v0.2.17 fused_gr.cu (`fmaf(bo, 2*sigmoid(inj/HC), R)`) and combine order; no name clash |
| expert_source.cpp heavy-first job order + partial hook | adapted (rejected) | src/core/expert_source.cpp:~5770-5817 | see 2.1 |
| verify.cpp release_gpu_waits + h_pflag_ | applied | verify.cpp:667 | |
| verify.cpp trace_dump names | adapted | verify.cpp:696-699 | v0.2.17 has 34 entries ("router done" at 33): [15]="out-proj", [16]="late rows" |
| verify.cpp diag "heavy rows (P)" | applied | verify.cpp:751-754 | |
| verify.cpp ~Verifier hosts + h_pflag_ | adapted | verify.cpp:822-823 | list now ends `h_bal_, h_ecap_, h_pflag_` (ECAP) |
| init: env read, PCIe-balance refusal, BELOW parse, helper turn-off | applied | verify.cpp:1029-1078 | before mapped staging, as PR |
| init: h_pflag_ mapped alloc | applied | verify.cpp:1097 | after ECAP's `h_ecap_`/`h_ymiss_` |
| init: taps refusal | applied | verify.cpp:1172-1178 | |
| init: `sink_.heavy` | applied | verify.cpp:1228 | |
| init: `def_parts_` carve (last, layout unchanged when off) | applied | verify.cpp:1281 | |
| init: start-up lines + device-plan turn-off | applied | verify.cpp:1496-1523 | device_plan_ is decided before this point (1468) |
| record_window: dfr / deferred / heavy / late_add | applied | verify.cpp:1599-1645 | after `groups_[T] = G` |
| record_window: `stamp(l,15)` + late_add in pre(l+1) | applied | verify.cpp:2513-2516 | right after the out-proj try/catch, before stamp 16 / FFN-side read |
| record_window: doorbell `\|\| heavy` | applied | verify.cpp:2613 | see 2.4 (HIP doorbell_store branch) |
| record_window: post(l) deferred branch | applied | verify.cpp:2783-2794 | before the device_plan_/fuse_rows branches |
| record_window: =check late_add after combine | applied, **placement fixed by hand** | verify.cpp:2852-2855 | fuzzy patch had put it inside the `remote_opt_->combine(...)` argument list; moved after the full statement |
| profile_report names | adapted | verify.cpp:3083-3084 | v0.2.17 names "plan+bell" and adds [33] |
| profile_by_t_report names | added (not in PR) | verify.cpp:3023-3024 | post-PR function, same index meaning, kept consistent |
| defer_ok / heavy_layer / capture line | adapted (rejected: `exec_[sel_long_][T]`) | verify.cpp:3126-3180 | + one exclusion, see 2.2 |
| stage_inputs: reset h_pflag_ | applied, **placement fixed by hand** | verify.cpp:3505 | fuzz had dropped it inside a GDN call in commit code; moved after the ECAP reset |
| run: sink_.weights/partial per layer | applied | verify.cpp:3981-3986 | |
| run: raise h_pflag_ before `*flag = want` | applied | verify.cpp:4025 | |
| raise_partial | adapted | verify.cpp:4297-4304 | `_mm_sfence()` -> `strata_store_fence()` (v0.2.17 portability wrapper used by every other raise) |
| run_slot_rows / batch_serve: sink_ reset | applied | verify.cpp:5342-5343, 5564-5565 | |
| diag_pipelined " P %u" | applied | verify.cpp:~5746 | |
| service: weights/partial + pflag raise | applied | verify.cpp:5926-5930, 5950 | |
| generate.cpp set_pool_gpu_helper | applied | src/program/generate.cpp:9817-9819 | after `drive.d.peer`, before any Verifier::init |
| docs/DETAILS.md section | applied + adapted | docs/DETAILS.md:1747- | blank line before heading; exclusion list gains windows past kVerifyMaxT. PR's two `<!-- TODO before the PR -->` comments kept verbatim |
| tests | none in PR | - | nothing to port |

## 2. Interactions with post-PR v0.2.17 code

### 2.1 Pool: MAXT continuation jobs (expert_source.cpp:~5786-5801)
v0.2.17 splits an expert routed to more than MAXT tokens (windows of 9..16 rows) into several jobs and `job_of[e]` keeps
only the last one. The PR marked heavy jobs via `heavy_job[job_of[ids[i]]]`, which would leave an earlier job of a heavy
expert in the light pass -> its heavy rows written after the partial flag -> GPU reads them early (silent wrong rows).
Port classifies each job by its own output rows (`(jb.out[r] - out) / H`), so every job holding a heavy row runs
first. (Deferral is off for T > kVerifyMaxT anyway, see 2.2, so this matters only if that exclusion is lifted, but it is
the correct form either way.) `run_split_multi_native` keeps v0.2.17's `arithmetic` argument in `run_jobs`.
`ExpertPool::kMaxSplitMulti` (=96) exists in v0.2.17 `pool.hpp` (not in this tree's copy; checked in the fetched
v0.2.17 header). 149-cold zero-copy `nj.fmt` points into `d.zc_fmt[original jo]`, which reordering does not touch.

### 2.2 Windows past kVerifyMaxT (record_window G, verify.cpp:1558)
v0.2.17 runs `T > kVerifyMaxT` (`--lookup-max-t`) as two token groups even without `--spec-split`. The PR excludes
two-group windows only via `split_`. **Added** to defer_ok (verify.cpp:3138): `T > kVerifyMaxT` -> no deferral, one
start-up line ("a window past the token group's rows ..."). Not in production (`--lookup-max-t 0`, `--spec 4` -> T <= 5).

### 2.3 ECAP (STRATA_VERIFY_ECAP)
ECAP code untouched. It rewrites `ids_`/`w_` on the GPU before plan + doorbell; the GPU heavy test (`w_`) and the pool's
(`h_w_` from the doorbell) read the same post-ECAP weights, so the split is consistent. Dropped entries carry weight 0
-> light. With DEFER unset ECAP's path is byte-identical (h_pflag_ stays null, no new graph nodes).

### 2.4 HIP `STRATA_DOORBELL_STORE` branch (verify.cpp:2602-2606)
The `|| heavy` publish is in the `else` of the HIP-only `g_doorbell_store` branch. That branch calls
`doorbell_publish_value(..., w_ + tb*K, ..., m_w_ + tb*K, ...)`, which publishes the weights too -> no exclusion needed.
CUDA builds never take it.

### 2.5 Others checked, compatible
- STRATA_ROUTE_TAIL_SKIP (kind -2): rows memset in the job-building loop, before any job runs or the partial hook -> zero
  rows for both copies.
- STRATA_ADAPT_OVERLAP gate: `adapt_gate_wait(l)` precedes the pool call; adapt copies are on their own stream, nothing
  in them waits on the current window -> no new wait cycle. Flag A still gates VRAM reads.
- STRATA_SIDE_MIXER=2: both side branches join before out-proj, i.e. before stamp 15 / late_add.
- sh_fork_late, BW-5 L2 prefetch fork, qdedup, PDL (`fill_zero` is a kernel node, keeps the kernel chain), early PLE
  flags (ar_on only), `sel_long_` graph variants (each captured through the same record_window/defer_ok).
- Batch windows, `--batch-mtp`, slot runs, pipelined groups' batch graphs: `batch_rec_` -> excluded; their pool calls
  reset `sink_.weights/partial`.
- Pipelined single windows (`pl_launch`/`service`): PR's service hooks ported.
- Adaptive tier with `doorbell_publish_res` skipping all-resident layers: with heavy the window uses `doorbell_publish`
  (as `always_publish_`), so `h_w_` is always fresh where the pool reads it.
- Stage split / `drive_pool_split`: per-stage sink, last layer of each stage never deferred.

### 2.6 Behaviour with STRATA_VERIFY_DEFER_CPU unset
No allocation (`h_pflag_`, `def_parts_` null; carve layout unchanged), `dfr == false` -> no new graph node, kernel or
doorbell choice change; pool: `heavy == false` -> `nfirst == njobs`, one `run_jobs` call identical to the old
`if (njobs > 0 && npend == 0)` block. Host: `sink_.weights/partial` stay null, pflag raise skipped (null).
Only differences: (a) one extra `stamp(l, 15)` that is a no-op unless STRATA_VERIFY_PROFILE / STRATA_VERIFY_TRACE (PR's
documented exception; profile columns: "out-proj" moves to slot 15, slot 16 "late rows" ~0); (b) diag/trace text;
(c) `set_pool_gpu_helper` stores a pointer. If `STRATA_VERIFY_DEFER_CPU_BELOW` is set alone, one stderr line.

## 3. Production trace (single RTX 4090, the --serve line and env given)

| Exclusion | Production value | Result |
|---|---|---|
| batch_rec_ | no `--batch` (o.batch <= 0) | solo windows |
| split_ / T > kVerifyMaxT | no `--spec-split`; `--spec 4` -> T <= 5; `--lookup-max-t 0` | G = 1 |
| remote_opt_ | no `--remote-expert-opt` | ok |
| STRATA_PCIE_BALANCE (m_bal_/bal_) | env unset (generate.cpp:5372-5375 needs "1") | ok |
| taps | no dflash2 / STRATA_TAP_FILE | ok |
| ar_on() | ~77% VRAM hit -> not all-resident | ok |
| control vector | none | ok |
| device_plan_ | STRATA_VERIFY_DEVICE_PLAN unset | split stays on |
| pool_gpu_helper | no --peer-device / --expert-cache-device1..3 | split stays on |
| STRATA_COLD_OVERLAP | unset -> 4 for the Linux in-place GGUF, else 0; npend > 0 only for 1-3 | split on |
| set_always_publish | only piped groups (needs --batch) / pipeline | n/a |
| HIP doorbell_store | CUDA | n/a |
| stage | one stage, all layers; last layer exact; layer 0 not deferred (PLE at layer 1, `--ple-io direct`) | layers 1..L-2 deferred |

Conclusion (static reading): with `STRATA_VERIFY_DEFER_CPU=1` deferral **is active** in the production config, with the
heavy/light split at 0.1 on. Start-up should print `STRATA_VERIFY_DEFER_CPU=1 (changes the output)...`,
`STRATA_VERIFY_DEFER_CPU_BELOW=0.1 (the default)...` and `capturing the N-token window (...), deferred`; a
`runs without deferral (...)` line means an exclusion hit. No production feature conflicts were found.
Cost to note: with heavy on, every layer's doorbell copies the activation to the host even when all its experts are
resident (`doorbell_publish` instead of `doorbell_publish_res`).

## 4. Unsure spots (review these first)
1. verify.cpp:2513-2516 / 1621-1645: late_add adds to `R_` after pre(l+1)'s attention-side read has folded layer l's
   pending write. Relies on v0.2.17's hc read still folding `bo_`/`inj2_` into `R` there for every mixer variant
   (side mixer, qdedup, QSA rows, GR_UP75, GU_SWIGLU). Read, not run.
2. expert_source.cpp:~5786-5801: own heavy-job classification (2.1) - diverges from PR text.
3. verify.cpp:3138: added `T > kVerifyMaxT` exclusion (2.2).
4. verify.cpp:2783-2794 with `hits_in_combine`/`fuse_hits` variants: needs zeros at GPU rows in `parts_out`;
   copy_rows_by_weight/fill_zero give that (same contract as copy_rows_from_mapped). fuse_rows (STRATA_FUSE_WAIT) is
   bypassed for deferred layers - intended.
5. verify.cpp:4298 `strata_store_fence()` instead of `_mm_sfence()`.
6. verify.cpp:1517 `cudaFreeHost(h_pflag_)` on the device-plan turn-off happens after `sink_` was set up; nothing
   captured yet, so no graph holds `m_pflag_` (as PR).

## 5. New environment variables
- `STRATA_VERIFY_DEFER_CPU` = `1` (defer, changes output) | `check` (same steps, rows added back in the same layer) |
  unset/`0` (off). Other values: one line, off.
- `STRATA_VERIFY_DEFER_CPU_BELOW` = weight `w` > 0 (default 0.1 with DEFER on); `w >= 1`: every CPU row late, no split.

## 6. Test plan (not run: no CUDA, 2-core/1 GB host)
Build: the usual CUDA build of engine (no new files, no CMake change).
CPU-side unit tests that touch changed files (should be unchanged): file_expert_source_test, split_lend_complement_test,
batch_rows_test, conv_cache_test, spec_prob_test, conversation_* tests, ecap_parity (ECAP unchanged).
GPU, in order:
1. DEFER unset: same prompt + seed, logits/tokens byte-identical to the unpatched build (with and without
   STRATA_VERIFY_ECAP); STRATA_VERIFY_PROFILE shows "late rows" ~0.
2. `STRATA_VERIFY_DEFER_CPU=check` (BELOW unset and BELOW=1): teacher-forced KL vs default within default run-to-run
   noise -> checks copy + arithmetic of late_add and copy_rows_by_weight.
3. `=1`, BELOW=1 and BELOW unset (0.1): start-up lines show "deferred"; KL vs default (tail-skip section protocol);
   decode tok/s interleaved pairs at low and ~100K context; STRATA_DECODE_TIMING waitCPU should drop.
4. `=1` + STRATA_VERIFY_ECAP on: KL and no stall.
5. Stall diagnostics: STRATA_VERIFY_TRACE=1 + a forced timeout shows `heavy rows (P)`; release_gpu_waits frees it.
6. Exclusions print one line each: STRATA_PCIE_BALANCE=1, STRATA_VERIFY_DEVICE_PLAN=1, `--lookup-max-t 16` with T > 8,
   `--batch`.
