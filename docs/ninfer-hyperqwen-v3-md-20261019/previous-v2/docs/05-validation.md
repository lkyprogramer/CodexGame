> V3 继承资料：P0—P6 的任务目标和上游合入顺序继续有效。命令依赖须先按根目录 `support/REHYDRATE.md` 恢复。

# 05｜测试体系与 RTX 4090 验收规范

## 1. 三层基线，而不是只有两个分支

**PROD** 是当前真实镜像/启动参数/代理/模型；**O** 是固定 b0-scanner 源码编译结果；**C** 是当前阶段集成候选。先比较 PROD 与 O，才能知道你是在保护已部署收益，还是保护尚未上线的分支优化。纯 U 用于诊断合并引入的额外成本，不自动替代 PROD 基线。

同一批实测必须记录 source commit、image digest、GPU UUID、驱动/工具链、模型 SHA、六个 frontend resource SHA、代理版本与 reasoning、采样、codec revision、KV 容量、并发、prefill chunk、MTP/draft 参数、cache namespace、测试集 SHA 和随机种子。

当前证据包没有 GPU 测量结果。本文阈值是建议的发布门槛，需在 P0 候选测量前冻结，不是从当前数据统计推导出的既成事实。

## 2. Gate A：源码、构建和测试真实性

固定 refs 存在；共同祖先与 11/34 分叉计数一致；工作区中的额外定制被审计，不被 reset；完成整仓 merge probe 并审核 16 个共享路径以外的冲突/rename。

构建矩阵：27B 主包、35B 单包、双包注册。P4 包含 35B 上游修复以后，三者均须构建。4090 不对 NVFP4 A4 做执行资格；不能据此跳过 groupwise-int 的真实模型测试。

现有根工程仍需要 CUDA 工具链来配置/构建，即使某些前端逻辑测试本身不启动 GPU；不承诺“没有 CUDA 的普通主机直接跑整个 CTest”。本包的 Python 辅助脚本自测才是真正的 CPU-only。

CTest 必须导出 JUnit 并核对测试存在、执行、返回码。必测项目缺失、0 tests、skip77 均失败。可选 NVFP4/未启用决策 adapter 项目，必须在 qualification-scope 中明确标为未资格化，不能从统计中静默消失。

## 3. Gate B：tokenizer 和边界语义

### B1. 精确 oracle

原始 token IDs、added token selection、restart trace、错误类别及明确稳定的错误优先级使用精确比较。模型输出的概率/浮点行为不要混入这一层。

至少包含：空串、无 added token、连续 added token、同位置前缀重叠、交换 token ID 顺序、首字节非 ASCII、NUL、合法/非法 UTF-8、NFC 组合字符、partial marker、截断多字节、parse_added_tokens=false、copy/move tokenizer、共享只读 tokenizer 的并行请求。

对不超过 256 字节的 case 枚举所有 byte cuts；长 case 在 marker、普通词片段、组合字符和 EOF 附近取样。除既有 G1 20K fuzz 外，新增分段 contract fuzz 覆盖切点位于 ordinary segment、added token 内、段尾以及边界重合。

### B2. 旧契约与新契约分开

旧 implicit-only 输入：冻结 Legacy DTO/算法；保持 token IDs 与旧预期，按明确映射检查旧语义。新 Explicit：独立计算 `LCP(legacy.encode(text[:cut]), legacy.encode(text))`；隐式 exact 失败与显式合法回退是两个不同断言。

对边界去重、归零、排序、rewrite frontier、empty/full prompt、uint32 溢出的合成探针逐项验证。不得为了构造 2^32 溢出真的分配数十亿 tokens；沿用独立 size 参数探针。

### B3. 真资源 G1 与补充套件

旧驱动 real53 / synthetic74，real 需要 `--toggle-template`；fixture 文件末尾的一个 POSIX newline 读取时会去掉，pin 的逻辑字节必须一致。资源应从同一 `.ninfer` 提取，不能临时下载另一个 tokenizer 替换。

同一 suite 在 immutable O legacy 与 candidate 上分别运行，按 case_id/input_sha256/resources_sha256 对齐结果，不依赖 JSONL 行顺序。输出中不该比较的实现标签与工作量计数分列，不从功能 golden 中粗暴删除未知字段。

