> TECHNICAL_REFERENCE_ONLY：以下固定源码/计算/旧论证保留，原先的“当前”时态或阶段要求不再调度任务。当前身份见[证据](../research/05-completed-baseline-and-current-state.md)，执行以[根注册表](../plans/02-task-registry.md)为准。原始字节另保存在本轮403份快照。

# 本次实际完成的静态计算

使用Python整数计算，2026-10-21。不是产品性能测试。

```text
raw_per_layer_row_column = 10240*2 + 16*128*2 + 48*128*2 + 2*48*4 = 37248
correction_per_layer_row_column = 10240*2 + 16*128*4 + 48*128*4 + 48*4 = 53440
difference = 16192
C4/W6/L48 raw MiB = 40.92187500
C4/W6/L48 correction MiB = 58.71093750
C4/W6/L48 overlay net increase MiB = 17.78906250
C4/W6/L48 dual-pool total MiB = 99.63281250
FP32 recurrent state per layer/row MiB = 3.00000000
FP32 recurrent state all 48 layers/row MiB = 144.00000000
Amdahl example f=0.08,r=2 => speedup = 1.04166667
```

payload不含对齐/Graph/descriptor。双池新增为完整correction，不是overlay差额。两个kernel路径相同的state读写不被重复计算成新收益。具体说明见[成本推导](../research/04-cost-and-memory.md)。
