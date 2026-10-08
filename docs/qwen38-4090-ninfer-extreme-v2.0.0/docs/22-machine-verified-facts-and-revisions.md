# 实机复核事实、决策记录与本次修订清单（2026-09-09）

本文是执行 AI 的**事实基线**：以下内容来自 2026-09-09 对 `hhtele@192.168.10.29` 的只读 SSH 复核、对 44a 源码与上游文档的逐行核对，以及用户当日的两项决策。与包内其他文档冲突时，**以本文为准**；本文未覆盖的部分仍以原文档为准。本文不替代 T00 的 runtime-lock：T00 仍须重新采集并与这里逐项对照，差异即重新锁定。

标注：`[实测]` 亲自执行命令观察到；`[源码]` 读 44a/上游源码或文档得到；`[推断]` 由实测数字按公式推算，未上机验证；`[决策]` 用户明确决定。

## 1. 两项决策

### 1.1 受保护容量 262144 → 200192 `[决策]`

- 用户原话："262144 是可以让，我的底线是保证性能的同时，窗口 200K 左右就行。"
- 原因：DFlash2 W8 companion 在 262144 预算内显存不成立（§3）。降到 200192 释放 ≈1597 MiB，DFlash2 W8 后预计仍有 ≈1.2 GiB 余量。
- 含义：
  - `tools/metrics.py::PROTECTED_CAPACITY=200192`；`candidate_gate` 对 capacity<200192 判 `TRADEOFF_ONLY`，≥200192 通过。
  - **生产现网仍是 262144**，它是基线与回滚点，本决策不改生产；候选 profile 的目标是 200192。
  - 候选若仍能装下 262144，作为事实记录（加分项），不是通过条件。
  - rk8v4 与 DFlash2 W8 争的是同一块 ≈1.6 GiB 显存（§3.3），200192 下二者**不能同时要**；DFlash2 上限更高，先走 DFlash2，rk8 作为 T03 的对照组与备选。
  - 容量硬门验证：实际 prompt ≈196000 + 输出 ≥2048，总含模板 ≤200192（docs/02 §3、docs/12 L5）。
  - Pi `contextWindow` = 200192（`configs/pi-models.example.json`）。

### 1.2 GPU 主机权限已配置并验证 `[实测]`

由用户以 root 执行、由 Claude 经 SSH 复核（2026-09-09 下午，UTC+8）：

| 项 | 状态 | 证据 |
|---|---|---|
| `/etc/sudoers.d/qwen38-extreme-lab`（0440 root） | 已配置 | `hhtele ALL=(root) NOPASSWD: /usr/bin/systemctl stop openclaw-qwen38-ninfer.service, /usr/bin/systemctl start openclaw-qwen38-ninfer.service` |
| 规则生效顺序 | NOPASSWD 排在原有带密码 `(ALL : ALL) ALL` 之后 → sudo "最后匹配生效"，stop/start 免密 | `sudo -n -l` 完整列表 |
| 真实免密验证 | `sudo -n systemctl start openclaw-qwen38-ninfer.service` 退出 0、无提示；unit 已 active 故为 no-op：`ActiveEnterTimestamp`/`NRestarts=0`/容器 `Up 5h` 前后不变，18343 `/v1/models` 200 | 同上 |
| 未变成全免密 | `sudo -n -v` → `a password is required` | 同上 |
| `systemd-journal` 组 | hhtele 已加入，新登录生效；`journalctl -u openclaw-qwen38-ninfer.service` 可读 Stopped/Started 记录 | `id -nG` |
| `~/qwen38-vllm/models/*`（vLLM W4 目录） | 已 `chown -R hhtele`；不可读文件数 0 | `find ... ! -readable \| wc -l` = 0 |
| `RmProfilingAdminOnly` | 仍为 1（**不改**）；ncu 走容器 `--cap-add=SYS_ADMIN`（§4.6） | `/proc/driver/nvidia/params` |
| `kernel.perf_event_paranoid` | 3（**不改**）；只影响 nsys CPU 采样，CUDA trace 不受影响 | `/proc/sys/kernel/perf_event_paranoid` |
| 旧 `~/qwen38-dflash2-20260819/launch/sudo-wrap.sh` | 含明文密码的历史路径，本包**不再使用**；是否删除/轮换由用户决定 | — |

