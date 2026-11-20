# v0.2.16 基线调优（4090，2026-11-20）

> 后续（2026-11-20）：100K decode 差距的 nsys 定位与 A0/B0 质量筛查见 [V0216-DECODE100K-NSYS-QUALITY](V0216-DECODE100K-NSYS-QUALITY-20261120.md)：不是 GPU 或单窗口退步，属于随请求序列变化的 tokens/window 差；质量筛查两版相同。

**结论：baseline B1 = B0，即 v0.2.16 + PT0/REUSE 移植补丁 + 迁移后的原生产参数与环境变量，另固定 `--lookup-max-t 0 --conversation-spill-mib 0 --ple-io direct`。本轮测的 9 个单因素变体，没有一个能在所有主指标上同时过 `4%` 门并保持其余指标非劣，因此 B1 不叠加任何调优项。**

**迁移结论：v0.2.16 的 prefill 全面快于 0.2.3 生产（A0）。decode 在 ≤42K 上下文持平到略快，在约 98K 上下文慢约 5%（11/11 对同向）。100K decode 这一项没有通过 4% 非劣门。** 原因已定位到两部分叠加：每窗口耗时略高，草稿接受率略低。还不能归结到单个开关，未修复。

全部实验在 4090 的 18089 端口执行，共 56 次全新启动（其中 55 次完成，1 次被资源守卫中止）。全程生产两个 unit 保持停止，生产树 7 个受保护文件的 hash 未变；结束时 GPU 1 MiB，18089 已释放。

## 1. 方法

| 项 | 内容 |
|---|---|
| 引擎 | v0.2.16（`64524fb9f`，engine 0.1.62）+ [补丁](../patches/v0216-pt0-reply-reuse.patch)。cmake 4.4.3、CUDA 12.3、sm_89、Ninja、`STRATA_BUILD_TESTS=OFF`，构建 365 s。二进制 sha256 `0ff27e2e…04fe`，静态链接 |
| 目录 | `/data/strata-data/v0216-baseline-20261120`（源码、构建、全部 run 原始数据，420 MB） |
| Python | v0.2.16 serve 用 `dsv41-0210-lab/terminal/0.1.56/python`（3.12，依赖版本与 requirements 一致，Pillow 除外：12.3.0）；A0 用生产 venv 只读执行 |
| harness | 由 11-04 `pt0-version-compare` 改写（[campaign.py](../evidence/v0216-baseline-20261120/campaign.py)）：每个 stage 都是全新启动；GPU ≤50°C 才开始；资源门（生产 unit 停止、无外来 GPU 进程、可用内存 ≥4 GiB、磁盘 ≥30 GiB）；每次启动核对引擎实际收到的参数；跑完前后核对生产受保护文件的 hash |
| A0 | 生产 0.2.3 的 config、engine、serve 原样只读使用，只把 `--expert-profile-save` 改到 run 目录 |
| B0 | 生产 args 与 11 个 env 原样，加 `--lookup-max-t 0 --conversation-spill-mib 0 --ple-io direct`；serve 进程 `STRATA_REPLY_REUSE=1`、`STRATA_PRESERVE_THINKING=0`；config 写死 `drafting: mtp`、`draft_costs: false` |

负载是 4 个固定请求（[fixtures.py](../evidence/v0216-baseline-20261120/fixtures.py)，fixtures.json sha256 `1d877166…2becf`）。内容是真实代码文件，取自 v0.2.16 自身源码，各请求使用不相交的文件集。token 数用 pack tokenizer 和模板精确计数，与服务端 usage 一致。全部 greedy（temperature 0），全部按 `length` 结束：

| leg | prompt | 输出 | 测什么 |
|---|---|---|---|
| d3k | 2,592 | 1,536 | 短上下文 decode、3K 读入 |
| c32k | 31,477（冷） | 256 | 32K 冷读 |
| f10k | 42,605（复用 31,472，读入 11,133） | 512 | PT0 形态追问读入、42K decode。assistant 回答是固定文本，各臂 prompt 逐字相同 |
| c100k | 97,786（冷） | 1,024 | 100K 冷读、98K decode |

