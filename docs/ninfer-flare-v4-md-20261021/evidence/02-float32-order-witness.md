> TECHNICAL_REFERENCE_ONLY：以下固定源码/计算/旧论证保留，原先的“当前”时态或阶段要求不再调度任务。当前身份见[证据](../research/05-completed-baseline-and-current-state.md)，执行以[根注册表](../plans/02-task-registry.md)为准。原始字节另保存在本轮403份快照。

# 实际CPU算术示例：实数等式不保证float32逐bit相同

2026-10-21，本次在Python/NumPy执行固定seed=20261021的4维示例，逐项float32乘加、不模拟CUDA FMA或warp reduction。此实验仅证明运算顺序可影响bits，**不是NInfer/Flare kernel错误复现，也不是GPU资格测试**。

计算A为alpha乘已完成float32点积；B为先在float32缩放state再点积。结果：

```json
{
  "alpha": 0.4271239936351776,
  "s": [
    1.3229047060012817,
    0.4820908308029175,
    1.301340937614441,
    -0.9972568154335022
  ],
  "k": [
    -0.01707368530333042,
    0.6243042945861816,
    0.797197699546814,
    3.1066040992736816
  ],
  "scale_after_dot": -0.761250913143158,
  "scale_before_dot": -0.7612509727478027,
  "after_bits": "0xbf42e157",
  "before_bits": "0xbf42e158"
}
```

因此，V4必须从NInfer当前计算点输出真实correction，不能把Flare源码的实数等价表达式直接替换。GPU bit等价仍需按K1计划测试；此示例不替代任何CUDA验证。
