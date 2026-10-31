> 历史实验规范与记录。后续探索的当前阶段见 [NEXT_ACTIONS](../plans/NEXT_ACTIONS.md)；本文原口径用于解释原报告，不覆盖 frontier 新阶段合同。

# 单4090 / 128K的综合排序

这不是原先泛泛的“可借鉴PR榜”。排序以用户**现有Strata部署**为对象，未更换GPU、模型或RAM。2026-10-23 按 29 号机的生产配置和 10-12～10-16 真实流量重排（事实见 [环境](02_ENVIRONMENT.md)）；doctor和实际机制探针仍优先于评分。

评分是工程判断，不是预测加速率：收益潜力30%、当前适用性25%、改造可控性20%、正确性风险可控性15%、证据质量10%；各维1～5，越高越有利。分数保留一位只为计算可复核，不能当作客观统计精度。

## 2026-10-26 重排：单会话用法 + Phase 0/1 实测（当前有效）

依据：用户用法是**一个会话长期追问、无切换、无并发**（[单会话](11_SINGLE_SESSION.md)）；一轮追问的墙钟约 96～98% 是 decode，TTFT 只占 2～4%。所以改善每窗口毫秒数或每窗口提交 token 数的方向排在前面；只在切换会话或并发时生效的项降级。分数按同一公式用新证据重算，**状态与资格优先于分数**。

| 次序 | PR | 收益/适用/范围/安全/证据 | 综合 | 状态 | 依据 |
|---:|---|---|---:|---|---|
| 1 | #1536 回复 token IDs 复用 | 3.5 / 5 / 4.5 / 4 / 5 | 86.0 | **已上线（2026-10-26，[部署报告](../reports/DEPLOY-PROD-20261026.md)）** | 重读 4/14 → 0/16，追问 TTFT 4.87 → 2.52 s |
| 2 | #3871 CPU 微基准修正 | 1 / 5 / 5 / 5 / 4 | 74.0 | 测量前置 | NP-3 之前必须让微基准走 pool 实际 Q2_0 路径 |
| 3 | #3307 Prefill 借用 MTP 显存 | 4 / 4.5 / 3.5 / 3 / 3.5 | 76.5 | **NOT_APPLICABLE（Gate A）** | ring 大小无影响；chunk 受 `--prefill auto` 默认上限 8192 限制而非显存，零代码的 `STRATA_PREFILL_AUTO_MAX=16384` 已拿到收益（超过 8192 的读入 TTFT −27%，[报告](../reports/P2-PR3307-20261026.md)） |
| 4 | #3281 请求级显存事务 | 4 / 3 / 2.5 / 2.5 / 3 | 62.5 | 不做（推论） | 目的同样是给 prefill 更大 geometry，29 上显存不是限制，见 #3307 报告 |
| 5 | #4040 lookup 长窗口 | 2 / 2.5 / 3 / 3.5 / 3.5 | 54.0 | 低 | 采样单会话被接受的 lookup 草稿只占生成 3.6～5.6%；**2026-10-26 Gate A：NO_BENEFIT**，可加速的回答段只占 decode 时间 0.8%（[报告](../reports/P2-PR4040-20261026.md)） |
| 6 | #3322 DFlash2 服务集成 | 4 / 2 / 1 / 1 / 2 | 45.0 | BLOCKED | 草稿质量直接影响 decode，但 DFlash2 下载未批准、`--serve` 不支持 |
| 7 | #3584 前缀挂载 / 递推检查点 | 5 / 3 / 1.5 / 2 / 3 | 63.0 | 低 | 单会话追问已由 #1536 / PT 解决主要重读；剩余价值在多会话 |
| 8 | #4039 更小 prompt scratch | 1.5 / 1.5 / 4 / 3.5 / 3 | 49.0 | 低 | chunk 大小已由 `STRATA_PREFILL_AUTO_MAX` 放开；#4039 剩下的作用是同一 chunk 少借 cache slot、每个 chunk 少搬一些专家（推论，未测） |
| — | #3453 Ada MMVQ 表 | 1.5 / 5 / 5 / 4.5 / 3.5 | 74.5 | NO_BENEFIT（表本身） | CFG-IL89 / CFG-IL0 窗口级 0 收益 |
| — | #2253 内存门槛 / glibc 堆 | 1 / 1 / 5 / 4 / 4 | 51.0 | 不推荐（本用法） | 默认 floor 下 0 次触发 |
| — | #3517 / #3711 / #2822 / #2964 | — | — | 不适用或低 | root 短于检查点 / park 相关 / 无并发 / overlap 冲突 |

