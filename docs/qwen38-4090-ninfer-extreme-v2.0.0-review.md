# Review：`docs/qwen38-4090-ninfer-extreme-v2.0.0`（GPT PRO 方案）对照 4090 实机

- 审阅对象：`docs/qwen38-4090-ninfer-extreme-v2.0.0/`（137 文件；`SHA256SUMS` 135 项全部校验通过）
- 审阅日期：2026-09-09；机器：`hhtele@192.168.10.29`（RTX 4090，只读 SSH 巡检，未停现网、未加载模型、未跑 GPU）
- 报告放在包外（包内有 `SHA256SUMS`/`check_bundle.py`，加文件会破坏其自校验）
- 前序文档：`docs/qwen38-27b-4090-extreme-optimization-roadmap.md`（我的方案，本包的输入）、`docs/kern-sm89-4090-evaluation-and-poc-review.md`

---

## 0. 结论

**方向正确，事实层大体可靠，但作为"极致优化执行包"有三处会改变执行顺序的实质问题，其中一处按它自己的门禁会把最大的一条研发线（DFlash2，T07–T10）直接判成 `TRADEOFF_ONLY`/`BLOCKED`。**

1. **DFlash2 W8 + 262144 在这张卡上显存不成立**（本次用 artifact 目录 + 上游 inventory + `nvidia-smi` 算出，不需要 GPU 实验）：现网空闲余量 **1509 MiB**；DFlash2 companion 常驻 ≈ **2124 MiB**，不加载 MTP 只省 **430 MiB**，净增 ≈ +1.7 GiB（未计 W8 工作区）。缺口 ≈ 0.3 GiB（零余量）/ ≈ 0.8 GiB（按包内 ≥512 MiB 余量门）。要么降容量到 ≈ 225–230K（包定义为 `TRADEOFF_ONLY`），要么 draft 主体 W4（余量 ≈ 550 MiB，压线）。包把这项算账放在 T08 内部"实现后再算"，应前移到 T00/T03，并**先向用户要一个 262144 是否可让的决定**。
2. **44a 的 session persistence 对 DFlash 后端显式抛错**（`session_snapshot_impl.h:342/534`），`docs/serving.md:130` 也写明 "The DFlash backend is not supported"。现网 85% 的 prompt token 靠前缀复用（报告 10），T10 的"Device/Host 恢复"因此不是移植而是**新功能**；若做不到，DFlash2 profile 的热 TTFT 会从 ~1 s 退回 ~21 s（报告 12 的 full reset 数字），任务墙钟必输。包只把它列成一条测试项。
3. **治理层重、设计层薄**：19 个任务、约 30 个"计划创建"文件、`ninfer_lab_validate` 尚不存在；docs/06–09 每篇 2–4 KB，几乎全是约束与禁令，"怎么做"很少；一小时筛选的时间预算按现网实测算不出来（见 §4.3）。同时有几处"已存在能力被当成待建"（exact rejection sampling、`/metrics` 计数），以及一个可以省掉 MTP bridge 全部风险的 Suffix 变体没被考虑。

其余：`sudo -n` 在该机不可用（`remote_guard.py` 首次运行即 BLOCKED，需 root 配两条 sudoers）；Mac 上 Pi 真实路径是 `~/.nvm/versions/node/v22.19.0/bin/pi`（v0.85.1）而非示例的 `~/.pi/bin/pi`（这条错源自我的 kern review，一并修正）；`self_check.sh` 在 macOS 上 66 项中 1 项因 `/private/var` 解析失败。

对包内 `references/CLAIM_AUDIT.md` 中针对我方案的 28 条纠正：**C05/C08/C09/C10/C12/C14/C19 成立，我接受并在 §2 逐条确认**；C20/C28 归因于我的说法在我的文档里不存在（C28 把 `kern review` 的小节号 "9.4" 读成了评分）；其余为合理的护栏。

---

## 1. 本次 review 的证据来源

