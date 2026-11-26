# EXPERIMENT · <experiment_id>

## 实验前冻结

| 项 | 必填内容 |
|---|---|
| 假设 | 可证伪的具体机制与预期改变 |
| 分类 | E / N / Q；target_fingerprint是否变化 |
| baseline / candidate | commit、binary、资产、profile、所有差异 |
| 主要终点 | 真实任务耗时/请求耗时/容量/质量，不能事后更换 |
| 次要终点 | TTFT、TPOT、p95、接受率、bytes等解释指标 |
| stratum与业务权重 | 冻结输入/上下文/冷热/任务类型分层 |
| 数据 | case ID、fixture hash、开发/holdout分区与oracle |
| 采样与预算 | temperature、processors、seed、输出/turn/wall上限 |
| AB/BA计划 | 预生成顺序与重复次数，case为独立单位 |
| 样本/统计 | 独立case数、bootstrap/CI、功效或证据不足处理 |
| 环境 | GPU/CPU/driver/runtime、负载、频率与温度记录 |
| cache | process、OS page cache、prefix三个维度 |
| 资源上限 | GPU/host/SSD预算、余量、timeout |
| 停止规则 | 正确性、资源、质量及无收益门 |
| 排除/重跑规则 | 实验前定义；保留原始失败和outlier |

## 原始记录

run目录：  
输入token IDs/hash：  
actual argv与profile hash：  
所有raw event/计时/错误/状态比较路径：  
唯一pair ID、case ID、stratum映射：  
H2D/SSD逻辑与实际读取、ledger/NVML/PSS轨迹：

## 结果（未执行时全部保持未测）

| 指标 | baseline | candidate | 效应/CI | 证据 |
|---|---|---|---|---|
| 成功率 | 未测 | 未测 | 未测 | 无 |
| 任务中位耗时 | 未测 | 未测 | 未测 | 无 |
| case等权gmean | 未测 | 未测 | 未测 | 无 |
| p95 | 未测 | 未测 | 未测 | 无 |
| 峰值GPU/host | 未测 | 未测 | 未测 | 无 |

最后状态：NOT_RUN / PASS / FAIL / BLOCKED / NO_BENEFIT。  
此结论适用的精确范围：  
不能据此推出的能力：  
下一次允许重开的新证据条件：
