# 环境核实、资源预算与安全边界

## 29 号机当前状态（2026-10-26，覆盖下文 10-23 表中已变化的项）

| 项 | 当前值 | 来源 |
|---|---|---|
| 生产版本 | **A0（v0.2.3，`5c8dd322`）+ EXACT6**，部署在 `/home/hhtele/strata-0.2.3`；`openclaw-qwen38-next.service` 指向它，unit 备份 `.bak-v0431-20261025`；端口 18343、NGINX 28343、模型名 `openclaw/Qwen3.8-next` 不变 | [部署报告](../reports/DEPLOY-A0-EXACT6-20261025.md) |
| 生产状态 | **停机测试中**：2026-10-26 09:44 EDT 按用户同意停止（inactive，仍 enabled，开机会自动拉起，且会带 KVRES 配置）。此前 09:24 起带四个开关运行了 20 分钟，只有上线冒烟请求；21:38～21:41 加上 KVRES 启动做冒烟，验证后按用户要求再停。恢复需用户发话：`systemctl start openclaw-qwen38-next`（经 sudo 包装） | [部署报告](../reports/DEPLOY-PROD-20261026.md)、[DEPLOY-KVRES](../reports/DEPLOY-KVRES-20261026.md) |
| 生产开关（10-26 上线） | 服务层：`run-iq3_xxs.sh` export `STRATA_REPLY_REUSE=1`（#1536）、`STRATA_PRESERVE_THINKING=0`（CFG-PT），代码为 `lab/prod-20261026` 补丁；引擎 env（`strata-iq3_xxs.json`）：`STRATA_PREFILL_CPU_SHARE_MAX=4096`、`STRATA_PREFILL_AUTO_MAX=16384`。备份 `/home/hhtele/strata-0.2.3/backup-20261026/`。21:38 引擎参数再加 `--kv-resident 20480`（K/V 1.55 GiB 在 pinned RAM，专家槽 9420 → 10290），备份 `backup-20261026-kvres/` | [部署报告](../reports/DEPLOY-PROD-20261026.md)、[DEPLOY-KVRES](../reports/DEPLOY-KVRES-20261026.md) |
| 回滚 | `/home/hhtele/strata-0.1.43.1`（含 `data/`）原样保留，不写 | — |
| host 调优 | `strata-host-tuning.service`：performance governor + C6 关闭（停止时恢复 schedutil / C6）；`kernel.perf_event_paranoid=1`；linux-perf 6.1.190 已装 | 部署报告 |
| 共存 | OCR 容器 `onnxocr-ppocrv6-small-cpu-compat` 已停；`openclaw-qwen38-ninfer` disabled + stopped；GPU 测试期间独占 | 部署报告 |
| Docker 镜像 | 有 `python:3.12-slim`（`sha256:ec7d6c95cd36…`，用于 `chain_bench` 隔离评分）；**仍无 JDK 镜像** | 2026-10-26 `docker images` |
| 上游 | 最新 v0.2.6（`4b9e05a2`），对本机 Flash-Next 无相关改动，基线不换（`sources/LOCK.json` 的 `upstream_after_snapshot`） | 2026-10-26 diff |
| 实验包 | 29 `/home/hhtele/strata-lab-4090`，端口 18089；构建需 venv cmake 4.4.3（`PATH=/home/hhtele/strata-0.1.43.1/.venv/bin:$PATH`），系统 cmake 3.25 报 CUDA20 dialect | P0 报告 |

## 29 号机生产事实（2026-10-23 核对，取代 10-08 记录；部分已被上表覆盖）

以下来自 29（192.168.10.29）上的生产配置文件、启动日志和 10-12～10-16 的真实 Pi 流量。数值仍以 `doctor` 和本轮启动日志复核；凡标“未验证”的项不得当作前提。

**部署身份**

