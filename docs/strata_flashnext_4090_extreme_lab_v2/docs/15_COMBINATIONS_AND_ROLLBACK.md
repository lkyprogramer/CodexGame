# 组合实验与回退

## 1. 禁止简单堆叠

| 组合 | 关系 | 验证方法 |
|---|---|---|
| CPU pool重排 × 新ISA核 | 可能互补，也可能降低nt权重复用 | 2×2 factorial，保持相同路由与布局 |
| 更大lookup T × CPU multi-token | 同时增加verify成本与复用 | 按T/accepted分层，记录effective tokens/window |
| 更大graph集合 × expert cache | 争显存 | 固定总显存预算并记录resident expert变化 |
| 低比特KV × expert cache | 可能释放容量，但加入解包成本/质量变化 | 先各自单测，再测实际多驻留收益 |
| cache malloc_trim × mmap阈值 | 都影响allocator，不应同时首次开启 | base/trim/mmap分别试，再必要组合 |
| PR2253 × PR4031 | 同一准入与淘汰路径，语义冲突 | 设计统一policy；不机械cherry-pick两套循环 |
| adaptive overlap × async tier / PR2964 | 当前存在互斥资格 | 不为开启新flag悄悄关闭既有收益 |
| residual prefetch × adaptive swaps | 竞争PCIe、CPU、slot | 统一预算和epoch；逐项消融 |
| GDN chunk × 新归约 | 累积数值变化 | 长状态轨迹、分块边界与spec拒绝重测 |
| conversation slots × batch并发 | 不同概念、可能争RAM | 独立参数与会话生命周期验证 |

## 2. 分支与GPU锁

一个方向一个隔离worktree，依赖通过已审查commit传播。源文件重叠的任务串行整合；CPU单元测试可并行，GPU性能实验共享独占锁。不要在同一GPU跑agent A/B或把后台编译污染为真实功耗。

## 3. 组合顺序

最新基线资格→测量修复→CPU pool/park独立候选→residency和spec→prefill/CUDA→KV/格式。每阶段只合并已通过留出的少量候选。组合版与所有单项版本保留二进制与配置hash；不只留最终HEAD。

## 4. 默认路径与回退

拟新增开关默认0；默认编译应保留legacy实现。未知shape/ISA先拒绝候选或fallback，并在日志统计，不偷偷换近似实现。撤销一个候选通过切换已知构建/配置，不在现网源码原地git reset。

部署前产出`deployment_plan.json`：old/new binary hash、config diff、service ownership、health与tool smoke、回滚条件和旧构建位置。真正部署由目标机执行者依既有授权处理；本包不自动停止生产或修改systemd。

## 5. 停止条件

- 启用后触发未经预期的路径、unsupported ISA、NaN、状态污染或错误答案：停止该候选。
- 微基准提升但目标场景无收益且落在噪声内：NO_GAIN，保存反例，不反复换题直到“成功”。
- 关键路径份额已经太低：按Amdahl将候选降级。
- 资源不足、回收不完成或外来负载出现：终止本轮自有进程，标环境失败，保留原始记录。
- 异常后不能确认state生命周期：丢弃候选状态，从冻结token重新计算；不能继续用可能污染的cache测性能。
