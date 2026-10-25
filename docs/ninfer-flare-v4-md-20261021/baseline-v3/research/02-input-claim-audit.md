# 附件与一级来源逐项核验

附件原文保留在 [HyperQwen 分析](../inputs/hyperqwen-analysis.md)。本表明确区分原文、源码/项目报告、本次判断；未核查的细节不自动升级为事实。参考 ID 见 [来源锁](00-source-lock.md)。

| 输入主张 | 核验结果 | V3 决定 |
|---|---|---|
| 381 是专项复述速度，不是通常吞吐 | HQ01 支持作者报告的 159/260/381 阶梯；本次未复现 | 复制、自由生成、真实 Agent 分开报告 |
| 7 neural + 8 lookup，总计 15 候选，16 verify | HQ02 明确 trained block 与 verify steps 分离；它还会替换头部，不是无条件拼接 | 用 N/K/W 三个维度，逐位置 source mask |
| 只要发现较长匹配就用长块 | 不充分；HQ02 结合可填 tail、前轮输出和连续命中；上下文阈值曾在不同配置下反向 | 成本校准+状态机，不硬编码“长上下文就用宽块” |
| Sticky 能稳定提升 | HQ02 明示只用于单请求；多请求曾因宽度/舍入出现不同 greedy 文本 | 单请求首发，batch 一致性另外 gate |
| Chain 模式跳过 drafter | HQ03 仍保留上下文更新/同步，且首次拒绝后退出并要新证据 | 跳过 proposal 不跳过 mandatory alignment |
| 40K 词表覆盖 97.5% | HQ01 为历史特定语料报告；HQ06 脚本注释另有 8.8M/95% 口径 | 不混成同一实验；必须保存语料版本与 held-out 划分 |
| donor 小词表适合中文 | HQ06 明示旧表 Han/Cyrillic 极少；这是 ID 类别覆盖，不等于中文频率覆盖 | 中文、Java、工具 JSON、字节碎片单独测量 |
| 只有完整 UTF-8 token 值得 draft | HQ06 的脚本注释/扩表规则如此写；但 byte-BPE 可以在连续 token 中拼出字符，本次不采纳该规则为语义约束 | 按实际 token ID 统计，保留被观察到的碎片，不能用单 token decode 成功率筛掉 |
| NInfer 应继续保留 E8 默认 | 附件描述的是旧 b0-scanner；V2 P4 明确移除旧 `rk4v4-e8` 并迁移 `rk4v4` | 2026-10-20 B29 已观察为 E8/schema20；先按 P0 兑现独立迁移，P6 合格后才沿用 `rk4v4`，不把未来默认当现场事实 |
| 给 NInfer 增加 Split-KV | V2 N07 已有相应 small-T/分割路径；NI03 有共同 verify | 只扩缺失宽度和测得热点，不重写整套 attention |
| 扩大一个常量即可到 16 | NI01/NI04 显示 replay、alignment、next draft 形状独立存在；HQ05 有 token/sequence 容量错误先例 | 做完整 shape closure 与容量属性测试 |
| 27B 已可用 DFlash2 | V2 N01 明确 unsupported/max0；没有后续实现证据 | H6 必须完整绑定和验证，不直接开 flag |
| KV 缩小必定更快 | HQ04 的 112K MTP FP8/KVarN 显示反例 | 保持 Target KV，donor 数字仅作成本警示 |
| 改页大小即可节约大量显存 | HQ04 是 vLLM hybrid 分组的特定几何 | 仅借鉴 planned/live bytes 与利用率审计 |
| 最新 FA2-FP8 对 4090 同样更优 | 可见源说明默认按 SM86 选择；另有 SM89 Triton 路线数据 | 不承诺 4090 新插件收益，不改变 NInfer backend |
| 给独立端口同时运行两个 27B | 端口隔离不代表显存足够 | 单 4090 串行 A/B/A；不得默认双模型共驻 |
| token 数/step 用 accepted drafts | donor 文档有 emitted/accepted 不同写法；V2 已纠正此口径 | 本项目只以 committed output 为速度分子，单列 accepted 与 bonus |

## 不以“修正”覆盖原始材料

附件中的图表 OCR/HTML/CSS 渲染残留不是有效数据表或实现；本包未从残留图形推测额外数值。关于 10 月 18 日 FP8、128 次前缀检查等未在本次可见源码范围逐一验证的详细计数，不写成验收已通过。论文 LongSpec/SpecExtend/Dustin 继续是 V2 的研究参考，不是 NInfer 256K 的已复现实验。

## 2026-10-20 现场适配纠正

“P6后默认rk4v4”不是当前29已完成迁移。B29仍E8/schema20，须兑现原PROD/O/C比较与codec数值/质量/速度门；不同codec不要求bit-identical。原比较helper的p95规则静默忽略已由受控负例复现，不能直接执行新p95门禁；见 [指标合同](../design/07-metrics-and-acceptance.md)。完整baseline与Pi回放先行，greedy/sampling分开。

## 2026-10-21采样主张的精确边界

确定性Lookup/greedy neural/mixed chain的实际q是delta，不是神经softmax或selector score；现有NInfer已有其Target sampling接受/residual/bonus入口，可作为复用seam。最终Target仍T1/.95/k20/presence0/preserve-thinking/medium；Target-greedy诊断不冒充生产收益。非一致tail可以是低质量确定候选，分布正确要求Target按最终mixed prefix求p；C14保守截断是性能/状态策略，不是必须重新求神经full-q的数学定理。资格前新组合OFF，随机drafter general-q未在本轮实现，见design/11。
