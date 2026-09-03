# buun-llama-cpp 4090 trial status

- Source: https://github.com/spiritbuun/buun-llama-cpp
- HEAD: `87b37eac9be678c8fcbef59506e6d16b6c4ba04c` (`speculative: align MTP context sizing and fit`)
- Empty-content clamp: hand-ported into `tools/server/server-schema.cpp` (upstream patch context drifted)
- Remote src: `/home/hhtele/buun-llama-cpp-87b37ea`
- Scripts: `/home/hhtele/qwen38-buun-20260901`
- Production 18343: left running during compile

Compile finished. `llama-server` 0.3.0-dev commit 87b37ea (18K trampoline + `libllama-server-impl.so`).

Eval chain finished 2026-09-01. B3 skipped (DFlash2 schema). WORK restored: enabled+active, 18343, n_ctx=200192.

See `01-eval.md`.
