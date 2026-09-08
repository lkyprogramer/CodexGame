# Source and Revision Ledger

Research/checkpoint date: 2026-09-06.

## Primary implementation

- Repository: `https://github.com/kernel-sanders/qwen38-27b-rtx4090-vision.git`
- Pinned revision used by this package: `36317835f2224c620f4d604bd57bf0a70f14cade`
- Important upstream files reviewed:
  - `README.md`
  - `single-user/start_qwen.sh`
  - `docs/long-context.md`
  - `docs/quality.md`
  - `docs/docker.md`
  - `docker/prepare.sh`
  - `Dockerfile`

## Models / algorithms

- Qwen base: https://huggingface.co/Qwen/Qwen3.8-27B
- W4A16 target used by upstream: https://huggingface.co/dbirks/Qwen3.8-27B-W4A16-AutoRound
- DFlash2 family: https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2
- KVarN upstream: https://github.com/huawei-csl/KVarN

## Pi

- Custom-provider model configuration supports OpenAI-compatible `baseUrl`/`openai-completions`.
- CLI supports print/JSON mode, provider/model selection, thinking level and built-in coding tools.
- Benchmark uses an isolated Pi HOME to avoid modifying normal user configuration.

## Environment facts used in this plan

- Reference Docker image is CUDA 13.0.1 with vLLM 0.27.1 / torch cu130.
- Upstream Docker documentation requires an NVIDIA driver that supports CUDA 13 (R580+).
- User's current driver is 545.23.08 and current CUDA Toolkit/report is 12.3.

## Evidence boundaries

Performance numbers in the research notes are community/upstream measurements, not measurements made on the user's machine by this package. The packaged benchmark is specifically intended to replace those extrapolations with local evidence.
