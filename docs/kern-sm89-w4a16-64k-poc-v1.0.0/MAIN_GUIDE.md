# Kern-SM89-W4A16 64K PoC：AI开发与验证总手册

版本1.0.0；2026-09-08。配套ZIP含独立任务卡、脚本、Java题目与CPU验证日志。本文是文档合集，不是已完成的SM89引擎；GPU验证NOT_RUN。文中的相对路径以ZIP解压根目录为准。



---

<!-- source: README.md -->

# Kern-SM89-W4A16 · Qwen3.8-27B · 64K PoC

**版本：1.0.0｜基线日期：2026-09-08｜交付类型：AI 开发执行文档 + 已实现的 CPU 辅助工具 + Java 测试夹具。**

这不是已经完成 SM89 移植的推理引擎安装包。包内不包含模型权重、CUDA cubin、可运行的 Kern 27B SM89 binary，也没有伪造 GPU 成绩。开发 AI 按 `AGENT_START.md` 执行任务，产出这些缺失的工程成果，再用这里的协议验证。

## 你的环境与目标

RTX 4090 24GB、64GB RAM、600GB SSD；最新用户提供 **Driver/KMD 610.57.04，CUDA UMD 13.3**。UMD 不是 Toolkit，实际 `nvcc`、cuBLAS、容器镜像由只读预检确认。现有 NInfer `44a2c6c`、`rk4v4-e8`、MTP3、262K 是受保护的生产基线。

首阶段只做：**Qwen3.8-27B，W4A16 权重，BF16 activations，FP32 GDN state，BF16 KV，单用户，no-spec，真实 65,536-token 输入 + 2,048-token 输出**。服务窗口/池的计划起点是 73,728 tokens，不把 `--capacity 65536` 当作“64K 输入还能继续生成”。

优先验证同权重正确性、64K 容量、长期 append cache 与 Java 工具循环；再优化速度。DFlash2/MTP、低比特 KV、200K 和随机采样属于后续独立阶段。

## 最快开始

```bash
unzip kern-sm89-w4a16-64k-poc-v1.0.0.zip
cd kern-sm89-w4a16-64k-poc-v1.0.0
# 已有numpy时可直接自检；缺依赖则先按docs/17建立隔离工具环境。
bash scripts/self_check.sh
bash scripts/preflight.sh
```

这两步不停止现网、不加载 27B、不安装驱动。把 `AGENT_START.md` 交给运行在外部模型或其他机器上的开发 AI，开始实施。**不要让执行器依赖即将被暂停的本机 NInfer。**

开发完成、T22 生成本机资格计划之后：

```bash
mkdir -p logs
ALLOW_PRODUCTION_PAUSE=1 nohup bash scripts/run_qualification.sh \
  configs/qualification.local.json > logs/qualification.log 2>&1 &
tail -f logs/qualification.log
```

只有你允许评测窗口时才设置该变量。程序默认拒绝暂停生产；正常退出/超时会尝试恢复原来处于 active 的 NInfer 服务。SIGKILL、断电和宿主故障仍需要人工恢复，详见运维文档。

## 目录

| 入口 | 内容 |
|---|---|
| `AGENT_START.md` / `AGENTS.md` | 开发 AI 的执行与禁止事项 |
| `docs/00-master-plan.md` | 总方案与决策 |
| `docs/01`–`docs/18` | 环境、模型、ABI、状态、缓存、数值、性能、Agent 与验收 |
| `tasks/` + `configs/tasks.json` | 有依赖关系、输入输出和验收命令的开发任务 |
| `poc_tools/` | 可运行的审计、SSE、数值、Java 和结果判定工具 |
| `fixtures/` | 三个独立 Java 8 修复项目；无需 Maven 网络 |
| `validation/` | 本次在生成环境实际运行的检查结果，与未执行的 GPU 项目 |
| `references/` | 固定源码位置和证据台账 |

**裁决：** `POC_GO` 只表示 64K、no-spec PoC；不表示胜过 NInfer，不表示 200K 已通过，更不自动切换生产。没有完整证据是 `BLOCKED`；预算耗尽是 `INCOMPLETE`；正确性失败是 `NO_GO`。



---

<!-- source: AGENT_START.md -->

# 开发 AI：从这里开始

你负责在用户的 4090 机器上实现并验证 **Kern-SM89-W4A16 64K PoC**，不是写一份“建议以后实现”的报告。当前 ZIP 已提供需求、接口合同、测试工具和题目；SM89 模型 provider 与 GPU 测试适配器仍需你实现。

## 不可变事实

- 用户最新 Driver/KMD = **610.57.04**，CUDA UMD = **13.3**。不沿用旧 545/12.3 作为驱动限制；也不假定 nvcc=13.3。
- RTX 4090 24GB、64GB RAM、600GB SSD，单 GPU 同时只允许运行一个 27B 引擎。
- 当前生产：`openclaw-qwen38-ninfer.service`；模型调用名 `openclaw/Qwen3.8-27B-WORK`；兼容端点 `127.0.0.1:18343/v1`；引擎 `18030`；NGINX `28343`。
- 禁止改现网 unit、NGINX、模型文件、NInfer repo、镜像 tag 和 production launch 脚本。允许的暂停是显式维护窗口，不是切流。
- 测试 candidate 用 `18041`，oracle 用 `18042`，**串行占 GPU**。既有 NInfer 是产品比较基线；同 W4A16 oracle 才是数值基线。

## 第一轮必须执行

```bash
# 已有numpy时可直接自检；缺依赖则先按docs/17建立隔离工具环境。
bash scripts/self_check.sh
bash scripts/preflight.sh
python3 scripts/next_task.py
```

阅读：`docs/00-master-plan.md`、`docs/01-machine-and-operations.md`、`docs/02-source-and-environment-lock.md`、`docs/03-architecture.md`、`docs/04-memory-budget.md`。复制 `configs/local.example.json` 为 `configs/local.json`，只用本机检查结果填写模型、tokenizer 和源代码路径；不要猜目录。

然后逐个执行 `configs/tasks.json` 中依赖满足的任务。一个任务一个小提交；先失败测试，再最小实现，再验证。每个任务的原始命令、退出码、git diff、硬件状态、证据路径写入 `work/records/<task-id>/`。用任务文件里的测试命令验收，而不是根据模型输出“看起来正常”标记完成。

## 开发闭环

1. T00–T03：冻结生产与工程环境、选同一量化源、读 safetensors header 算内存、生成 reference oracle。
2. T04–T10：SM89 制品合同、Marlin packing/ABI、控制投影、GDN、Attention、完整 provider。
3. T11–T14：4K/64K 数值闭环、图执行、内存与可靠 telemetry。
4. T15–T21：协议拒绝语义、Pi、append cache、生命周期和性能/质量验证。
5. T22–T23：生成本机一小时资格计划与最终裁决，进行有边界的优化。
6. P1 任务只在 P0 通过后考虑；不得为完成 64K PoC 偷换成压缩上下文、FP16 state 或更小模型。

## 动手前的三个硬检查

**控制平面独立。** 开发 AI 不得通过被测 NInfer 提供自己的推理。否则暂停 NInfer 后会失去恢复能力。用外部 Codex/其他受控模型或异机执行器。

**网络可达。** 已有报告说明该机默认不能直连 GitHub。优先在联网机器制作固定 git bundle、wheelhouse、Cargo vendor 和镜像 tar；在目标机按哈希验收。不能把网络失败当成 CUDA 不支持。

**资源排他。** CPU 文档/代码/测试可并行，GPU 编译运行/基准采集串行。没有明确授权的维护窗口，不运行 `guard_gpu.py --allow-production-pause`，也不自行 `systemctl stop` 或 `docker kill`。

