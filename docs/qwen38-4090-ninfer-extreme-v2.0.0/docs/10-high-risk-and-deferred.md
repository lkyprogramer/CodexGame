# 高风险研究：A4、重训练与长期方向

## 1. A4仅独立研究，不阻塞主要收益路线

先用sm89编译一个s4 IMMA microprobe、检查SASS和实际throughput；不得从广告TOPS或另一架构弃用说明推测当前编译器支持。输入/输出布局、group64缩放与累加类型必须完全明确。

已有Q4整数可落入s4范围，但逻辑codes、物理row-split布局、K分组与MMA操作数tile不自动一致。A4激活新增误差。若Hadamard旋转折叠入权重，`W·Hᵀ`改变原矩阵，需要从可信源重新量化；不再拥有原target payload identity。Q5敏感层保留旧A8路径，禁止截断成Q4。

任何新artifact使用不同ID/hash和独立缓存schema；旧target基准继续存在。用相同训练/验证切分记录校准数据，禁止在holdout上选scale。原Java3题和needle不够证明安全，需原质量集、更大推理/指令遵循测试、真实repo任务。失败时回退A8，而不是降低门槛。

## 2. Drafter训练

公开推荐4×H100是实现/效率配置，不是数学上“4090绝对不能训练”的定理。离线hidden-state数据、冻结target、参数高效训练可能减少需求，但数据提取/存储/精度和实验规模都需另案；目前不与推理改造混合。先验证已有drafter在medium桶的实测收益再决定是否值得训练。

## 3. 低bit主权重、超频与megakernel

低于现有主权重精度属于质量新实验；KL差不能单独量化Java能力，但足以要求更严门。显存超频/电压/功耗不默认执行，温度阈值应按该板卡传感器和厂商限制，不照搬95°C。megakernel的上限取决于kernel/launch占比；prefill已主要kernel-bound时不重写调度来追微小launch份额。

这些都列为独立后续，不提供默认可执行超频脚本，不在本包基础版本自动触发。
