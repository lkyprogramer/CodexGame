# Qwen3.8-27B RTX 4090 Extreme Deployment & 60-Minute Agent Benchmark

**Target machine**

- NVIDIA RTX 4090 24 GiB (Ada / SM89)
- Host RAM: 64 GiB
- SSD: 600 GiB
- Current NVIDIA driver: `545.23.08`
- Current host CUDA Toolkit / reported CUDA: `12.3`
- Primary workload: **Pi coding agent + Java development + long-running single-user Agent sessions**
- Required working context: **~200K tokens**

## Recommended production candidate

```text
Qwen3.8-27B
  └─ W4A16 AutoRound target
      ├─ int8 embeddings/lm_head preparation
      ├─ fp16 recurrent/GDN state
      ├─ MTP-3 (default for general 100K–200K agent work)
      ├─ optional DFlash2 (edit/copy/RAG-heavy work)
      ├─ KVarN K4/V2 KV cache for ~200K+
      └─ prefix cache retaining attention KV + recurrent state
          ↓
      patched vLLM 0.27.1
          ↓
      OpenAI-compatible API
          ↓
      Pi coding agent
```

This package deliberately **does not replace your existing llama.cpp WORK stack**. Keep it as the quality/stability fallback while the vLLM profile is qualified.

## Important environment conclusion

Your current **driver 545.23.08 cannot run the pinned CUDA-13 container stack**. The preferred low-impact path is therefore:

1. **Do not upgrade/remove host CUDA Toolkit 12.3.**
2. Upgrade **only the NVIDIA driver to R580+**.
3. Run the new stack in a CUDA 13 Docker container.
4. Keep all existing CUDA-12.3 projects and llama.cpp binaries untouched.

A strict “driver 545 + CUDA 12.3 unchanged” deployment is intentionally marked **NO-GO** for this patched vLLM build; use the existing llama.cpp fallback until the driver can be changed.

## Quick path after driver is ready

```bash
cp configs/benchmark.env.example configs/benchmark.env
# edit API key / pi path if needed

./scripts/preflight.sh
./scripts/setup_upstream.sh
./scripts/prepare_model.sh
./scripts/start_server.sh huge-mtp
./scripts/wait_server.sh

nohup ./scripts/run_all.sh configs/benchmark.env > logs/nohup-suite.log 2>&1 &
tail -f logs/nohup-suite.log
```

The default test suite is bounded by `SUITE_TIMEOUT_SEC=3600` and is designed to finish in roughly **40–60 minutes** on a healthy 4090 deployment.

## Package map

- `AGENT_START.md` — instructions for an autonomous coding/ops AI.
- `docs/00-research-and-decision.md` — why this stack was selected.
- `docs/01-memory-and-profiles.md` — 4090 memory/context design.
- `docs/02-deploy-keep-cuda12.md` — preferred deployment: keep host CUDA 12.3, upgrade driver only.
- `docs/03-deploy-cuda13-host.md` — full host driver + CUDA 13 path.
- `docs/04-60min-test-plan.md` — exact one-hour qualification plan.
- `docs/05-pi-java-agent-tests.md` — Pi configuration and Java-focused tasks.
- `docs/06-result-gates.md` — GO / NO-GO thresholds.
- `docs/07-troubleshooting.md` — common failures.
- `docs/08-sources.md` — source/revision ledger.
- `scripts/` — install, start/stop, benchmark, report scripts.
- `fixtures/java-agent-*` — self-contained Java tasks; no Maven/network dependency.

## Default serving profiles

| Profile | Purpose | Context | Speculation | KV |
|---|---|---:|---|---|
| `huge-mtp` | **default long Agent profile** | 200K | MTP-3 | KVarN K4/V2 |
| `huge-dflash2` | edit/copy/RAG-heavy long context | ~220–245K | DFlash2 | KVarN K4/V2 |
| `fast-dflash2` | short/medium daily work | ~64K | DFlash2 | BF16 |
| `long-mtp` | quality/speed middle ground | 150K | MTP-3 | FP8 |

For your stated target, qualify **`huge-mtp` first**. Only promote `huge-dflash2` if your Java workload is dominated by copying/revising code already present in context.

## Core acceptance gates

A candidate is a daily-driver only when all mandatory gates pass:

- Actual occupied prompt at least **185K tokens** without silent truncation.
- Long-context sustained decode **>=20 output tokens/s**.
- 100K and ~185K needle/retrieval checks pass.
- Prefix-cache append test shows meaningful reuse on a growing conversation.
- All three packaged Pi/Java tasks pass without modifying protected tests.
- No OOM, illegal memory access, corrupted output, or server restart during the suite.
- Total suite completes within the configured 60-minute cap.

See `docs/06-result-gates.md` for the scoring rules.
