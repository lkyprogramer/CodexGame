# buun-llama-cpp 4090 旁路结果

日期：2026-09-01  
二进制：`/home/hhtele/buun-llama-cpp-87b37ea` HEAD `87b37eac`  
权重：现网 V3 `Qwen3.8-27B-UD-Q4_K_XL-dv3.gguf`  
口：18443。测完已 restore WORK（`openclaw/Qwen3.8-27B-WORK`，`n_ctx=200192`，22958 / 1259 MiB）。

## 结论

**不上现网，不加 systemd unit。**

- 换 fork 本身（B0，旗标与 WORK 相同）能跑、空正文 0、28k 针全中、工具 JSON 完整。短码 ~91 t/s，并不比现网慢。
- **VBR（B1）** 是唯一有新杠杆的车道：空载只要 **18374 / 5843 MiB**（现网钉死 q4 约 23G）。64k 针仍中，但 64k decode 掉到 **37 t/s**，且 `A_tools` MTP 接受率掉到 0.43。
- **turbo4 钉死（B2）** 空载 21538 / 2679，针和工具都过，速度与 B0 同级。余量更好，但没有质变。
- **DFlash2（B3）** 盘上 Q2_K 被拒：`upstream DFlash convolution/selector tensor schema is unsupported; use fork DFlash2 schema`（与 issue #112 一致）。不另下草稿。

OpenClaw 主路径继续用官方栈 WORK。buun 只留作以后若要「短会话高质量 KV、长了再压」时的研究二进制。

## 数字

对照：现网 WORK 历史（同卡 MTP n=2）短码/工具大约 83 / 75 t/s（旧 112K q8 C0）。本轮没有再打一遍 WORK，避免双开。`A_tools` 本轮只有 36–53 个 completion token（一次 `read_file`），t/s 噪声大，以 **finish=tool_calls + JSON 完整** 为准。

| 车道 | 空载 used/free | S 短码 | T 中位 | A_tools t/s (accept) | A_chat | L 28k / 64k | 针 | 空 content |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| B0 同 WORK 旗标 q4 MTP n=2 | 22798 / 1419 | 91.4 (0.97) | 85.3 | 50.2 (0.88) `read_file` | 70.8 (0.58) | 75.5 / — | 28k 全中 | 0 |
| B1 VBR floor turbo4 | **18374 / 5843** | 95.3 (0.97) | 85.2 | 48.0 (**0.43**) `read_file` | 75.8 (0.63) | 80.9 / **37.4** | 28k+64k 全中 | 0 |
| B2 turbo4 钉死 | 21538 / 2679 | 91.6 (0.97) | 84.9 | 59.5 (0.90) `read_file` | 74.2 (0.62) | 81.7 / 39.7 | 28k+64k 全中 | 0 |
| B3 DFlash2 Q2 | — | 未跑 | | | | | | 加载失败 |

B1 `meta.vbr.enabled=true dynamic=true floor_bpv=4.125`。B0/B2 vbr.enabled=false。

## 和 issue 的对应

| 预测 | 实测 |
|---|---|
| #106 fork 不一定更快 | B0 短码不慢；工具轮 t/s 无优势。未挂 mmproj，无 slash-loop |
| #112 官方 DFlash2 schema 不进 buun | Q2_K 加载失败，原文一致 |
| #41 turbo4 截断 tool JSON | 三车道 `arguments` 均完整 `{"path":"Agents.md"}` |
| #96 禁止自动 `-c` | 全程显式 200000，无 OOM |
| #107 多会话 DFlash2 | 未进入该路径 |

## 不做

- 不 `enable` buun
- 不换 18343 二进制
- 不找「fork DFlash2 schema」第二份草稿
- 不把 VBR 当默认：64k 已经 37 t/s，agent 长会话会痛
