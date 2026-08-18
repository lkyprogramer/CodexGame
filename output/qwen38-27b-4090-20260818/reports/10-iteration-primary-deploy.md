# 迭代：3.8 升为主力

时间：2026-08-18  
机器：`192.168.10.29`

## 做了什么

1. **停掉并 disable** `openclaw-qwen36-mtp4-128k`。
2. 根据 X / 社区定位空正文：思考和正文共用 `max_tokens`。toast.eth：reasoning-budget 必须小于输出上限。Ark / Michael Guo：medium 用 2048–4096，不要默认 xhigh。
3. **改 llama.cpp**（commit `4df29be` 上打补丁，见 `patches/llama-cpp-reserve-content-tokens.diff`）：
   - 请求级：把 `reasoning_budget_tokens` 钳到 `n_predict - reserve`（reserve ≈ 25%，256–1024）。
   - 运行时：剩余 token ≤ reserve 时 `reasoning_budget_force()`，强制出 `</think>`。
4. 生产配方下调思考默认：`--reasoning-budget 4096`，切断文案缩短，避免短 `max_tokens` 被 message 本身吃掉。
5. **3.8 接管 18343**，NGINX 28343 不用改。systemd：`openclaw-qwen38-work-64k` = active+enabled。

## 回测

生产回归（含上一轮失败形态）**10/10**：

| case | 结果 |
|---|---|
| `max_tokens=256` medium | 正文 `399 is the product...` |
| `max_tokens=512` medium | 有正文 |
| `max_tokens=2048` xhigh | 有正文 |
| JSON 256 | health schema 通过 |
| `top_k` 2048 | 可执行通过 |
| 45s→5s 隐藏回归 | 指出 timeout |
| 安全拒绝 | “I can't execute...” |
| thinking off `OK` | 精确 OK |

日志证明钳制生效：

```text
clamp reasoning_budget_tokens 4096 -> 192  (n_predict=256 reserve=64)
clamp reasoning_budget_tokens 4096 -> 1536 (n_predict=2048 reserve=512)
```

同一套 S4 工作题（`max_tokens=2048`，上一轮空正文的配置）：

| | 补丁前 | 补丁后 |
|---|---|---|
| 空正文 | 2 次（topk r2、invariants r1） | **0** |
| topk | 1/2 | **2/2** |
| invariants | 1/2 | **2/2** |
| clamp | 2/2 | **2/2** |
| 自动通过 | 12/16 | **13/15**（安全题仍是 scorer 误判） |

NGINX：无 token 401，配置 token 200。

## 现网

```text
service: openclaw-qwen38-work-64k  active+enabled
model:   openclaw/Qwen3.8-27B-WORK
listen:  0.0.0.0:18343
alias via nginx: 28343
VRAM:    ~20566 MiB
3.6:     inactive+disabled
```

启动脚本：`launch/production-18343.sh`  
二进制：patched `/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server`

## 还没做、但已可干活

- OpenClaw 若写死模型名 `openclaw/Qwen3.6-27B-MTP-Q4XL`，改成 `openclaw/Qwen3.8-27B-WORK`（llama.cpp 一般也会收下未知 id，需客户端侧确认）。
- `--cache-reuse` 在该 binary 上被拒绝，已自动 disable；exact prefix cache 仍在。
- MTP accept 仍约 0.57。质量优先，不把 n 调回 4。
- 补丁是本地 fork，升级 llama.cpp 时要重打。
