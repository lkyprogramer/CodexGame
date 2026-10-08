# 4090 NInfer 三叉融合方案（tensorninja 为基线）

日期：2026-09-08  
对照树（本机浅克隆 tip）：

| 树 | 仓库 | 分支 / SHA | 父仓库 |
|---|---|---|---|
| **现网** | tensorninja/ninfer-4090 | `tensorninja` `44a2c6c` 2026-09-03 | **sergiuszm/ninfer-4090** |
| sergiuszm | sergiuszm/ninfer-4090 | `rtx4090-port` `6f327f4` 2026-09-05 | Don-Chad/ninfer-3090 |
| UDP | UDPSendToFailed/ninfer-4090 | `feat/rtx-4090-sm89-native` `39a6f20` 2026-09-02 | Don-Chad/ninfer-3090 |

源码落盘：`output/qwen38-27b-4090-ninfer/{ninfer-4090,forks/sergiuszm-ninfer-4090,forks/udpsend-ninfer-4090}`。  
现网镜像：`ninfer-4090:44a2c6c`。制品仍是 `neroued/Qwen3.8-27B-NInfer` rev `3526913004b1`（16.96 GiB MTP，**不是** main 19G DFlash2）。

---

## 1. 结论（先读这段）

**不要再发明第四棵树，也不要切到 sergiuszm 或 UDP 当默认运行时。**  
现网 tensorninja **已经是** sergiuszm 的 sm_89 调优 + UDP E8 KV 的融合体，并且多了后两者都没有的：INT8 prefill（宣称 115K **2409 t/s**）、L1/L2/L3 continuation cache、dashboard、LoRA、J/tok。

本机 4090 上已经测到（thinking=medium，HTTP 采样，不是他们 README 的 greedy 代码）：

| | WORK llama MTP n=2 | **NInfer n=3 E8 221K** | vLLM huge-mtp |
|---|---:|---:|---:|
| Java p50 | 32 s | **31 s** | 48 s |
| 184k decode | 38 t/s | **98.5 t/s** | 53 t/s |
| 184k TTFT | 134 s | 94 s | **66 s** |

融合 A1（同镜像只改 `--draft-tokens`）：n=4 184k 94 t/s 略升；**n=5 掉到 76，有害**。默认保持 **n=3**。

**4090 最优版 = tensorninja@44a2c6c + 配置档 + 少量可隔离 cherry-pick。**  
禁止：合入 UDP DirectStorage/D3D12；整树 merge sergiuszm 的 09-04 上游 catch-up（会拆掉 tensorninja 的 INT8 prefill 与 attention 文件布局）；把 greedy MTP7 230 t/s 当 Agent 目标。

下一步仍是配置 A2：`--max-context/--kv-capacity 262144`（n=3，`rk4v4-e8`）。脚本已写好未跑。

---

## 2. 三棵树实际关系（源码事实）

```
Neroued/ninfer (sm_120a 5090)
        │
Don-Chad/ninfer-3090
        ├──────────────┐
        ▼              ▼
 sergiuszm          UDPSendToFailed
 sm_89 retune       E8 / rk* / Windows DS
 148.6 t/s MTP3     MTP7 greedy ~230 t/s
        │
        │  fork（GitHub parent）
        ▼
   tensorninja  ← 现网
   + INT8 prefill 1.415x
   + L1/L2/L3 continuation
   + dashboard / LoRA / energy
```

文件级核对：

- `e8_lattice.cuh`：**三树字节相同**。
- `e8_root_codec.cuh`：tensorninja ≡ sergiuszm；UDP 多了 `bfi.b32` + `redux.sync.add`（只加速 **rk2v4-e8** 的 cylinder root 编码）。tensorninja 文档写明：现网 `rk4v4-e8` 走 `kv_e8_lattice`，**不走** root 编码器。
- sergiuszm 09-04 把 attention 重构成 `src/ops/softmax_attention/...`，**没有** `gqa_attention_prefill_i8.cuh`。tensorninja 仍是旧布局 + Ada retune。整树 merge 成本极高。
- UDP `DirectStorageEngine` 整文件 `#if defined(_WIN32)`；`disk_state_cache.cpp` 的 DMA 路径同样 Windows-only。Linux 4090 上无收益。
- tensorninja **没有** `--auto-long-anchors`（sergiuszm 09-02 才加）。现网用的是 `--prefix-checkpoint-policy rolling-tool` + continuation L1/L2，语义相近但不是同一套锚点。