| 类型 | 做了什么 |
|---|---|
| 包内容 | 全部 137 文件读完（docs 00–21、tasks T00–T18、tools、tests、configs、contracts、references、validation、fixtures）；`SHA256SUMS` 135 项校验 OK |
| 4090 实机（只读） | `nvidia-smi`、systemd unit、docker ps/images、监听端口、`/v1/models`、`sudo -n -l`、artifact 目录头解析（1124 对象分组字节）、`~/ninfer-4090` 源码 grep/sha256、`docs/maintainer/*`、`docs/serving.md`、`docs/continuation-cache.md`、生产日志启动时间 |
| 上游源码 | `raw.githubusercontent.com`：`Neroued/ninfer@b88c0f6` 的 `qwen3.8-27b-dflash2.md`（27 KB）与 `qwen3.8-27b-artifact.md`（45 KB）；`tensorninja/ninfer-4090@44a2c6c` 的 `src/CMakeLists.txt`（sha 与本机一致）；`git ls-remote` 确认分支 `tensorninja`=44a2c6c |
| HF | `z-lab/Qwen3.8-27B-DFlash2@50307d4c` 存在（2026-08-19），`config.json` 全部字段核对 |
| 本地报告 | `output/qwen38-27b-4090-ninfer/reports/09,10,11,12`、`ninfer-4090/docs/udp-fork-comparison.md`、`docs/qwen38-4090-vllm-extreme-v1.0/fixtures`（23 文件 hash 与 `fixture-lock.json` 全部一致） |
| 包内工具 | 拷到 `/tmp` 跑 `scripts/self_check.sh`（macOS/Python 3.14）：65/66 通过 |
| 未做 | 未 sha256 18 GB artifact（避免生产 I/O；字节数 18210531328 与 lock 一致）；未启动任何 GPU 进程；GitHub REST API 被限流，改用 raw/ls-remote |

---

## 2. 事实核对：包内声明 vs 实测

### 2.1 机器与生产身份（docs/01、configs/source-lock.json、remote_guard.py）

| 项 | 包内声明 | 实测 | 判定 |
|---|---|---|---|
| GPU / 驱动 | RTX4090 24564 MiB，KMD 610.57.04，UMD 13.3 | 同 | ✓ |
| PCIe | Gen3 x16 | `pcie.link.gen.max=3`，width 16（空闲时 gen 1） | ✓ |
| CPU / RAM | Xeon Silver 4216 16C32T；62.5 GiB，可用 ~47 GiB | 同；`free -g` avail 48 | ✓ |
| 磁盘 | 915 GiB / 557 GiB 空闲 | 同 | ✓ |
| 宿主 nvcc / 容器 | 12.3.107；`nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04` 已有 | 同；devel 镜像内有 `ncu`，无 cmake/ninja（Dockerfile 本来就 apt 装） | ✓ |
| 系统 / JDK / Python | Debian 12、JDK17、Python 3.11.2 | Debian 12.2、17.0.20、3.11.2 | ✓ |
| Pi 位置 | 在 Mac，GPU 主机无 Pi | 4090 上 `which pi` 为空；Mac 有 `~/.nvm/versions/node/v22.19.0/bin/pi` v0.85.1 | ✓（示例路径错，见 §4.6） |
| unit / 容器 / 镜像 | `openclaw-qwen38-ninfer.service` / `ninfer-4090-prod` / `ninfer-4090:44a2c6c` | 同；unit `Restart=always`，`ExecStop` = `docker rm -f` | ✓ |
| 端口 | 原生 18030、兼容 18343、NGINX 28343 | 18030 绑 127.0.0.1；18343/28343 绑 0.0.0.0 | ✓ |
| 模型 id | `openclaw/Qwen3.8-27B-WORK` | `/v1/models` 两端口均返回该 id，`context_window 262144`，`vision:false` | ✓ |
| artifact | `/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer`，18210531328 B | 同（sha 未复算） | ✓（sha 未验） |
| 启动参数 | 262144 / rk4v4-e8 / MTP3 / rolling-tool / preserve-thinking / L1 6144 / L2 8192 / 单并发 | `launch/production-18343.sh` 逐项一致；另有 `--lm-head-draft`、`--prefill-chunk 1024`、`--default-max-tokens 32768` | ✓ |
| W4 目录已被改写 | 是 | root 属主，shard 6/7 有 `.bak`/`.bak_embed`，`config.json.bak-*` | ✓ |
| 候选端口 18041/18042 | 应空闲 | 空闲 | ✓ |
| `sudo -n` | 假定可配置 | **`sudo -n -l` → "a password is required"**；历史流程用 `~/qwen38-dflash2-20260819/launch/sudo-wrap.sh` 喂密码 | ⚠ 见 §4.4 |

### 2.2 源码事实（docs/00 §2.2–2.3、references/base-source-audit.json）

`references/base-source-audit.json` 里 9 个文件的 sha256 与 `~/ninfer-4090` **全部一致**；`~/ninfer-4090` 不是 git 仓库（`PINNED_COMMIT`=44a2c6c），包在 docs/15 已预判此情况。