## 证据输出

完成任务后更新 `work/task-status.json`（任务 id → PASS/FAIL/BLOCKED + evidence），但不要修改签发时的 `configs/tasks.json` 初始状态。最后生成 `results/<run>/evidence.json`：引用同一 run 下的真实文件及 SHA；运行 `python3 -m poc_tools.cli report ...`。

`configs/evidence.template.json` 的 null 和 NOT_RUN 是诚实的初态，不能以任意数值补齐。开发时新增的命令、二进制、tensor layout 和库版本都要固化到 run 的 profile/lock。

## 最终回报用户

报告已实现的 commit、模型/packed 权重 digest、准确输入长度、no-spec 吞吐、cold/append TTFT、Java 3题、恢复/取消测试和生产恢复状态。失败时给出第一个失败合同、复现命令和最小日志，不得声称“已经达到极致”。



---

<!-- source: docs/00-master-plan.md -->

# 总方案：用可审计的 64K PoC 建立 4090 性能实验底座

## 目标与非目标

用户希望把 Qwen3.8-27B 在 4090 上的质量、速度、长 Agent 工作体验推向更好的组合。当前要交付的工程里程碑是 **Kern-SM89-W4A16、真实64K输入**，不是证明已达到理论最优，也不是一次实现完整200K生产替代。

原方案中“只换 sm_89”“greedy 必须全程同文本”“默认 FP16 GDN”需要精确化：Kern 的当前发布包是 GB300 kernel + BF16权重；需要新的量化 provider、ABI 和布局合同。不同合理浮点路径可能在近似平局处产生不同 token，必须定位数值差异而不是用文本差异一票判断。P0 保留源配置 FP32 state，减少同时变化的变量。[S01][S02][S05]

## 推荐路线

`固定 W4A16 checkpoint → 在4090运行同权重 reference → 导出经过验证的 packed buffers/ABI → 新 Kern provider → SM89 kernels → plain eager → plain graph → 64K + append cache + Pi Java`。

使用现有 kernel-sanders vLLM 环境作为**可选依赖/算子来源**，但不照搬它的默认 DFlash2、INT8 embedding、FP16 state、KVarN、八槽配置。每项都必须显式关闭或还原到 P0 合同；做不到时该环境不是合格 oracle。[S04]

另一条路线是重写完整 NInfer codec/Program 到 Kern；它会增加转换与状态边界工作，当前不推荐。直接 offload BF16 27B 到 CPU 只适合辅助调试，不作为“4090高性能”交付。

## 固定 P0 合同

| 项目 | 值 |
|---|---|
| 模型 | Qwen3.8-27B 完整语言 decoder，64层，不删层/头 |
| 权重 | dbirks W4A16 AutoRound（本机实际 revision/hash 冻结） |
| activation / GDN | BF16 / FP32 |
| Attention KV | BF16，16层、4 KV头、head_dim256 |
| 输入 / 输出 | 65,536 / 至少2,048 target token |
| 最大窗口/池计划 | 73,728 tokens；以页对齐后的真实容量验收 |
| 并发 / 草稿 | 1 / none |
| 采样 | temperature=0 的 greedy；其他非默认采样请求明确拒绝 |
| 首选prefill chunk | 512；256/1024 为独立受控候选 |
| 生产 | NInfer 保持默认，PoC 不自动切流 |

首阶段文本模式不装载 vision/MTP 未使用权重，**不是改变语言模型权重**。原始文件保持只读。embedding/lm_head 保持源精度；需要再量化时升级为单独 profile，oracle 必须同步。

## 两个不同的成功判定

**工程可用 POC_GO：** 同权重数值门、实际64K、最低速度、缓存、Java、生命周期和资源安全都通过。

**值得替代 NInfer：** 在同机产品任务、相同 thinking/采样、相同工作量下有稳定改进，且没有质量或恢复退化。两边权重/KV精度不同，不能把这种产品比较称为严格引擎A/B。3个Java题只是一组 smoke gate，不是统计上的通用能力等价证明。

本包提供工程可用 gate；替代结论必须保守。继续优化的实际价值可能在冷 prefill、少量新增 token 的 extend、缓存恢复和 host 开销，而非单一峰值 tok/s。



---

<!-- source: docs/01-machine-and-operations.md -->

# 机器、环境与生产隔离

## 已确认与待测事实

| 信息 | 来源 | 处理 |
|---|---|---|
| Driver/KMD610.57.04、CUDA UMD13.3 | 用户最新消息 | 当前基线，不再使用545驱动假设 |
| 4090 24GB、RAM64GB、SSD600GB | 用户 | 容量上限，空闲量仍需实测 |
| Debian12、Docker、现网NInfer路径 | 用户部署报告[S00] | 先只读核对，再执行 |
| Toolkit/nvcc/cuBLAS版本 | 尚无最新运行输出 | 用预检确认，不能从nvidia-smi推导 |
| GPU UUID、PCIe链路、功耗、温度 | 需本机测量 | 纳入每次基准证据 |

当前610驱动并不意味着需要安装13.3 Toolkit。Kern固化 CUDA13.0 API，参考vLLM环境使用13.0用户态；可选择固定13.0.1开发容器，保留宿主既有Toolkit。新驱动兼容旧CUDA应用的一般规则适用，但最终以设备探针和实际二进制为准。[S03][S06]

## 只读检查

```bash
bash scripts/preflight.sh
nvidia-smi
nvcc --version
systemctl is-active openclaw-qwen38-ninfer.service
docker image inspect ninfer-4090:44a2c6c --format '{{.Id}}'
```

不要打印 `docker inspect` 完整环境或 nginx配置，可能包含鉴权信息。不要将密码写进变量、脚本、日志。无需额外安装 `cuda-compat`，尤其不要用旧 compat 库覆盖宿主610提供的 libcuda。[S06]

## 生产白名单

生产 unit：`openclaw-qwen38-ninfer.service`。
保护端口：18030、18343、28343。candidate/oracle 只用18041/18042，默认 loopback。
保护模型：`/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer`。
SHA：`eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`。

不得复制“latest”覆盖现有模型；不得启用WORK/TEXT unit作为评测结束后的自动恢复目标。当前默认是NInfer，回退WORK是另一项用户操作。[S00]

## 维护窗口

```bash
python3 scripts/guard_gpu.py --allow-production-pause --timeout 3600 -- \
  bash work/commands/run_candidate_checks.sh
```

此脚本只停止白名单服务，只在它原来 active 时恢复。它不会杀未知GPU进程。若停止后仍有进程占卡，退出并恢复生产。GPU0的文件锁只能约束本套工具，不能阻止别人的程序，因此仍检查 `nvidia-smi`。

必须让 candidate 以前台进程运行，容器用 `--rm --init`；禁止 detached daemon。任务内也必须注册自己的后台子进程清理。若 guard 被SIGKILL/机器掉电，读取 `.state/gpu-lease.json`，确认guard/child已结束，再人工 `sudo systemctl start openclaw-qwen38-ninfer.service` 并检查18343。finally/trap不可能覆盖断电。

评测模型进程用普通用户。测试Pi最好放在只挂载其工作目录的容器中；哈希保护测试文件是评测完整性措施，不是操作系统沙箱。


### 容器退出与恢复边界

前台`docker run`客户端被杀不构成“容器一定已退出”的证明。T22的candidate supervisor必须使用唯一名称和`kern-poc-run=<run_id>` label记录自己创建的容器；finally中按名称+label核对后执行`docker stop --time 10`，再等待该容器退出/移除。禁止处理标签或owner不匹配的容器。原始PID/容器ID写进run日志；回到生产前确认本次候选不再占GPU。不能以`--rm`替代这个生命周期测试。