| 项 | 当前值 |
|---|---|
| 生产服务 | `openclaw-qwen38-next.service` → `/home/hhtele/strata-0.1.43.1/run-iq3_xxs.sh` → `serve/server.py --engine strata` |
| 部署树 | `/home/hhtele/strata-0.1.43.1`，git HEAD `a0116b2782a5b82622358c04a06496485d12b2d6`（Engine 0.1.43.1，可能带本地补丁，P0-T2 必须备份 `git status`/diff） |
| 生产配置 | `/home/hhtele/strata-0.1.43.1/strata-iq3_xxs.json`（与 `.prod-20261014` 字节一致），端口 18343 |
| 模型 | Qwen3.8-Flash-Next **GSQ-RCO IQ3_XXS**（不是 IQ3_S）；`/data/strata-data/models/IQ3_XXS/…-00001-of-00002.gguf` + `--ple-gguf …-00002-of-00002.gguf` |
| pack / tokenizer | `/data/strata-data/packs/iq3_xxs`，模板 `/data/strata-data/packs/iq3_xxs/tokenizer/chat_template.jinja` |
| MTP | `--mtp /data/strata-data/mtp/rt`，`--spec 4 --spec-min-p 0.5`（10 月 A/B 后保留 0.5） |
| KV | `--kv int8`，`--max-context 131072`。实验 base（0.1.43.1 的归一化配置）不传 `--kv-resident`，即默认 0：**全部 K/V 驻显存**；生产 10-26 21:38 起传 `--kv-resident 20480`（见上表）（v0.2.3 `--help`：“0 (default): all of it in VRAM”，2026-10-26 核对）。GGUF 元数据：48 层，每 4 层一个全注意力（QSA）层共 12 层，KV head 2；专家 512 个，每 token 路由 top-10。int8 每层每 cell 1056 B，全上下文 K/V 约 12 × 131072 × 1056 B ≈ 1.55 GiB（按公式推算，启动日志不单独打印） |
| 显存 | `--expert-cache auto` → 9434 slots / 15.29 GiB；`--vram-reserve-mib 974`；`--prefill auto` |
| Expert Profile | 读 `data/expert-profile-iq3xxs.bin`，生产会写 `expert-profile-iq3xxs-learned.bin`（runner 已剥离 `--expert-profile-save`） |
| 会话缓存 | `--conversation-cache-mib 6144 --conversation-cache-slots 4`（**不是 0**） |
| 生产 env | `STRATA_DECODE_TIMING=1`、`STRATA_PREFILL_TIMING=1`、`STRATA_PREFILL_CPU_SHARE_MAX=3072`、`STRATA_ADAPT_OVERLAP=1` |
| CPU / RAM | Xeon Silver 4216，32 线程，约 62 GiB RAM；pool workers 15；Strata 停止时 MemAvailable 约 57.6 GB |
| GPU / 工具链 | RTX 4090 sm_89，驱动 610.57.04，CUDA 12.3（`/usr/local/cuda-12.3`），gcc 12.2，cmake 3.25.1；GPU Target Temperature 84 °C。实验包温度保护 85 °C（`gpu_temp_abort_c`）：A0 默认配置下连续冷读最高 79 °C，`STRATA_PREFILL_AUTO_MAX=16384` 下连续约 6 分钟冷读到 84～85 °C（2026-10-26，[P2-PR3307](../reports/P2-PR3307-20261026.md)）。decode 时 SM 稳定在 2745 MHz（出厂最高 boost），显存 10251 MHz，GPU 利用率 99%，功耗 240～280 W，`clocks_event_reasons` 为 0（没有功耗 / 温度降频），所以频率侧没有软件可调的空间（2026-10-26 实测） |
| 系统 / 启动 | Debian 12，内核 `6.1.0-17-amd64`（cmdline `quiet iommu=pt`），GRUB，initramfs-tools 0.142，dkms 3.4.1；Secure Boot disabled；显示为 ASPEED 板载显卡，4090 在 `0000:65:00.0`，功率上限 450 W；有 BMC（`/dev/ipmi0`）。访问方式只有 `jssh 29`（2026-10-25 核对） |
| Python | 部署树 `.venv`，已有 jinja2、numpy；无 huggingface_hub |
| 磁盘 | 约 327 GB 可用 |

**真实流量画像（10-12～10-16，0.1.43.1）**

- 引擎时间里 decode 占 75～80%（10-12：prompt 474 s / decode 1800 s；10-14～16：150 s / 445 s）。decode 窗口约 17.2 ms，其中等待 GPU 可达约 9.65 ms。0.1.43.1+overlap 实测 129.0 tok/s，旧版 116.1 tok/s。
- prefix reuse 89～94%；PCIe share 中位 **0.007**（不是 0.022）。
- Pi 共享 system+tools root 约 **12.3K token**（新会话复用 12275 / 12470 / 12520），低于主线默认 `prompt_cache_every=16384`。
- 续轮中约 90%（424/473）直接复用上一轮回复，约 10%（48/473）重读回复，合计约 120 s prompt 时间（约占 prompt 15%）。重读原因 2026-10-25 已确认是 BPE 非规范生成（不是 Pi 改写），见 [单会话](11_SINGLE_SESSION.md)。
- 67 个请求中 6 个冷启动，约占 prompt 时间一半。
- 会话缓存：10-12 parking 45 次、restore 7 次；10-15 起共 12 次 `skip parking (physical RAM admission ...)`：1 次 `evicted 3, 0 still parked`（驱逐全部 3 个会话后仍拒绝），11 次 `evicted 0, 0 still parked`（缓存已空，MemAvailable 约 1.5 GB 仍低于 2560 MiB 下限加快照大小）。进程 `[heap]` 约 6.9 GB。glibc 2.36。根因与 #2253 描述一致（16 MiB 分段释放后留在 glibc 空闲链表）——**推断**，未做 malloc 对照实验，见 `prs/11_PR2253.md`。