| 声明 | 实测 | 判定 |
|---|---|---|
| small-T 编译范围 1..6（`src/CMakeLists.txt` ~279 行） | 第 278 行 `foreach(token RANGE 1 6)` | ✓ |
| `gqa_attention_decode.cu` 19/239/243 行限定 T=1..6 | 19：`#error ... must be in [1, 6]`；239：`uses_small_t … tokens <= 6`；243：`split_capacity … tokens > 6 → throw` | ✓ |
| `docs/serving.md`：MTP `--draft-tokens 1..5`，DFlash `1..15` | 第 571 行 | ✓（W8 对 MTP 路径当前直接被拒，不是"可能走 generic"） |
| rk4v4-e8 读路径是 PackedK unpack，`e8_root_decode_8d_int8` 属 rk2 | `gqa_attention_decode_i8.cuh` 235/257/420/437；`prefill-throughput-plan.md:719-720` "E8 lattice is an encode-side codec only" | ✓ |
| 半陪集近似注释 | `gqa_attention_decode_i8.cuh:269` | ✓ |
| `mtp_bridge_and_propose` 存在 | `mtp_impl.h:13`，被 `program_impl.h:2888/2989`、`text_prefill_impl.h:138` 调用 | ✓ |
| 44a DFlash 骨架是 35B-A3B 的 v1 | `round_state.h:26 enable_dflash=false`；`dflash_context_impl.h` 有 `local_layers/pending_features/full.layers()==1`，无 dynamic conv / selector | ✓ |
| MTP 与 DFlash 互斥 | `round_state.cpp:26` | ✓ |
| CMake ≥3.28、FFmpeg≥60、CURL≥7.85、`NINFER_BUILD_QWEN3_8_27B` 等选项、`ninfer_add_test/ninfer_add_op_test` | 全部存在 | ✓ |
| 任务卡列出的 24 个"已有源码"路径 | 全部存在 | ✓ |
| 源码中无 lookup/ngram/suffix | 确认 | ✓ |

### 2.3 上游与外部源（S01/S02/S07/S08）

| 声明 | 核对 | 判定 |
|---|---|---|
| 上游 DFlash2：K=1..15、B=1..8、eager/graph、Text/Vision、Device/Host | `qwen3.8-27b-dflash2.md:3` | ✓ |
| top-16 / rank 256 / 40 MiB ring（5×2048×8×128×4 B） | 同文 52/53/413 | ✓ |
| 66 对象 suffix、W8G32 主体 + BF16 conv/selector、旧 1124 对象文件合法且缺 DFlash2 | `qwen3.8-27b-artifact.md:31-39、366-404`；本机 artifact 恰 1124 对象、identity `groupwise-int` | ✓ |
| DFlash2 模型合同：5 层/5120/17408、32Q/8KV/128、taps [5,19,33,47,61]、SWA 2048、非因果、mask 248070、vocab 248320 | HF `config.json` 逐项一致 | ✓ |
| `text/draft_head [131072,5120] Q4` 已在 artifact | 存在（`--lm-head-draft` 用） | ✓ |
| `frontend/tokenizer.json` 可抽取 | 存在，12.8 MB | ✓ |
| 报告 09/11/12 数字（112/111/110/87.2；127.1/110.6/115.4/98.5；145/129/117/103.7；92.2 vs 94.1 s；85% 复用；Java 3/3 沿用上一轮） | 逐条一致 | ✓ |

### 2.4 CLAIM_AUDIT 对我方案的纠正——逐条裁定

