# v0.2.17 迁移（B2）与路由尾部跳过开关对照（2026-11-20）

接 [V0216-SEQDEP-PCE0](V0216-SEQDEP-PCE0-20261120.md)。在 4090、端口 18089 上共启动 22 次（seq 18 次 + 质量筛查 4 次），生产保持停机。

## 结论

1. **B2 = v0.2.17 + PT0/#1536 + B1 参数 + `STRATA_ROUTE_TAIL_SKIP=7` 可以替代 B1，没有看到退步。**
   - 序列 c100k 中位：B1 133.6 tok/s，B2 134.0（各 n=4）；d3k、c32k、f10k 的 decode 和 prefill 都在 ±1.5% 内（d3k prefill B2 慢 4%，单项小样本）。
   - 中途分叉复用完全相同：fork60 / fork90 分别复用 48891 / 81485 token。
   - 每个 CPU 专家条目的主机耗时，B2 低 2%～3%（c100k 两段中位 3.027/2.979 对 3.135/3.048 ms），方向与上游 `STRATA_POOL_DEP` 默认开启的 −2.9% 一致。样本少，且我们奇数层的 Q2_0 down 不走这条路径，**只算弱证据**。
   - 全新服务的 c100k 文本：B1、B2 和 v0.2.16 B0 属于同一族（两两公共前缀 ≥1045 字符）。
   - 质量筛查：B2 两段都是固定 corpus 21/23（失败的两个 park-prime 冷取回用例与 v0.2.16 两臂相同）、ledger chain 8/8。
2. **v0.2.17 默认关闭尾部跳过（TS0），在本机 decode 慢 12%～20%，prefill 不变。必须显式设置 `STRATA_ROUTE_TAIL_SKIP=7`，与生产（0.2.3）和 B1 保持一致。**
   - 序列中位（各 n=4）：c100k 117.1 对 134.0（−12.6%），d3k 121.1 对 145.4（−16.7%），c32k 118.0 对 147.7（−20.1%），f10k 121.3 对 143.6（−15.5%）。全新服务 c100k 113.2/115.4 对 129.8/131.2。
   - 原因已直接观察到：每层每窗口落到 CPU 计算的专家条目增加 30%（c100k 第一段 1.98 对 1.52）到 53%（第二段 2.96 对 1.93），而每个条目的耗时不变（约 3.1 ms 对 3.0 ms），GPU-reach 也不变。
   - 质量：TS0 的筛查结果同为 21/23 和 8/8。这个筛查对上游测得的 KL 0.0126 量级的差异不灵敏，不能据此判断关闭尾部跳过对质量有没有好处。
   - TS0 的文本落到另一族（与 A0 全新服务共享 490 字符，与 B 系只共享 38 字符），所以它和 B2 的速度差里也混有文本差异。不过每个条目的成本相同、条目数大增，方向和量级都很明确。
3. **对上一份报告的更正：全新服务的 greedy 文本只在开头一段可复现。**
   - 上一份报告按前 400 字符分组，说全新服务"可复现"。全文比较后，同版本两次全新启动的公共前缀只有 1045～1233 字符（v0.2.16 B0-F 三次之间、本轮 B1-F 两次之间都是如此），之后仍会分叉。
   - 所以"重启服务就得到固定文本"不成立，固定文本的速度对照仍需 teacher forcing。版本或开关的对照应以每窗口耗时、每条目 CPU 成本、CPU 条目数和 prefill 耗时为主，tok/s 只作参考。上一份报告关于顺序依赖来自文本轨迹的结论不受影响。

## 1. 构建与离线验证

| 项 | 结果 |
|---|---|
| 源码 | `git archive v0.2.17`（annotated tag 对象 `028e6826b`，commit `12d491da4`）导出 `engine` 和 `terminal` 到 `/data/strata-data/v0217-baseline-20261120/src` |
| 补丁 | [v0217-pt0-reply-reuse.patch](../patches/v0217-pt0-reply-reuse.patch)：由 v0.2.16 版补丁在 v0.2.17 上带行偏移应用后重新生成，6 个文件、新增 242 行，内容不变；4090 构建树中这 6 个文件的 sha256 与之逐一相同 |
| 构建 | 与 B1 同一 CMake 选项（Release、CUDA 12.3、sm_89、tests OFF），只有源码路径不同；`build/strata` sha256 `df2d006b…32a5`，`--version` 为 0.1.63 |
| CPU 单测 | `serve.test_prompt_encoder` + `test_frontend` + `test_server`（4090 上 anaconda Python 3.11.7）：补丁版 492 OK，未打补丁的 v0.2.17 为 478 OK |
| 红灯检查 | 新增的 14 个测试放到未打补丁的 v0.2.17 上：涉及新行为的 11 个 FAIL/ERROR；另外 3 个是"不影响默认行为"的不变量测试（env 未设、取值非法、关闭思考），在未打补丁的代码上也通过，符合预期 |
| 启动参数 | B1 的 18 个启动参数在 v0.2.17 中仍然存在；production env 里的 11 个开关在 v0.2.17 源码中仍被读取；运行时每段校验启动参数与 engine 实际接收的一致 |

