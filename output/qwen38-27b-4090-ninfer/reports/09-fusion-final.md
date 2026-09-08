# 4090 NInfer 融合验证最终报告

日期：2026-09-08  
镜像：`ninfer-4090:44a2c6c`（tensorninja，已含 sergiuszm sm_89 + UDP E8）  
制品：`qwen3_8_27b.ninfer` SHA `eec39564…` 16.96 GiB  
thinking=off HTTP / Pi Java。测完 **WORK 已 restore**（18343 正常，18030 已停，GPU 22822 MiB）。

原始 JSON：`output/qwen38-4090-compare/results/fusion/`  
自动表：`reports/08-fusion-p0.md`  
方案：`reports/07-fusion-best.md`

---

## 结论

**4090 上最优可部署 NInfer 档就是现网镜像 + 把窗口从 221184 提到 262144，其余旋钮保持。**

```
ninfer-serve … \
  --max-context 262144 --kv-capacity 262144 \
  --max-concurrency 1 --max-pending-requests 8 \
  --pending-timeout-ms 600000 --prefill-chunk 1024 \
  --kv-dtype rk4v4-e8 \
  --spec mtp --draft-tokens 3 --lm-head-draft \
  --prefix-checkpoint-policy rolling-tool \
  --continuation-cache l1-l2 \
  --continuation-cache-l1-mib 6144 \
  --continuation-cache-l2-mib 8192 \
  --preserve-thinking
```

驻留实测 **22594 / 24564 MiB**，没有 OOM。

| 决策 | 结果 |
|---|---|
| 换 sergiuszm / UDP 树 | **否**。tensorninja 已融合两者核心，再加 INT8 prefill 与 L1/L2 |
| draft 4 / 5 | **否**。n=5 184k **76 t/s** 有害；n=4 仅 184k 略快、短档更慢 |
| ctx 262144 | **是**。针全中，Java 3/3，184k **87.2 t/s** ≈ 221k 的 87.5 |
| 开 L3 | **否（本 harness）**。重建后 cold 仍 ~40s、`cached=None`，对单轮 dump 无收益 |
| rk2v4-e8 当默认 | **否**。184k 针过、decode 88，但 184k TTFT **+17s**，Java 题3 **未过** |
| 重建镜像拣 UDP bfi / MMA | **未做**。配置档已满足目标；kernel 补丁要单独 tag + bench |
| 切 18343 默认 | **未切**。A2 在 Java 墙钟和 184k decode 上已优于 WORK，但是产品切换需你明确说 |

---

## 总表（thinking=off）

基线 n=3 / 221184 / rk4 来自此前 off 阶梯。WORK / vLLM 来自 medium 套件（WORK systemd 本就是 medium）。

| 档 | 4k | 64k | 120k | 184k | 184k TTFT | 针 | append TTFT | Java |
|---|---:|---:|---:|---:|---:|---|---:|---|
| WORK MTP n=2 200k | 77.6* | 60* | 46.5* | **38.4*** | 134s* | 中 | 5.0s | 3/3 p50 32s* |
| NInfer n=3 221k | 117 | 98 | 102 | **87.5** | 96s | 中 | 3.5s | 3/3 p50 31s* |
| **A2 262k rk4 L1=6144** | 112 | **111** | **110** | **87.2** | 94s | 全中 | **3.3s** | **3/3 38/24/26s** |
| A2b +L3 | 123 | 103 | 104 | 93.0 | 95s | 全中 | 3.3s | 未跑（同权重） |
| A2b L3 重建后再测 | — | — | — | — | — | — | cold 仍 39.7s | — |
| A1 n=4 221k | 101 | 101 | 96 | 94.1 | 94s | 全中 | 3.4s | — |
| A1 n=5 221k | 112 | 104 | 93 | **76.4** | 95s | 全中 | 3.4s | — |
| **A3 rk2 262k** | 109 | 98 | 92 | 88.3 | **110s** | 全中 | 3.9s | **2/3**（题3 verify 失败） |
| vLLM huge-mtp* | 58 | 64 | 63 | 53 | **66s** | 中 | ~5s | 3/3 p50 48s |