**注意**：`sudo -n -l <命令>` 在存在任一 NOPASSWD 条目后（`listpw=any`）会对**任何**被允许的命令打印路径，包括带密码的 `(ALL:ALL) ALL` 覆盖的命令，因此它只能证明"允许"，不能证明"免密"或"够窄"。`remote_guard.py` 用它做预检是合理的（拒绝完全无权限的情况），但验证免密要看真实 no-op 命令或 `sudo -n -v`。

## 2. 实机与源码事实（2026-09-09 只读复核）

### 2.1 机器与生产身份 `[实测]`

| 项 | 实测 |
|---|---|
| GPU | RTX 4090，24564 MiB，`ninfer-serve` 常驻 22592 MiB，**free 1509 MiB**（差额 ≈463 MiB 为驱动保留） |
| 驱动 / UMD / 宿主 nvcc / 容器 | KMD 610.57.04 / 13.3 / `/usr/local/cuda-12.3/bin/nvcc` 12.3.107 / `nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04`（含 `ncu`，无 cmake/ninja；Dockerfile 自行 apt 装） |
| PCIe | gen.max=3，width 16（空闲时 gen 1） |
| CPU / RAM / 磁盘 | Xeon Silver 4216 16C32T；62.5 GiB（avail ≈48）；915 GiB / 557 GiB 空闲 |
| 系统 / JDK / Python | Debian 12.2 / 17.0.20 / 3.11.2 |
| unit / 容器 / 镜像 | `openclaw-qwen38-ninfer.service`（唯一 enabled 的 openclaw unit；另有 executor、qwen36-mtp4-128k、qwen38-text、qwen38-work-64k 四个 disabled unit）/ `ninfer-4090-prod` / `ninfer-4090:44a2c6c`；`Restart=always`，`ExecStop=docker rm -f` |
| 端口 | 18030 绑 127.0.0.1（原生）；18343（compat proxy）与 28343（NGINX）绑 0.0.0.0；两端口 `/v1/models` 均返回 `openclaw/Qwen3.8-27B-WORK`，`context_window 262144`，`vision:false` |
| 候选端口 18041/18042 | 空闲 |
| artifact | `/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer`，18210531328 B（sha 未复算，避免 18 GB 生产 I/O）；1124 对象；按前缀：`text` 16.252 GiB、`mtp` 0.420 GiB（W8G32）、`vision` 0.275 GiB、`frontend` 0.012 GiB |
| 启动参数 | `launch/production-18343.sh`：`--max-context 262144 --kv-capacity 262144 --kv-dtype rk4v4-e8 --spec mtp --draft-tokens 3 --lm-head-draft --prefill-chunk 1024 --continuation-cache l1-l2`（L1 6144 / L2 8192）`--prefix-checkpoint-policy rolling-tool --preserve-thinking --default-max-tokens 32768`，单并发 |
| 日志 | `/var/log/llama/openclaw-qwen38-ninfer.{,err.}log`，root 0644，hhtele 可读；`NINFER_ENGINE_READY` ≈28 s（页缓存热） |
| `~/ninfer-4090` | 不是 git 仓库（PINNED_COMMIT=44a2c6c）；`references/base-source-audit.json` 9 个文件 sha256 全部一致 |
| 上游分支 | `tensorninja/ninfer-4090`：`tensorninja`=44a2c6c；另有 `rtx4090-port`=981b685（包此前未提及，T00 记录两分支关系） |
| docker | hhtele 在 `docker` 组；daemon apparmor+seccomp+cgroupns，cgroup driver systemd |
| Mac 控制端 | Pi 在 `~/.nvm/versions/node/v22.19.0/bin/pi`（v0.85.1；`--approve/--thinking/--tools/--no-skills` 均存在）；4090 上 `which pi` 为空；Mac JDK 25（原题含 record，JDK17+ 均可编） |

### 2.2 44a 源码事实 `[源码]`