sergiuszm 自己的 `docs/maintainer/port-ledger.md`（2026-09-04 扫）：UDP 约 30 条 09-01/09-02 kernel 优化 **bench-first**；此前 Q4/Q5 shuffle 在 Linux CUDA 13.1 sm_89 上测到 Q5 **-52.6%**，已拒绝。tensorninja 的 `docs/udp-fork-comparison.md` 是同一结论的上游记录。

---

## 3. 社区口径 vs 本机口径（不要对错数字）

| 来源 | 数字 | 条件 | 对本机的含义 |
|---|---|---|---|
| sergiuszm README | **148.6 t/s** | greedy 代码、MTP3、INT8 KV、浅上下文、`/metrics` | 峰值代码接受率 ~81%。本机 Agent/HTTP 采样 4k 约 117、184k 约 87–98 |
| UDP README | **229.9 t/s** | greedy MTP7、32k、`rk4v4-e8`、100% draft accept | 结构化 greedy 才成立。本机 n=5 采样长上下文 **76 t/s** |
| UDP | DirectStorage 77k restore 150 ms | Windows WDDM + DS 1.3 | Debian 4090 无 D3D12，不移植 |
| UDP Reddit 08-16 | 250–350K ctx、80–160 t/s 重复负载 | rk2v4-e8，作者卡 | 容量方向可借鉴；质量要用 Java/针，不只 NIAH |
| tensorninja HN (netsroht) | 149 t/s decode、prefill >2500、262k、缓存层、J/tok | 水冷 4090、64G RAM | 与现网同一作者线；INT8 prefill + L1/L2 已在镜像里 |
| r/LocalLLaMA 2×4090 | 80–100 TG @256K + llama-swap metrics | 另一用户 | `/metrics` 已在 tensorninja |
| llama.cpp 社区 | DFlash2 150k ~77 t/s；MTP GGUF 130k ~60 | GGUF 路线 | 本机 WORK 184k **38 t/s**，NInfer 已明显快 |
| Escha X | W2+MTP 4090 129 t/s | 另一权重/运行时 | 不混进 NInfer 数字 |

**本机 Agent 最优看 Java 墙钟 + 184k 采样 decode，不看 greedy MTP7。**

---

## 4. 现网已经合入、不必再搬的

来自 sergiuszm：

- sm_89 CMake/runtime gate
- Ada INT8 attention prefill retune（fp16-acc PV、128 reg、producer warp）
- causal-tile 内部分区（UDP `c5f70526` 的思想，在 retune kernel 里重写）
- llama.cpp `/metrics` `/slots` `timings`
- rolling-tool 前缀检查点

来自 UDP：

- `rk8v4` / `rk4v4` / `rk4v4-e8` / `rk2v4-e8`
- E8 lattice + cylinder codec（含 hardening `bc569eb8`）
- 262k–1M visible-keys 信封
- `--vision-max-tokens`

tensorninja 独有、sergiuszm/UDP 都没有或明显弱：

- 六路 dense GEMM 的 **prefill-only INT8 MMA**（decode 仍 BF16，bit-identical）
- continuation cache L1 GPU / L2 host / L3 disk（POSIX，跨容器 volume）
- dashboard + energy
- 运行时 LoRA（本机 OpenClaw 暂不用）

现网启动（`4090_ninfer_start.sh`）：

```
--max-context 221184 --kv-capacity 221184
--max-concurrency 1 --kv-dtype rk4v4-e8
--spec mtp --draft-tokens 3 --lm-head-draft
--prefix-checkpoint-policy rolling-tool
--continuation-cache l1-l2
--continuation-cache-l1-mib 6144 --continuation-cache-l2-mib 8192
--preserve-thinking   port 18030
```

作者 README 默认是 **ctx 262144 + L1 768 MiB + L3 disk**。我们把 L1 拉到 6 GiB，所以 qualify 时 ctx 收到 221184。这是 **缓存 vs 窗口** 的显存权衡，不是漏了 262k 能力。

---

## 5. 可借鉴清单（按可行性）

### P0 配置（零源码，已部分完成）

| ID | 改动 | 可行性 | 预期 | 风险 |
|---|---|---|---|---|
| A1 | `--draft-tokens` 3/4/5 | **已测完** | 默认 **3**；4 仅 184k 略升；5 有害 | 无 |
| A2 | ctx/kv **262144**，n=3，仍 `rk4v4-e8`，L1 先保持 6144 | 高；可能 OOM | 作者声称 1.37 GiB slack（L1=小）。我们 L1=6G，**可能装不下** | OOM → 立刻 restore WORK，再扫 L1 768/2048/4096 |
| A2b | 262k 成功后再开 L3（`--continuation-cache l1-l2-l3` + 已有 `/var/cache/ninfer`） | 高 | 重启后冷会话 TTFT 接近 UDP 宣传的 disk restore，但是 POSIX 拷贝不是 DS DMA | 磁盘磨损、脏 cache |
| A3 | `--kv-dtype rk2v4-e8` 同容量或冲 300k+ | 中 | 每 token ~19 KB vs rk4 ~26 KB；NIAH 作者 314k/360k 过 | cosine 96.2%；Agent 代码质量未知。必须 Java+多针 |

