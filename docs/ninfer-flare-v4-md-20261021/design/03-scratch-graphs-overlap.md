# GPU生命周期、Graph与有限重叠

workspace复用只按GPU最后消费者事件证明，不按CPU函数返回。列出异步D2H/逃逸输出/跨流/取消/restore实际consumer；只合并互斥区间，调优选择后缩到已选容量、重绑view，再固定地址捕获Graph。复用既有planner，不另建allocator。

不要求先完成correction才能做workspace。只证明真实峰值/容量或分配成本收益；理论payload少不等于可用显存增加。Graph仅验受影响shape的地址/encoding/capture/replay，未改路径不重复全面压力矩阵。

有限投影fork/join是独立可选实验：先证关键路径上的真实独立投影和资源余量，不拆已有GDN norm/control融合；并行分支独立scratch、正确join与consumer事件。必须比较完整Graph争用/同步/空间成本，无净收益保持串行。

详见[K3-T01](../plans/tasks/K3-T01.md)、[K3-T02](../plans/tasks/K3-T02.md)。不将全部流组合、所有模型或新调度平台变成前置。
