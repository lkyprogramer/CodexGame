# 统一测试题集与测量协议

## 固定集合

`fixtures/questions.json`有21个固定短请求：8个精确回答/JSON、5个工具调用、5个协议边界、3个定长输出性能题。`fixtures/java/tasks.json`另有8个Java任务及可信断言。full生成82个请求：21短题、8 Java单题、5长检索、5长Prefill/Decode、19 Root churn、12历史改写、12回复Token边界。

全部测试内容为合成数据，不读取用户源代码。每个请求有哈希，每个corpus有哈希；base/off/on必须一致。Java参考实现与oracle不发给模型，不能让AI修改oracle迎合候选输出。

## 上下文

- `HARD_CONTEXT=131072`，不可放大。
- 长输入目标4096/32768/65536/98304/122880，用实际Strata tokenizer+ChatTemplate归一化计数。
- 无特殊标记的输入也计算完整模板；含标签时使用与服务端相同的literal marking/plain spans路径。
- 启动每个arm后发普通文本和特殊标签两次短探针，对比本地count与server `usage.prompt_tokens`，不一致则禁止长测。
- 每次提交前 `prompt + max_tokens + 4096 <= 131072`；服务端关闭自动缩减max_tokens。返回usage再次审计；计数变化超过32或实际预算越界停止。
- PR1536可能保留合法的非规范BPE分段；小幅count变化需记录，不强行要求等于重新tokenize。安全余量不是允许未知渲染逻辑的借口。

## 分组与含义

| group | 作用 | 主要用于 |
|---|---|---|
| quality | 算术、JSON、Long精度、Unicode | 所有PR |
| tool | 名称白名单、参数类型/值、中文与长ID | 所有服务端/缓存PR |
| protocol | 字面think/tool标签、无工具请求 | 所有PR |
| decode | 固定512输出 | 3453/2964/3322 |
| cold-prefill | 新前缀4K～120K，固定512输出 | 3307/3281 |
| long-retrieval | 多深度唯一值，严格JSON | 所有长上下文PR |
| root-churn | 约12.3K根（29上Pi实测，`root_target_tokens=12288`）+多轮淘汰+新会话；24K根仅作压力对照、不作采用依据 | 3517 |
| cache-edit | 原文重放、中段改写、尾部改写 | 3584/3711 |
| reply-reuse | Unicode/数字/代码BPE边界 | 1536 |
| java | 单次生成后隔离编译与断言 | 所有候选 |

长性能题与检索题不是同一指标。检索通过不证明编码能力；输出全在thinking内的截断不算质量通过。performance允许length结尾，但只有确实生成固定token数才比较速度；不以模型少写了内容作为收益。

## P→A0 迁移评估（MIG，START_HERE P0-T2b）

**目的：** 判定生产能否从 P（0.1.43.1）升到 A0（v0.2.3）。它决定后面所有结论最终落在哪个版本上，所以排在 DIAG（P0-T5）和配置对照（P0-T6）之前。MIG 的差异属于版本迁移，不计入任何 PR 或 CFG 的收益。需要用户批准的 GPU 维护窗口。

**两个 arm：** P = 部署树里现有的 0.1.43.1 二进制（路径以 doctor 记录为准），只读执行，不重新编译、不复制改名；A0 = 本包用同一 cmake 参数构建的冻结 main。两边使用 runner 归一化后的同一份生产配置：同一模型/pack、`--spec 4 --spec-min-p 0.5`、KV int8、expert cache、`--vram-reserve-mib 974`、生产 env（`STRATA_ADAPT_OVERLAP=1`、`STRATA_PREFILL_CPU_SHARE_MAX=3072`）和 conversation cache 形态。

**先做配置兼容表：** 逐条核对 P 的参数和 env 在 A0 上是否被接受、改名、删除或换了默认值（例如 0.1.43.1 起 adaptive overlap 默认关闭，A0 仍需显式开启）。不兼容项做最小改写并记录理由；以行为等效为准，不为凑结果调参。

