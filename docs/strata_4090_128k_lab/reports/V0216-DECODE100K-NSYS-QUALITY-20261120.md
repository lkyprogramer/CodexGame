# v0.2.16 · 100K decode 定位（nsys）与 A0/B0 质量筛查（2026-11-20）

接 [V0216-BASELINE-TUNING](V0216-BASELINE-TUNING-20261120.md)。A0 = 生产 v0.2.3 配置；B0 = B1 = v0.2.16 + PT0/#1536 移植 + `--lookup-max-t 0 --conversation-spill-mib 0 --ple-io direct`。全部在 4090、端口 18089 上运行，生产保持停机。

## 结论

1. **100K decode 慢约 5% 不是 v0.2.16 的 GPU 或单窗口耗时退步。**
   - nsys 下每 token 的 GPU kernel 时间、kernel 数和 GPU 空闲时间两版持平。
   - 所有运行中每窗口 GPU-reach wait 都在 8.8～9.6 ms，两版相同。
   - campaign 里 B0 的差距几乎全部来自每个验证窗口接受的 token 更少（tokens/window 低约 6%）；单窗口耗时只差 −0.4%～+1.7%。
2. **该差距依赖请求序列，单独测时方向相反。**
   - 全新服务只跑 100K（3 对交替），B0 比 A0 快约 8%：C 协议中位 133.1 对 122.7 tok/s，P 协议 130.9 对 120.9 tok/s。
   - campaign 中 c100k 排在 d3k→c32k→f10k 之后，11/11 对 B0 慢。
   - 序列依赖的具体机制（前序请求留下的专家缓存或草稿状态）**未定位**。temperature 0 下每次生成的文本都不同，所以不能用"固定文本的可草稿性"来解释。
3. **PCE0（`--prompt-cache-every 0`）在全新服务的 100K 上有明显收益，但在 campaign 序列中没有。** 收益为：C 协议 +11%（148.0 对 133.1），P 协议 +3.5%。来源是 prefill 后第一段 decode 的 CPU 专家条目更少（1.16 对 1.75～2.03 / layer-window）。源码显示 checkpoint 是主机内存里的状态副本，不占 VRAM，机制未证实。此前 screen 中 PCE0 的 c100k 与 B0 无差异，所以**不改 B1**，只记作需要在混合序列中复测的候选。
4. **质量筛查：A0 与 B0 结果完全相同，未见退化；这不是正式非劣证明。**
   - 固定语料两版均为 21/23（4 段），失败的都是 `park-prime-69632/102400` 冷检索，两版错答相同（`1751936` / `6395887`）。
   - 8 轮 Python ledger 链（Docker 判题）4/4 全部 8/8 通过。
   - 正式质量门（约 184 个独立任务、2% 非劣边界）`NOT_EVALUATED`。

## 1. nsys

- **v1 失败（保留）**：`nsys_run.py` 用 `nsys launch` 加中途 `start/stop`。
  - nsys 2023.3.3 在 CUDA 上下文初始化后才开始采集时，守护进程报 `FATAL ... Can't find UUID for CUDA device 0`，`stop` 返回 "not allowed in this state"。
  - 同时旧的 swap 守卫被触发：触发时可用内存 8.7 GiB，换入的是旧换出页。
  - `launch` 拉起的服务不在驱动的进程组里，残留的 18089 进程按 PID 组手工停止，GPU 已回到 1 MiB。
  - 之后所有驱动都改为：按本运行目录的命令行精确匹配自己的进程来收尾；只有可用内存低于 6 GiB 时才计入持续换入。
- **v2 方法**：`nsys2.py` 用 `nsys profile --trace=cuda --cuda-graph-trace=node` 包住整个服务生命周期。
  - 请求顺序：d3k 预热（max 1）→ d3k 解码 512 → c100k 预热（max 1）→ c100k 解码 512，请求之间间隔 4 s。
  - 按墙钟截取首 token 之后的解码区间（`nsys_cut.py`，用 `TARGET_INFO_SESSION_START_TIME` 对齐）。
  - 臂顺序 A0、B0、B0、A0。

| 每 token（两段合计） | 3K A0 | 3K B0 | 100K A0 | 100K B0 |
|---|---|---|---|---|
| 墙钟 µs | 9504 | 9431 | 10677 | 10342 |
| GPU 忙（kernel 并集）µs | 7278 | 7214 | 7892 | 7599 |
| GPU 空闲 µs | 2226 | 2217 | 2784 | 2744 |
| kernel 数 | 960 | 995 | 1091 | 1091 |
| 草稿接受率 | 0.696 | 0.721 | 0.650 | 0.677 |

- 追踪开销约 +35%，只看比例。
- 唯一系统性的 kernel 变化是 dense 投影改走另一条路径：`native_mmvq_il_kernel` 从 700 降到 325 µs/token，`b6_mmvq_rows_kernel` 从 410 升到 736 µs/token，两项合计持平。
- `wait_flag_ge_kernel`（GPU 等 CPU 专家结果）在两版之间来回变化（3K +280、100K −350 µs/token），与运行时主机侧的专家未命中一致，不是固定差。

## 2. 窗口拆解

campaign c100k（A0 11 次，B0 14 次，含 screen；两段分别是 thinking hold 前后的中位数）：