### P1 隔离 cherry-pick（值得，但要在 A2 之后、单独镜像 tag）

| 来源 | 改动 | 可行性 | 做法 |
|---|---|---|---|
| UDP `11aae2d` | `e8_root_codec.cuh` bfi/redux | **高、补丁小** | 只对 **A3 rk2v4-e8** 编码热路径有意义。`rk4v4-e8` 现网几乎无感。先 A3 质量过关再拣 |
| UDP `39a6f20` | T=1 draft-head → Ada MMA double-buffer | 中 | 与 tensorninja INT8 prefill 文件可能冲突。**必须** kernel bench + 本机 HTTP 阶梯。同类 Q4/Q5 优化已在 Linux 上回退 |
| UDP `9e4ca72a` | GQA decode grid 1-wave / reg cap | 中 | 同上，bench-first。sergiuszm ledger 点名从 `45a5ae57` SM-count 开始 |
| sergiuszm `9f63c77b` | `--auto-long-anchors` | 中高 | Pi/OpenClaw 会改写最近 user/tool 块。tensorninja 的 rolling-tool 管 tool 前沿，**不管**客户端把 reminder 挪到最新 user 消息。作者自己测过 46.7k：reuse 0→46552、TTFT 16.6s→0.59s。这是 Agent 真需求。不能整树 merge，要 **设计移植** 到现网 `program_impl` / frontend |
| tensorninja 自己未开的 L3 | 见 A2b | 高 | 不是 fork 差异，是我们没开作者默认 |

### P2 明确不做 / 以后再说

| 项 | 原因 |
|---|---|
| UDP DirectStorage / D3D12 / WDDM | `_WIN32` only；Debian 无对等 DMA |
| UDP MTP K=7..15 当默认 | 本机 n=5 已掉速；greedy 100% accept ≠ sampling |
| UDP Q4/Q5 shuffle / bfe 微优化 | tensorninja 在 **同卡 Linux** 测到大回退 |
| sergiuszm 09-04 `neroued/master` 整树 merge | attention 目录重写；`6f327f4` 就是 merge 后 E8 decode 读错 partial（垃圾 logits、MTP accept 0）。tensorninja 现网用 `cache.dtype == I8` 分发，**没有这个 bug**。merge 会引入 bug 再修，并可能打掉 INT8 prefill |
| 切 sergiuszm 镜像当生产 | 丢掉 2409 t/s prefill 与 L1/L2，得不偿失 |
| 切 UDP 镜像 | Windows 工具链、无 continuation L1/L2、无 Ada retune 深度 |
| 19G DFlash2 `.ninfer` | 制品合同分叉；现网 loader 校验旧 SHA |
| 替换 18343 WORK 默认 | 必须 A2+Java+184k **同时**优于 WORK 再谈 |
| xkeyC host prefix cache | 多会话 200K 旋转 TTFT 4.36s vs 冷 150s，对本机单用户优先级低于 A2/A3/anchors |

---

## 6. 「最佳版」目标形态

**二进制：** 继续 `ninfer-4090:44a2c6c`。只有 P1 拣入后才打新 tag（例如 `ninfer-4090:44a2c6c-e8bfi`），旧 tag 保留可回滚。

**推荐服务档（A2 成功后的目标，A2 失败则回退）：**

```
ninfer-serve … \
  --max-context 262144 --kv-capacity 262144 \
  --max-concurrency 1 --max-pending-requests 8 \
  --pending-timeout-ms 600000 --prefill-chunk 1024 \
  --kv-dtype rk4v4-e8 \
  --spec mtp --draft-tokens 3 --lm-head-draft \
  --prefix-checkpoint-policy rolling-tool \
  --continuation-cache l1-l2-l3 \
  --continuation-cache-dir /var/cache/ninfer \
  --continuation-cache-l1-mib <A2 扫出来的最大不 OOM 值> \
  --continuation-cache-l2-mib 8192 \
  --preserve-thinking
```

并发保持 **1**：现网是单用户 Agent；fork Docker 默认 4 会让深 prefill 堵死队列。作者自己也写深 prefill 串行。

**质量档（仅当 Java 与 184k 针不回退）：** 另备 `rk2v4-e8` 冲窗口，不当默认。

---