若上次journal仍标记`restore_required=true`，下一次guard会拒绝覆盖它。先确认旧guard/候选进程已经退出，恢复并验证NInfer，再归档该journal；不要删除它来绕过一次尚未完成的恢复。



---

<!-- source: docs/02-source-and-environment-lock.md -->

# 源码与环境冻结

## 基线

- Kern：`5188aaf8dc992ebe635f111d17c269969706da27`，schema v4。
- 可参考的 vLLM recipe：`kernel-sanders/qwen38-27b-rtx4090-vision@36317835f2224c620f4d604bd57bf0a70f14cade`。
- 用户生产 NInfer：`tensorninja/ninfer-4090@44a2c6c`；其自有兼容层属于生产，不改。
- Kern依赖：`cudarc=0.19.7` + `cuda-13000`；HF tokenizer库版本参考0.22.2。[S03]
- recipe Docker声明 vLLM0.27.1、torch2.13/cu130、Triton3.7.1。它们是候选来源，不是假定本机已安装；实际wheel、patch和库哈希写入环境锁。[S04]

## 目标机不能直连GitHub时

在联网机器克隆并确认完整SHA，保存：

```bash
git -C kern bundle create kern-pinned.bundle --all
sha256sum kern-pinned.bundle > kern-pinned.bundle.sha256
# 同时保存 reference recipe 的固定源码、Cargo vendor、wheelhouse 和构建后的镜像tar。
```

目标机：

```bash
sha256sum -c kern-pinned.bundle.sha256
KERN_GIT_BUNDLE=/data/offline/kern-pinned.bundle \
  POC_SOURCE_DIR=/data/kern-sm89-poc/source/kern bash scripts/setup_sources.sh
```

联网阶段可以下载所需 crates/wheels；目标机编译使用 `cargo build --locked --offline`。`kern-serve` 是独立workspace，也要单独 vendor 它的依赖，不能只准备根Cargo.lock。[S03]

## 必须冻结的四组身份

1. 源码：Kern、oracle、patchset、provider生成器。
2. 模型：每个safetensors/config/tokenizer/template文件SHA，选定tensor列表，派生/重排buffer SHA。
3. 工具链：镜像digest、nvcc、ptxas、Rust、cuBLAS、CUDA runtime、动态加载的真实库路径。
4. 执行合同：dtype、chunk、page、batch、spec、sampling、模板、最大窗口、workspace plan。

不要只锁“Qwen3.8”名字。`model_sha256` 在工具中是完整文件清单的内容digest；它不等于HF revision，两者都应记录。

## 本包刻意未填写的值

本机模型目录、HF最新精确revision、镜像digest尚未被这次生成环境读取，因此配置为null/待本机锁定。AI在T00/T02自动发现与冻结，不允许猜一个40位hash。不能下载时保持BLOCKED，并使用已有同源本地文件核验；不能偷偷改用另一个量化模型。



---

<!-- source: docs/03-architecture.md -->

# 新provider的架构与所有权

```text
Original W4A16 safetensors (read-only)
  └─ validated export/repack → packed tensors + provenance
       └─ gen_qwen38_sm89_w4a16.py → schema-v4 manifest
            └─ SM89 cubins + typed Op ABI
                 └─ kern-runtime
                      └─ KernScheduler + Pi frontend
```

模型知识放在 provider/生成器：层数、GDN布局、norm、rope、gating、tensor拼接、quant codec。runtime只处理类型、字节、ABI、状态租约与launch。不得在通用runtime里加入“model==qwen3.8”分支。[S01]

## 新增文件的合同

| 路径（相对Kern源码） | 职责 |
|---|---|
| `tools/sm89/artifact_key.py` | arch/toolchain/source/flags/shape共同定义制品身份 |
| `tools/sm89/export_packed.py` | 冻结oracle真正使用的重排weight/scales；分片流式导出 |
| `tools/sm89/capture_ops.py` | 小规模oracle捕获、ABI与tensor角色标注 |
| `tools/sm89/weight_contract.py` | group128/对称/pack/reorder的校验 |
| `tools/gen_qwen38_sm89_w4a16.py` | 新provider生成器；不覆盖GB300示例 |
| `tools/kernels-src/sm89/` | Ada专用入口与必要适配核 |
| `examples/qwen3.8-27b-sm89-w4a16.json` | 新manifest，no-spec，batch1 |
| `tests/sm89/` | provider、数值、内存与生命周期测试 |

以上是**要创建的代码路径**，不是声称仓库已经存在。现有修改热点见任务表和源码地图。

## Op合同与Runtime边界

把4bit weights放在合法typed packed buffer（通常i32）中，scales为独立buffer；类型通过不等于codec正确。只有provider知道pack规则。可把“W4 GEMM + activation/residual”封成一个逻辑Op，内部多次launch与scratch，不要求host层解释数学语义。

输入buffer、carry、state分别有不同生命周期。模型持久状态不得藏进临时scratch；scratch不得被当作下一HTTP轮的缓存。图captured pointers的稳定性由runtime负责，语义offset和页布局由provider负责。

## 不直接用原版Kern启动27B

当前发布Qwen包绑定GB300的sm103制品与约50GiB BF16权重。更改环境变量不能让这些bytes在4090上变成正确高性能实现；必须重新生成全部被引用模块，确认ABI、shared memory和tensor layout。[S01][S02]



---

<!-- source: docs/04-memory-budget.md -->

# 内存账：先证明装得下，再跑64K

## 精确的KV公式

源模型16层Full Attention、4个KV头、每头256维、K和V、BF16每值2字节：[S05]

`bytes/token = 16 × 4 × 256 × 2 × 2 = 65,536 = 64 KiB`。

64K输入对应4GiB KV；本PoC池计划73,728 tokens对应4.5GiB。不能用4GiB输入账忽略输出、page rounding与pad。

GDN参考布局每层3,211,264B，48层每sequence约147MiB。runtime显存预算需要active、null、pad、checkpoint所用全部slot。**新增checkpoint首先是GPU slot，不是“64GB RAM里随便留300MB”。** park到host才转移placement，而且存在复制/页共享费用。[S01]

## 预算工具

```bash
python3 -m poc_tools.cli weights /data/path/to/W4A16 --out results/weights.json
python3 -m poc_tools.cli memory --weight-gib 16.0 --capacity 73728 \
  --slots 4 --workspace-gib 1.0 --out results/memory-estimate.json
```

`16.0`只是算例，必须替换为实际被绑定的device weight bytes。safetensors文件大小不等于device占用：重排、padding、衍生表、临时双份buffer都会增加峰值。反之，vision/MTP不被provider引用时不应加载到device。

## 强制检查

- 先按tensor+workspace+state+graphs+headroom逐项核对；目标留1GiB，硬底线留512MiB。
- `vars.tokens.max` 默认512，不把prefill chunk轴误设成64K；`seqs.max`只保留需要的batch上界。
- logits只输出最后一行或当次验证需要的行，不保留 `[65536,vocab]`。
- 根runtime的所有上界分配与kern-serve `max_seqs` 默认256分别检查；**只传max_seqs=1并不自动缩小manifest里所有workspace**。[S07]
- 使用 `Capacity{tokens,seqs}` 算实际allocator开销；页对齐后池不能少于请求+输出。
- 不把host页缓存、CPU offload、Unified Memory页面换出当成显存内成功。

## 若P0内存不够

顺序：删未引用加载 → 收紧workspace轴和临时生命周期 → chunk512降256 → 移除多余graph/batch capture → 减少checkpoint保留数量。每步重新审计峰值。

