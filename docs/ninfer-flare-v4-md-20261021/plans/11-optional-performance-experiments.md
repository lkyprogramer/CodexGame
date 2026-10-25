# 有性能可能的可选实验，非顺序待办

这次收缩去掉的是无关功能与重复验证，不是尚未验证的性能研究。DFlash2、全局检索、W8/W16和utility scheduler都进入可选candidate scope；不能只降为研究参考，也不能从理论可能直接宣称已具备4090净收益。

| 实验 | 为什么可能变快 | 什么会抵消收益 | 选择条件与最小第一证据 |
|---|---|---|---|
| CPU内容指纹（C0） | 降低实际快照发布/缓存就绪CPU时间 | 异步成本未必在请求关键路径；provider启动/依赖 | K0已定位无SHA指令标量路径；先精确CPU资格，再测服务收益 |
| W8 / W16 | 一轮提交更多token，减少Target轮数 | 更大的verify/Attention/Graph、alignment和KV余量；低接受率 | W4实测曲线→单shape W8；W8通过且仍有增长空间再W16 |
| DFlash2 | 并行块草稿降低串行draft成本，可能提高接受长度 | companion权重、特征传输、draft KV、Graph与显存 | 精确27B资产/接口先静态核对；一个可容纳宽度，不等全套Lookup/W16 |
| 全局检索 | 发现局部ring之外重复草稿，改善长历史命中 | 索引/查询/搬运/位置修正/DraftKV重建 | 先离线测ring外有效命中；token-only可独立，feature版本绑定相应H6 |
| Utility scheduler | 依据真实成本选择backend/宽度/恢复计划，减少低效轮次 | CPU决策、统计/同步、cache miss与策略抖动 | 至少有两个合格可选行为且成本有变化；先简单固定规则，不建调度平台 |
| draft head | 降低实测占比显著的草稿投影成本 | 词表覆盖下降、接受下降、mapping/稀疏成本 | 一个profile与完整Target支持集对照 |
| 有限投影重叠 | 独立关键路径可并行 | 争用、同步与独立scratch | 先证明独立与资源余量；比较整个Graph |
| 完整上游U34 | 可能包含共享text修复/性能改动，或降低必要改动的拆分风险 | 无关代码/编译依赖、格式变化、cache冷启动与回归 | 复用源码审计；有Chat收益或实质耦合理由时建立与P4/选择性版本的对照 |

W8/W16是宽度选择；DFlash2是草稿来源；全局检索是候选来源/上下文机制；utility是合格路线选择。它们解决不同成本项，不应被捆成全部实现才验收的大改造，也不应默认做所有交叉组合。

DFlash论文证实并行块草稿具有加速机制，但不认证本项目命名DFlash2的27B资产或本机效果。[DFlash原论文](https://arxiv.org/abs/2602.06036v2)。接受长度只是代理指标，draft与verify总时间才决定有效吞吐；自适应草稿研究也明确处理这个成本差异。[ICLR论文](https://proceedings.iclr.cc/paper_files/paper/2026/hash/34345e243156da67605d4b63d71c8d98-Abstract-Conference.html)。这里不把论文倍数挪作B29预期。

所有路线必须遵循[Target sampling合同](../design/08-target-sampling-and-baseline.md)，以完整round/service成本验证，预算与估时见[统一预算](08-validation-budget-and-estimate.md)。没有兼容资产/热点/命中/资源证据可暂不选择；不是没有理论可能，也不是被永久删除。
