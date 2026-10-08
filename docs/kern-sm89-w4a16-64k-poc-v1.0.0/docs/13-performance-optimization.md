# 性能优化顺序：用工作负载决定，不赌“更底层必然更快”

## 测量口径

分开记录cold prefill、cached-prefix extend、decode、host/tokenization、state恢复与Agent工具时间。每个request由输入token数组、profile SHA和request_id串起来。

`TTFT = 首个真实生成delta时间 − 发请求时间`。
`decode_tps = 已提交target tokens / engine_decode_wall_s`。
`task_wall = Agent开始到controller测试结束`。

SSE包含reasoning与content，分开统计再合计；不只统计visible answer。warm-up、图编译与模型加载单列。GPU功耗/温度/频率、其他进程必须记录；仅固定功耗不保证时钟固定。

## 优化梯度

1. 修错误的shape/重复repack/CPU-GPU同步/冗余workspace，不改变数学。
2. M=1、tiny-batch的W4 GEMM选择与融合；真实5120×N矩阵，不只小toy。
3. GDN控制/conv/norm融合，保留有限精度路径；对持久state特别谨慎。
4. 合并norm/rope/cache-write等低算量阶段，用完整graph测收益。
5. 关注长prefix extend；缓存命中仍需对旧KV执行attention，不能将其视为零成本。
6. checkpoint策略优化，减少不必要全量prefill，避免频繁host迁移。

优化采用A/B/B/A交替、至少3个seed；先null对照测噪声。只有总体耗时改善超过噪声且≥3%才保留“小性能patch”；大于10%的改善也必须检验完整Java/缓存，不让少数kernel快掩盖全流程变慢。

不把4090与GB300带宽比例直接换算成tok/s。没有测量就报告潜力，不报告预计必达120/200 tok/s。P0未达到参考后端时，先定位时间份额，最多进行3个有证据的局部优化循环；无法解决就NO_GO并保留oracle/NInfer。

## 追求极致但不混变量

精度不变的调度/融合优先。FP16 state、INT8 embed/head、低比特KV、DFlash2分别建立新profile，逐项证明Pareto收益。若速度提升伴随代码错误或长会话错缓存，直接淘汰。不要为了胜出benchmark关闭正常thinking、缩短输出或截掉工具结果。