| 段 | 臂 | tokens/window | ms/window | GPU-reach | 主机每层 | CPU 专家条目 | PCIe |
|---|---|---|---|---|---|---|---|
| 1 | A0 | 2.12 | 16.16 | 9.10 | 4.85 | 1.24 | 0.09 |
| 1 | B0 | 2.00 | 16.43 | 9.00 | 5.32 | 1.15 | 0.21 |
| 2 | A0 | 2.48 | 18.15 | 9.29 | 6.53 | 1.94 | 0.19 |
| 2 | B0 | 2.33 | 18.07 | 9.24 | 6.61 | 1.51 | 0.29 |

协议 A/B（`proto.py`，全新服务，臂顺序 A0 B0 PCE0 PCE0 B0 A0 A0 B0 PCE0）。C = 全新 97786 token prefill + 1024 解码；8 s 后 P = 同一请求复用 97781 token + 1024 解码：

| 臂 | C tok/s | C 中位 | P tok/s | P 中位 | C prefill ms |
|---|---|---|---|---|---|
| A0 | 117.2 / 125.8 / 122.7 | 122.7 | 120.2 / 122.3 / 120.9 | 120.9 | 25070～25329 |
| B0 | 133.1 / 129.9 / 134.8 | 133.1 | 129.5 / 133.9 / 130.9 | 130.9 | 21310～21897 |
| PCE0 | 148.0 / 150.1 / 145.9 | 148.0 | 132.1 / 140.4 / 135.5 | 135.5 | 21623～21773 |

- 单窗口耗时 = GPU-reach（固定约 9 ms）+ 主机 CPU 专家时间（条目数 × 单条成本）+ 草稿约 1.4 ms。
- 单条成本在不同运行之间为 2.9～4.0 ms/条目（`CPU ms / entries`），受主机争用影响。后台有 6013 端口的 gunicorn 服务，内存带宽上限约 36 GB/s。
- tokens/window 随生成文本和状态浮动。
- A0 的 P 请求复用 5 个 token 要 1.3～1.8 s，B0 只要 47～163 ms：这是 #1536 / v0.2.16 复用路径的收益，与 decode 无关。

## 3. 质量筛查

`quality.py`，A0:43、B0:43、B0:44、A0:44。每段做两件事：

- **固定语料**：P3 冻结语料 `kvres-20261027/corpus.json` 中 23 条非性能用例，按冻结顺序发出，用 lab 原 `scoring.score` 判分。
- **Python ledger 链**：`chain_bench` 8 轮，reasoning xhigh，模型代码只在本地 `python:3.12-slim` 不可变镜像 `sha256:ec7d6c95…` 中执行，参数为 `--pull=never --network none --read-only --cap-drop ALL`，非 root，限 512 MiB。

| 段 | 固定语料 | 失败项 | ledger 链 | 链耗时 s | 各轮输出 token |
|---|---|---|---|---|---|
| A0 seed43 | 21/23 | park-prime-69632, park-prime-102400 | 8/8 | 649 | 314 … 18254 |
| B0 seed43 | 21/23 | 同上 | 8/8 | 740 | 722 … 26381 |
| B0 seed44 | 21/23 | 同上 | 8/8 | 595 | 519 … 25681 |
| A0 seed44 | 21/23 | 同上 | 8/8 | 672 | 554 … 26076 |

- 工具 6/6、协议 5/5、追加历史 5/5、park-side 2/2，两版全部通过。
- 长检索 6 项中 `restore-*` 与 `sampled-retrieval-*` 两版均通过，冷检索 `park-prime-*` 两版都错，答案相同。
- P3 当时记录的是 0/6，且 restore 只答出数字前半段。本轮 A0 与 P3 的 base 同为 v0.2.3 生产配置，但没有先跑性能用例，冷却和缓存序列不同，所以不与 P3 直接比较。
- 链各轮 finish 全为 `stop`。
- 样本量太小：每臂 46 条固定请求、2 条链，不能做 2% 非劣判定。

## 资源与安全

- 运行规模：nsys v2 4 次启动，协议 9 次，质量 4 次，加上 v1 的 1 次中止。
- 质量段：最高温度 77 °C；可用内存最低 4144 MiB，出现在每段启动后约 100 s 的 100K 检索 prefill，两版相同；单个 2 s 采样的最大换入为 23102 页，出现在模型加载阶段，当时可用内存 8.5 GiB 以上。
- 每个驱动收尾时：保护的 7 个生产文件 hash 不变，无残留进程，18089 未监听，GPU 回到 1 MiB。
- 未修改任何生产文件、systemd、NGINX 或驱动。

## 未覆盖

- 序列依赖的机制：需要在 d3k→c32k→f10k→c100k 序列下逐窗口导出接受数和专家缓存状态，两版对照。
- PCE0 在混合序列中的复测，以及关闭周期 checkpoint 对中途分叉复用的代价。
- 正式质量门。

## 证据

[evidence/v0216-decode-quality-20261120/](../evidence/v0216-decode-quality-20261120/) 包含：

- 驱动：`nsys_run.py`（v1 失败）、`nsys2.py`、`nsys_cut.py`、`proto.py`、`quality.py`
- 运行控制台输出 `*-console.txt`（原 `*.log`，因仓库忽略 `*.log` 而改名）
- `runs/nsys2/CUT.json`：逐 kernel 汇总
- `runs/proto/DECODE_TIMING.txt`：引擎窗口行
- `runs/quality/*/corpus.jsonl`、`chain/chain.json`

`trace.nsys-rep`（4 × 约 55 MB）、完整的链请求/响应和服务日志留在 4090 `/data/strata-data/v0216-baseline-20261120/runs/`。