**Pi 客户端（本机 `~/.pi/agent`，2026-10-23 只读核对；其他客户端未核对）**

- `models.json` 中 `openclaw/Qwen3.8-next`：`contextWindow 131072`、`maxTokens 32768`，`api: openai-completions`，经 NGINX 访问 29。`compat` 为 `supportsReasoningEffort: true`、`maxTokensField: max_tokens`、`supportsDeveloperRole: false`，**没有 `thinkingTokenBudgetField`**，所以 Pi 不发送任何 thinking budget 字段，#3340 不适用。
- thinking 长度由 `reasoning_effort` 决定：`thinkingLevelMap` 为 high→`xhigh`、medium→`medium`、low/minimal→`low`、off→`none`。29 的 chat template 默认 `xhigh`，只接受 `xhigh`/`medium`/`low`（`high` 映射为 `xhigh`）。近 14 天本机会话记录中 thinkingLevel 条目 high 232 条、medium 182 条。
- 采样参数：`temperature 1.0 / top_p 0.95 / top_k 20`；thinking 关闭时 `0.7 / 0.8 / 20`。即生产请求是采样而非 greedy。
- `settings.json`：默认模型是 `openclaw/Qwen3.8-27B-WORK`（不是 Next），compaction 开启（`reserveTokens 16384`、`keepRecentTokens 20000`），codemode 开启。本机近 14 天会话里 Next 的使用远多于 27B。
- 推断：decode 占比高的一部分原因是 `xhigh` 的长 thinking；在服务端用 `reasoning_budget_tokens` 截断会改变输出，属于产品决策，不作为性能实验项。

**噪声基线**：同配置重启 A/A 的 ms/window 差异可达约 5%，抽样配对噪声约 7%；同 seed greedy 输出跨重启**不保证逐字节一致**。因此 PR 收益门槛不得低于噪声，正确性比较不得依赖跨进程 bitwise 相同。

## 共存负载与当前占用

- （10-23 状态，已过时）29 同时运行其他实验：端口 18343 被其他进程占用，18089 空闲。2026-10-25 起 18343 属于 A0 生产（当前停止）。实验开始前重新确认。
- Docker 常驻容器（10-23）：onnxocr-ppocrv6-small-cpu-compat（约 8 GB RAM，**2026-10-25 经用户同意已停**）、vault-transit-test、old-hand-verify、fervent_moore。它们吃掉 MemAvailable，直接影响本包 4096 MiB 门槛和 cache 实验；不得由实验 AI 自行停止。
- `/home/hhtele/strata-cvec-ablation-20261020*` 属于其他实验，不读写。
- 本机**没有 JDK Docker 镜像**。Java 组需要用户事先离线准备镜像并填 `java_image`，否则一律 NOT_RUN。有 `python:3.12-slim`，`tools/session/chain_bench.py` 用它隔离执行模型生成的 Python。

## 历史证据（2026-10-08，已过时）

10-08 上传的 `Pasted text(20261008-035514).txt` 记录的是 IQ3_S、8004 slots 约 15.17 GiB、conversation cache 0、加载后可用 RAM 约 6.6 GiB、prefix reuse 97.9%、PCIe 0.022。模型、版本、缓存配置都已变化，只作背景参考，不用于资格判断。本包**不强制换模型**，也不把增加 RAM 当作实验前提。

## 固定项

模型/量化及其sha、pack、tokenizer/template、MTP/其他draft、KV格式/驻留策略、Expert Profile、CPU workers与亲和性、CPU Share、Tail Skip、Adaptive Overlap、控制向量、prefill参数、PCIe参数、采样全部登记。PR不涉及的项保持相同。学习型profile不得写回生产；关闭自动保存或复制到每个arm独立目录。