若原 cases/toggle fixture 缺失：P0 首先在指定项目/证据目录找回；没有找回就记录阻断。可以额外建立新的 frozen suite，但不得声称它是原来的 G1 复跑，也不得把原 53/74 改小。

### B4. 工作量与性能

同一次 Chat prepare 的 main encode calls 应为 1。相同 offset 重复查询必须命中 request-local memo；选中 added token 的完整前缀复用不应重复 encode 全量文本。对计数关闭和开启分别测量，计数不能改变 token/identity。

四路 benchmark 至少包含 4K、32K、128K、192K 的文本和短/长工具历史。记录 CPU prepare 的 p50/p90、单次主输入量、局部重编码总字节/最大局部片段、candidate checks、memo hits；不要只用次数更少推断实际时间一定更短。

## 4. Gate C：CUDA 与状态数学

small-T 覆盖 T=1,2,3,4,8,12,16,24,32，并加 T=33 的切换边界；模型维度和非整齐尾部用既有 Op oracle 范围补齐。验证 q4/q5/w8 可执行路径、workspace 字节、split-K 归并、图捕获/重放、并发 C=1/2/3，以及 MTP draft=3/关闭。

KV codec 验证 A1/A2/A3 的编码字节与独立参考一致，数值注意力与既有 oracle 容差一致；A4 覆盖 empty prefix、page/split 边界、1/2/4 fold CTAs、own token causal mask、多 question 隔离和长分支 scratch。检查 h=0、全零、极值、饱和、FP16 scale rounding 和 key/value rotation。

**不能对所有 warm/cold 或 MTP/non-MTP 路径强求完整输出逐 token 一致。** 不同 chunk 与 A8/GDN 浮点累积顺序可能改变 argmax；上游真实 prefix 测试已明确记录这种情况。对算法/状态先做相应精确或数值 oracle，再对已确认稳定的 golden fixture 做 token 精确比较；其余用质量、logit/概率差异及明确不回退的业务断言，不能用“浮点误差”一概掩盖状态污染。[S23]

新 codec 与旧 E8 本来就是不同数值编码，必须评估质量而非伪造 bit-identical。上游 kev 样本的 BF16 资格不能扩展成“所有 KV codec 的所有业务都合格”。

## 5. Gate D：缓存、导出、调度与故障

| 场景 | 必须断言 |
|---|---|
| 冷请求 → 同会话追加 → 改末尾 reminder | 命中来源、reused tokens 与预期一致；不误复用被修改区域 |
| 修改中间历史 / system / tools | 回退到合法边界或 full reset；不假命中 |
| 同 tokens，不同 adapter | 不跨 adapter 复用语义状态 |
| 相同 payload 的 frontier/session 发布 | 共享 payload 而非重复保留两份大 image |
| 显式断点与 implicit mode | Explicit 不意外关闭 session routing；非法参数严格拒绝 |
| 导出未结束即 cancel/reset/evict/restore | 无悬空 buffer、重复 release、半成品可见 alias |
| 满队列 / 资源不足 | 受控拒绝/等待，无进程级 OOM 或永久丢容量 |
| RoundFault | 仅本轮受影响 lanes 失败；后续队列可继续；非 RoundFault 不被吞掉 |
| 重复周期停止 | committed token 触发；停止原因可序列化；draft reject 不被计入 |
| 旧 snapshot/continuation/alias | 明确版本拒绝或 miss；不按新 codec 解释旧 payload |
| 新 namespace 重启恢复 | L3 还原正确；恢复失败不污染其他可用会话 |
| 监控和决策混跑 | telemetry/health 不因执行锁长时间无响应；Chat 客户端输出率单独评估 |

故障注入在测试进程、独立 cache 目录完成，不通过杀生产进程、覆盖旧 cache 或修改真实模型来构造。

## 6. Gate E：生成协议与 Agent 回路

三个生成端点均测试非流式与 SSE：`/v1/chat/completions`、`/v1/responses`、`/v1/messages`（Anthropic 路径最终以该提交 routes 为准）。保持原有 compat proxy 参与一组端到端验收，而不只直连 native server。