prefill 用引擎时钟的 `prompt_ms`，decode 用 `predicted_per_second`。两版的 decode leg 都会在思考预算处切成两段（hold 后续接），处理方式相同。

**噪声：** 与 B0 配置相同的样本有 AM24K（见第 4 节）和 NOAM。单次 decode 的 A/A 偏差可达 ±6%～±10%；prefill 的 A/A 偏差在 ±2% 以内。判定依据是同轮配对的比值和方向一致性，不看单次结果。

**过程中修正了 harness 本身：** 11-04 的守卫把"每 2 秒换入加换出 ≥256 页、连续 3 次"判为抖动。第一次冒烟在 arena 加载期间被它中止：其他服务的空闲页被一次性换出，峰值 320 MB/s；这台机器的 swap 只有 976 MB，引擎的 arena 是 pinned 内存，本身不会被换出。之后改为只在持续换入时中止（每 2 秒 ≥1,024 页、连续 5 次）。56 次启动中，单次换入最多 11 MB，换出最多 597 MB，可用内存最低 5,382 MiB，GPU 最高 77°C。

## 2. 启动事实

| | A0（0.2.3 / engine 0.1.48） | B0（v0.2.16 / engine 0.1.62） |
|---|---|---|
| 专家缓存 | 10,290 槽 | 10,126 槽 / 16.42 GiB |
| prompt 路径借用 | 4,390 槽 / 7.13 GiB | 3,875 槽 / 6.30 GiB |
| 加载完空闲显存 | 512 MiB | 768 MiB（graph 捕获后最低 696） |
| prompt chunk | 16,384 | 16,384 |
| CPU share | 由 env 放到 4096 | 默认就是 ≤4096 开启 |
| PLE | direct | direct（显式），探测 94,898 rows/s；自动放进内存的条件不满足 |
| layer-major / 小显存路径 | 无 | 无（日志中没有任何相关行） |
| `pcie_frac` | 起步 0.34 → 0.30 | 新的自适应规则：起步 0.10 → 0.45 → 0.35～0.45 |
| 就绪 | — | 约 39 s |

## 3. 迁移：A0 → B0（11 对，同轮配对）

| 指标 | A0 中位 | B0 中位 | B0/A0 中位 | 范围 | B0 更好 |
|---|---|---|---|---|---|
| d3k decode tok/s | 136.0 | 139.4 | 1.020 | 0.953～1.042 | 9/11 |
| f10k decode tok/s（42K） | 130.6 | 134.7 | 1.031 | 0.880～1.088 | 8/11 |
| **c100k decode tok/s（98K）** | **134.7** | **124.8** | **0.946** | 0.903～0.990 | **0/11** |
| d3k 读入 ms | 2,414 | 2,251 | 0.922 | 0.618～0.997 | 11/11 |
| c32k 冷读 ms | 9,049 | 7,521 | 0.837 | 0.781～0.864 | 11/11 |
| f10k 追问读入 ms | 4,700 | 3,893 | 0.818 | 0.798～0.843 | 11/11 |
| c100k 冷读 ms | 25,011 | 20,990 | 0.839 | 0.821～0.857 | 11/11 |

**100K decode 退步的定位（mig 8 个 stage 的引擎分解计时）：** 两版每窗口的 GPU 等待相同，约 9.2 ms，专家缓存命中率相近（c100k 94.9% 对 94.3%）。差异由两部分叠加：每 token 耗时 7.76 对 7.30 ms，其中每窗口耗时高 1.5%～3%（mig 第一对的两段）；草稿接受率 0.684 对 0.699。

已排除 `pcie_frac` 自适应：固定 `--pcie-frac 0.30`（A0 的稳态值）后，4 对 PF30/A0 的 c100k decode 是 0.943，和 B0 没有差别。进一步定位需要用 nsys 做长上下文 decode 的 kernel 级对比，本轮未做。

