# Flash-Next MTP 4090 排查（2026-09-03）

`all_nohup.sh` **已跑完并退出**。现网 WORK 正常：`openclaw/Qwen3.8-27B-WORK`，`n_ctx=200192`，22958 / 1259 MiB，18343 listen。18443 无进程。

## 链路

| 步 | 结果 |
|---|---|
| CUDA 12.3 / sm_89 重编 `586b15e` | **BUILD_OK**（12.8 portable 的 kernel invalid 已消失） |
| F0 无 MTP 加载 IQ3_XXS | 成功，空载 **20396 / 3821 MiB** |
| F1 `-md` shared Q4_K_M + draft-mtp n=3 | 草稿加载成功（启动时有一次误把 draft 当主模型的报错，随后 `common_speculative_init` 成功） |
| 空载 F1 | **22862 / 1355 MiB**（相对 F0 +2.4G，和帖子 21.5→23.3 同量级） |
| trap restore WORK | **prod_ready 9s** |

## 测速数字为什么不能对帖子

`bench_fill.py` 只让模型回 `OK`（**2 个 completion token**）。`decode_tok_s=0.02` 是 **90s 填窗 / 2 token**，不是 decode。

llama.cpp 日志里的真实数：

| 车道 | 窗（prompt tok） | prefill t/s | decode t/s（仅 2 tok，噪声大） | MTP accept |
|---|---:|---:|---:|---|
| F0 | 17788（~16k） | 199 | 11.8 | — |
| F0 | 累计 35569（~32k） | 209 | 15.6 | — |
| F0 | 目标 64k | **400**：请求 72788 > n_ctx 65536 | — | — |
| F1 | 17788 | 195 | **3.3**（比无 MTP 更慢） | 1.00（3/3） |
| F1 | ~32k | 202 | **5.9** | 1.00（3/3） |
| F1 | 64k | 同 400 | — | — |

64k 没测到：filler 把 prompt 估爆到 72k。帖子的 64k **23→38 t/s** 对不上。

MTP 在 **只生成 2 token** 时草稿开销大于收益（F1 decode 更慢）。帖子是长 decode；这次脚本没测那个。

Prefill ~200 t/s：`-ncmoe 34` 把大量 expert 放 CPU，比现网 27B 的 1k–2k prefill 慢一个数量级，符合 MoE+offload。

日志警告：`tensor overrides to CPU are used with mmap enabled - consider using --load-mode none`。

## 和帖子

| | 帖子 3090 | 这次 4090 |
|---|---|---|
| 加载 | 是 | **是**（重编后） |
| VRAM MTP 增量 | +1.8G | **+2.4G** |
| 64k decode 23→38 | 有 | **无**（窗估爆 + 只生成 2 tok） |

## 若要真对比

1. `max_tokens` ≥ 128（更好 256–512），`ignore_eos`。
2. 填窗按 **token 数** 卡在 16k/32k/**60k**（不要 65500 字符估算）。
3. 以 stderr 的 `eval time` / `draft acceptance` 为准，不要用 wall/2。
4. 可选 `--load-mode none` 看 CPU MoE 是否少抖。

现网未改。无定时 loop。