| ID | 裁定 | 说明 |
|---|---|---|
| C08 T=1..8 → 实为 1..6 | **成立** | 我的 roadmap 第 115/137 行错误引用 fork 文档；W8 需 T07 |
| C09/C10 E8 读路径 | **成立** | roadmap 第 82/136/222 行把 rk2 的 lattice decode 成本归给了 rk4 |
| C12 19.03−16.96 是文件差 | 成立但**无实际差别** | 权重 1:1 常驻，本次算出的常驻差就是 2.07 GiB（§4.1） |
| C14 AL +9–12% → 8.8–20.1% | **成立** | roadmap 第 109 行范围写窄了 |
| C19 Sage 有 Ada kernel ≠ 可用 | **成立** | Sage 仅 head_dim 64/128；本目标 d256 |
| C05 nvcc 13.3 | 成立（针对 kern POC） | 我的 kern review 已写 12.3，此条不针对 roadmap |
| C03 Pi 在 4090 | 针对 kern POC | 我的 kern review 已说在 Mac，但写错了路径 `~/.pi/bin`，包照抄 |
| C20 "d256 拆两个 128 各自 softmax" | **归因不成立** | 我的两份文档均无此说法；作为负对照护栏保留无妨 |
| C28 "已达 9.4/10 最优" | **归因不成立** | 唯一的 "9.4" 是 `kern review` 的小节号 "9.4 本报告的局限" |
| C23 "AL<3 立即判失败" | 表述偏强 | roadmap P0 行原文是 "AL<3.0 → A1 期望收益 <15%，先做 P2/P3"，是重排序不是否决 |
| C24 1.4×1.15×1.2 | 成立 | roadmap 已标 [推断]；包改成"不给数字"，代价见 §4.7 |
| C02/C27 | 护栏 | 不影响决策 |

---

## 3. 包做对的地方（保留）

- **方向**：停 kern、冻结 44a 现网为回滚点、增量改造 NInfer——与我的结论一致，且做了独立核对（源码 sha 匹配、上游合同精确）。
- **状态模型**（docs/03 §3–6）：`F_target / F_draft / committed` 三个 frontier 分离、checkpoint 必须带 KV+GDN+hidden+draft conditioning、publish-after-commit、cache 身份含 schema/artifact/companion hash——这是 44a 现有 MTP/continuation cache 语义的正确抽象，比我的 roadmap 严谨。
- **采样合同**（docs/05）：p/q 同管线、拒绝/残差/bonus、RNG 按 `(seed, position, purpose)` 绑定、"同 seed 逐 token 一致"不作判据——正确。
- **证据纪律**：`input-review` 原文 hash、E0–E5 分层、`validation/` 明标 GPU NOT_RUN、`CANDIDATE_PASS_NOT_RELEASED` 不自动上线、`paired_gain_lcb = ratio_low − 1` 单位钉死。
- **两处纠正我的错误**（T≤6、E8 读路径）都是从源码读出的，对 W8/W16 与 decode kernel 任务的范围判断有实质影响。
- **Java 夹具**：23 文件与 `docs/qwen38-4090-vllm-extreme-v1.0/fixtures` 逐字节一致；30 道 JDK 实测语义题是有用的低成本 holdout。
- **ncu 权限**：不全局改 `RmProfilingAdminOnly`——正确；补一句实操：hhtele 在 docker 组，可直接 `docker run --cap-add=SYS_ADMIN --gpus all <devel 镜像> ncu …`，devel 镜像内已有 `ncu`（宿主只有 `nsys`）。

---

## 4. 主要发现（按严重度）

### 4.1 【高】DFlash2 W8 在 262144 下显存不成立——包把这项算账放错了位置

**实测输入**

- `nvidia-smi`：total 24564 MiB，`ninfer-serve` 用 22592 MiB，**free 1509 MiB**（total−used=1962，差额是驱动保留；报告 11 同口径空闲 22594 MiB）。
- artifact 目录（1124 对象）：`text` 16.252 GiB、`mtp` **0.420 GiB**（W8G32）、`vision` 0.275 GiB、`frontend` 0.012 GiB → 16.96 GiB。
- 上游 66 对象 inventory（`qwen3.8-27b-artifact.md §7.4`）按形状与格式逐项累加：

| 组件 | 计算 | 常驻 |
|---|---|---|
| `feature_projection` [5120,25600] W8G32 | 131.1 MB + scales 8.2 MB | 0.130 GiB |
| 5 层 × (qkv 6144×5120 + o 5120×4096 + gate_up 34816×5120 + down 5120×17408) W8G32 | 319.8 MB/层 + scales 20 MB + conv `kernel_projection` BF16 26 MB | 0.341 GiB × 5 = 1.705 GiB |
| selector 两个 codebook [248320,256] BF16 | 254 MB | 0.237 GiB |
| **合计** | | **2.074 GiB = 2124 MiB**（与 19.03−16.96 一致） |

**常驻差（W8，DFlash2 时不加载 MTP）**：+2124 − 430 + 40（ring）= **+1734 MiB**，尚未计 W8 verify 的 logits/head 工作区、pending features、CUDA Graph 与 draft attention 工作区（估 50–150 MiB）。