仍不足时，不悄悄压GDN或KV。建立单独`p0-q8-kv`派生profile，oracle使用相同Q8 codec/scales，重新走数值与质量门。再量化embed/lm_head属于P1另一条路线。优先保留语言权重质量，不为了凑一个“64K通过”偷偷删层/截断输入。

200K低比特KV属于后续；本包四bit预算功能只是估算器，没有实现任何四bit attention kernel。



---

<!-- source: docs/05-sm89-artifacts-and-abi.md -->

# SM89制品、ABI与设备能力

## 一个必须先修的上游细节

`tools/handwritten.py` 在`target/cubins`缓存手写核；带defines的变体用名字/时间戳决定是否重新编译，arch来自`KERN_SM`但不进入文件名身份。[S08]

新实现必须使用：

`artifact_key = SHA256(source_closure + compiler_version + compiler_binary_sha + flags + defines + arch + ABI + shape_contract)`。

目录为`target/cubins/sm89/<toolchain-key>/<artifact-key>/`。不能以mtime判断正确，也不能仅用文件名里写sm89作为兼容证据。切arch、编译器、flags、header任一个都必须cache miss。

## 明确禁用的特性

4090 CC8.9的P0禁止引用：sm100/sm103/sm120 cubin、PDL、thread-block cluster、TMA tensor map、WGMMA/TCGEN05及Blackwell FP4专用核。关闭manifest的PDL标志不等于二进制不含其指令。需要SASS核查与实际module加载。[S09]

Ada每block shared-memory opt-in上限99KiB，静态默认48KiB；上游verifier允许更大shared memory不意味着Ada支持。加载后查询实际`cudaFuncGetAttributes`与device属性，检查静态+动态总量，不能只看manifest动态字段。[S09]

## 最小探针

在固定工具链容器内、授权维护窗口：

```bash
nvcc -O3 -arch=sm_89 scripts/gpu_probe.cu -o work/gpu_probe
./work/gpu_probe > results/gpu-probe.json
```

此探针验证一个小kernel能运行与CC8.9，不验证Marlin、GDN或64K。

## ABI登记

每个module保存：入口mangled名、源码commit/license、cubinSHA、SM、编译flags、shape/constexpr、参数size/offset/方向、strides、shared-memory、grid、引用权重codec。

Triton会删除等于1的参数并固化divisibility，不能凭函数名推断真实ABI。用实际捕获实例、编译IR/metadata与`cuFuncGetParamInfo`交叉核对。两个实例参数布局相同，也可能因constexpr不同而计算不同。[S02]

`poc_tools.cli lint`只是附加的保守SM89静态检查；还必须运行Kern verifier、实际ABI校验和compute-sanitizer。声明自洽不证明cubin数学正确或内存安全。



---

<!-- source: docs/06-w4a16-provider.md -->

# W4A16权重与Marlin接入

## 源合同

选择dbirks版本：group_size128、symmetric、num_bits4、actorder=null、compressed-tensors pack-quantized，activations为BF16；小的GDN控制投影、lm_head、MTP、vision保留BF16。[S05]

`weight_packed`、`weight_scale`等**真实tensor名和shape从下载文件读取**；不要把HF统计的packed元素数误当模型参数量，也不要凭模型名字推定packing。

## 不重写一个错误的“通用int4 decoder”

优先在oracle实际加载后捕获它交给Marlin的packed buffer、scale排列、group index/zero约定、padding与workspaces。把这组结果输出为新safetensors，保留原model目录只读。运行期Kern不能依赖Python/PyTorch执行MatMul；导出和oracle阶段可以使用它们。

每层同一输入分别比较：原compressed-tensors在oracle的线性输出、导出packed内容回到oracle的输出、新SM89入口输出。只有三者闭环才接进整个模型。

## 三组测试不能省

1. 编码边界：int4所有16个码值、scale=0/小值/大值；零点/符号/两个nibble顺序；group边界127/128/129；非整tile尾部。
2. 实际几何：M=1/2/7/8/16/128/256/512；K/N取本模型真实投影，特别是5120→96控制投影不要错当quantized GEMM。
3. 重排幂等与完整性：repack不能重复应用；每个输出buffer带codec+producer版本+输入SHA，加载不匹配就拒绝。

## host launcher不是cubin

Marlin的Python包装可能执行repack、选择kernel、分配workspace、维护locks和动态shared memory。抓到一个launch不等于完整算子。为每个M形状冻结完整host准备语义，再用flat CUDA ABI入口或schema-v4 Op内部多launch表达。不要把需要PyTorch Tensor对象的C++ extension函数伪装为runtime extern。

raw-input→packed准备应在load阶段完成。热decode禁止把完整4bit矩阵解压为BF16再调用cuBLAS；这既浪费带宽也破坏24GB预算。若调试临时单层解压，输出必须标为DIAGNOSTIC，不能进入性能成绩。

## GDN/MLP拼接

QKV+gate、GDN qkvz、ba、gate_up的拼接次序必须来自oracle与源config。拼接shape吻合不代表语义正确。每个融合buffer输出index map，至少测试一个单hot通道，排除q/gate或a/b交换。



---

<!-- source: docs/07-state-attention-and-prefill.md -->

# GDN、Attention与prefill路径

P0把源模型的FP32 recurrent state保持到底。FP16 state只能作为独立P1优化；不是代码移植的默认前提。[S05]

## 持久状态

GDN含causal conv历史与SSM state。conv kernel_dim4表示3个历史位置；每个layer/sequence/slot都有明确stride。padding行写null/dedicated pad slot，不得写真实session。prefill与decode都从同一已提交frontier续算。

Attention的page-size、K/V interleave、head顺序与scale是provider合同。旧Kern捕获曾固化784-token页，后来TRTLLM路线改用64。**不能只把JSON中的784改64，却继续用旧cubin。** 新provider可选64-token页，但必须重新编译/捕获配套read/write/attention核。[S01][S02]

## Prefill末token

源Kern的Qwen bring-up指出：GDN chunk prefill与recurrent decode的结合/舍入路径不同。应让完整prompt（包含末token）走prefill，由最后一行norm/head产出首个生成token，不能机械复用纯Transformer“最后prompt token走decode”的旧约定。[S02]

## 正确的输入增量

下一轮复用的是**已被模型消费并形成状态**的token，不是“已经发给客户端的所有token”。最后一个sampled token可能尚未输入下一步。输出、KV/GDN frontier、checkpoint.len必须记清，不能缓存未执行的token，亦不能重复执行最后一位。

## 不采用的捷径

不截短attention window、不做PFlash、不语义压缩用户输入、不只保留GDN而丢KV、不使用旧session的state冒充前缀新状态、不改变rope scaling以便假装64K支持。所有这类改变都属于新模型数值配置，需要独立评估。

## 验证形状

chunk=256/512/1024，输入长度1/63/64/65/511/512/513、跨页、跨chunk；prefill后1步/16步/256步decode。先用相同chunk比较eager与graph，再做不同chunk漂移诊断；不要把不同chunk的文本完全相同当作所有实现的必然条件。



---

<!-- source: docs/08-numerical-validation.md -->

# 数值正确性：避免“文本一样才正确”和“文本连贯就正确”两个错误

## Reference hierarchy

A0：同一个已冻结W4A16 checkpoint、同source precision和模板的4090 oracle。
A1：新Kern eager/no-spec。
A2：同Kern graph/no-spec。
NInfer：产品质量/速度比较组，不是这个量化provider的逐tensor真值。[S00][S05]

先用A0重复两次建立本身的噪声/确定性基线。A1/A2强制喂**相同token轨迹**，即teacher forcing；不能比较自由生成已经分叉后的activations。

## 分层门槛（工程起点，不是已证明的模型误差定理）