| 事实 | 位置 |
|---|---|
| small-T 专用 decode attention 只编译 T=1..6 | `src/CMakeLists.txt:278 foreach(token RANGE 1 6)`；`gqa_attention_decode.cu:19/239/243`（`#error [1,6]`、`uses_small_t tokens<=6`、`tokens>6 → throw`） |
| `--draft-tokens`：MTP 1..5，DFlash 1..15 | `docs/serving.md:571` |
| rk4v4-e8 读路径是 PackedK unpack；`e8_root_decode_8d_int8` 属 rk2；lattice 是 encode-side codec；半陪集近似注释 | `gqa_attention_decode_i8.cuh:235/257/269/420/437`；`docs/maintainer/prefill-throughput-plan.md:719-720` |
| **exact rejection sampling 已实现**（T>0 distribution-correct，one-hot draft accept `p(d)`，首拒 masked residual resample，末列 bonus） | `src/ops/kernel/speculative_round.cuh:60-68` |
| **请求级遥测已实现**：`/metrics` 有 `ninfer:draft_accepted_tokens_total`、`llamacpp:prompt_tokens_total`、`prompt_seconds_total`、`prefill_energy_joules_total`；请求结果含 `speculative_accepted_tokens`、`reused_prompt_tokens`、`cached_tokens`；compat proxy 注入 `usage.prompt_tokens_details.cached_tokens` | `tests/test_serve_metrics.cpp:145-214`；`concurrent_executor.h:1514/3114`；`apps/serve/openai_compat_proxy.py` |
| 尚无的遥测：**每轮** `round_ms / physical W / live Q / licensed / committed / origin / catchup_ms` | — |
| DFlash 骨架是 35B-A3B 的 v1；27B `enable_dflash=false`；有 `local_layers/pending_features/full.layers()==1`，**无** dynamic conv / selector | `round_state.h:26`；`dflash_context_impl.h` |
| MTP 与 DFlash 互斥 | `round_state.cpp:26` |
| **DFlash 后端无 session persistence**：`speculative_backend==DFlash → throw invalid_argument("session persistence …")`；serving 文档写明 "The DFlash backend is not supported" | `session_snapshot_impl.h:342/534`；`docs/serving.md:130` |
| 进程内 L1/L2 image 已为 DFlash ring 预留字段（`dflash_local / dflash_checkpoint_local`），但持久化/快照未做 | `continuation_image.h:683-711` |
| `mtp_bridge_and_propose` 存在并被 program/text_prefill 调用 | `mtp_impl.h:13`；`program_impl.h:2888/2989`；`text_prefill_impl.h:138` |
| `text/draft_head [131072,5120] Q4` 在 artifact 中（`--lm-head-draft`）；`frontend/tokenizer.json` 12.8 MB 可抽取 | artifact 目录 |
| 源码中无 lookup/ngram/suffix | grep |
| L1 6144 MiB 不是独立显存池（retained GPU lanes 用启动时固定的共享 KV pool） | `docs/continuation-cache.md:52` |
| INT8 prefill GEMM 已实现（1.68× 聚合、e2e 1.435×，上限 1.76×）；GQA prefill attention 在混合天花板的 41%；冷 prefill 184K 已是 BF16 tensor-core 天花板的 ~75%，launch/sync 仅 1.5% | `docs/maintainer/prefill-throughput-plan.md` |

### 2.3 上游 / 外部合同 `[源码]`

- `Neroued/ninfer@b88c0f6` `qwen3.8-27b-dflash2.md`：K=1..15、B=1..8、eager/graph、Text/Vision、Device/Host；top-16 / rank 256 / 40 MiB ring（5×2048×8×128×4 B）。
- `qwen3.8-27b-artifact.md §7.4`：66 对象 `dflash2/` suffix，feature/attention/MLP 为 W8G32_F16S，norm/dynamic conv/selector BF16；旧 1124 对象文件合法且缺 DFlash2。
- HF `z-lab/Qwen3.8-27B-DFlash2@50307d4c`：5 层 / 5120 / 17408、32Q/8KV/128、taps [5,19,33,47,61]、SWA 2048、非因果、mask 248070、vocab 248320——逐字段一致。
- 报告 09/11/12 数字：112/111/110/87.2；127.1/110.6/115.4/98.5；145/129/117/103.7；92.2 vs 94.1 s；85% 复用；报告 12 Java 3/3 沿用上一轮——逐条一致。
- SageAttention 仅支持 head_dim 64/128；本目标 d256。

## 3. 显存账（CPU 可算，T08 loader plan 实测确认）

### 3.1 DFlash2 companion 常驻（按上游 66 对象 inventory 逐项累加）`[推断]`