**结论**：
- 零余量都差 ≈ 0.3 GiB；按包自己的"峰值后余量 ≥512 MiB"门（docs/02 §3、`metrics.candidate_gate`）差 ≈ **0.8 GiB**。
- 降容量：fork 自己的 load-log 斜率 rk4v4-e8 ≈ 26.4 KB/token（`udp-fork-comparison.md:53`）→ 0.8 GiB ≈ 32K token → **cap ≈ 229K**；若要 1 GiB 余量（缺口 1.3 GiB ≈ 53K token）→ ≈ 210K。包定义这类结果为 `TRADEOFF_ONLY`，与"第二优先主线"矛盾。
- draft 主体 W4（包内 fallback）：主体 1.61 GiB 参数 → Q4G64 ≈ 0.86 GiB，+BF16 conv/selector 0.36 GiB → companion ≈ 1.22 GiB；常驻差 ≈ +860 MiB + ring + 工作区 ≈ 0.95 GiB → 余量 ≈ **550 MiB，压 512 线**，258K prefill 峰值下大概率不满足。且 draft W4 会改变 q/AL，需另测。
- `vision` 0.275 GiB 不能拿来省：`/v1/models` 已是 `vision:false`，很可能本就没 materialize。
- L1 6144 MiB 不是独立显存池（`continuation-cache.md:52` "retained GPU lanes… uses the startup-fixed shared KV pool"），不构成杠杆。

**对计划的影响**：T08→T09→T10 是包里最大的工程块（converter、5 层算子、dynamic conv、selector、q、状态事务、Graph、恢复）。按包自己的门，它在 262144 下的终点几乎确定是 `TRADEOFF_ONLY` 或 `BLOCKED`。这笔账不需要 GPU，T00 就能算清（本节就是），应：

1. 把"显存 ledger（component × stage）"从 T08 步骤 3 前移为 T00 的交付物；
2. 在 T03 决策前**向用户要一个明确答复**：262144 是否可为 DFlash2 让到 ≈225K？（既有测试最长 184K，报告 11/12 的 rk8 200192 已是"不淘汰"档）；
3. 若答复"不可让"，DFlash2 只剩 W4-draft 压线一路，投入应降级为"可行性尖峰"，把 T09/T10 的完整状态事务工作推后。

### 4.2 【高】DFlash 后端缺 session persistence：T10 是新功能不是移植

- `src/targets/qwen3_8/impl/runtime/session_snapshot_impl.h:342` 与 `:534`：`speculative_backend == DFlash → throw invalid_argument("session persistence …")`。
- `docs/serving.md:130`："The DFlash backend is not supported."（session save/restore 段）。
- `continuation_image.h:683-711` 有 `dflash_local / dflash_checkpoint_local`（进程内 L1/L2 image 已为 DFlash ring 预留），但持久化/快照路径明确未做。

现网 `--continuation-cache l1-l2`、`--prefix-checkpoint-policy rolling-tool`，报告 10 测得 85% prompt token 复用，报告 12 的热命中 TTFT 1.1 s vs 全重算 21 s。DFlash2 profile 若无等价的恢复能力，每次会话切换/重启都退回全重算，任务墙钟必然回退，`task_wall_ratio > 1.02` 直接 `NO_MEASURABLE_PRODUCT_GAIN`。

**建议**：T10 增加硬断言"L1/L2 image 含 40 MiB ring + pending，A→B→A 会话切换后 `reused_prompt_tokens` 与 MTP profile 相同"，并把 L2 image 增大（每 image +40 MiB ring，含 turn checkpoint 再翻倍）计入 8 GiB L2 预算——8192 MiB 下能存的 image 数会少 ~10%。

### 4.3 【高】治理/工程比例与预算算术

- **规模**：19 任务、~30 个"计划创建"文件、`ninfer_lab_validate` 待建、每任务四段模板步骤。包自己没有一个工期估计（docs/16 §4 "不是承诺工期"）。基于 44a 代码量与任务内容，我的估计 [推断]：T00–T03 1–2 周；Suffix 链（T04–T06）2–4 周；DFlash2 链（T07–T10）6–10 周；W16（T12）2–4 周；d256（T13）4–8 周。全包串行 4–7 个月一人。这不是缺陷本身，但应让用户知道"极致"在这份包里的时间尺度。
- **一小时筛选**（docs/12 §2 "核心性能 15 min：4K/64K/184K，输出≥1024，重点桶 5 配对"）按现网实测算：184K 冷 prefill 94 s + 1024 token 解码 ≈ 11 s，5 配对 × 2 臂 = 10 次 ≈ **17.5 min**；64K ≈ 6 min；4K ≈ 2 min；合计 ≈ 26 min。且 baseline/candidate 不能同驻，ABBA 每次切换要重启（观测启动 28 s + 图捕获），"跨两次启动"再翻倍。15 分钟只够一个长度桶。包有"预算不足先做主要桶"的兜底，但表格给出的是做不到的数字，执行 AI 会按它排。
- **`paired_summary` 统计**：`metrics.py` 允许 n≥3，用 3000 次 percentile bootstrap；n=5 时只有 5⁵=3125 种重采样，percentile CI 明显偏窄。门禁"95% 下界 ≥3%"整个判定系统建在这上面。建议 n≥8–10 或改 log-ratio t 区间，并强制先跑 A/A 得到噪声底（docs/12 N1 已要求，但 `candidate_gate` 没读这个字段）。

