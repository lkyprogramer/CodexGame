# Flash-Next MTP 4090 trial status

帖子：Qwen3.8-Flash-Next IQ3_XXS + shared MTP Q4_K_M，3090 配方。  
本机：4090 24GB + 62Gi RAM。

- 权重已齐（三片 IQ3_XXS ~11M+46G+30G，MTP shared-Q4_K_M 1.78G）。日志无 `DOWNLOAD_OK`，文件完整。
- 二进制：Unsloth prebuilt `b10715-mix-86bd2d3` **CUDA 12.8 portable 不能在驱动 545 / CUDA 12.3 上跑**（F0 warmup `device kernel image is invalid`）。
- 评测：`01-eval.md`。无 F0/F1 summary，无 16k/32k/64k 数字。
- 现网 WORK `:18343` 已 restore。不要再用该 portable 二进制停卡。

下一步：CUDA 12.3 / sm_89 重编后再 eval。
