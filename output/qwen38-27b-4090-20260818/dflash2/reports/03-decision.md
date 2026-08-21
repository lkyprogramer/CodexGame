# 决策：不切 18343

**DFlash2 在这台 4090 上是真的快，但快在代码复述，不是 OpenClaw 主力形态。现网 MTP n=2 + q8 + 112K + medium 保持。**

## 门禁

| 门禁 | 结果 |
|---|---|
| D1 的 T+A 混合 ≥ C0 × 1.20 | **未达**。T 1.30×，A 0.84×，混合约 1.08× |
| 空 content = 0 | 通过 |
| 工具抽样不回归 | 通过（仍调用 `read_file`） |
| 空载 VRAM ≤ 23500 且余量 ≥ 1GB | D1 通过（21736 / 2481）；Analogalok 110K 本机也只有 21.2GB，不是 23.96 |
| 28k 交叉三事实 | 通过 |
| C1/C3 的 134 tok/s 当 MTP 上限 | **否**。短码 120–125，思考长答 68–91 |

## 为什么不换

1. OpenClaw 是工具环，不是 HumanEval。DFlash2 把 `A_tools` 从 75 tok/s 打到 32–43。
2. 思考长答接受率 ~0.5，闲聊 ~0.4；MTP 仍在 0.6–0.8。阿超的「自带 MTP 就别外挂」在本机成立。
3. 112K q8 工作窗口 DFlash2 没跑（64K 公平档已经输工具）。要 110K 只能 q4 KV，质量门我们特意避开。
4. 多一个 1.14GB draft + 未合主线 PR，运维成本高于 MTP 头。

## 意外收获：gavwhittaker 的 MTP 旋钮

C3 只把现网改成 `n-max 6` + `p-min 0.82` + 92K：短码 125、medium 编码 95、工具 72（≈C0）。本机 S2 曾在关思考填 1024 token 时看到 n=4 无益；**带 p-min 的 n=6 在短码/中等编码上确实更快**，且不需要 DFlash2。

这不是切流授权。若以后要挖 MTP，优先在旁路复现 C3 的长时间稳定性（junk、单层头），不要先上 DFlash2。

## 现网

`openclaw-qwen38-work-64k.service` 已 `active`，别名 `openclaw/Qwen3.8-27B-WORK`，112128 ctx，22664 MiB。18443 无常驻进程。DFlash2 GGUF 留在 `/data/models/qwen/qwen38/`，二进制在 `/home/hhtele/llama.cpp-qwen38-dflash2-pr27342/`，需要时再开旁路。