**对墙钟的影响是推断：** 按 10-26 汇总的单会话形态（每轮生成 10～28K token，96%～98% 的时间在 decode）估算：会话在 50K 以内时，v0.2.16 的每轮墙钟持平到略快；会话接近 100K 时，每轮约慢 4%～5%，追问读入省下的 0.8 s 抵消不了。

## 4. 单因素筛查

screen（3 轮）、chunk（3 轮）、pf（4 轮），比值都是变体对同轮 B0。decode 比值 >1 表示更快，prefill 耗时比值 <1 表示更快。

| arm | 变化 | 关键结果 | 判定 |
|---|---|---|---|
| R700 | reserve 974→700（+170 槽，空闲 492 MiB） | decode 0.92～1.04（无一致方向），prefill 约 −1% | NO_BENEFIT，保持 974 |
| R1536 | reserve 974→1536（−332 槽） | f10k decode 0.888/0.891/0.835，c100k 0.990/0.920/0.946，prefill +0～3% | REJECT |
| LMT12 | 去掉 `--lookup-max-t 0`（新默认 12） | prefill 不变，f10k decode 0.896/0.990/0.943 | NO_BENEFIT，保持 0 |
| CS2048 | `PREFILL_CPU_SHARE_MAX` 4096→2048 | d3k 读入 1.291/1.301/1.318 | REJECT |
| PCE0 | `--prompt-cache-every 0` | c32k 冷读 0.985/0.975/0.969，c100k 0.989/0.995/0.988，decode 在噪声内 | NO_BENEFIT（未达 4%）；保留默认的周期 checkpoint，它对取消后续读有用 |
| AM24K | `PREFILL_AUTO_MAX=24576` | **设计错误**：该变量只认 8192/16384/32768，24576 被归到 16384（`generate.cpp:3887`），实际等于 B0，作为 A/A 样本使用 | 无效 |
| LMX | reserve 1536 + `PF_FUSED=0` + `PREFILL_LAYER_MAJOR=1` | layer-major 一次都没有执行（`no VRAM for a super-chunk (1138 MiB free)`）；prompt 被切到普通 int8 kernel，c100k 冷读 1.212，c100k decode 0.858 | REJECT |
| NOAM | 去掉 `PREFILL_AUTO_MAX`（走 v0.2.16 的 NVIDIA 默认上限 32768） | 被 #2090 内存守卫降回 16384（可用 11,041 MiB < 估计借出量 9,464 + 6,144），与 B0 等价 | 无效（这台机器上 = B0） |
| AM32K | `PREFILL_AUTO_MAX=32768`（显式，会绕过 #2090 守卫） | chunk 32768，借用 6,587 槽 / 10.65 GiB；**c100k 冷读 0.859/0.861/0.874**；c32k 冷读 1.027/1.076/1.039；追问读入与 decode 在噪声内，命中率不变；最低可用内存比 NOAM 只低 259 MiB | 有取舍，未纳入 B1，见下 |
| PF30 | `--pcie-frac 0.30` 固定 | 对 B0 全部在噪声内；c100k decode 未改善 | NO_BENEFIT |

**AM32K 的取舍：** 100K 冷读快 14%（21.2 → 18.3 s），32K 冷读慢约 4%。单会话用法下，冷读只在重启、compaction 或缓存淘汰后出现，对墙钟的贡献在 1% 量级。#2090 守卫防的是另一种部署：专家经文件缓存或 mmap 读取、借出槽位时产生大量缺页（30 GB 机器的案例）。这里的 arena 是 pinned 常驻，实测没有额外的内存压力（推断，有本轮的内存曲线支撑）。如果你更在意长上下文冷读，可以单独采纳；它需要显式设置才会生效。

**迁移相关的语义变化：** 在 v0.2.16 上，`STRATA_PREFILL_AUTO_MAX=16384` 不再是"放开到 16384"，而是让 `--prefill auto` 不走 NVIDIA 默认上限 32768。这台机器上 #2090 守卫本来也会停在 16384，结果相同，所以 B1 保留这个变量，以保证换到可用内存更多的环境时行为一致。

## 5. 对外部建议（Engram / Reserve / layer-major）的实测结论

