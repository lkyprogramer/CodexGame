# DFlash2 试跑计划（落地副本）

约束：GitHub 源码由本机中转；模型走 `https://hf-mirror.com/`。不替换 18343。

- llama.cpp：本机 `git fetch origin pull/27342/head` → 打空正文补丁 → tar/scp。commit `5ecbe1ac1 support DFlash2`。
- 权重：`hf-mirror.com/incoai/Qwen3.8-27B-DFlash2-GGUF` 的 `Qwen3.8-27B-DFlash2-Q4_K_M.gguf`。
- mmproj：`hf-mirror.com/unsloth/Qwen3.8-27B-GGUF` 的 `mmproj-BF16.gguf`（仅 C1）。
- 试跑口：18443。现网 systemd 保持 disabled-during-trial，测完 `restore-prod.sh`。
