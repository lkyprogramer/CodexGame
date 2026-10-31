# Offline evidence tools Implementation Plan

> HISTORICAL IMPLEMENTATION RECORD: the offline tools below already exist. This is not a new task, authorization, or required skill invocation. See the current P00/P01 plan for missing adapters.

**Goal:** Add four small standard-library CLIs that reject incomplete evidence and never approve deployment.

**Architecture:** Shared strict JSON and exclusive-output helpers; independent package, headroom, paired-statistics, and manifest checks. Tests use synthetic data and temporary files only.

**Tech Stack:** Python 3.10+, standard library.

**Spec:** Parent task of 2026-10-30 plus ../config/policy.json and ../sources/LOCK.json.

## Global Constraints

- Write only tools/, tests/, fixtures/; no network, subprocess, SSH, GPU, production actions or --execute.
- Six independently declared fresh-engine pairs, twelve unique engine identities, fixed request/output identity, no dropped failures.
- Main ratio upper CI <= 1 - max(0.04, 2 * preregistered AA noise); both other metrics among TTFT/wall/decode must have upper CI <= 1.02.
- All fixture results are synthetic; no hardware-performance claim or deployment approval.
- Explicit new output path or stdout; existing files, including input, cannot be overwritten.

## Review Focus

- Duplicate JSON keys, boolean-as-number and nonfinite values must fail closed.
- Overlapping intervals must be unioned; unknown dependencies must remain INSUFFICIENT.
- Missing pairs, repeated engines, failed runs or request/output drift must reject the whole inference.
- DAG cycles, missing dependency/doc, loosened safety policy and deployment flags must fail.
- Manifest traversal, symlinks, duplicate/missing/extra files and content changes must fail.

## Tasks and ledger

- [x] Tests: write rejection/interval/statistical/manifest cases and observe RED.
- [x] Tools: implement common.py, headroom.py, paired_stats.py, validate.py, verify_manifest.py.
- [x] Fixtures/help: document schemas, conditional assumptions, synthetic P24 rounded sanity limits and CLI exits.
- [x] Verify tool behavior: run full unittest suite and fixture CLIs.
- [x] Verify completed package: complete DAG/registry/docs validated; 69-file manifest verified. Final sealing details are recorded in ../VALIDATION.md.

## Verification ledger

- Initial seven test methods failed before implementation. After implementation, seven passed.
- Added adversarial checks for boolean schema versions, missing required SHA fields and loosened policy thresholds/order; observed five failing subcases before tightening validation. All now pass.
- `python3 -B -m unittest discover -s tests -v`: seven test methods, including rejection subcases, passed on 2026-10-30; exit 0.
- `headroom.py --input fixtures/headroom_synthetic.json`: exit 0, `RESEARCH_RESULT_ONLY`; interval union 350 ms, conditional finite-speedup improvement 0.155.
- `paired_stats.py --input fixtures/paired_synthetic.json`: exit 0, `PERFORMANCE_GATE_ONLY`; six synthetic pairs / twelve identities / 46656 exact resamples; quality not evaluated, deployment false.
- `paired_stats.py --input fixtures/p24_rounded_synthetic.json`: expected exit 1, `PERFORMANCE_GATE_NOT_MET`; TTFT ratio 0.9917556419544836, decode upper CI 1.0687834680890858. This checks the rounded synthetic input, not original raw measurements.
- `validate.py --root .`: expected exit 2 while the parent-owned `config/task_dag.json` was absent. This is an incomplete authoring snapshot, not a successful package validation.
- Implementation plus tests: 454 Python lines at the initial checkpoint. Imports and source were checked for network/process execution; there is no live adapter or execution option.

### Review correction: non-target coverage

- Review identified that fixed wall/decode gates omitted TTFT when decode was the preregistered primary metric.
- Added a synthetic case with decode 20% faster and TTFT 10% slower. Before the fix, the test failed because the tool incorrectly returned `PERFORMANCE_GATE_ONLY`.
- Changed non-target gates to cover both remaining metrics among TTFT/wall/decode, and explicitly report the selected primary metric. README updated to match.
- `python3 -B -m unittest discover -s tests -v`: eight test methods passed after the correction on 2026-10-30; exit 0.

### Final policy lock correction

Three tampering subcases first confirmed missing checks for the 120-second cleanup reserve, decode_ms primary metric and three-pair A/A calibration cap. The validator now fixes all three values. All eight test methods passed again; paired_stats retains its general three-metric calculator API. Final package checks are documented in ../VALIDATION.md.