- **PLE 自动放进内存**：v0.2.16 的准入条件是表 26.8 GiB + arena 40 GiB + 8 GiB，这台机器可用内存只有约 53 GiB，不会触发。B1 显式写 `--ple-io direct`，不依赖这个判断。
- **加大 Reserve 让 prefill 变快**：不成立。R1536 让 decode 一致变慢 1%～16%，prefill 不变或略慢。
- **Reserve 触发 layer-major**：不成立。4090 的 chunk 16384 ≥ 8192，小显存路径不会开启；fused 布局拒绝 layer-major；super-chunk 至少要 32,768 token。reserve 1536 时空闲 1,138 MiB 仍然放不下。强开的代价见 LMX。
- **#6128（Windows 4090 decode 骤降）**：针对 Windows 显存回退到系统内存的问题，这台 Linux 机器不适用。默认的 974 MiB 预留留有 696～768 MiB 余量。

## 6. B1 配置

```
args: 生产 strata-iq3_xxs.json 的 args 原样（--expert-profile-save 改到新目录）
      + --lookup-max-t 0 --conversation-spill-mib 0 --ple-io direct
env : 生产 11 项原样（EXACT6、ADAPT_OVERLAP=1、CPU_SHARE_MAX=4096、AUTO_MAX=16384、DECODE/PREFILL_TIMING、SIDE_MIXER=2）
serve 进程: STRATA_REPLY_REUSE=1, STRATA_PRESERVE_THINKING=0
config: drafting=mtp, draft_costs=false
```

B1 的参考数字（与 B0 配置相同的 16 个样本的中位数 [IQR]）：

| 指标 | 数值 |
|---|---|
| d3k decode | 137.1 [135.8～141.1] tok/s |
| f10k decode | 132.7 [131.3～138.9] tok/s |
| c100k decode | 127.8 [124.8～132.4] tok/s |
| d3k 读入 | 2,247 ms |
| c32k 冷读 | 7,507 ms |
| f10k 追问读入 | 3,899 ms |
| c100k 冷读 | 21,064 ms |

## 7. 未覆盖与风险

- **质量：未运行。** 没有跑 Java 判题、工具调用、长检索质量门。只抽查了 A0、B0、AM32K 的 100K 输出，三者连贯，并引用了 prompt 中真实存在的文件。迁移是否质量非劣仍待验证。
- **短时形态：** 每个 stage 只有 4 个请求。生产会连续跑数小时，`pcie_frac` 自适应收敛、learned profile 积累和热态都没有测到。
- **背景负载：** 4090 上的 gunicorn 服务（6013 端口，4 个 worker）全程占用约 1 个核，属于同轮配对共同承受的噪声，没有停用。
- **greedy 跨版本不逐字一致：** decode 速率里包含了内容差异带来的草稿接受差异。100K 的退步 11/11 同向，不是噪声。
- **100K decode 退步：** 根因未定位，需要 nsys 对比。决定是否把生产切到 v0.2.16 之前，应先补这一项和质量门。

## 8. 本轮顺带更正

- [配置迁移表](V0216-CONFIG-MIGRATION-20261120.md)里"11-04 PT0 报告关闭后缀草稿不准确"的说法是错的：该 campaign 两臂都显式传了 `--suffix-draft 0`。已改为说明生产与该实验的差异。
- 补丁文件原先缺少末尾换行，`git apply` 会报 corrupt patch，已重新生成，sha256 改为 `4d79840a…61d0`。

## 9. 证据

- 本仓库：[evidence/v0216-baseline-20261120/](../evidence/v0216-baseline-20261120/)。包含 harness、fixture 生成器、分析脚本、arm 定义、各 run 的 ANALYSIS.json 和冒烟时 B0 的启动事实。
- 4090：`/data/strata-data/v0216-baseline-20261120/runs/{smoke,screen,chunk,mig,pf}/<NN-arm>/`，每个 stage 有 engine.log、server.log、SSE、ROW.json、resources.jsonl 和 profile.json；`smoke-swapguard/` 是被旧守卫中止的那一次。
