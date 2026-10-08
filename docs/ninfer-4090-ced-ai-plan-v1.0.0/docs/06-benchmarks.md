# 06 可复现 Benchmark、Java/Pi 场景与统计

## 1. 四组对照，禁止混淆

A：原始44a2c6c二进制native；B：候选二进制但LSP=off；C：候选LSP=on；D：Teacher-state injection，只用于正确性。

A↔B评估工程回归；B↔C隔离近似路径收益；A↔C回答用户最终收益；D不能进入速度排名或质量训练。先no-spec三组对齐，再MTP3三组对齐；MTP3结果不能直接除以no-spec当作CED收益。

所有对照保持模型SHA、codec、最大容量、采样、thinking、chat template和客户端行为一致。`--prefill-chunk 2048`仅作独立ablation；不要和CED一起切换后计算收益。

## 2. 输入长度与冷热矩阵

基准实际token数为4096、32768、65536、131072、200000。容量262144另做`prompt+output<=capacity`边界检查。长度由同一原生tokenizer对最终渲染prompt计算，不以字符数估算，不用max-context替代实际输入。

| 场景 | 构造 | 正确计时方式 |
|---|---|---|
| Cold | cache off、no-prefix-reuse；独立session | prepare+predict+state+tail+MTP+首token全计 |
| Warm append | 完整对话追加1K工具结果，不改前缀 | 明确reused tokens、computed suffix、restore成本 |
| Root rewrite | 修改第一轮user或system的一小段 | 必须安全miss；这是CED潜在适用面 |
| Tool schema change | 调整函数参数顺序/定义内容 | 不能只靠prompt_cache_key强命中 |
| Session switch | A→B→A；相同/不同profile两类 | L1/L2命中类型分开统计 |
| Restart L3 | 显式可选，独立实验namespace | 精确保存真实会话，重启后验证来源与输出 |
| No-op repeat | 完全相同request | 缓存成本单列；不当作cold-prefill成绩 |

P4仅cold；P5新增warm/session；P6纳入实际Pi循环。P4的24个smoke项见`configs/smoke-fixtures.json`，不与P6的24个独立Java任务混称。已有部署文档建议L3先不默认开启，本计划沿用：L3只是可选耐久性测试，不改变生产默认。

## 3. 长上下文任务（12类）

必需矩阵采用均衡的36个case：12类分别在64K、128K、200K各跑一次，目标位置按 `(fixture_index + length_index) % 5` 在5%、25%、50%、75%、95%轮换。因此每一类覆盖三种长度，整个suite覆盖五种深度。完整12×3×5=180个case只作可选扩展或定位，不在每个Phase重复跑。扰动内容来自同域真实代码/日志，不只重复同一句话。

| ID | 任务 | 自动评分 |
|---|---|---|
| L01 | 单个唯一配置值 | 精确字符串；不接受同义 |
| L02 | 五个分散配置值汇总 | key/value全部正确 |
| L03 | 有日期顺序的覆盖配置 | 选有效最新项，忽略旧值 |
| L04 | 跨三个文件方法调用链 | method/file/方向全部正确 |
| L05 | 很早出现的禁止改动要求 | patch没有触碰保护文件 |
| L06 | 编译日志真实根因与干扰warning | 错误行号和修复点正确 |
| L07 | 两段冲突接口契约 | 按指定优先级选择，并保留兼容 |
| L08 | 长JSON中精确字段提取 | 完整schema校验+值比较 |
| L09 | 已撤销工具结果不能再采用 | 最终行动使用有效数据 |
| L10 | 相似ID/文件名辨别 | 不混淆大小写/尾缀 |
| L11 | 源码范围的边界条件 | 生成补丁通过隐藏边界测试 |
| L12 | 多轮要求累积与最终约束 | 所有先前有效约束均满足 |

检索通过不等于代码能力通过。测试split与训练repo/session分离；禁止训练使用这些目标字符串和答案模板。

## 4. Java/Pi 24个独立任务

具体题目、故障种子、最小断言见 `configs/java-fixtures.json`。P0/P6的任务负责生成独立小仓库、broken revision和隐藏judge测试；本包给的是确定的fixture规范，不声称已经创建了24个Java项目。

每个任务必须经过“broken版本失败、reference补丁通过、candidate补丁评分”的三角验证。测试若broken也绿，则fixture无效，不能统计。候选Agent只看到需求和工作区，不看到reference补丁、judge答案或隐蔽测试目录。

每题固定3seeds（17,41,73），最大20个tool调用、每题wall预算300秒、总输出预算4096token。编译等待时间计入agent任务耗时。一次完整Pi循环包含读文件、修改、运行测试、解析结果和最终返回；不以一次HTTP生成代替。

优先Java8兼容、Maven/JUnit离线缓存，避免网络下载成为随机变量。Java平台或依赖版本写入run manifest。现有真实repo任务可以补充，必须用户已授权且独立划分，不覆盖标准24题。

## 5. 数值诊断

Full-vocab KL只在相同token前缀上比较，使用Teacher强制token序列。对合法token域248077个ID计算FP64 logsumexp，物理lm_head padding行不能进入分布。报告首token、前32和前128步KL均值/p95/max与NLL差；不把两个已分叉自由生成序列直接逐步相减。[S06]

尾部长度0仅可作为数学ablation，不是可发布模式；正常sweep为512/1024/2048/4096。同时记录prefix误差、tail末端误差和decode漂移，不能只展示被tail遮盖后的最后一项。

## 6. 性能重复与统计

Cold各长度/配置至少5次，先独立warmup1次不计分。固定seed随机ABBA/BAAB排列；native和candidate都记录频率、温度、功耗、显存。性能报告使用每次未四舍五入耗时；中位配对ratio与bootstrap（10000重采样、seed20260911）95%区间。

单请求TTFT包括所有候选额外成本；prefill吞吐=`raw_prompt_tokens/prefill_total_seconds`；cached场景另报`uncached_tokens`，不能给全prompt分母的数字贴上kernel吞吐标签。decode tok/s遵循现有引擎定义；同时报告完成token总量，防止少生成看似更快。

Agent成功、失败、超时分开报告，完成时间同时给全体预算截断值、成功样本值和总makespan；不只挑成功任务。质量比较按独立task/repo成组，不把同一任务的三个seed当三个独立任务制造置信度。

## 7. “未见下降”与“证明不下降”

默认24题只支持小范围个人试用。总完成率观察差≥−2pp不是统计等效证明。

可选更严格晋级：以每个独立任务中“candidate三seed成功数小于baseline”为harm事件，计算单侧95%Clopper–Pearson上界；要求harm概率上界≤2%。当观察0次harm时，上界为`1−0.05**(1/n)`；约150个真正独立任务零harm才能把这一保守上界压到2%以内。它是“退化任务发生率”的约束，不是准确率差的同一指标。

本计划不强迫个人项目首轮运行150题。证据不够时明确 `private_opt_in_only`，不宣称无损，不自动替换生产默认。

## 8. Fault injection

必须覆盖：predictor SHA错误、缺head、split不匹配、tail0、容量不足、codec变更、profile变更、空prompt、T边界、非法页表、conv历史错序、未来位置泄漏、MTP shift错一位、approx/native alias碰撞、取消发生于state写入中、首token前异常、恢复后位置错误、缓存损坏、GPU进程意外退出、生产恢复失败。

每个fault只能得到明确拒绝、安全miss、完整rollback或受控失败之一；不得返回200并隐瞒不完整state。
