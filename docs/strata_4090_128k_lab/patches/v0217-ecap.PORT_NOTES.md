# Port of upstream Strata PR #3545 (verify-window expert cap) onto v0.2.17

Patch: `v0217-ecap.patch` (applies to v0.2.17 + PT0 with `patch -p1 -F0`; `v0217-defer-cpu.patch` applies after it).
Env: `STRATA_VERIFY_ECAP=N` (N > top-k; unset or <= k: off, byte-identical path) and `STRATA_VERIFY_ECAP_READS=1`.

## Deviations from the PR

1. **Caps distinct experts, not entries.** Token 0 keeps all k picks; tail entries, by (weight desc, index asc), keep an
   expert already kept, keep a new one while fewer than N are kept, and the rest drop to weight 0.
2. **Dropped entries fold onto a kept expert**, a VRAM-resident one first (round robin), so a dropped entry never makes
   a CPU or PCIe job.
3. **Prompt reads are not capped.** The PR's only guard is `n > 1`, which would also cap the verify windows of prompt
   reads (`read_windows`, head sampling off). Here a mapped int (`h_ecap_`) is set per window in `stage_inputs` from
   `ecap_for(T)`: the cap applies only with head sampling on, or with `STRATA_VERIFY_ECAP_READS=1`. quant_quality reads
   with head sampling off, so the KL screen of ECAP needs `ECAP_READS=1`, which caps every position: a pessimistic proxy.
4. **Size guard.** The kernel holds a window in shared memory: only `n*k <= kEcapMaxEntries` (128) and
   `n_expert <= kEcapMaxExperts` (1024); also off with G > 1, `batch_rec_`, and T < 2. The PR would overflow past 80-128 entries.

## Test

`ecap_parity` (new CMake target, GPU): bit-for-bit against a scalar reference over 40 rounds x T in {1..12} x caps,
with ties, invalid ids and residency 0 / 75% / 100%. It also checks no-op when off, token 0 untouched, distinct experts
<= max(N, k), dropped weights exactly 0 and ids of a kept (resident when possible) expert, and determinism.

Status: not built or run yet (it runs on the 4090 after the B2 approx measurements, `prepare --label --patch --target`).