## 7. 具体改造步骤

### 7.1 零源码（现在就能做）

1. A2：`NINFER_KEEP=0 DRAFT_TOKENS=3 NINFER_CTX=262144` 走现成 `run_fusion_a2.sh`。trap restore WORK。
2. 若容器 `Exited` / `cudaMalloc`：不要反复重试。改 L1：6144→4096→2048→768，每次只改一个旋钮。
3. A2 稳态后再 A2b 开 L3，用同一套 HTTP 阶梯 + cache-append，看重启后 TTFT。
4. A3：`NINFER_KV=rk2v4-e8`，ctx 先 262144 再尝试 300k（模型 native 仍是 262144，超过是 RoPE/信封问题，**先不要 YaRN**）。

### 7.2 若要动源码（A2 完成且仍不够）

工作树：本机 `output/qwen38-27b-4090-ninfer/ninfer-4090`，**不要**在 4090 上 git clone。Mac 改完 `scp` Dockerfile 构建上下文，或 `docker save` 后丢过去。

顺序：

1. **只拷** UDP `e8_root_codec.cuh` 的 bfi/redux hunk 到 tensorninja 同文件（lattice 文件不动）。跑 `ninfer_test_e8_codec` + 本机已有 `tests/ops/test_e8_root_codec.cu`。
2. draft-head MMA：单独 commit，镜像 tag 不同。对照 kernel：`ninfer_q4_linear_*` / draft_head bench，再跑 HTTP 4k/64k/184k。任何一档 decode 掉 >3% 就丢弃。
3. auto-long-anchors：对照 sergiuszm `serve_options.cpp` + frontend 消息边界，接到现网 Engine 的 continuation 模型。这不是 cherry-pick，是 2k 行级设计移植。做之前用 Pi 抓一发「把 reminder 拼进最新 user」的真实请求，证明 rolling-tool 复用为 0，再开工。

构建约束保持：`Dockerfile.sm89-nobake`、CUDA 13.2 镜像、不烤权重、hf-mirror、不碰 18343。

---

## 8. 测试验证方案

互斥：NInfer 占卡时停 WORK；结束 **必须** `4090_ninfer_stop_restore.sh`。端口 18030，隧道本机。`NINFER_KEEP=0` 强制重建，避免假档。

**每档相同 harness**（已有）：

| 层 | 命令 / 产物 | 通过线（相对 n=3 / 221184 基线） |
|---|---|---|
| 启动 | `docker logs` + `nvidia-smi` | 不 OOM；权重 SHA 仍 `eec39564` |
| HTTP 阶梯 | `http_bench.py` thinking=off | 4k/64k/120k/184k decode **不低于** 117/98/102/**87.5** 的 95%；针全中 |
| cache | `cache_bench.py` | append TTFT ≤ 3.5s ±20% |
| Agent | Pi Java 三题 + tools 环 | 3/3；p50 墙钟 ≤ 31s +15% |
| medium | 可选 `run_medium_suite.sh` 只跑 ninfer | 184k decode 不低于 98 t/s 的 95% |
| 指标 | `GET /metrics` + request JSONL | 记录 `prefill_tok_s`、`draft_n_accepted`、cache restore 来源 L1/L2/L3 |

**A3 额外：** 5-needle @118k 与 184k；Java 三题输出 hash 与 n=3 rk4 对照（允许文本差，不允许 verify.sh 失败）。

**停止条件：**

- 启动 OOM / 健康检查失败 → restore WORK，记档，改 L1 或放弃该 ctx。
- 184k decode < 80 t/s 或 Java 任一失败 → 该档不作候选。
- 任何时候不切 18343，除非用户明确要求且 Agent+184k 双赢。

监控：每档 nohup + 10 分钟 scheduler（沿用 A1 做法），SSH 断了靠 trap/脚本 restore，不靠会话。

---

## 9. 决策摘要

| 问题 | 答案 |
|---|---|
| 部署的是哪棵树？ | tensorninja@44a2c6c，不是 sergiuszm，不是 UDP |
| sergiuszm 还剩什么？ | 上游 merge 后的 attention 重构（不要整树）；`--auto-long-anchors`（Agent 改写历史时值得设计移植） |
| UDP 还剩什么？ | rk2v4 容量、E8 root 编码微加速、若干 decode MMA（要测）；Windows DS **无** |
| 融合策略 | 配置优先 → 小补丁 → 锚点设计移植。禁止第四棵树 |
| 已完成 | A1 draft 3/4/5 → 保持 3 |
| 下一步 | A2 262144 |

未跑：A2/A3、任何 cherry-pick 构建、Pi 在 262k 上的复测。
