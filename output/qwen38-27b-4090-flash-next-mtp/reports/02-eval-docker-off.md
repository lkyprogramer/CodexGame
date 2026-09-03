# Flash-Next MTP · Docker 停掉后重测（2026-09-03）

`eval_docker_off_nohup.sh` 已结束。WORK 18343 已恢复，10 个 Docker 已 `docker start`。

空载 VRAM：F0 **20396 / 3821**，F1 **22862 / 1355**（MTP +2.4G）。

每次生成 **174 token**（不是上次的 2 token）。64k 窗口实际填了 **59828** prompt tok。

## Decode（llama.cpp `predicted_per_second`）

| 填窗 | F0 无 MTP | F1 MTP n=3 | 帖子 3090 均速 无→有 | 帖子 peak 无→有 |
|---|---:|---:|---|---|
| ~16k | 18.2 | **30.0**（accept 87%） | 33→32 | 35→38 |
| ~32k | 18.2 | **27.9**（82%） | 29→39 | 30→42 |
| ~60k | 16.9 | **27.7**（87%） | 64k: 23→38 | 24→48 |

Prefill 全程约 **195–215 t/s**（`-ncmoe 34` CPU expert）。

## 读法

- 停 Docker 之后测法是对的：MTP 在长生成上 **+60%～+65%**（17→28 t/s），方向和帖子一致。
- 绝对速度仍低于帖子（60k MTP **27.7 vs 38 均 / 48 peak**）。不是显存：GPU 仍有余量。剩下是 62Gi RAM + mmap CPU MoE，带宽不如帖子那台干净 64G 3090。
- 帖子 16k MTP 均速还不涨（33→32）；我们 16k 从 18→30，因为无 MTP 基线更低。
