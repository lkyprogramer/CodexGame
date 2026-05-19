# Qwen3.6 4090 Extreme Inference Execution Status

Date: 2026-05-13

## Completed

- Installed isolated ModelScope venvs:
  - 4090: `/home/hhtele/ms-venv`
  - GCP relay: `/home/luo/ms-venv`
- Copied ModelScope token env files with `0600` permissions:
  - 4090: `/home/hhtele/.qwen_ms.env`
  - GCP relay: `/home/luo/.qwen_ms.env`
- Built mainline llama.cpp on 4090:
  - Path: `/home/hhtele/llama.cpp-qwen36-main-20260513`
  - Commit: `856c3adac1709be15e1ea2529a0e89f742d25fe0`
  - CUDA arch: `89`
  - Targets: `llama-cli`, `llama-server`
- Built MTP llama.cpp branch on 4090:
  - Path: `/home/hhtele/llama.cpp-mtp-unsloth-20260513`
  - Commit: `ebe4fca4b59ef8871bb07c34d148bc37fe57fadd`
  - CUDA arch: `89`
  - Targets: `llama-cli`, `llama-server`
  - Confirmed server help exposes `--spec-type none,draft,eagle3,mtp,...` and `--spec-draft-n-max`.
- Built Lucebox DFlash on 4090:
  - Path: `/home/hhtele/lucebox-hub-main-maxperf-qwen36/dflash`
  - Targets: `test_dflash`, `test_flashprefill_kernels`
  - CUDA arch: `89`
  - `DFLASH27B_ENABLE_BSA=ON`
- Mirrored Unsloth MTP GGUF through GCP to ModelScope:
  - Source: `unsloth/Qwen3.6-27B-MTP-GGUF`
  - Target: `wuniansky/Qwen3.6-27B-MTP-GGUF`
  - File: `Qwen3.6-27B-UD-Q4_K_XL.gguf`
  - ModelScope revision observed: `5cddeaa63af7d4aabf1604ed0b260a546dd0f541`
  - Size: `17909097600`
  - SHA256: `4085665ee36d82a672a238a43f0e5643f2f0e39f2d7bd5d373f0ef10ecf53095`
- Downloaded and verified the MTP GGUF on 4090:
  - Path: `/data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf`
  - Size: `17909097600`
  - SHA256: `4085665ee36d82a672a238a43f0e5643f2f0e39f2d7bd5d373f0ef10ecf53095`
- Cleaned relay temp files on GCP:
  - `/tmp` usage recovered from `94%` to `50%`.

## Runtime Constraints

- Existing 4090 service on port `18343` was left untouched.
- Current GPU state blocks live 27B benchmark startup:
  - Running process: `/opt/llama.cpp/build/bin/llama-server`
  - PID: `2467976`
  - GPU memory used by process: about `21860 MiB`
  - GPU memory free: about `2347 MiB`
- Because only about 2.3 GiB VRAM is free, starting mainline/MTP/Lucebox 27B experiments concurrently would fail or disturb the existing service.

## Ready Commands

Mainline llama.cpp baseline:

```bash
cd /home/hhtele/llama.cpp-qwen36-main-20260513
./build/bin/llama-server \
  -m /data/models/qwen/Qwen3.6-27B-Q4_K_M.gguf \
  -ngl 99 -c 131072 -np 1 -fa on \
  -ctk q4_0 -ctv q4_0 \
  --chat-template-kwargs '{"enable_thinking":false}' \
  --host 0.0.0.0 --port 18360
```

MTP llama.cpp:

```bash
cd /home/hhtele/llama.cpp-mtp-unsloth-20260513
./build/bin/llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  -ngl 99 -c 131072 -np 1 -fa on \
  -ctk q4_0 -ctv q4_0 \
  --spec-type mtp --spec-draft-n-max 3 \
  --chat-template-kwargs '{"enable_thinking":false}' \
  --host 0.0.0.0 --port 18364
```

Lucebox DFlash build path:

```bash
cd /home/hhtele/lucebox-hub-main-maxperf-qwen36/dflash
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES=89 -DDFLASH27B_ENABLE_BSA=ON
cmake --build build --target test_dflash test_flashprefill_kernels -j "$(nproc)"
```

## Next Execution Gate

To run live latency/throughput benchmarks, the existing `18343` service must be stopped or moved long enough to free VRAM. No benchmark server was started in this run because the plan explicitly required preserving the default service.
