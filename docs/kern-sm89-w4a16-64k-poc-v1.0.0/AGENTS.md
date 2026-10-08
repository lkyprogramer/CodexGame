# Repository execution rules

- Scope is a 64K Qwen3.8-27B SM89 W4A16 PoC. Keep model-aware logic in providers/generators, not the generic Kern runtime.
- Read `AGENT_START.md`. Work from the pinned Kern SHA. Do not merge floating upstream or mutate production.
- Target: BF16 activations, FP32 GDN state, BF16 KV, no speculation, max_seqs=1. Numerical variants get separate profile identities.
- Do not lower test thresholds to make a run pass. Do not silently ignore sampling or protocol fields.
- Do not overwrite original model files. Never treat `.ninfer` as interchangeable with safetensors/Marlin.
- Every GPU run needs a documented maintenance lease. Stop only the allowed production unit, restore only when it was active before the lease.
- Do not run `sudo` from a model task. The orchestrating developer, not the test Agent, controls infrastructure.
- Keep secrets out of prompts, git, screenshots and logs. Bind test APIs to loopback.
- Test fixtures are protected. Controller verification recompiles candidate production sources against original tests.
- Emit NOT_RUN/BLOCKED/INCOMPLETE honestly. A successful mock test is not a GPU test.
- Do not run two 27B backends simultaneously. Oracle and candidate are measured sequentially with saved inputs/outputs.
- Stage-local files under `work/` and `results/` are generated; never commit weights, logs containing secrets, or cubins without source/license provenance.
