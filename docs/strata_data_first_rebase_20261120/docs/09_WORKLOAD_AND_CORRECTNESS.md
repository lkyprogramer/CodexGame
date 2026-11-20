# 09｜工作负载与正确性合同

## 1. 三种实验分开

| 合同 | 比较对象 | 不允许的混用 |
|---|---|---|
| 新基线诊断 | 同一新版binary，observer off/on；无算法变量 | 不拿旧v0.2.3数字当对照，不称已提速 |
| 可选版本迁移 | 同资产、同工作负载，旧/新engine版本是唯一因子 | 自动route变化要列出；不能归因单一kernel |
| 候选A/B | 同一新版source/配置、只改变一个合格机制 | 禁改量化、KV codec、draft、sampler、模板、工具策略 |

新版本的“绝对可用”要单独判定：旧版也错不代表新版合格；new-vs-old token差异也不自动证明新版本bug，需绑定oracle和源变更。

## 2. 工作负载不是 context 长度一维

最少保留以下场景卡。它们是待绑定任务族，不是要求本轮全部执行。

| ID | 场景 | 核心问题 | 固定条件 |
|---|---|---|---|
| W01 | 4K短任务，代码/结构化工具 | 协议与低固定开销 | 已有合法任务、固定工具schema |
| W02 | 64K或约100K cold read，128K总窗 | prefill实际route/chunk/CPU-IO | 文件page cache、engine冷与prefix冷分别说明 |
| W03 | exact repeat | 相同渲染prefix能否复用 | 输入hash与工具/历史策略完全一致 |
| W04 | 真实100/1000/3000-token追加中的一个 | warm tail与恢复、重算 | 选择一个实际尾长，不默认3档全扫 |
| W05 | A→B→A及两个短子任务 | idle parent状态是否保留、谁在排队 | 首轮先串行，不从Dense建议推出Strata并发 |
| W06 | 同会话键但工具或模板真实变化 | cache miss是否正确 | positive/negative prefix对照；不是改prompt促成PASS |
| W07 | 合法EOS/cap/取消/超时/重启 | token/state/terminal计数正确 | CPU协议fixture优先；live次数单独计费 |
| W08 | compaction后首轮 | 渲染、prefix失配与质量 | 仅现有投影器支持时启用，否则NOT_APPLICABLE |
| W09 | copy/edit与non-copy control | C01反事实是否只利于复写 | 任务源/许可/权重预登记，不用合成高命中当总体 |

P2.0先复用有效当前L0原件；确有缺口且获授权时采一个合法长输入的 W02+W03+W04 组合。P3仅按缺口补所选L1或CASE，W05等不是必跑全套。C01缺W09内容原件时，只能在明确授权下用同一CASE上限替换为W09，否则INSUFFICIENT。不得把所有场景族展开成参数网格。

## 3. 总窗与真实token

沿用128K硬合同：GPU总context≤131072，**完整渲染输入+最大输出+4096安全余量≤131072**。128K window不等于能送128K输入再生成。若多slot占用语义不同，P0实测/源码解释后按更严格总量约束。

以实际tokenizer计数，包括system、工具schema、历史thinking/assistant/tool结果、模板控制token。不能仅拿文本字符估算。长度不合格提前拒绝，不截掉题目关键位置。

每场景记录 `actual_input_tokens, logical_prefix, actual_read, max_output, actual_output, stop_reason`。自然EOS与固定输出长度任务必须分开；短失败看起来很快，应进入失败桶。

## 4. 三层正确性

### 4.1 数据正确

请求集合、输出位置、原始计数、终点和时钟可核。沿用A1反例：missing request / short position / single stock arm不得被工具交集规则误判PASS。`force_check`只是数值工具的一环，不能替代本包完整性门。

### 4.2 数值与状态正确

同一实施路线先off与原版，再on与off：

- 固定合法形状与真实量化/布局的局部oracle；
- 支持时比较greedy token哈希、logit/误差合同、state/checkpoint；
- seeded sampling需确认算法保持同一随机数消费或分布合同；相同seed不天然保证跨路径逐token相同；
- EOS/max_tokens/lookup命中及不命中、cache save/restore、cancel后续聊、短尾/尾分组、图重放都覆盖；
- 若候选改变归约顺序或有新的近似，退出当前exact track。不得把松KL门无声替代用户原合同。

全局已有placement/tail-skip等近似必须记录原设置；“不新增近似”不等于声称整个基线数学上无近似。禁止为了适配donor改变原设置又称单因子优化。

### 4.3 任务正确

结构化工具、完整答案、真实工具回执、长检索gold、代码测试与延续会话分别统计。执行生成Java只用现有受限Docker；缺镜像记NOT_RUN。

最新历史的 NInfer工具开启5/16与关闭16/16提示要分失败时长，不允许沿用“HTTP200=PASS”。该历史不证明Strata同样失败，只要求它的新基线也过实际任务门。

P0/P5必须登记一份具体质量清单：`required_case_ids`、既有gold/测试引用及hash、每题结构条件/真实工具执行与回执条件、数值和状态等价条件、缺题/超时/执行环境缺失的处理、绝对通过阈值。不能临时发明gold或事后放宽阈值；必测缺失不能靠其他题均分补齐。P2.0/P3可输出有限BASELINE_DIAGNOSTIC而不声称绝对门已经证明；缺该清单或缺必测回执的P5不得READY。

## 5. 数据最小化与回放

优先复用已授权且合法投影的历史trace，锁来源hash及预处理脚本。不能凭“有一段SSE”重新构造未保存的真实prompt，也不以固定token trace替代真实工具I/O的业务验收。

C01在每个时点构建索引和生成proposal只使用当时可用的prompt/已提交历史，不读取未来答案。事后评分可以把proposal与已录答案比较，但必须标 ORACLE_UPPER_BOUND，不能当在线命中率或target实测接受率。真实acceptance还需target验证与其成本；只知道长匹配长度不能凭空生成相应logits/采样接受。必须同时有copy/edit与non-copy任务及预登记权重，普通SSE摘要不能还原完整token trace。

## 6. 输出格式

每个case必须写：

- qualification状态、执行次数、fresh engine/block ID、warm/cache定义；
- 质量成功/结构成功/完整答案、错误/取消/NOT_RUN；
- client与engine各自时间/计数，观测缺口；
- 收集模式、额外内存/CPU/I/O、产物hash；
- 该case可以支持什么、不能支持什么结论。

P2.0/P3有限诊断样本不作线上p95/SLO或2pp质量非劣证明。正式统计规则见 [10](10_EVALUATION_AND_STATS.md)。