| 对象 | 初始门槛 | 解释 |
|---|---|---|
| repack/scale/index与重排后权重 | bytes exact | 不能放宽packing错误 |
| 完全相同elementwise内核/schedule | bytes exact | 若更改算术，另立variant |
| 相同FP32 GDN数学路径 | atol2e-7、rtol1e-4；长轨迹另看漂移 | 逐layer、selected checkpoint比较 |
| W4 GEMM BF16输出 | atol0.002、rtol0.002，记录RRMS/max error | shape-specific容差须先用oracle重复与CPU小参考校准 |
| logits | 无NaN/Inf；teacher-forced至少512位置；报告max error、RRMS、KL、top1及margin | 不用单一自由生成字符串代替 |
| eager vs graph，同shape/chunk/kernel | bit exact为默认门 | graph不应改变运算，只改变提交方式 |

容差写进run profile并签名。自动AI不得“试到PASS”为止不断放宽。若固定路径仍不相同，第一步定位第一个不同Op和完整state，而非修改最终答案。

## near-tie处理

记录reference top1/top2 margin与当步最大logit误差e。margin≤2e的step可以解释argmax翻转，但不能自动豁免整次运行：检查误差本身、near-tie比例、未近平局位置的一致率，并做Java/retrieval回归。将reference与candidate都严重错误的logits称作“near-tie”是不可接受的。[S02]

## 现成比较工具

```bash
python3 -m poc_tools.numeric_check --reference work/oracle/layer.npz \
  --candidate work/candidate/layer.npz --out results/layer-check.json
python3 -m poc_tools.numeric_check --reference work/eager/state.npz \
  --candidate work/graph/state.npz --exact --out results/graph-state.json
```

工具比较NPZ中的同名数组，拒绝pickle、shape不同与非有限值。生成这些真实GPU数组的exporter由T03/T11实现；本包没有虚构oracle数组。

## 内存限制

不要每个cut拷贝所有128个GDN slot。只读当前租约的有效slot、选定层/时刻；单比较批≤512MiB，分片写盘、及时释放。全vocab logits按64–128 step分片，不一次保留长序列全量logits。原始BF16 27B整体上卡不是本机oracle方案。



---

<!-- source: docs/09-cache-and-long-agent.md -->

# 长Agent缓存验证

核心问题不是“同一个prompt重复发有多快”，而是“上一轮实际生成+tool结果回灌后，还能否复用完整旧历史”。Kern已有checkpoint/retire/lease_from/park/wake基元，但GDN只有在正确state frontier才可截断/恢复。[S01]

## P0必过

- 一份20K Java/日志内容读入一次，连续10个短追问，不再次read全文。
- 历史从约48K增长到64K，加入多个真实tool_call/tool_result，记录每轮实际LCP、被restore长度和新算token。
- 对有效append历史，旧内容大部分复用；computed_prefill应接近真实新增尾巴+有解释的模板replay，不应反复吞掉20K大文件。
- exact resend可因checkpoint长于prompt而miss；这不是状态错误。输出必须正确，日志必须解释路径。
- 不共享不同模型hash/模板/state layout的cache；session id仅查找提示，不是真实前缀证明。

## 近期rewrite（P1性能，P0正确性）

改变最近user reminder或tool_result：不能误命中旧state。没有合适checkpoint时允许冷算，不允许错误复用。后续可加最近两个真实消息边界anchor。

**边界checkpoint不能追溯创造。** 若当前GDN state已在64K，无法仅复制它并标成50K。必须在prefill经过50K时保存，或从更早合法checkpoint重放到50K再保存；最后再回到正确执行点。前缀哈希/模板版本/weight digest/position/state layout都绑定该位置。

KV整页可共享、末页COW；GDN新slot复制也计入GPU预算。host64GB不代表GPU checkpoint无费用。P0默认host tier关闭，让一个主session尽量留在卡上；host park/wake做独立生命周期测试，不套用GB300的C2C速度到4090 PCIe。

## 每轮日志

`request_id, session_id_hash, prompt_tokens, exact_lcp_tokens, reused_tokens, computed_prefill_tokens, replayed_tokens, checkpoint_frontier, state_frontier, cache_source, restore_ms, snapshot_ms, prefill_ms, decode_ms, target_tokens`。

原始tools/system/rendered-token SHA用于定位变化；不要在公共日志写入私密代码/令牌。真实read同一文件第二次产生一份新tool_result时仍是新tokens，不期待引擎按路径自动复用非前缀KV。



---

<!-- source: docs/10-protocol-and-pi.md -->

# HTTP / Pi合同

当前上游kern-serve的非greedy参数会warning后仍greedy。这不满足可审计A/B。P0先修成：支持temperature0；不支持的非默认采样字段返回明确4xx，绝不静默忽略。[S07]

## 测试API

生产18343及鉴权不改。candidate18041、oracle18042只在loopback提供：`/v1/models`、`/v1/completions`、`/v1/chat/completions`、SSE。raw completions需要支持token-id数组，用于精确64K测试；若frontend不支持，由T15补齐，不偷偷decode→encode改变长度。

开发专用trace endpoint由T14新增：`/poc/v1/traces/<request_id>`，只监听本地、默认生产禁用。服务必须接收并返回X-Request-ID，trace绑定该请求，不能取上一条metrics冒充本条。

### trace最小schema

```json
{"request_id":"uuid","prompt_tokens":65536,"generated_token_ids":[123],
 "accepted_target_tokens":2048,"engine_decode_wall_ms":60000,
 "prefill_ms":30000,"reused_tokens":0,"computed_prefill_tokens":65536,
 "truncated":false,"speculation":"none","state_frontier":67583,
 "kv_dtype":"bf16","gdn_dtype":"fp32","profile_sha256":"64hex"}
```

这里数值是schema示例，不是真实成绩。`engine_decode_wall_ms`包含生成阶段必要的host控制、图提交、同步与commit，不仅是某一个kernel event；计数为真正提交的target tokens。CPU采样若有，不得排除在该时间之外。

## Pi测试模式

P0：双方greedy、thinking off、同模板。包内`poc_tools.java_runner`在临时PI_CODING_AGENT_DIR下写models.json，并实际运行Pi工具循环；现有 ~/.pi 不改。启动前保存 `pi --version`/`pi --help`，若当前版本flag不同，修测试适配并记录差异，不能把CLI错误算模型失败。

P1再实现温度/top_p/top_k和medium thinking，才有资格与现网medium生产体验比较。不能把P0 off的耗时直接压过NInfer medium宣称同等质量。

## stream要求

解析reasoning/content/tool-call arguments，忽略只有role/usage的帧。SSE一个事件可能含多个token；特别是投机输出，不得把帧数当token数。缺usage就记null；缺[DONE]/协议中断记INCOMPLETE。客户端window-tps仅探索值，最终速度gate必须有engine trace。



---

<!-- source: docs/11-java-test-cases.md -->

# Java / Pi实际题目

三个夹具均仅用JDK标准库，目标Java8。controller使用较新JDK时通过`--release 8`编译；JDK8用source/target8。无Maven下载时间污染。

| 题目 | 真实业务合同 | 主要风险 |
|---|---|---|
| java-01-idempotency | 成功幂等、并发同key、失败不缓存、不同key不全局串行 | check-then-act与粗锁 |
| java-02-retry | maxAttempts含首次、只重试IOException、保留中断、传播terminal exception | off-by-one与吞异常 |
| java-03-reconnect | 秒→毫秒、到期边界、clock rollback、旧连接清理不能删新连接 | 单位错误和ABA式状态覆盖 |

运行：