**runner 现状：** 只支持 base（A0 构建）与候选 worktree，**没有 P arm**。执行 AI 二选一：
1. 给 runner 加只读 P arm：exe 指向部署树二进制，日志、会话缓存、学习 profile 等写入全部改到 run 目录；启动前后对部署树做文件清单加 mtime/哈希校验，发现任何写入即 BLOCKED。补对应单测。
2. 用同一 corpus 手工交替运行，并保存请求哈希与每轮启动回执。

两种方式都不得往 `/home/hhtele/strata-0.1.43.1` 写任何东西，也不得占用 18343。

**负载：** decode 组（4K/32K/64K/120K，固定 512 输出；greedy 加 Pi 采样参数抽查，两组分开统计）；cold-prefill 组；Pi 形态的多轮会话切换，含 park/restore（与 #2253 的切换场景共用）；quality/tool/protocol；Java。

**轮次与指标：** 至少 5 轮，AB/BA 交替，每轮新进程。记录 ms/window、token/window、接受率、TTFT、prefill tok/s、park/restore 次数、峰值显存、加载后 MemAvailable 和 `[heap]` Rss。

**结论分支：**

| 结论 | 条件 | 后续 |
|---|---|---|
| MIG-PASS | A0 在 decode 与 prefill 上都不比 P 差超过 A/A 噪声（约 5%），质量/工具硬门全部通过 | 之后的所有工作都在 A0 上做；最终生产候选 = A0 + 通过的 CFG + 采用的 PR。P 上不重复测 |
| MIG-REGRESS | A0 某项比 P 差超过噪声 | 先定位：查默认值变化和配置改写，再用 DIAG 构建对比窗口构成。能用配置消除的，记录后重测。仍不能消除时，生产留在 P；PR 与 NP 改造继续在 A0 上做，以消除回归后再升级为目标。此时只有 CFG-MMAP 与 CFG-IL0 允许在 P 上作为“留在 0.1.43.1 期间的生产候选”另测（P 替换 A0，其余方法同下表），每次重启都要用户单独批准 |
| MIG-BLOCKED | A0 用 29 的 CUDA 12.3 / gcc 12.2 编不过，或配置无法等效 | 报告原因，不自行升级 toolkit，不改生产 |

**交付：** `MIGRATION.md`（参数兼容表、配对数据、分支结论）和原始日志。

## 配置与诊断对照（不属于任何 PR）