## 2. 方法

`mig17.py` 复用 v0.2.16 的 `campaign`、`seqtrace` 和 `quality` 驱动（代码不变），每个臂只切换构建、terminal 和 state 目录。

| 臂 | 构成 |
|---|---|
| B1 | v0.2.16 + 移植补丁，尾部跳过沿用 v0.2.16 默认（rank 7） |
| B2 | v0.2.17 + 移植补丁 + `STRATA_ROUTE_TAIL_SKIP=7` |
| TS0 | v0.2.17 + 移植补丁 + `STRATA_ROUTE_TAIL_SKIP=0`（等同 v0.2.17 默认） |

顺序：

```
seq:     B1:S B2:S TS0:S TS0:S B2:S B1:S B2:S B1:S TS0:S TS0:S B1:S B2:S B1:F B2:F TS0:F TS0:F B2:F B1:F
quality: B2:7 TS0:7 TS0:11 B2:11
```

- S 段：d3k → c32k → f10k → c100k → fork60 → fork90；F 段只跑 c100k。逐窗口开 `STRATA_SPEC_TRACE`。
- 每段日志都核对了尾部跳过的实际状态：B1/B2 打印 "is ON" 并有跳过计数（S 段约 8.5 万～9.4 万条目，F 段约 2.2 万～3.0 万）；TS0 无 ON 行、计数为 0。
- 质量筛查与上一轮相同：固定 corpus（23 个非性能用例）+ 8 轮 Python ledger chain，只在隔离、无网络的 Docker 中评分。

## 3. 结果

### 3.1 各请求（S 段中位，n=4）

| 指标 | B1 | B2 | TS0 |
|---|---|---|---|
| d3k decode tok/s | 144.8 | 145.4 | 121.1 |
| c32k decode tok/s | 145.9 | 147.7 | 118.0 |
| f10k decode tok/s | 143.2 | 143.6 | 121.3 |
| c100k decode tok/s | 133.6 | 134.0 | 117.1 |
| d3k / c32k / f10k / c100k prefill ms | 3007 / 7288 / 3791 / 20957 | 3138 / 7292 / 3797 / 20865 | 3030 / 7272 / 3798 / 20911 |
| fork60 / fork90 读入 ms | 4280 / 4288 | 4287 / 4381 | 4278 / 4313 |
| 全新服务 c100k tok/s（F，n=2） | 135.7 / 139.5 | 129.8 / 131.2 | 113.2 / 115.4 |

### 3.2 c100k 解码窗口（S 段中位；两段 = thinking hold 前后）

| 指标 | B1 | B2 | TS0 |
|---|---|---|---|
| 段 1 ms/window | 15.58 | 16.45 | 17.22 |
| 段 1 tokens/window | 2.03 | 2.17 | 1.97 |
| 段 1 GPU-reach ms | 9.05 | 8.95 | 8.42 |
| 段 1 主机 CPU 专家 ms | 3.92 | 4.69 | 6.28 |
| 段 1 CPU 条目 / 层·窗口 | 1.24 | 1.52 | 1.98 |
| 段 1 CPU ms / 条目 | 3.135 | 3.027 | 3.196 |
| 段 2 ms/window | 18.16 | 18.04 | 21.01 |
| 段 2 CPU 条目 / 层·窗口 | 1.87 | 1.93 | 2.96 |
| 段 2 CPU ms / 条目 | 3.048 | 2.979 | 3.100 |