```bash
python3 -m poc_tools.java_runner --base-url http://127.0.0.1:18041/v1 \
  --model qwen3.8-27b-kern-sm89-p0 --out-dir results/pi-run-001
```

每题原始状态必须FAIL，Pi修复后controller复制原始测试与候选src/main到新临时目录再次编译。修改src/test、verify.sh、TASK.md、AGENTS.md即FAIL。仅输出建议、没有真实src/main修改也FAIL。

三个题在本交付生成环境已检查“初始失败/临时参考修复成功”；**这不代表任何模型已经通过它们**。参考修复没有复制进测试Agent的工作目录。

计量累加每条assistant message_end usage，不能只取最后一次响应。tool_execution_start按id去重；不识别的事件保留到原始JSONL，不用零调用补齐。记录总工具次数、失败重试、编译次数、墙钟、TTFT与新算输入量。

3/3是发布smoke门槛，不是“模型能力≥原版99%”的统计证据。后续可用用户真实Java迁移任务扩展，但本阶段避免把题量做大掩盖移植问题。



---

<!-- source: docs/12-qualification-and-gates.md -->

# 一小时左右的资格测试与裁决

**前置条件：** 开发/编译/下载/模型重排/oracle捕获已完成，原始trace与模型锁已落盘。它们不计入一小时资格测试。第一次从零开发不可能由一个基准脚本凭空完成。

## 固定预算

| 阶段 | 预算上限 | 必需输出 |
|---|---:|---|
| 环境/制品复查、warm-up | 3min | device/config/artifact identity |
| 数值核心回归 | 10min | 同权重、teacher-forced、eager/graph |
| 4K/32K速度 | 5min | 3个seed×2048 target token |
| 真实64K | 10min | 3个seed速度 + 单独检索 |
| 10轮append与rewrite安全 | 8min | LCP/state/checkpoint trace |
| Pi Java三题 | 12min | 3/3、测试保护、真实工具记录 |
| 取消/切会话/restore | 7min | 有限状态、无污染、无OOM |
| 汇总/恢复 | 5min | decision与生产恢复状态 |

合计60min预算。某阶段超时则停止或标INCOMPLETE，不跳过必需门后给GO。生产恢复有独立安全尾部，不能为了卡住60min而省掉。

## 硬门

- 环境与制品：实际SM89；无Blackwell cubin；没有上下文截断/CPU权重offload；相同weight+profile身份。
- 数值：见08；所有pack/索引合同通过；没有非有限值或无法解释的state漂移。
- 容量：实际prompt id数=usage=65,536；连续完成至少2,048 target输出；真实峰值留≥512MiB。
- 性能：no-spec，短输入4K–8K至少3样本均≥50 tok/s；64K至少3样本均≥20 tok/s。50是阶段目标，不是承诺；若正确但未到50，记录性能未达标，可保留研究分支，不称GO。
- Agent：append能解释复用旧历史；近期rewrite不错误命中；Java3/3；取消后可继续；会话A/B/A不污染。

## 验收不同于系统比较

NInfer MTP3与Kern no-spec不能作同算法速度A/B。产品横比可看总任务完成时长，但必须列出各自精度/投机/thinking差异。正式引擎隔离比较使用同一W4A16 oracle、同KV、同state、同输入输出长度、同温度。

## 输出身份与证据

由T22把真实原始结果聚合为`evidence.json`，其路径相对本run目录，包含SHA。CPU工具`evaluate_evidence`拒绝缺文件、缺哈希、缺hardware/身份、不完整samples或“draft当output”。它是fail-closed的机械检查，不是防恶意伪造的远程证明；reviewer还要核对原始trace和运行来源。

```bash
python3 -m poc_tools.cli report results/RUN/evidence.json --out results/RUN/decision.json
```

`POC_GO`不自动升生产。失败或超时都保留已完成结果，不伪称全部成功。



---

<!-- source: docs/13-performance-optimization.md -->

# 性能优化顺序：用工作负载决定，不赌“更底层必然更快”

## 测量口径

分开记录cold prefill、cached-prefix extend、decode、host/tokenization、state恢复与Agent工具时间。每个request由输入token数组、profile SHA和request_id串起来。

`TTFT = 首个真实生成delta时间 − 发请求时间`。
`decode_tps = 已提交target tokens / engine_decode_wall_s`。
`task_wall = Agent开始到controller测试结束`。

SSE包含reasoning与content，分开统计再合计；不只统计visible answer。warm-up、图编译与模型加载单列。GPU功耗/温度/频率、其他进程必须记录；仅固定功耗不保证时钟固定。

## 优化梯度

1. 修错误的shape/重复repack/CPU-GPU同步/冗余workspace，不改变数学。
2. M=1、tiny-batch的W4 GEMM选择与融合；真实5120×N矩阵，不只小toy。
3. GDN控制/conv/norm融合，保留有限精度路径；对持久state特别谨慎。
4. 合并norm/rope/cache-write等低算量阶段，用完整graph测收益。
5. 关注长prefix extend；缓存命中仍需对旧KV执行attention，不能将其视为零成本。
6. checkpoint策略优化，减少不必要全量prefill，避免频繁host迁移。

优化采用A/B/B/A交替、至少3个seed；先null对照测噪声。只有总体耗时改善超过噪声且≥3%才保留“小性能patch”；大于10%的改善也必须检验完整Java/缓存，不让少数kernel快掩盖全流程变慢。

不把4090与GB300带宽比例直接换算成tok/s。没有测量就报告潜力，不报告预计必达120/200 tok/s。P0未达到参考后端时，先定位时间份额，最多进行3个有证据的局部优化循环；无法解决就NO_GO并保留oracle/NInfer。

## 追求极致但不混变量

精度不变的调度/融合优先。FP16 state、INT8 embed/head、低比特KV、DFlash2分别建立新profile，逐项证明Pareto收益。若速度提升伴随代码错误或长会话错缓存，直接淘汰。不要为了胜出benchmark关闭正常thinking、缩短输出或截掉工具结果。



---

<!-- source: docs/14-task-execution-and-parallelism.md -->

# AI任务执行与并行

任务详细文件位于tasks/，机器可读DAG是configs/tasks.json。T00开始，每个任务以“独立可验证成果”为单位，不以修改行数划分。

CPU并行组：环境锁/权重header/协议测试/Java夹具/文档检查可以分工。GPU依赖组：oracle→packing/GEMM→GDN/Attention→全模型→性能与Agent，必须在同一时间只有一个owner。

每个独立开发任务在独立git worktree；共同改provider生成器时由一个integrator合入。不得多个AI同时改一个文件、同时写同一个artifact cache。所有编译输出按arch+toolchain+source+shape key隔离。

`python3 scripts/next_task.py`给出尚未完成、依赖已满足的任务。实际状态记录在`work/task-status.json`，初始任务清单不可直接改成全PASS。状态必须绑定证据文件。

每个任务结束：小范围单测→源diff审阅→相关GPU回归（如涉及）→提交→记录commit/命令/退出码。reviewer不能仅看“主AI说测试通过”。模型挂了或进程超时，先保留原始日志、停止当前候选、恢复NInfer，再做系统化debug。

本包不提供远程SSH凭据、不替用户自动创建外部AI任务。它是交给已有执行AI的工作合同。执行器能力不足时用BLOCKED说明缺的是哪项工具/权限，不伪造通过。

## 路径约定（避免两个work目录互不相见）

`KIT_ROOT`是解压目录；`POC_ROOT`默认`/data/kern-sm89-poc`；Kern源码是`POC_ROOT/source/kern`。任务里的`tools/`、`crates/`、`tests/sm89/`、`examples/`相对Kern源码；本包的`configs/`、`scripts/`、`poc_tools/`相对KIT_ROOT。

