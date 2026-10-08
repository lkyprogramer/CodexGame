# 数值正确性：避免“文本一样才正确”和“文本连贯就正确”两个错误

## Reference hierarchy

A0：同一个已冻结W4A16 checkpoint、同source precision和模板的4090 oracle。
A1：新Kern eager/no-spec。
A2：同Kern graph/no-spec。
NInfer：产品质量/速度比较组，不是这个量化provider的逐tensor真值。[S00][S05]

先用A0重复两次建立本身的噪声/确定性基线。A1/A2强制喂**相同token轨迹**，即teacher forcing；不能比较自由生成已经分叉后的activations。

## 分层门槛（工程起点，不是已证明的模型误差定理）

| 对象 | 初始门槛 | 解释 |
|---|---|---|
| repack/scale/index与重排后权重 | bytes exact | 不能放宽packing错误 |
| 完全相同elementwise内核/schedule | bytes exact | 若更改算术，另立variant |
| 相同FP32 GDN数学路径 | atol2e-7、rtol1e-4；长轨迹另看漂移 | 逐layer、selected checkpoint比较 |
| W4 GEMM BF16输出 | atol0.002、rtol0.002，记录RRMS/max error | shape-specific容差须先用oracle重复与CPU小参考校准 |
| logits | 无NaN/Inf；teacher-forced至少512位置；报告max error、RRMS、KL、top1及margin | 不用单一自由生成字符串代替 |
| eager vs graph，同shape/chunk/kernel | bit exact为默认门 | graph不应改变运算，只改变提交方式 |

容差写进run profile并签名。自动AI不得“试到PASS”为止不断放宽。若固定路径仍不相同，第一步定位第一个不同Op和完整state，而非修改最终答案。

## near-tie处理

记录reference top1/top2 margin与当步最大logit误差e。margin≤2e的step可以解释argmax翻转，但不能自动豁免整次运行：检查误差本身、near-tie比例、未近平局位置的一致率，并做Java/retrieval回归。将reference与candidate都严重错误的logits称作“near-tie”是不可接受的。[S02]

## 现成比较工具

```bash
python3 -m poc_tools.numeric_check --reference work/oracle/layer.npz \
  --candidate work/candidate/layer.npz --out results/layer-check.json
python3 -m poc_tools.numeric_check --reference work/eager/state.npz \
  --candidate work/graph/state.npz --exact --out results/graph-state.json
```

工具比较NPZ中的同名数组，拒绝pickle、shape不同与非有限值。生成这些真实GPU数组的exporter由T03/T11实现；本包没有虚构oracle数组。

## 内存限制

不要每个cut拷贝所有128个GDN slot。只读当前租约的有效slot、选定层/时刻；单比较批≤512MiB，分片写盘、及时释放。全vocab logits按64–128 step分片，不一次保留长序列全量logits。原始BF16 27B整体上卡不是本机oracle方案。