- "CPU ms / 条目"= 每窗口 CPU 专家时间 ÷ 每层每窗口 CPU 条目数，只用于臂间相对比较。
- B2 有一次段 1 为 4.12（05-B2-S），中位不受影响。逐次数据见 `ANALYSIS.json`。
- B2 段 1 的条目数和 ms/window 高于 B1，但 tokens/window 也更高，c100k 整体 tok/s 相同。这一项随文本轨迹浮动（B1 四次为 0.97～2.00）。

### 3.3 文本轨迹（c100k 全文最长公共前缀，字符）

| 对比 | 公共前缀 |
|---|---|
| B1-F × 2 之间 | 1045 |
| B2-F × 2 之间 | 1179 |
| B1-F / B2-F 与 v0.2.16 B0-F（3 次） | 1045～1886 |
| TS0-F × 2 之间 | 725 |
| TS0-F 与 v0.2.16 A0-F | 490 |
| TS0-F 与 B 系 | 38 |

### 3.4 质量筛查

| 段 | 臂 | seed | 固定 corpus | 失败用例 | ledger chain | chain 耗时 s |
|---|---|---|---|---|---|---|
| 1 | B2 | 7 | 21/23 | park-prime-69632、park-prime-102400 | 8/8 | 782.8 |
| 2 | TS0 | 7 | 21/23 | park-prime-69632、park-prime-102400 | 8/8 | 725.8 |
| 3 | TS0 | 11 | 21/23 | park-prime-69632、park-prime-102400 | 8/8 | 679.6 |
| 4 | B2 | 11 | 21/23 | park-prime-69632、park-prime-102400 | 8/8 | 902.7 |

- 四段结果完全相同，失败用例也与 v0.2.16 的 A0/B0 筛查相同（都是冷取回）。
- chain 是采样生成（temperature 1.0），耗时随生成长度变化，不作速度比较。
- 正式非劣门 `NOT_EVALUATED`。

## 4. 对生产切换的影响（本报告时未执行；后续已切换，见 [V0217-PRODUCTION-SWITCH](V0217-PRODUCTION-SWITCH-20261120.md)）

- 若切换，目标应为 B2，而不是 v0.2.16。
- 与当前生产相比，需要变更的是：新安装树（v0.2.17 + 补丁 + 自编 CUDA 12.3 引擎）、`--lookup-max-t 0 --conversation-spill-mib 0 --ple-io direct`、env 加 `STRATA_ROUTE_TAIL_SKIP=7`。服务层的两个 export 保持不变。
- systemd unit 直接执行 `/home/hhtele/strata-0.2.3/run-iq3_xxs.sh`，切换必须修改 unit 或该脚本，两者都在保护范围内。回滚路径是恢复原 ExecStart 或原脚本。
- 正式质量门（约 184 个独立配对任务、2% 非劣边界）**无法运行**：仓库只有统计工具和合成示例，没有 184 题的 gold 题集。这次的筛查只能排除明显退步。

## 资源与安全

- 22 段全部完成，无守卫触发；`RESULT.json` 的 error 都为 null。
- 最高温度 75 °C；可用内存最低 4121 MiB，出现在质量筛查 02-TS0 启动约 100 s 时的模型加载阶段（守卫线 4096 MiB）；单个 2 s 采样的最大换入 37198 页，同样在加载阶段。
- 每段收尾时无残留进程，18089 未监听，GPU 回到 1 MiB；7 个保护文件 hash 不变；生产 unit 保持 inactive。

## 未覆盖

- 尾部跳过对质量的细微影响（上游在 RTX 5090 上测得 KL 0.0126）：本筛查的灵敏度不够，需要 logit 级对照或大样本配对任务。
- POOL_DEP 的单独收益：没有拆出单独的臂，只有 B1→B2 的整体比较。
- 固定文本的速度对照（teacher forcing）。

## 证据

[evidence/v0217-migration-20261120/](../evidence/v0217-migration-20261120/) 包含：

- `build.sh`、`mig17.py`、`ana17.py`、`run_all.sh`
- `seq-console.txt`、`quality-console.txt`、`cpu-tests-console.txt`
- `runs/mig17/seq/{PLAN,RESULT,ANALYSIS}.json`、`DECODE_TIMING.txt`、每段的 `ROW.json` 和 `START.json`
- `runs/mig17/quality/{PLAN,RESULT}.json`，以及每段的 `ROW.json`、`START.json`、`corpus.jsonl` 和 `chain/chain.json`

原始 `spec.trace`、SSE 和日志留在 4090 `/data/strata-data/v0217-baseline-20261120/runs/mig17/`。
