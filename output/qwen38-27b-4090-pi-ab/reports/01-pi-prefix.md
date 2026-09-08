# Pi × 4090：WORK 基线 + Lucebox 真实 Agent 前缀缓存

时间：2026-09-04 16:07–16:10  
Pi 只在本机 `nvm v22.19.0` / `pi 0.84.4`。4090 无 Pi。本机打不到 18343（防火墙），走 `ssh -L 127.0.0.1:18343`。Pi 用隔离 `PI_CODING_AGENT_DIR`，未改 `~/.pi/agent/models.json`。

剧本：P-short（读 Agents.md 报 tickMs）、P-loop（5 步：列 runtime → grep reconnect → 读 GameRuntimeServer → 风险说明 → JSON）。

## WORK 基线（MTP n=2，未停服务）

| 任务 | 墙钟 | 结果 |
|---|---:|---|
| P-short | 4.67s | `{"tick":200,"protocol":"v1"}` |
| P-loop | 15.26s | 五步工具齐全，reconnect 护栏读对 |

`sha_tools` / `sha_system` 全程不变。llama.cpp 走 SSE，本轮 WORK 的 timings 未解析。

## Lucebox 200K q4 + 采样验收 + 8 prefix slots

Pi 真实 4 工具（read/bash/edit/write），首包 **2891** token（> chunk 512）。任务均完成。测完 restore WORK。

### prefix only（`--agent-turn-cache` 关）

| 轮 | pt | cached | prefilled | prefill_ms | wall_s | hit |
|---|---:|---:|---:|---:|---:|---|
| 冷 | 2891 | 0 | 2891 | **2341** | 3.03 | false |
| 热 | 3449 | **2560** | 889 | **485** | 0.85 | true |
| … | 3000–5581 | 2560–3584 | 440–1997 | 248–1248 | 1.1–6.6 | true |

P-short 4.26s，P-loop **10.63s**。冷→热 prefill **4.8×**。

### + `--agent-turn-cache`

| 轮 | pt | cached | prefilled | prefill_ms | wall | agent_hit |
|---|---:|---:|---:|---:|---:|---|
| 冷 | 2891 | 0 | 2891 | 2332 | 3.62 | false |
| 热 | 3449 | **2990** | **459** | **262** | 0.67 | **true** |
| 后续 | 3553–5636 | 3087–4296 | 466–1340 | 265–743 | 1.7–6.7 | 多为 true |

P-short 4.73s，P-loop **12.39s**（末轮 completion 582 tok，墙钟被生成拖住）。  
日志：`[agent-turn-cache] saved slot=… replayed=430`。相对只开 prefix，热轮 **prefill 485→262 ms**，cached **2560→2990**。

## 和合成 4 工具 miss 的差异

合成 bench 工具头 **482 &lt; chunk 512**，只写不读。Pi 真实工具头 **~2560–2891**，跨过 chunk，**restore 生效**。根因是请求形态，不是「Pi 每轮改 tools」——哈希稳定。

## 现网

WORK active，22958 MiB。未改 NGINX / 开机默认。