\* medium 套件数字，不是本轮 off。

A2 相对「184k ≥ 87.5×95% = 83.1」**过关**。n=5 **不及格**。A3 速度过关、质量门 **不及格**。

---

## 分档证据

### A1 draft 3/4/5（同 221k rk4）

已在 `06-fusion-a-draft.md`。默认 **3**。n=4 只在 184k 有小幅正收益，Agent 短档更慢。n=5 有害。

### A2 ctx=262144、L1=6144、rk4、n=3

- 启动 28s，`NINFER_READY`，docker Args 已核对 ctx/kv/l1。
- 担心的「L1 6GiB 吃掉 1.37GiB slack」**没有发生**（L1 预算不是额外一整块 KV）。
- 中长 decode 比 221k 基线更好（64k 111 vs 98，120k 110 vs 102），184k 持平。
- Java 三题全过，墙钟 38/24/26s，优于 WORK 32/17/53 的 p50。
- prefix：exact 命中 99697 tokens，TTFT 0.63s。

### A2b L3

- 同卡同权重，HTTP 与 A2 同级（184k 甚至 93 t/s，视为噪声）。
- 容器重建 `NINFER_READY 4s`（权重走主机页缓存，不是 KV 热启动）。
- 重建后 cache-cold **仍 39.7s、`cached=None`**。本套单轮 100k dump **没有**变成 L3 命中。continuation L3 服务的是完整 Qwen 状态别名，不是任意 prompt 字节缓存。日常 OpenClaw 多轮是否值回磁盘，要用真实 session 重启再测，**不能**凭这套 ladder 打开 L3。

### A3 rk2v4-e8

- 启动同样 28s，262k + L1=6144 站住。
- 针全中；184k decode 88.3 不差。
- 代价在 **prefill**：184k TTFT 110s vs rk4 94s（prefill 1682 vs 1983 t/s）。
- Java 题1/2 过；题3：模型打出 XML `<tool_call>`，Pi **没有执行工具**（`toolResults=[]`，3s、0 tools），verify 仍是基线 `heartbeat timeout must be measured in milliseconds`。n=1，可能是工具格式偶发，但按门禁 **不能当默认**。

---

## 和 WORK / 社区数字怎么对齐

- sergiuszm 148.6 t/s：greedy 浅代码 MTP3。本机 Agent 采样 184k ~87，口径不同。
- UDP 230 t/s：greedy MTP7。本机 n=5 采样掉到 76。
- UDP DirectStorage 150ms restore：Windows only；Linux L3 对本 harness 未兑现。
- 本机 NInfer 相对 WORK：长 decode 约 **2.3×**（87 vs 38），Java 墙钟更好或持平。vLLM 仍是 185k 首字最短、Agent 最慢。

---

## 未做 / 剩余风险

- P1 源码：UDP `e8_root_codec` bfi/redux（只对 rk2 编码热）、draft-head Ada MMA、sergiuszm `--auto-long-anchors`。**未重建镜像**。anchors 仍是 Agent 改写历史时最值得做的下一工程项，要用真实 Pi 抓「reminder 拼进最新 user」证明 rolling-tool 复用为 0 再开工。
- A3 Java 题3 未复跑，不能把失败全归到 2-bit KV。
- L3 未用真实多轮 session 重启验证。
- 未测 ctx>262144 / YaRN。
- 未切 18343。若要把 OpenClaw 默认换成这档 NInfer，需要另一次明确授权（端口、alias、互斥 systemd）。

---

## 建议的现网动作

1. **NInfer 试验档默认参数改为上面那条 262k 命令**（改 `4090_ninfer_start.sh` 的 `NINFER_CTX` 默认即可）。  
2. OpenClaw **继续 WORK**，直到你要求切 18030/18343。  
3. 不要开 rk2、不要开 L3、不要 draft≥5。  
4. 下一工程若还要挖：只做 auto-long-anchors 的设计移植，不做第四棵 fork。