| 名称 | 内容 | 比较方式 | 采用规则 |
|---|---|---|---|
| CFG-EXACT | A0 + main `nv_defaults.cpp` 中 sm_86 的 exact 开关：`STRATA_CPU_IQ_ALL_EXACT1=1`、`STRATA_SIDE_MIXER=2`、`STRATA_ATTN_DAILY=1`、`STRATA_GR_UP75=1`、`STRATA_GU_SWIGLU=1`、`STRATA_QSA_ROWS=1`、`STRATA_B6_MMVQ_ROWS=1`。**不含** `STRATA_ADAPT_NOWAIT`/`STRATA_ADAPT_LAG`（与生产使用的 adaptive overlap 互斥） | 两份 local 配置（第二份用 `extra_frozen_env` 注入）各跑 `noise`，再跑 decode/quality/tool 组 | 先在 A0 上确认首 token logits 转储（`STRATA_DUMP_FIRST_LOGITS`）跨重启稳定；稳定则要求 CFG-EXACT 与 A0 一致，不稳定则以质量/工具组全部通过为门。decode 收益超过 A/A 噪声（约 5%）才采用，并成为后续所有 arm 的公共基线 |
| CFG-IL0 | A0 + `STRATA_MMVQ_IL=0`（关掉 2～4 token dense 投影的交错 q8_1 路径，回到 `native_mmvq` 多列 kernel；输出逐位一致）。依据 Issue [#1842](https://github.com/Niko1221/Strata/issues/1842)：4090 + Qwen3.8-Flash-Next IQ3_S + `--spec 4`，0.1.41 的 128K decode 比 0.1.40.3 慢约 18%，IL=0 全部找回；8K 时 IL 开着反而更快；A30 上无差别。v0.2.3 的 `native_mmvq.cu` 仍写明 sm_89 没有实测表、套用 sm_86/sm_120 共享表 | 两份 local 配置各跑 `noise`，再跑 decode 组；上下文分 4K/32K/64K/120K 报告，短（≤32K）和长（≥64K）分开统计，不合并成一个均值；追加 Pi 采样参数抽查 | 长上下文收益超过 A/A 噪声且短上下文不退步超过噪声，才采用并成为公共基线；长快短慢的混合结果不采用，交给 #3453 用本机参数表解决。CFG-IL0 与 CFG-EXACT 都改动 verify 窗口的 MMVQ 路径（后者含 `STRATA_B6_MMVQ_ROWS`），两者都通过时要再测组合，组合不劣于单项才一起进入基线 |
| CFG-MMAP | A0 + `MALLOC_MMAP_THRESHOLD_=8388608` | 见 `prs/11_PR2253.md`；只比较内存指标与 park 耗时 | 只作为 #2253 的对照和对生产的零代码候选，不进入 PR 基线 |
| DIAG | 冻结 main + #1864 + #3631（只记录） | 单独构建，见 START_HERE P0-T5 | 不进入统计，只给 #3453/B6 提供窗口构成证据 |

29 的真实请求是**采样**的（Pi 对 Qwen3.8-next 发 `temperature 1.0 / top_p 0.95 / top_k 20`，关闭 thinking 时为 `0.7 / 0.8 / 20`），本包题集为 temperature 0。MTP 接受率在两种模式下不同，凡以 decode tok/s 为主指标的项（#3453、CFG-EXACT、CFG-IL0、#3307/#3281 的 decode 回归）都要追加一组使用 Pi 采样参数的抽查，结果单列，不与 greedy 配对统计混合。

## Java题与工具循环

8题：BigDecimal银行家舍入、半开区间合并、分页溢出、TTL减法溢出、Locale.ROOT稳定去重、Long转JSON字符串、lower_bound、并发幂等。

`scenario java-agent`最多8轮，只允许write_solution/run_tests，最多3次隔离编译。真实运行固定assertion，错误反馈给模型，记录完整任务耗时、尝试次数、工具与编译结果。它仍是受控mini-agent，不能冒充真实Pi的大型仓库评测。

Docker以无网络、只读root、只读输入、临时编译目录、非root用户、限制内存/CPU/PID、移除capability运行。失败/超时都是失败；没装Docker/JDK镜像标记NOT_RUN，不宿主执行生成代码。

## PR专项测试必须补齐

通用HTTP题集不能证明C++指针、缓存状态或图捕获正确。每个PR文档有必须实现的机制测试：GPU读回、固定布局对照、失败注入、取消、回收等。下游AI要将它们加入源码测试，并把可重跑的命令写入READY。

## 缓存与冷暖

这里的cold表示**新引擎/新逻辑前缀**，不宣称OS Page Cache冷。禁止全机drop_caches。若要测SSD冷读，用独立测试文件/受限环境并单独标记，不和默认热文件缓存结果合并。

checkpoint重用指标至少记录reused/read tokens、capture/restore/park耗时、Host bytes、RSS、MemAvailable。重复请求tps极高可能只是cache命中，不是Prefill Kernel更快。

## 必须保留的协议测试

自然停止、max_tokens、reasoning budget、取消、工具名未声明、tools空、JSON参数分片、字面`</think>`、跨chunk代码围栏、同一会话修改历史。服务端正常HTTP200不等于任务完成。空visible answer且无tool_calls单独判异常。
