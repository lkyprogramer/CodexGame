# Qwen3.5-27B Distilled v1 vs v2 Delta Report

## Scope

This note compares the fresh `Distilled v2` run against the previously recorded `Distilled v1` history on the same baseline family `Qwen3.5-27B-UD-Q4_K_XL`.

Historical references:
- 64K: `output/model-compare-v2/20260308-130031/64k/summary/compare_report.md`
- 262K: `output/model-compare-v2/20260308-130031/262k/summary/compare_report.md`
- agentic: `output/model-compare-agentic/20260308-232041/summary/agentic_compare_report.md`

## 64K Coding

Historical v1 signal:
- baseline `22 / 22`
- v1 `22 / 22`
- quality judgment leaned toward v1 on the 22-task extended set

Fresh v2 signal:
- baseline `22 / 22`
- v2 `21 / 22`
- fresh provisional rubric totals: baseline `244`, v2 `229`
- visible hard regression: `java_permission_scope_trust_bug` returned `503`

Conclusion:
- v2 did **not** improve the 64K coding result relative to the old v1 outcome
- on this run, v2 looks weaker than v1 on the core 64K coding profile

## 262K Extreme

Historical v1 signal:
- baseline `2 / 4`
- v1 `3 / 4`

Fresh v2 signal:
- baseline `2 / 4`
- v2 `3 / 4`
- v2 succeeded on `extreme_java_change_impact_longctx`, where baseline returned `503`
- both baseline and v2 still failed `extreme_reconcile_script_longctx` with context overflow style failure

Conclusion:
- v2 preserved the main long-context advantage that v1 had over baseline
- on 262K, v2 is roughly **on par with v1**, not clearly better

## Agentic

Historical v1 signal:
- baseline best-of-2 validation success `3 / 4`
- v1 best-of-2 validation success `1 / 4`

Fresh v2 signal:
- baseline best-of-2 validation success `2 / 4`
- v2 best-of-2 validation success `1 / 4`

Conclusion:
- v2 did **not** repair the old distilled-model weakness on strict agentic artifact delivery
- on agentic tasks, v2 remains materially behind the dense baseline

## Overall

Net takeaway:
- relative to v1, `Distilled v2` keeps the long-context upside
- but it does **not** show a clear 64K coding improvement
- and it still does **not** cross the agentic gate

Recommendation:
- do not replace the 27B dense coding baseline with v2
- if v2 is kept at all, treat it as a long-context / review-side candidate rather than the default executor model