覆盖 Hermes/Qwen、字符串值看似 JSON、真正 object/array/null、嵌套参数、中文、未闭合 think、工具前后普通文本、malformed markup、输出 token limit、cancel、连接断开、previous_response_id。参数 deltas 拼接后与完整结果一致；未收到完整 end 的工具不能执行；历史存储不收录半个 JSON 工具结果。

prefill progress 是进度事件，不是模型 token，也不能算 TTFT 的首内容。测试客户端必须能区分首 HTTP 字节、首进度、首 reasoning、首 content、首 tool delta。

准备至少 20 个冻结 Java 修复/实现小任务，每个 3 个固定种子/重复，用 Maven/Gradle 编译和测试判定：类型/序列化边界、事务回滚、MyBatis 参数、异常链、幂等、分页、并发锁、缓存失效、接口兼容、单测补齐等。使用用户实际 JDK/项目约束，不为评测擅自升级框架。真实私有代码只留在用户机器；工具执行在隔离工作树，不回放生产写操作。

验收记录 compile/test pass、修复成功、tool-call 正确率、无效重试、循环/卡死、完成 token/时延。观测成功率不下降是工程门槛；样本量不足时不宣称已经证明 3 个百分点的统计非劣效。报告配对差异/置信区间与不确定性。

## 7. Gate F：长上下文与单卡容量

上游 `ninfer_qwen3_8_27b_prefix_real_test` 的 engine_options 使用 max_context/kv_capacity=4096，因此它不能替代长上下文资格。[S23]

| Profile | 输入规模 | 并发 | 目的 |
|---|---|---:|---|
| Long-cold | 32K/128K/192K/248K 附近的实际 token 数 | 1 | 冷预填充、容量、质量 |
| Long-hot | 128K/192K/248K 前缀 + 小工具增量 | 1 | 高命中 prepare/restore/TTFT |
| Mixed-agent | 多会话，例如 60K+40K+20K | 3 | 准入、导出、热冷干扰；总量须先过容量账本 |
| Capacity-negative | 明确超过共享 KV 总容量 | 2—4 | 应拒绝/排队，不承诺请求成功 |
| Decision-reference | 中等上下文，BF16 KV | 单实例内受控 | 决策数值参考，独立容量预算 |
| Vision-state | 小图/不同 detail，再扩到预算边界 | 受控 | preprocessing identity、MRoPE、取消与缓存 |

K 只是场景标签；必须用实际 tokenizer 记录整数 token 数。`prompt_tokens + requested_output + 实际系统保留 <= max_context`；共享 `kv_capacity=262144` 不是“每个 lane 都各有 262144”。不得用 C=4、每个 200K 的配置测试成功性，再把合理的容量拒绝当成回归。

长文本不能只重复一句话。使用 Java/SQL/日志/补丁/工具结果组合，包含跨段类名、方法签名、约束、依赖关系和 5 个唯一检索标记。至少包括 248K 的 5-needle 与代码细节回忆；精确检索在规定格式下不得丢标记。

## 8. 性能门槛、统计与对比口径

建议每个关键 case 至少 10 次配对测量、3 次 warmup，并使用 A/B/A 或 ABBA 交替，记录 GPU 频率/温度/功耗上限。正式指标与 warmup 分开。长场景成本高也不能用单次结果宣称 p90；不足样本标 BLOCKED/INCONCLUSIVE。

初始 guardrail：TTFT p50 不超过基线 +5%、p90 不超过 +10%；decode rate p50 不低于 -3%、p10 不低于 -5%；prepare p50/p90 同 TTFT。毫秒级很小的分母采用绝对预算：TTFT 5ms，prepare 0.5ms。数值在候选运行前冻结，禁止看到失败后改阈值。

`compare_metrics.py` 只比较归一化后的配对测量，并检查模型、GPU、数据集、profile、并发、上下文、reasoning、codec、MTP 元数据。P4 有意改变 codec 时显式 `--allow-change kv_dtype`；不能通过更换数据集、降低 reasoning 或缩短上下文“通过”。脚本不是统计显著性证明，也不替代业务质量 gate。

冷 prefill rate 的分子是本次实际 computed prefill tokens，热命中的 reused tokens 不计入。请求级 decode rate、服务器总 committed tokens/s、客户端可见 output tokens/s 分开；不能拿单个执行 round 的速度代表用户收到内容的速度。
