# Research and Architecture Decision

## Why this stack

Qwen3.8-27B is a 27B dense hybrid model with 64 decoder layers: 48 Gated DeltaNet layers and 16 full-attention layers. That hybrid layout is unusually favorable to very long contexts on a 24 GiB card because only one quarter of the layers grow a normal KV history; the other layers maintain recurrent state.

The selected community stack starts from `dbirks/Qwen3.8-27B-W4A16-AutoRound`, then requantizes the untied embedding/lm-head and MTP components, uses fp16 recurrent state, and adds speculative decoding plus an optional aggressively compressed KV cache. The current reference implementation is `kernel-sanders/qwen38-27b-rtx4090-vision`.

### Evidence relevant to this machine

The reference repository reports on an RTX 4090:

- W4A16 + DFlash2 is the fastest short-context single-user path.
- `CTX=long` uses FP8 KV and targets ~150K.
- `CTX=huge` uses KVarN K4/V2 and targets ~200K with MTP, and up to ~240K with DFlash2 depending on verify-block settings.
- Prefix caching retains both full-attention KV and recurrent state for follow-up turns.

Its long-context measurements also show an important tradeoff: KVarN buys capacity but can substantially reduce single-stream decode at >100K compared with FP8 KV. Therefore KVarN should be treated as a **capacity mode**, not the universal default.

## Why `huge-mtp` is the default 200K Agent profile

For a long-running Java agent the response is usually a mixture of reasoning, new code, tool calls, summaries and edits. Community measurements at ~112K show MTP outperforming DFlash2 on general QA/summary work, while DFlash2 is strongest when the answer reproduces or edits text already in the prompt. MTP is therefore the safer default for a mixed workload at 100K–200K.

Use DFlash2 when:

- the agent applies edits to code already loaded in context;
- RAG answers quote substantial source text;
- shorter 64K contexts are acceptable and raw interactivity is the priority.

## Why KVarN is necessary for the 200K target

With ordinary FP8 KV, the single-card profile has a practical ceiling around the high-100Ks. KVarN compresses K/V substantially enough to make the native 262K neighborhood addressable on 24 GiB cards. The cost is extra dequant/attention work and some speculative-acceptance degradation at deep context.

For this reason the package qualifies two dimensions independently:

1. **Capacity:** actual prompt >=185K with successful generation/retrieval.
2. **Usability:** sustained decode >=20 tok/s and acceptable warm-turn latency.

## Why not Kearuga on this 4090

Kearuga's mixed-precision strategy is technically attractive, but its published deployment is designed around Blackwell/DGX Spark and NVFP4. Its weight footprint also leaves inadequate room on a 24 GiB discrete Ada GPU for a 200K context plus draft/runtime state. The design principles are useful; the artifact itself is not the best fit here.

## Why not Escha-W2 as the 200K Agent baseline

Escha-W2 is exceptionally compact and fast on RTX 4090 at short/medium contexts, but its published SGLang runtime has shown weak reuse for an append-growing hybrid conversation: identical prompts cache well, while an appended tail can trigger full re-prefill. That is a poor match for Pi sessions that repeatedly append tool results. It remains an excellent performance challenger, but not the first 200K long-Agent qualification target.

## Source-of-truth rule

This package wraps an upstream pinned implementation rather than reimplementing its CUDA/vLLM patches. That minimizes divergence and keeps the custom work here focused on deployment orchestration and realistic qualification.