| 组件 | 计算 | 常驻 |
|---|---|---|
| `feature_projection` [5120,25600] W8G32 | 131.1 MB + scales 8.2 MB | 0.130 GiB |
| 5 层 × (qkv 6144×5120 + o 5120×4096 + gate_up 34816×5120 + down 5120×17408) W8G32 | 319.8 MB/层 + scales 20 MB + conv `kernel_projection` BF16 26 MB | 0.341 GiB × 5 = 1.705 GiB |
| selector 两个 codebook [248320,256] BF16 | 254 MB | 0.237 GiB |
| **合计** | | **2.074 GiB = 2124 MiB**（与 19.03−16.96 文件差一致） |

常驻差（DFlash2 时不加载 MTP）：+2124 − 430 + 40（ring）= **+1734 MiB**，另加 W8 verify 的 logits/head 工作区、pending features、CUDA Graph 与 draft attention 工作区 **估 50–150 MiB**（精确值由 T07 `width-audit.json` 与 T08 loader plan 给出）。`vision` 0.275 GiB 不可拿来省（`vision:false`，很可能本就未 materialize）。

### 3.2 两个容量下的余量 `[推断]`

| 容量 | KV 释放（rk4v4-e8 ≈26.4 KB/token，`udp-fork-comparison.md:53`） | 空闲 | 加 DFlash2 W8 后余量 | 判定 |
|---|---|---|---|---|
| 262144 | 0 | 1509 MiB | **−225 … −325 MiB**（零余量都不够） | 不成立 |
| 200192 | 61952 token × 26.4 KB ≈ **1597 MiB** | ≈3106 MiB | **≈1222–1322 MiB** | ≥512 硬门、≥1 GiB 偏好 均满足 |

因此 draft 主体 W4（原 T08 fallback：companion ≈1.22 GiB，余量 ≈550 MiB 压线且会改变 q/AL）**不再是主线需要的路径**，仅当 T08 loader plan 实测余量 <512 MiB 才开。

### 3.3 rk8v4 与 DFlash2 的互斥 `[推断]`

rk8v4 相对 rk4v4 每 token 多 16 层 × 4 KV head × 256 × 4 bit = 8 KiB → 200192 × 8 KiB ≈ **1564 MiB**，正好吃掉 200192 释放的 ≈1597 MiB（这也解释了报告 11/12 为何把 rk8 配到 200192）。所以 200192 下 rk8 与 DFlash2 W8 只能选一个。

### 3.4 L2 image 预算影响 `[推断]`

DFlash2 profile 若要保住热 TTFT（§4.3），每个 L1/L2 continuation image 需多带 40 MiB ring（含 turn checkpoint 再翻倍）；L2 8192 MiB 下可存 image 数约少 10%。计入 T10 的 RAM 账。

## 4. 对计划有实质影响的复核结论

### 4.1 DFlash2 链的关键路径是 T07（W8 路径），不是 T08/T09 `[推断，公式可查]`

- DFlash2 每轮固定开销：draft 权重读 2.07 GiB ≈ 2.2–2.4 ms/轮（4090 实效 ~900 GB/s），MTP 0.42 GiB ≈ 0.5 ms → **净 +≈2 ms/轮**。
- 现网轮时：184K ≈ 29 ms（98.5 t/s ÷ AL≈2.9 ≈ 34 轮/s）、4K ≈ 23 ms（127.1 ÷ 2.9）。打平需 committed/轮 +7%（184K）/ +9%（4K）。
- 模型卡同 K 下 DFlash2 对 MTP 的 AL 增益 +8.8–20.1% → **同 K=3 换 drafter 净收益约 0–12%**，接近噪声。DFlash2 的实质收益只能来自 **K=7（W8）的宽度**。
- 4-bit KV 下 W 从 4 到 8 的 verify 读字节几乎不变（184K × 26.4 KB ≈ 4.9 GB/轮），W8 的额外代价主要在 draft 与 head 计算 → W8 在长上下文更划算。
- **结论**：T07 必须在 T09/T10 之前拿到 W8 route 的 184K 轮耗时；若 W8 verify 每轮额外成本 > 预期 AL 收益能覆盖的范围，DFlash2 链降级为可行性研究。

### 4.2 T10 的会话持久化是新功能 `[源码]`

44a 对 DFlash 后端的 session save/restore 显式抛错（§2.2）。现网 85% prompt token 靠前缀复用（报告 10），热命中 TTFT 1.1 s vs 全重算 21 s（报告 12）。DFlash2 profile 若没有等价恢复能力，每次会话切换/重启退回全重算，`task_wall_ratio > 1.02` 直接 `NO_MEASURABLE_PRODUCT_GAIN`。T10 因此必须：解除 `session_snapshot_impl.h` 的 DFlash throw；L1/L2 image 含 40 MiB ring + pending；A→B→A 会话切换后 `reused_prompt_tokens` 与 MTP profile 相同。