### 4.4 【中】`sudo -n` 在该机不可用；`remote_guard.py` 首跑必 BLOCKED

- `sudo -n -l` → "a password is required"。`remote_guard.py:76-77` 先 `sudo -n -l systemctl stop/start <unit>` 预检，失败即退出——这是**正确**行为，但意味着 T01 之前必须由 root 写一条 sudoers（仅这两条命令 NOPASSWD），包的 docs/04 §2 提到了，任务卡 T01 没把它列为前置阻塞。
- 历史脚本（`output/*/scripts/4090_*.sh`）全部经 `~/qwen38-dflash2-20260819/launch/sudo-wrap.sh` 喂密码；包建议不复用是对的。
- 小 race：`systemctl stop` 后 `ExecStop=docker rm -f` 异步释放显存，`remote_guard.py:87-88` 立即读 `memory.free ≥ 20000`，可能在容器退出前失败 → 进 finally 恢复生产 → 整轮作废。应轮询 ≤30 s。
- 健康等待 120 s：生产日志 `NINFER_ENGINE_READY 28s`（页缓存热），冷盘 +10 s 左右，够用。
- 一个 `Restart=always` 相关的脚本事实：`production-18343.sh` 在引擎就绪后 `exec python3 $PROXY`，systemd 跟踪的是 proxy 进程。若有人绕过 systemd 直接 `docker rm -f ninfer-4090-prod`，unit 仍 active、18343 仍开、GPU 已空——`remote_guard` 用 `systemctl is-active` 判断 `was_active` 会误判。建议 `check_production_ready` 同时要求 18030 `/v1/models` 通。

### 4.5 【中】已存在的能力被当成待建：T02 / T04 范围应缩

- **exact rejection sampling 已在 44a**：`src/ops/kernel/speculative_round.cuh:60-68` 注释明写 T>0 时 "distribution-correct speculative rejection sampling … one-hot (greedy) draft: accept with p_i(d), resample from masked residual on first rejection, bonus from last column"。包 docs/05 §2 与 T04 的 `PointMass` 路径就是这个。真正新的是 `Sparse16`（DFlash2 随机 selector 的实际条件 q）。T04 应写成"扩展现有 sampler 增加 Sparse16 q"，而不是"新建 ProposalBatch 验证器"。
- **请求级遥测已在 44a**：`/metrics` 有 `ninfer:draft_accepted_tokens_total`、`llamacpp:prompt_tokens_total`、`prompt_seconds_total`、`prefill_energy_joules_total`（`tests/test_serve_metrics.cpp:145-214`）；请求结果有 `speculative_accepted_tokens`、`reused_prompt_tokens`、`cached_tokens`（`concurrent_executor.h:1514/3114`）；compat proxy 把 `timings.cache_n` 注入 `usage.prompt_tokens_details.cached_tokens`。T02 缺的只有**每轮** `round_ms / licensed / committed / origin / catchup_ms`。docs/11 §1 的"三种账本"里 HTTP 与 request 两层已基本可用。

### 4.6 【中】Suffix+MTP 漏了一个零 bridge 成本的设计

包 docs/06 §4 / T06 的第一版是"某轮用 suffix 替代 MTP 草稿，之后 MTP 私有 KV/hidden 需 bridge/catch-up"，并正确指出 catch-up 成本可能吞掉收益。但有更小的变体没被考虑：

**MTP 常驻照跑，suffix 只做"链延长"**：每轮 MTP 仍产 3 个 greedy 草稿（状态照常前进），suffix 索引在 `[committed…, d1, d2, d3]` 之后查最长匹配，把链延长到 K=5（W=6，恰在现有 small-T 与 `--draft-tokens ≤5` 范围内），延长部分 q 为 one-hot，走现有 sampler。