非 PR 方向（CPU pool、spec 宽度、短追加 prefill、PT 开关等）与本表交错执行，完整次序见 [README](../README.md) 与 [非 PR 方向](10_NON_PR_DIRECTIONS.md)。v2 包新增但本包不收的 PR：#4031 / #4002 / #4005（多会话或多卡 / HIP 平台）、#4068 / #2690 / #4046 / #4010（Q 轨道、格式不符或多卡），理由见 [非 PR 方向](10_NON_PR_DIRECTIONS.md) 第 10 节。

## 2026-10-23 排序（历史，保留作对照）

| 排名 | PR | 收益/适用/范围/安全/证据 | 综合 | 改造范围 | 本机前提 |
|---:|---|---|---:|---|---|
| 1 | [#2253](https://github.com/Niko1221/Strata/pull/2253) 内存门槛释放glibc堆并停止无效驱逐 | 4 / 5 / 5 / 4 / 4 | 89.0 | S | 29 日志 12 次 park 被拒（1 次驱逐 3 个后仍拒、11 次缓存已空仍拒），堆约 6.9 GB；与 CFG-MMAP 同测 |
| 2 | [#3453](https://github.com/Niko1221/Strata/pull/3453) Ada MMVQ 实机参数表 | 3.5 / 5 / 5 / 4.5 / 3.5 | 86.5 | S | decode 占引擎时间 75～80%；main 只有 `kIlRows_89` 注释、未注册，需本机生成表；与 B6 行复用一起评估；#1842 显示 4090 共享表在 128K 失配，先测 CFG-IL0 |
| 3 | [#1536](https://github.com/Niko1221/Strata/pull/1536) 复用模型生成的 Token IDs | 3 / 4.5 / 4.5 / 4 / 3.5 | 77.5 | S-M | 约 10% 续轮重读回复（约 120 s，约占 prompt 15%）；先分清 BPE 不一致还是 Pi 剥离 thinking |
| 4 | [#3307](https://github.com/Niko1221/Strata/pull/3307) Prefill 借用 MTP 专家显存 | 4 / 4 / 3.5 / 3 / 3.5 | 74.0 | M | 与3281互斥；主指标收窄为 ≥8K 未读 token 的 TTFT |
| 5 | [#3584](https://github.com/Niko1221/Strata/pull/3584) 前缀挂载与递推状态检查点 | 5 / 3 / 1.5 / 2 / 3 | 63.0 | L | 高潜力；生产已开 cache，但 MemAvailable 是硬门槛，宜在 #2253 之后 |
| 6 | [#3281](https://github.com/Niko1221/Strata/pull/3281) 请求级 Decode 资源显存借用 | 4 / 3 / 2.5 / 2.5 / 3 | 62.5 | M-L | 先证明planner瓶颈；与3307独立对照，同看长读 TTFT |
| 7 | [#3517](https://github.com/Niko1221/Strata/pull/3517) 正确固定 System Root Checkpoint | 2 / 1.5 / 4.5 / 4 / 3.5 | 56.5 | S-M | Pi root 约 12.3K < 16384 检查点，新会话已复用约 12.3K，预期 NOT_APPLICABLE |
| 8 | [#3711](https://github.com/Niko1221/Strata/pull/3711) 复用Host KV缓冲页 | 2.5 / 2.5 / 3.5 / 2.5 / 2.5 | 54.0 | M | 保留页面，与 #2253/CFG-MMAP 方向相反；内存有界后再评估 |
| 9 | [#2822](https://github.com/Niko1221/Strata/pull/2822) 单引擎短请求协作式抢占 | 3.5 / 2 / 1.5 / 2 / 3 | 49.0 | L | 仅有真实helper流量且可容纳被暂停状态时实验 |
| 10 | [#3322](https://github.com/Niko1221/Strata/pull/3322) DFlash2差量服务集成 | 4 / 2 / 1 / 1 / 2 | 45.0 | XL | v0.2.3 有 DFlash2 但 `--serve` 下退回 MTP（`ENGINE_SERVES_DFLASH2=False`）；先过命令行上限测试，禁止整分支合并 |
| 11 | [#2964](https://github.com/Niko1221/Strata/pull/2964) PCIe Expert Fetch 直接晋升缓存 | 1.5 / 1 / 3.5 / 3 / 3.5 | 44.0 | M | PCIe share 0.007，且原PR拒绝 adaptive overlap（生产开启）→ NOT_APPLICABLE |

相对初稿的调整：新增 #2253 并排第一（2026-10-23 扫描全部 390 个 open PR 后加入，见下文“补充关注”）；#3517 从第3降到第7（root 短于检查点）；#2964 降到最后（生产形态被资格规则拒绝）；#3711 先升后降到第8（与 #2253 方向相反）；#3584 升到第5；#1536 收益维度下调、证据维度上调。

## 投入层级

**第一层：1～4。** #2253 直接对应 29 现网的 park 失效，先做，同时测 CFG-MMAP。#3453 必须自己生成4090表，并和 main 已有的 B6 行复用、exact 开关组放在同一次 decode 诊断里评估；#1536只覆盖约10%的续轮；#3307要扣除借还DMA，且只对长读有意义。
**第二层：5～6。** #3584 与会话缓存和内存直接相关，放在 #2253 之后；#3281 与 planner 强相关，与 #3307 二选一先比较，不同时上两套显存管理。
**第三层：7～10。** #3517 预期不适用，只做 root 长度与检查点位置的资格检查；#3711 等内存有界后再看；#2822 需要真实多客户端；#3322 只做差量 spike，无法安全服务则BLOCKED。
**第四层：11。** #2964 在生产形态下由 `qualify` 直接判 NOT_APPLICABLE；不为了让它可测而关闭 overlap 或改 PCIe 参数。资格检查结束就停也是合格交付。

## 补充关注（2026-10-23 扫描 390 个 open PR 后，不单列为实验项）

| 项目 | 作用 | 在本包中的位置 |
|---|---|---|
| [#2962](https://github.com/Niko1221/Strata/pull/2962) 空闲时内存低于下限主动归还已 park 会话 | 每 2 s 检查，先 `malloc_trim`，按最旧释放，有滞回 | #2253 通过后的第一个组合项（29 有常驻容器挤压内存） |
| [#3404](https://github.com/Niko1221/Strata/pull/3404) 丢弃被改写过的旧副本 | Pi 改写历史后旧副本占预算 | 先用生产日志按 token 前缀核对是否存在陈旧副本，命中再组合 |
| [#2443](https://github.com/Niko1221/Strata/pull/2443) 驱逐重复持有同一 pin 前缀的会话 | 提供 #2253 需要的可驱逐字节统计 | 与 #2253 的 `evictable_bytes()` 语义对齐时参考 |
| [#3631](https://github.com/Niko1221/Strata/pull/3631) `STRATA_WINDOW_TRACE` / [#1864](https://github.com/Niko1221/Strata/pull/1864) decode 计时补全 | 每个 decode 窗口一条记录；把 adaptive wait/join 计入总和 | P0 诊断构建（不进入 A/B 统计），先拆清 29 每窗口 17.2 ms 的构成 |
| [#3230](https://github.com/Niko1221/Strata/pull/3230) B6 MMVQ 跨行复用片段 | 逐位一致；gfx1201 上 Q6_K head T=4 −29.6%、MTP head T=5 −19.2% | main 已有 `STRATA_B6_MMVQ_ROWS` 与 `b6_mmvq_bench`，随 #3453 一起在 4090 上测 |
| Issue [#1842](https://github.com/Niko1221/Strata/issues/1842) 4090 上 MMVQ IL 共享表失配（非 PR） | 同款模型 + `--spec 4`：128K decode 慢约 18%，`STRATA_MMVQ_IL=0` 全部找回；8K 时 IL 更快；无修复记录，v0.2.3 仍无 sm_89 表 | P0 配置对照 CFG-IL0，排在 CFG-EXACT 前；结论决定 #3453 的目标 |
| main 的 exact 加速开关组（`nv_defaults.cpp`，非 PR） | sm_86 上 IQ3_XXS +9.6%/+14.6%，输出一致；sm_89 未启用 | P0 配置对照 CFG-EXACT |
| [#3340](https://github.com/Niko1221/Strata/pull/3340) Pi thinking budget 字段别名 | — | 不适用：本机 Pi 配置未设置 `thinkingTokenBudgetField`，只发 `reasoning_effort` |
| #2843 分支 checkpoint、#3341/#3565/#3251 磁盘 park、#3309 prompt 预热、#3624 O_DIRECT 加载 | — | 对 29 不适用或价值低：Pi 的重读分叉点在 turn checkpoint 之后；磁盘 park 只在 #2253 后仍不够时作备选；后两项只影响首个请求或启动 |
| #3222、#3259、#3226、#3225 等 RDNA 专用 kernel | — | CUDA 不走这些代码路径 |

不依赖 PR 的方向不参与本表评分，见 [非 PR 方向](10_NON_PR_DIRECTIONS.md)。

## 初稿中为什么没有选进的项目

| 项目 | 不优先投入的原因 | 后续条件 |
|---|---|---|
| #3742 多GPU stage并行拷贝 | 单卡路径原本不创建stage pool，直接收益为零 | 真正升级多卡后 |
| #3752 GP100 weight-stationary / #3455 nibble | 依赖sm_60和全驻留层，4090部分驻留不能直接开；nibble还增加VRAM | 另立Kernel研究项目 |
| #3545 Verify Expert Cap / #2690 Deferred CPU | 改变近似验证或模型数值，Java任务质量优先 | 有大型质量评测预算后 |
| #3060 RAM自适应晋升 | IQ3_XXS 两分片合计约 75.8 GB，大于 62 GiB RAM；但 file-tier 读是否发生、占比多少**未测量**，现有 decode 计时里 GPU 等待占主导 | 当前inventory证实file-tier读成为瓶颈时可替换第8/9项 |
| #1614 Shared KV Pool | 主要收益来自多个lane转移；当前parallel1，KV驻留方式未验证 | 确认多客户端/slot调度且RAM不足 |
| #1937 磁盘会话层 | 额外持久化/版本身份/写放大，当前单会话低收益 | 频繁重启或主/子agent大量切换 |
| #3312 MMQ scratch loan | 小范围稳健性修复，当前head缺served性能数据；不把未触发OOM当加速 | Prefill loan触发scratch OOM时作为依赖修复 |
| #2399 elastic+kv-grow | 需要同时引入两种新内存策略，无独立当前GPU速度证明 | 精确证明KV/elastic碎片瓶颈 |
| #2683 Spill guard | 很值得作为公共性能门禁，但它本身不是运行时加速PR | Phase0/CI工具先吸收思想，不计入各项收益 |

## 证据解释

Kernel微基准、单机A/B、PR分支完整任务、维护者主线行为、我们的推断分开记录。所有旧百分比仅用于选择研究方向，最终选型只用你的同配置三态实测。关闭PR未merge不等于拒绝，也不等于实现没被移植；新版main的差量审计是每项第一步。