AI在T01建立一个共享工作目录`POC_ROOT/work`，将`KIT_ROOT/work`与`KERN_SOURCE/work`链接到它（只在目标不存在时创建，不覆盖目录）。这样任务命令从Kern源码运行时的`work/poc.local.json`与本包next_task看到的是同一份。`configs/qualification.local.json`永远位于KIT_ROOT；其中全部argv路径由T22写为已存在的绝对路径。记录每条命令cwd，不依赖执行器猜测。



---

<!-- source: docs/15-troubleshooting-and-stop-loss.md -->

# 故障隔离与止损

| 现象 | 先看什么 | 禁止的“修复” |
|---|---|---|
| no kernel image / invalid image | cubin真实arch、源/toolchain key | 改文件名、移除hash校验 |
| invalid value / too many resources | 参数ABI、shared-memory总量、grid | 盲降校验门 |
| 文本连贯但后续错误 | teacher-forced第一个差异、GDN/conv位置 | 仅调temperature掩盖 |
| 64K OOM | manifest最大shape、graph/pad/state slot、重复权重 | silent truncation或CPU offload冒充 |
| exact repeat快但append慢 | template重渲染、最后token是否消费、end checkpoint | 按session id强制错复用 |
| graph快但结果漂移 |指针生命周期、host-write事件、shape bucket|跳过graph正确性测|
| Pi无工具调用 | tool schema/template/parse/usage/CLI | 把自然语言描述当工具执行 |
| HTTP墙钟慢 | tokenization、prefill/decode、restore拆账 | 用kernel单测数字替代E2E |
| GitHub不可达 | 源码bundle、vendor、离线镜像 | 全局改DNS/代理或安装无关CUDA |

## 止损条件

未知codec/ABI不能安全解释；需要超过可用显存的常驻BF16整模型；必须依赖SM90+专用指令；P0持续出现state corruption；无法保护/恢复生产；64K靠截断才通过——立即停止本路线交付，输出最小复现。可以保留已完成的单层实验，但不能给POC_GO。

单一优化不超过3次有证据的调参循环。用户生产已经有可用NInfer，不应为了追一个不确定的小提升长期破坏工作环境。

## 恢复动作

先停止你自己登记的candidate前台进程/实验容器，确认GPU没有该进程。若 `.state/gpu-lease.json` 写了restore_required，且guard/child已终止，再启动白名单unit、检查18343模型id与18030。不要启动多个冲突服务，不用`pkill -9 python`等全局命令。



---

<!-- source: docs/16-roadmap-after-poc.md -->

# P0之后：不是这次验收的隐含承诺

## P1a：真实采样与medium thinking

新增device sampler/RNG计数器，top-k/top-p/temperature/seed的明确合同。先无spec验证分布，再做Pi medium和现网对齐。不能把greedy接受逻辑直接套到随机采样的spec路径。

## P1b：DFlash2或MTP

优先从完整plain provider出发。DFlash2新增draft权重、tap/local context、draft/verify/accept/advance的事务，最后token/EOS/取消下只能commit实际接受的prefix。概率采样必须使用正确accept/reject规则；greedy正确不能证明随机采样无损。

## P1c：内存精度变体

FP16 GDN、INT8 embed/head、INT8/FP8 KV分别做profile与oracle。先测质量和长会话，再测速度。低bit并不自动更快；量化/反量化或状态replay可能增加计算。

## P2：120K→200K

当且仅当64K可用与数值合同稳固，再引入完整低比特KV codec+scale+attention消费路径。不是把manifest dtype写成u8就算压缩完成。需要200K实际输入、输出余量、checkpoint预算、long-needle/Java代码精确检索、多轮append与soak。

NInfer E8与KVarN只能作为独立参考，不混成一个未验证的codec。未来完成200K也要单独发布证据，不能沿用本包的POC_GO。

## 另一种价值路径

如果Kern最终未胜过NInfer serving，但得到验证过的SM89 kernel/数值测试器，可在许可允许和接口匹配下将局部成果移回NInfer。实验平台价值与生产替代价值分开判断。



---

<!-- source: docs/17-tooling-reference.md -->

# 本包工具手册

| 命令 | 已实现功能 | 不代表什么 |
|---|---|---|
| `bash scripts/self_check.sh` | CPU单测、语法、文档/任务检查 | 不是GPU测试 |
| `bash scripts/preflight.sh` | 只读采集机器/工具/服务信息 | 不改驱动，不加载模型 |
| `python3 -m poc_tools.cli weights DIR --out FILE` | safetensors头与大小审计 | 不证明全部device布局 |
| `... lock-model DIR --out FILE` | 流式SHA锁定模型文件 | 不生成Marlin权重 |
| `... memory --weight-gib X` | 明确KV/state/workspace估算 | 不是真实显存峰值 |
| `... lint MANIFEST` | PoC SM89禁用特性/资源粗检 | 不能替代Kern verifier或SASS |
| `python3 -m poc_tools.build_prompts ...` | 使用本地tokenizer生成精确长度token数组 | 不假定服务已接受长度 |
| `python3 -m poc_tools.http_probe ...` | SSE/usage/TTFT/trace采集 | SSE帧数不是token数 |
| `python3 -m poc_tools.numeric_check ...` | 同名NPZ数组差异 | 不替用户生成GPUoracle |
| `python3 -m poc_tools.java_runner ...` | Pi真实工具循环+独立测试验证 | 不是全能力benchmark |
| `python3 scripts/guard_gpu.py ...` | 显式维护租约、正常恢复 | 不能处理断电/SIGKILL |
| `bash scripts/run_qualification.sh` | 执行T22生成的本机资格计划 | 不是自动完成GPU引擎开发 |
| `... cli report evidence.json` | fail-closed证据裁决 | 不是防恶意伪造的硬件证明 |

`configs/qualification.example.json`只是展示argv编排的探索例子，故意不能当完整资格套件。正式文件由AI在实现GPU exporter、cache/lifecycle adapter和candidate launcher之后生成；脚本缺该文件时BLOCKED，不擅自创建假的结果。

依赖：CPU基础工具用Python标准库；NPZ比较需要numpy；精确token生成需要tokenizers；Java夹具需要javac/java；Pi测试需要本机Pi。requirements-tools.txt应安装在隔离venv。不要修改用户全局Python/Node环境。


## 工具依赖安装（非GPU开发环境）

```bash
# 推荐离线：联网机先用目标Python/架构下载requirements-tools.txt中的wheels。
WHEELHOUSE=/data/offline/wheelhouse bash scripts/setup_tools.sh
# 或明确允许联网：ALLOW_NETWORK=1 bash scripts/setup_tools.sh
source .venv/bin/activate
bash scripts/self_check.sh
```

setup_tools只创建本包.venv，不安装驱动、不停止生产。未提供wheelhouse且未授权联网时退出78。它不负责安装Rust/CUDA/vLLM，这些属于T01的独立环境锁。



---

<!-- source: docs/18-source-map-and-evidence.md -->

# 源码地图与证据等级

证据分为：U=用户实测/机器事实，S=已读取源码/模型卡，D=本方案设计，R=需要目标机运行确认。D/R不能写成S或U。