- 零 MTP 状态修改、零 bridge、零新 kernel、零新权重；GPU 侧改动只是 draft 数组长度可变（`live_proposals ≤ 5`）。
- 命中时每轮多 2 个候选；未命中时与现网完全相同。
- 它回答的正是 T05/T06 想回答的问题："本机 Java/rewrite 流量是否有可利用的长重复"。
- 缺点：上限 W=6，copy 类拿不到 W16 的 3–4×；但这正好是 T12 的动机。

建议把它作为 T06 第一版，包里的 alternating-source + bridge 作为第二版（仅当第一版显示命中率足够）。

另一个 DAG 问题：**T12（W16）依赖 T10（DFlash2 全链完成）**。W16 对 suffix copy/rewrite 同样有价值且不需要新权重；若 DFlash2 因 §4.1 被阻断，W16 也一起没了。T12 的依赖应改为 T07 + T06。

### 4.7 【中】拒绝给任何量化预期的代价

包反复声明"不承诺 175/250/500 tok/s"（合理），但也不给任何有界估算，导致三条线没有优先级信号。用现网数字能给出边界 [推断，公式可查]：

- **DFlash2 每轮固定开销**：draft 权重读 2.07 GiB ≈ 2.2–2.4 ms/轮（4090 实效 ~900 GB/s），MTP 0.42 GiB ≈ 0.5 ms → **+~2 ms/轮**。现网 184K 轮 ≈ 29 ms（98.5 t/s ÷ AL≈2.9 ≈ 34 轮/s）、4K ≈ 23 ms（127.1 ÷ 2.9 ≈ 44 轮/s）。要打平，committed/轮需 +7%（184K）/ +9%（4K）。
- 模型卡同 K 下 DFlash2 对 MTP 的 AL 增益 +8.8–20.1% → **同 K=3 换 drafter 净收益约 0–12%**，接近噪声。DFlash2 的实质收益只能来自 **K=7 的宽度**——这意味着 T07（W8 合法路径）不是"资源完整性"配套，而是 DFlash2 有无收益的**关键路径**；T09/T10 不应在 T07 的 W8 route 有性能数据前启动。
- 4-bit KV 下多 4 行 verify 读的字节几乎不变（184K × 26.4 KB ≈ 4.9 GB/轮不随 W 变），W8 的额外代价主要是 draft 与 head 计算，因此 W8 在长上下文更划算——与我 roadmap 的判断一致。
- **d256 prefill**：fork 自己测 GQA prefill attention 在其混合天花板的 41%（`prefill-throughput-plan.md`）；若 attention 占冷 prefill 的 f（未测，需 nsys 阶段占比），把 41%→65% 相当于 s≈1.6，Amdahl 上限 `1/((1−f)+f/1.6)`；f=0.45 时 ≈1.20×，即 184K TTFT 94 s → ~78 s，不是 vLLM 的 66 s。包 docs/09 §6 的 Amdahl 公式是对的，只是没代入这台机器的数。

### 4.8 【低】工具与配置的小问题

| 位置 | 问题 | 影响 |
|---|---|---|
| `configs/local.example.json` `pi_bin` | `/Users/luo/.pi/bin/pi` 不存在；实际 `~/.nvm/versions/node/v22.19.0/bin/pi`（v0.85.1，`--approve/--thinking/--tools/--no-skills` 均存在） | 示例文件，复制后必改；错误源头是我的 kern review §2 |
| `tests/test_io.py` `safe_child` | macOS `/var`→`/private/var` 解析，66 项中 1 失败 | Mac 控制端跑 `self_check.sh` 会 FAILED；比较时应 `.resolve()` |
| `configs/pi-models.example.json` | `reasoning:true` + `--thinking medium`；历史脚本是 `--thinking off` + 服务端 medium | 包 docs/13 §2 已要求以引擎有效参数为准，需 T01 落实 |
| `tools/preflight.py` | 硬编码 `/usr/local/cuda-12.3/bin/nvcc` | 该路径存在，可用 |
| `tools/extract_tokenizer.py` | 依赖 `frontend/tokenizer.json` | 存在（12.8 MB） |
| `tools/remote_guard.py` 模型 id 判定 | `openclaw/Qwen3.8-27B-WORK` in `data[].id` | 与 18343 实际返回一致 |
| `validation/generation-environment.json` | 生成环境 JDK 21，目标 JDK 17 | Mac 实际 JDK 25，4090 主机 17；原题含 record 均可编 |
| docs/12 §2 | 15 min 核心性能表 | 见 §4.3 |
| docs/07 §3 | "计算后才知道 262K 能否保留" | 本可在包内算出（§4.1） |

