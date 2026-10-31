> 历史实验规范与记录。后续探索的当前阶段见 [NEXT_ACTIONS](../plans/NEXT_ACTIONS.md)；本文原口径用于解释原报告，不覆盖 frontier 新阶段合同。

# 单会话长期追问：用法画像、成本模型与已定结论

**用户实际用法（2026-10-25 说明）**：同一时间只有一个会话；长期追问；不派子代理、尽量不切换；没有并发。本包此后的排序和场景设计都以此为准。凡依赖“多会话切换 / park / 并发”才有收益的项，默认降为低优先级，除非用法改变。例外：单会话里，请求只要不接着引擎当前的会话往下读，也会 park。PT=0 时每个新用户轮都会如此（见第 3 节）。

原始数据：29 `workspace/reports/{session,chain,p2253}/`。阶段报告：[#2253](../reports/P1-PR2253-20261025.md)、[#1536 + preserve_thinking](../reports/P1-SESSION-1536-PT-20261025.md)。

## 1. 一轮追问的时间花在哪里（已观察，A0 + EXACT6，Pi 请求形态）

| 项 | 观察值 | 说明 |
|---|---|---|
| 每轮生成 | 1.0～2.8 万 token，thinking 约占 2/3 | `reasoning_effort` xhigh，temperature 1.0 / top_p 0.95 / top_k 20 |
| decode | 124～150 tok/s；采样下每窗口提交 2.05～2.44 token，15.1～17.5 ms/窗口 | greedy 题集是 2.78 token/窗口：采样降低了 spec 接受率 |
| 追问 TTFT | 正常 2.3～2.9 s（只读新消息约 3K）；重读时 8～12 s | TTFT = 首个输出事件，含 thinking 首 token |
| 一轮墙钟 | 约 1.5～3.5 min，其中 decode 约 96～98% | prefill / TTFT 只占 2～4% |
| 上下文增长 | PT=1 每轮约 17～27K；第 5～7 轮逼近上限 | Pi 在约 114.7K 触发 compaction |

**推论**：对这种用法，提速几乎只能来自 decode（每窗口毫秒数、每窗口提交 token 数）。prefill / 恢复类优化只在会话开始、compaction 后、重读时起作用；多会话类优化基本碰不到。

## 2. 三个已经定论的服务层问题

### 2.1 追问时整段重读上一轮回复 → #1536

- 现象：A0 上约 29% 的追问（off 14 轮中 4 轮）回退到上一轮 prompt 末尾，整段重读上一轮回复（2～3 万 token），TTFT 从约 2.5 s 变成 9～12 s。
- 根因：Qwen3.8-next 以 GDN 递归状态为主，只能回退到 checkpoint。服务端把历史回复按规范 BPE 重新编码；模型生成的 token 序列不是规范编码时，前缀在回复内部分叉。下一轮渲染文本与引擎原始输出逐字一致，排除了模板问题（`tools/session/reread_diag.py`）。
- #1536（`STRATA_REPLY_REUSE=1`）复用模型自己生成的 token id：重读 0/16，追问 TTFT 4.87 s → 2.52 s，decode 不变，输出文本不变。
- 状态：**2026-10-26 已上线**（`lab/prod-20261026` = `dcd67870` + CFG-PT，`STRATA_REPLY_REUSE=1`，[部署报告](../reports/DEPLOY-PROD-20261026.md)）。PT=0 下 Pi 默认请求用不到它，请求显式 `preserve_thinking=true` 时生效。

### 2.2 历史 thinking 是否进 prompt → CFG-PT（新增开关）

- 事实：chat template 的 `preserve_thinking` 默认 true；A0 的 `openai_to_messages` 会丢弃请求里的这个字段；Pi 也不发。所以现网每轮都把所有历史 thinking 重新喂进 prompt。
- 开关：`lab/cfg-pt@83a68423` 新增 `STRATA_PRESERVE_THINKING=0|1`（服务端默认值），请求里的 `chat_template_kwargs.preserve_thinking` 可透传且优先；`enable_thinking=false` 不受影响。只改服务层 Python，3 个文件，+45 行。

| 维度 | PT=1（现网） | PT=1 + #1536 | PT=0 |
|---|---|---|---|
| 轮数（Java 会话，到上限前） | 5～7 | 5～7 | **12** |
| 追问 TTFT | 均值 4.9 s，最差约 12 s | **2.5 s** | 均值 4.9 s，3.4～6.4 s |
| decode | 124～145 tok/s | 同左 | 127～150 tok/s |
| 质量（8 轮编码链，各 3 条） | 全满分 | 未测（输出不变） | 全满分（天花板效应，只能说未测出差异） |

- PT=0 每轮都要重读上一轮回答正文（前缀在上一轮 thinking 开头分叉），所以 #1536 在 PT=0 下无收益、也无害处。
- 状态：**2026-10-26 已上线，`STRATA_PRESERVE_THINKING=0`**（[部署报告](../reports/DEPLOY-PROD-20261026.md)：同一组消息默认 157 prompt token，显式保留 thinking 为 284）。难题质量在真实 Pi 使用中确认（质量门见 [统计](05_STATISTICS.md)）。

### 2.3 park / 内存门槛 → #2253

- 机制在 29 上成立，移植正确；但只在切换会话时发生，默认 floor 下 0 次触发。**不进生产**，候选保留。CFG-MMAP 同样不推荐。

## 3. 由实测得出的新问题（进入排序）

| 问题 | 证据 | 去向 |
|---|---|---|
| 采样下每窗口提交 token 低于 greedy | 2.05～2.44 vs 2.78 | 已测（[P2-CFG-SPEC-S](../reports/P2-CFG-SPEC-S-20261026.md)）：保持 `--spec 4`。窗口变宽，每窗口的 CPU 专家同比例增加，每 token 成本 spec 3/4/5 基本持平；O33 要等 NP-3 之后 |
| lookup 草稿在采样下确实触发，但份额小 | 被接受的 lookup 草稿占生成 token 3.6～5.6% | #4040（lookup 长窗口）Gate A NO_BENEFIT：份额 ≥20% 的只有编码链思考后的回答段，占 decode 时间 0.8%（[报告](../reports/P2-PR4040-20261026.md)） |
| thinking 占生成的 2/3 | 每轮约 1.2 万 thinking token | `reasoning_effort` 是用户侧质量选择（Q 轨道），本包不替用户改；如需，另做速度–质量对照 |
| 追问的 3～13K 读入只有约 1300～2300 tok/s | 冷长 prefill 约 3080 tok/s | 已测（[P2-CFG-CPUSHARE-S](../reports/P2-CFG-CPUSHARE-S-20261026.md)）：`STRATA_PREFILL_CPU_SHARE_MAX=4096` 使 3.1～3.2K 读入快 12.2%，为采用候选；7～13K 中超过 8192 的读入：`STRATA_PREFILL_AUTO_MAX=16384` 变单 chunk，TTFT 0.732 [0.708, 0.783]，每次省 1.0～2.2 s，为采用候选（[P2-PR3307](../reports/P2-PR3307-20261026.md)）；#3307 / #3281 不再需要 |
| 追问 TTFT 中有 0.6～0.8 s 不在 prefill 内 | STRATA_TRACE：park 0.15～0.5 s，槽位回填 0.2～0.35 s，checkpoint 保存约 0.06 s | park 只在请求不接着当前会话时发生：PT=1 + 工具循环几乎没有（真实流量 83 次续接中 4 次），PT=0 时每个新用户轮都有（模板只保留最后一条用户消息之后的 thinking）→ CFG-PARKGAIN，只在选 PT=0 后测。回填 → 与 decode 重叠（代码，NP-3 之后） |

## 4. 单会话测试工具（`tools/session/`，从 29 实测脚本收编）

| 工具 | 作用 | 关键约束 |
|---|---|---|
| `session_bench.py` | 一个 Java 长会话持续追问；Pi 请求形态；按 pi-ai 规则收缩 max_tokens；记录每轮 prompt / reused / read / TTFT / decode / thinking 与正文 | `--tree` 选候选树，`--env` 传 `STRATA_*`；不模拟 compaction，满了就停 |
| `chain_bench.py` | 8 轮递增需求的 Python 模块编码链，隐藏测试检查 1..t 全部需求 | **评分只在本地 Docker 镜像内执行**（`--image python:3.12-slim`，无网络、只读、非 root）；不给镜像则 NOT_RUN |
| `reread_diag.py` | 解释某轮为何重读：文本分叉还是 BPE 不一致 | 需要 `STRATA_DEBUG=1` 的 raw 行 |
| `ledger_ref.py` | 编码链的参考实现（校验评分器：完整 8/8，只做需求 1 为 1/8） | — |
| `../park/park_scenario.py` | 多会话 park / restore 场景（#2253 用） | 本用法下低优先级 |
| `../analysis/*.py` | MIG / CFG / DIAG 分析与语料生成脚本 | 历史报告的复算入口 |

这些脚本直接用 `lab.runner.OwnedServer`，还没有接入 schema2 计划与收尾回执（见 [测试协议](04_TEST_PROTOCOL.md)），结论按“配对筛查”口径报告。

**更正（2026-10-26）**：2026-10-25 的 6 条质量链在 29 宿主机上用 `python -I` 直接执行了模型生成的代码，违反本包“模型生成代码只在隔离容器执行”的规则。之后已改为 Docker 隔离评分，并用容器把 48 个评分点重评一遍，结果与原评分逐一相同；结论不变。