P 臂必须带齐上表的生产 env 与参数。A0/A1/B 基于冻结 main（即正式版 v0.2.3，引擎 0.1.48），与 0.1.43.1 差距很大（P→A0 是独立迁移评估 MIG，排在 P0 诊断与对照之前，见测试协议）；main 上 adaptive overlap 仍是 opt-in。runner 会把生产配置的 env 复制到每个 arm，但必须在 A0/A1/B 的启动日志里确认 `STRATA_ADAPT_OVERLAP=1` 与 `STRATA_PREFILL_CPU_SHARE_MAX=3072` 在 main 上实际生效（变量名或语义变了就记录差异），否则会把生产调优差异错算成 PR 收益。**禁止**开启 `STRATA_STAGE_PIN`（会损坏 IQ3_S 系权重）和 `STRATA_ROUTE_RESIDENT`（会改变答案），任何 arm 都不行。

Windows驱动545是更早的历史记录，不能当作今天的事实。按实际 `nvidia-smi` 与所选toolkit验证；本包不安装驱动。编译源码与运行官方CUDA12/13包的最低驱动条件不同，不能仅看版本字符串猜兼容。

## 内存准入

live runner在启动前与运行中检查MemAvailable，默认不得低于4096MiB。它读Linux主机和可读cgroup v2限额；cgroup不可读取时有日志限制。原生Windows不提供等价adapter，拒绝live模式。

29 上共存容器会占用数 GB，门槛按**加载完成后**的实际 MemAvailable 判断；不够时报告 BLOCKED 并请用户安排停共存负载，不得降低门槛或自行停容器。

实验默认 conversation cache 为0（与生产 6144×4 不同，是 PR 无关组的保守默认）。#3584/#3711/#2822需要另建同参数的cache profile，先测加载后内存，再从至多512MiB实验预算起步；#3711 复现生产问题时再升到生产形态 6144 MiB × 4 slots，前提仍是 MemAvailable 门槛成立。如果一份合法状态都装不下，标记不适用。不得将阈值降到几十MiB来勉强通过。每个checkpoint需记录真实bytes；不能把KV大小当作全部状态大小（还有递推/草稿/元数据）。

128K窗口≠实际使用128K输入。默认输入目标4K/32K/64K/96K/120K，输出64～4096，另留4096安全余量。所有模板/工具/历史在计数内。长会话不得通过截断测试数据“通过”，超限应明确拒绝。

## 生产隔离

29 专属禁区：不改 systemd unit、NGINX、`production-18343.sh`、驱动和 CUDA 12.3；不装内核模块、不改 initramfs/GRUB/内核参数（CFG-UNLOCK 经用户批准的维护窗口除外）；不写 `/home/hhtele/strata-0.1.43.1` 树（含 `data/` 下的 profile）；不占用 18343；不运行 `./update.sh` / `UPDATE.bat` 或任何更新器；不删除旧版本目录（它们是回滚路径）。生产服务停启每次都需用户授权。

使用独立clone（不共享硬链接objects）和worktree，不在生产repo建worktree。模型只引用已有绝对路径，不复制或重新打包。测试端口默认127.0.0.1:18089，禁止复用已占用端口。测试临时API key运行后从配置证据中移除；原始日志仍需人工检查后再分享。

MCP、图像生成、vision、before_load、after_load等在实验复制配置中禁用以免触发额外副作用；这属于所有arm一致的text-only实验形态，并非生产原样重放。需要比较纯迁移时单独记录这些差异。原配置不变。

GPU必须空闲且独占。工具检查nvidia-smi进程与`/proc/PID/exe`/cmdline，确认唯一native engine和131072 context；只终止自己启动的进程组。WSL PID视图不一致时停止而非绕过。测试中出现其他GPU进程立即终止本轮，不能杀对方。

## 编译

示例配置 build_jobs=8，sm_89（29 有 32 线程，Strata 停止时约 57 GB 可用；若共存负载占用大量内存则降回 2～4）。main 在 CUDA 12.3 上能否编译**未验证**，第一次 build 失败时如实记录，不自行安装新 toolkit。沿用用户已有的Strata Python环境和依赖，不自动sudo/apt/pip全局安装。若CMake需要`.ref/llama.cpp`，用源代码记录的依赖revision，配置ggml_dir并保存其SHA。禁止拿更新的ggml悄悄替换固定依赖。

## 真实 Pi 验收

本包的HTTP重放和Java mini-agent不是完整Pi。最终留出集在实验端口运行用户现有Pi，保持原compaction/codemode/插件配置；不要执行`strata connect pi --write`。只改复制profile的baseURL，任务仓库也应是临时副本。没有实际Pi执行的结果必须标记未测。