---

## 5. 修订建议（不推翻方向，只改顺序与范围）

1. **T00 增加显存 ledger 交付物**（CPU 可做，本报告 §4.1 可直接引用），并在 T03 决策前拿到用户对 262144 的取舍答复。
2. **T01 前置阻塞**：root 写两条 sudoers（`systemctl stop/start openclaw-qwen38-ninfer.service` NOPASSWD）；`remote_guard` 显存检查改轮询；健康检查加 18030。
3. **T02 改为"扩展"**：在现有 `/metrics` + 请求结果上加 per-round 字段；不重建 request 账本。
4. **T04 改为"扩展 sampler 增加 Sparse16"**，PointMass 路径直接复用 `speculative_round.cuh`。
5. **T06 第一版改为 MTP 链延长（W≤6）**；alternating + bridge 作第二版。
6. **T07 提到 DFlash2 链最前**且带性能门（W8 generic route 的 184K 轮耗时）；T12 依赖改为 T07+T06。
7. **T10 加硬断言**：DFlash2 profile 下 L1/L2 continuation image 恢复与 `reused_prompt_tokens` 与 MTP 等价；`session_snapshot_impl.h` 的 DFlash throw 需解除。
8. **统计门**：配对数 ≥8，log-ratio t 区间或 BCa；A/A 噪声底进入 `candidate_gate` 输入。
9. **一小时筛选表**按 §4.3 重排：一轮一个长度桶，184K 冷测单独一轮。
10. 给每条线一个**有界估算与停止点**（§4.7 的公式），而不是完全不给数字。

---

## 6. 未验证项与限制

- 未复算 18 GB artifact sha256（字节数一致；避免在生产主机上做 18 GB 读）。
- 未运行任何 GPU 进程、未暂停现网；所有性能数字来自既有报告或公式推算，已标 [推断]。
- W8 工作区/Graph 的额外显存（§4.1 的 50–150 MiB）是估计值；精确值需 T07 的 `width-audit.json`。
- DFlash2 draft W4 对 AL 的影响未测；上游只发布 W8G32 主体。
- 未逐行审 `tools/metrics.py` 之外的统计实现；未验证 SageAttention issue #47 原文（对结论无影响，Sage 仅支持 64/128 head_dim 是公开事实）。
- GitHub REST API 限流，上游核对改用 raw 文件与 `git ls-remote`；`tensorninja/ninfer-4090` 另有分支 `rtx4090-port`（981b685），包未提及，T00 应记录两分支关系。
- 包内 `tasks.json` 与 T 卡依赖一致（19 任务无环，已核对）；未逐条核对 T 卡"反例"与 docs 的交叉引用。

---

## 附：本次实测关键命令（只读）

```bash
# 显存/生产
nvidia-smi --query-gpu=memory.total,memory.used,memory.free --format=csv   # 24564 / 22602 / 1509 MiB
systemctl cat openclaw-qwen38-ninfer.service; docker ps; ss -ltnp | grep -E '18030|18343|28343'
curl -s http://127.0.0.1:18343/v1/models
sudo -n -l                                                                  # "a password is required"
# artifact 目录（1124 对象，按前缀汇总字节）
python3 - <<'EOF'
import struct,json; f=open('/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer','rb'); pre=f.read(16)
n=struct.unpack('<Q',pre[8:])[0]; m=json.loads(f.read(n)); t={}
for o in m['objects']: k=o['name'].split('/')[0]; t[k]=t.get(k,0)+o['bytes']
print({k:round(v/2**30,3) for k,v in t.items()})
EOF
# 源码事实
grep -n 'foreach(token RANGE' ~/ninfer-4090/src/CMakeLists.txt                        # 278: 1 6
sed -n '19p;239p;243p' ~/ninfer-4090/src/ops/launcher/gqa_attention_decode.cu
sed -n '60,68p' ~/ninfer-4090/src/ops/kernel/speculative_round.cuh                     # exact rejection sampling
grep -n 'DFlash' ~/ninfer-4090/src/targets/qwen3_8/impl/runtime/session_snapshot_impl.h # 342/534 throw
sed -n '130p' ~/ninfer-4090/docs/serving.md                                            # DFlash backend not supported
```
