# Lucebox Qwen3.8 4090（按批注：18343 + bench_lane smoke）

- 源码：`/home/hhtele/lucebox-qwen38-4090` HEAD `298031a`，BSA submodule 已带
- 编译：CUDA 12.3 / sm_89 / `dflash_server`，日志 `logs/compile.out`
- Target：UD-IQ4_XS（下到 `/data/models/qwen/qwen38-lucebox/`）
- Draft：incoai DFlash2 safetensors → 自转 q8_0（不用盘上 llama.cpp 的 DFlash2 GGUF）
- 服务：**停 WORK 后占 18343**，`--max-ctx 32768`，q8 KV，block-size 16
- 测试：现有 `bench_lane.py`（S/T/工具/闲聊/28k 针），**不测 Pi**
- EXIT trap restore WORK

编排：`logs/wait_build_smoke.sh`（setsid nohup）
