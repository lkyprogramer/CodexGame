# 11 · RTX 4090 调优与公平性

## 显存预算

24GB 不等于 24GB 全部可给权重。还需要 KV、GDN/运行状态、CUDA buffer、context、MTP 和桌面占用。Q6 权重“勉强装下”通常不代表适合多轮 Coding Agent。

## 推荐测试层级

- 主质量对照：Q4_K_M/相近高质量 Q4，32K；
- 高精度对照：Q5_K_M，较短 context；
- 长上下文：IQ4_XS/低体积 mixed quant，64K+；
- MTP：只在 Regular 基线后测，并记录 acceptance、速度和任务成功率。

## 性能记录

区分：prompt tok/s、decode tok/s、TTFT、完整任务 wall time。标准 Runner 非流式，TTFT 只能从 server telemetry 获取并单独合并。Agent 任务中，少生成 reasoning token 和减少重试可能比 decode tok/s 更重要。

## 防止热态偏差

- 固定 power limit；
- 每个 block 前预热；
- 记录峰值温度；
- 模型顺序轮换；
- 长任务后给所有模型同样的恢复条件；
- 不在一部分模型上开启 flash attention/MTP 而不披露。

## OOM

OOM 是部署结果的一部分，但不能直接记为“模型能力 0”。质量榜可标为未完成；部署榜应计入可运行性和最大稳定 context。报告必须说明失败发生在载入、prefill 还是 decode。