| 阅读点 | 决定的设计 |
|---|---|
| Kern `Cargo.toml` | CUDA API固定13.0、runtime无Python、serve独立workspace |
| `tools/handwritten.py` / `tools/build_kernels.sh` | 需要SM89专属artifact cache key与构建目标白名单 |
| `tools/gen_qwen35.py` / `tools/qwen_weights.py` | 模型几何、GDN/rope/拼接和source绑定 |
| `crates/kern-manifest/src/types.rs` / `verify.rs` / `protocol.rs` | 新typed Op与动态shape、数据流和caller合同 |
| `crates/kern-runtime/src/compile.rs` / `cubin.rs` / `weights.rs` | ABI、内核加载、weight binding、extern边界 |
| `crates/kern-runtime/src/pages.rs` / `prefix.rs` / `host.rs` | 页共享、state slot、checkpoint/host恢复 |
| `crates/kern-serve/src/lib.rs` / `scheduler.rs` / `tray.rs` | 默认并发、容量、仅greedy、末token提交、请求生命周期 |
| `docs/qwen38-bringup.md` | 旧schema历史记录、数值分叉与ABI陷阱；不能当当前CLI |
| dbirks model config | W4 group128/对称、BF16 activation、FP32 GDN |

本包生成环境无法联网clone完整仓库，已通过GitHub connector读取上述关键源/已有上下文，且不宣称已编译Kern。目标机T01必须验证固定SHA与实际文件；若发现与文档不符，记录差异并停止相关假设，不对着过时行号盲patch。

完整primary来源见 `references/sources.md`。用户报告来自 `d6f1461e-1648-4dbf-925a-7e087c9483ac.md`；本包只记录任务需要的非秘密生产身份，不打包原始可能含私人内容的报告。



---

<!-- source: references/sources.md -->

# 来源与冻结日期

检索/设计截止：2026-09-08。来源中的性能和能力只代表其自身条件；本文包没有在RTX4090上复现。没有把社区宣传数字填进验收结果。

| ID | 来源 | 采用范围 |
|---|---|---|
| S00 | 用户附件 `d6f1461e-1648-4dbf-925a-7e087c9483ac.md`，以及本次明确给出的610.57.04/KMD/UMD13.3 | 机器、生产服务/路径、模型SHA、网络和恢复约束；最新消息覆盖旧驱动描述 |
| S01 | [Kern固定源码](https://github.com/pegainfer-project/kern/tree/5188aaf8dc992ebe635f111d17c269969706da27)，尤其docs/manifest.md、runtime.md、serve.md | schema-v4、states/pages/checkpoint与runtime边界 |
| S02 | [Qwen bring-up记录](https://github.com/pegainfer-project/kern/blob/5188aaf8dc992ebe635f111d17c269969706da27/docs/qwen38-bringup.md)、tools/gen_qwen35.py | 历史ABI、GDN数值与prefill末token问题；历史CLI不照抄 |
| S03 | [Kern Cargo.toml](https://github.com/pegainfer-project/kern/blob/5188aaf8dc992ebe635f111d17c269969706da27/Cargo.toml) | cudarc0.19.7/CUDA13.0 API；serve独立workspace |
| S04 | [4090 vLLM参考recipe](https://github.com/kernel-sanders/qwen38-27b-rtx4090-vision/tree/36317835f2224c620f4d604bd57bf0a70f14cade)，README.md、Dockerfile | 算子/依赖来源；默认profile不作为本PoC oracle |
| S05 | [dbirks W4A16模型卡](https://huggingface.co/dbirks/Qwen3.8-27B-W4A16-AutoRound)、[config.json](https://huggingface.co/dbirks/Qwen3.8-27B-W4A16-AutoRound/blob/main/config.json) | group128/symmetric、BF16act、FP32 GDN与几何；本机必须另锁文件hash |
| S06 | [NVIDIA CUDA兼容性](https://docs.nvidia.com/deploy/cuda-compatibility/forward-compatibility.html)、[CUDA13.0.1发布说明](https://docs.nvidia.com/cuda/archive/13.0.1/cuda-toolkit-release-notes/index.html) | 新驱动与旧用户态、compat限制；不依据UMD推导nvcc |
| S07 | [Kern ServeOpts](https://github.com/pegainfer-project/kern/blob/5188aaf8dc992ebe635f111d17c269969706da27/crates/kern-serve/src/lib.rs)、[scheduler.rs](https://github.com/pegainfer-project/kern/blob/5188aaf8dc992ebe635f111d17c269969706da27/crates/kern-serve/src/scheduler.rs) | 并发默认、容量、greedy限制、state/前缀策略 |
| S08 | [handwritten.py](https://github.com/pegainfer-project/kern/blob/5188aaf8dc992ebe635f111d17c269969706da27/tools/handwritten.py) | 实际artifact缓存键未绑定arch/toolchain，需要修复 |
| S09 | [NVIDIA Ada Tuning Guide](https://docs.nvidia.com/cuda/ada-tuning-guide/index.html)、[Programmatic Dependent Launch](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/programmatic-dependent-launch.html) | SM89共享内存/硬件能力和PDL边界 |

源模型卡通过Exa读取，关键仓库文件通过GitHub connector读取；NVIDIA文档通过web读取。生成环境的直接GitHub网络下载失败，未声称完成clone、Rust构建、CUDA编译或GPU验证。上面的完整SHA来自已读取的GitHub ref/文件；HF实际权重revision在目标机获取和冻结，不伪造。

下载到目标机的第三方源码/内核需保留原license与provenance。该ZIP不包含第三方cubin、模型权重或字体。CPU辅助工具是本交付生成的参考工程工具。



---

<!-- source: validation/README.md -->

# 本交付验证记录

本目录只记录**交付包辅助工具与测试夹具**在文档生成环境中的验证，不代表用户4090上的Kern实现。

## 已实际执行

- `bash scripts/self_check.sh`：63项Python辅助工具测试，含SSE分片/UTF8、权重头、内存账、清单限制、证据缺失/篡改/NaN/输出不足、进程超时和信号清理、维护控制面mock、任务依赖与文件完整性。
- Python compileall 与所有随包shell脚本 `bash -n`。
- 三个Java8夹具：原始版本全部真实失败；在临时副本上加入已知正确修复后全部通过。原夹具保持有bug，参考修复不放入Agent工作目录。详见`java-fixtures.json`。
- `configs/evidence.template.json`交给结果判定器：退出78、`BLOCKED`，未验证的包不会生成`POC_GO`。
- ZIP归档完整性与内容SHA256在打包后另行检查。

## 日志解释

`*-red.log`是修复前故意暴露缺陷的RED回归证据；**不是最终状态**。最终看`self-check.log`/`tooling-tests.log`。单测中构造的“完整结构→POC_GO”只是判定器测试，内容明确写`test-only`，没有拿它当GPU成绩。

维护控制面的测试用mock替代了systemctl、nvidia-smi和模型健康接口；没有暂停用户服务。另有真实的本地子进程超时/信号测试，但这些子进程不运行模型。

## 明确未执行

| 内容 | 状态 |
|---|---|
| 用户RTX4090设备探针/nvcc编译 | NOT_RUN |
| Kern Rust构建、SM89 CUDA内核实现与运行 | NOT_RUN |
| W4A16模型下载/真实权重重排 | NOT_RUN |
| 同权重GPU oracle、state/logits数值对比 | NOT_RUN |
| 实际64K输入与2K持续输出 | NOT_RUN |
| Pi连接真实模型完成Java三题 | NOT_RUN |
| 用户机器生产暂停/恢复 | NOT_RUN |
| 精确Qwen tokenizer实例运行 | NOT_RUN（生成器算法以测试encoder验证） |
| 两小时或更长实机soak | NOT_RUN |

GitHub连接器完成了源码查阅，但生成容器直接访问GitHub的下载遇到DNS失败。因此不宣称本环境克隆或编译了上游仓库。包内是固定来源的开发合同，不携带上游cubins或权重。

最终GPU资格证据由开发AI在目标机T03–T23实施时生成。签发此包的实际状态是`DEVELOPMENT_KIT_READY / GPU_NOT_RUN`。