### 4.3 Suffix+MTP 有零 bridge 成本的第一版 `[设计]`

MTP 常驻照跑、每轮仍产 3 个 greedy 草稿（状态照常前进）；suffix 索引在 `[committed…, d1, d2, d3]` 之后查最长匹配，把链延长到 K≤5（W≤6，恰在 small-T 1..6 与 `--draft-tokens ≤5` 范围内），延长部分 q 为 one-hot 走现有 sampler。零 MTP 状态修改、零 bridge、零新 kernel、零新权重；GPU 侧只有 draft 数组长度可变（`live_proposals ≤ 5`）。上限 W=6 是 T12（W16）的动机。包原设计（alternating-source + bridge）降为第二版，仅当第一版显示命中率足够才做。

### 4.4 T02 / T04 是扩展，不是新建 `[源码]`

exact rejection sampling 与请求级遥测已在 44a（§2.2）。T04 真正新的是 `Sparse16`（DFlash2 selector 的实际条件 q），PointMass 路径直接复用 `speculative_round.cuh`；T02 只缺每轮字段。

### 4.5 统计门 `[方法]`

原 `paired_summary` 允许 n≥3 的 percentile bootstrap；n=5 只有 3125 种重采样，CI 明显偏窄，而 "95% 下界 ≥3%" 整个判定建在它上面。现改为：配对数 ≥8（`MIN_GATE_PAIRS`）；CI 取 percentile bootstrap 与 log-ratio Student-t 区间中更保守者；`candidate_gate` 新增必填 `paired_n`（<8 → BLOCKED）与 `aa_noise_abs`（A/A 同 harness 同桶的 max|ratio−1|，>0.03 → BLOCKED）。

### 4.6 一小时筛选的算术 `[推断]`

184K 冷 prefill 94 s + 1024 token 解码 ≈11 s ≈ 105 s/样本；8 配对 ABBA = 16 次 ≈ 28 min；baseline/candidate 不能同驻，每次切换重启 ≈40 s（就绪 28 s + 图捕获）×16 ≈ 11 min → **一个 184K 桶 ≈40 min**。原表"15 分钟做 4K/64K/184K 三桶各 5 配对"做不到。docs/12 §2 已按"一轮一个长度桶"重排。

### 4.7 ncu 的实操路径 `[实测]`

hhtele 在 docker 组，devel 镜像内有 `ncu`：`docker run --rm --gpus all --cap-add=SYS_ADMIN -v <lab>:/lab nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04 ncu --set basic -k <kernel> <binary>`。不改 `RmProfilingAdminOnly`。ncu 运行只计 diagnostic，不进 ABBA。宿主只有 `nsys`（CUDA trace 可用；CPU 采样受 `perf_event_paranoid=3` 限制，不改）。

### 4.8 工期尺度 `[推断]`

按 44a 代码量与任务内容：T00–T03 1–2 周；Suffix 链 v1（T04–T06）2–4 周；DFlash2 链（T07–T10）6–10 周；W16（T12）2–4 周；d256（T13）4–8 周。全包串行约 4–7 个月一人。不是承诺，是让用户知道"极致"在这份包里的时间尺度；每阶段以产物验收界定完成。

## 5. 本次修订清单（包内文件 → 变更）

| 文件 | 变更 |
|---|---|
| `AGENTS.md`、`AGENT_START.md`、`PROMPT_FOR_AI.md`、`README.md` | 200192 决定；sudo 已配；阅读顺序加入本文；路线顺序 |
| `docs/00` | §2.1 rk8 结论按决策更新；新增 §2.11–2.15（显存账、持久化缺口、已有能力、Suffix v1、T07 关键路径）；§3 路线顺序 |
| `docs/01` | 事实表补 2026-09-09 复核项；生产身份区分"生产 262144 不动"与"候选 200192" |
| `docs/02` | §1/§3 200192 与决策记录；工程补丁门 ≥8 配对 + 保守 CI + A/A 噪声底 |
| `docs/04` | §2 sudo 已配置与验证方法；§3 显存轮询与 18030 健康；§5 ncu 实操命令 |
| `docs/05` | 注明 44a 已有 exact rejection sampling，T04 为扩展 |
| `docs/06` | §2–§5 改为链延长 v1；alternating + bridge 降为 v2 |
| `docs/07` | §3 显存账与 200192 结论替换"计算后才知道"；§4 顺序前置 W8 路径门；新增 §8 会话持久化、§9 有界估算 |
| `docs/03` | 注明 bridge 段只对 T06 v2 生效 |
| `docs/08`、`docs/09`、`docs/14` | 262144/262K → 200192 |
| `docs/11` | §1 注明 request 层已基本可用；§3/§6 配对数与 A/A |
| `docs/12` | §2 筛选表按算术重排；§3 L5 200192；§5 加 BLOCKED 条件 |
| `docs/13` | Pi 真实路径与版本；`contextWindow` 200192 |
| `docs/16` | §3 停止点加入 W8 route 门与本机数字；§4 工期量级 |
| `docs/17` | 全局约束 200192；执行顺序（T07 前置）；任务目录依赖同步 |
| `docs/19` | `long_prompt --tokens 196000`；gate 新字段说明 |
| `docs/21` | §2/§3 200192；§3 附实际显存账；§4 换成本机有界估算 |
| `tasks/T00` | 显存账/分支关系/W4 目录哈希（现已可读） |
| `tasks/T01` | sudoers 前置改为"已配置，演练前复核"；健康检查含 18030 |
| `tasks/T02` | 标题与范围改为"扩展每轮字段"，列出已有指标 |
| `tasks/T03` | rk8@200192 与 DFlash2 的二选一决策；显存账实测确认 |
| `tasks/T04` | 标题与范围改为"扩展现有 sampler 增加 Sparse16"，加逐位回归断言 |
| `tasks/T05`、`T06` | T05 查询含草稿、200192；T06 重写为链延长 v1（v2 条件启动） |
| `tasks/T07` | 前置为 DFlash2 收益门（`Δ_w8` + `width-audit.json` gate）；依赖改为 T01；enabled |
| `tasks/T08` | W4 fallback 降为条件实验；200192 |
| `tasks/T09` | 依赖含 T07 性能门 |
| `tasks/T10` | 会话持久化硬断言（新功能） |
| `tasks/T11` | 桶上界 200k |
| `tasks/T12` | 依赖改 T07 + T06 |
| `tasks/T15`、`T16` | 196K 探针/200192；T16 一轮一桶、≥8 配对、A/A |
| `configs/tasks.json` | 标题/依赖/enabled/路径与任务卡同步（T06/T07/T10/T12/T00/T02/T04） |
| `configs/local.example.json` | `pi_bin` 真实路径 |
| `configs/pi-models.example.json` | `contextWindow` 200192 |
| `contracts/qualification.schema.json` | 新增 `paired_n`、`aa_noise_abs` |
| `tools/metrics.py` | `PROTECTED_CAPACITY`、`MIN_GATE_PAIRS`、保守 CI、A/A 门 |
| `tools/remote_guard.py` | 显存释放轮询 ≤30 s；健康检查 18343+18030 |
| `tests/*` | 边界测试、guard 轮询测试、macOS `safe_child` 路径解析 |
| `references/CLAIM_AUDIT.md` | 附 2026-09-09 复核裁定 |
| `validation/empty-gate.json` | 新必填字段 |
| **2026-09-10 增补**：`AGENT_START.md`、`docs/12`、`tasks/T06`、`tasks/T07` | 记录 `output/qwen38-4090-compare/extreme_v2` 一次误执行（`--draft-tokens 5` 当 Suffix v1、`--spec dflash` 当 T07、5-token `none` 探针当吞吐样本、绕过 remote_guard）；T06/T07 加"什么不是本任务"；docs/12 §2 加有效 decode 样本最低条件；两条结论由"否决/未过门"改判 `BLOCKED: 未实现/未构建` |
| `SHA256SUMS` | 全部刷新 |

## 6. 仍未验证

- 18 GB artifact sha256 未复算（字节数一致）。
- W8 工作区/Graph 额外显存（50–150 MiB）是估计；DFlash2 draft W4 对 AL 的影响未测（上游只发布 W8G32 主体）。
- 所有性能数字来自既有报告或公式推算；未运行任何 GPU 进程、未暂停现网。
- T01 真实维护演练（停生产 1–2 分钟）需用户给出时间窗口后执行。
