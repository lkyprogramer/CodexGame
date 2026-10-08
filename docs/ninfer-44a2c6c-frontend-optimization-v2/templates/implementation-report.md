# B0+B1 实施总报告模板

## 结论状态

`NOT_RUN`。实施者根据证据更新，不能继承文档包辅助测试PASS。

## 版本与资源

完整pin/candidate SHA、overlaydiffhash、新旧image完整ID、六资源fullSHA、实际ReasoningEffort模板与preserve、编译器/CUDA/CPU/GPU、启动参数变化表。

## 产品变更

解释B0 earliest-ID等价；桶copy/move；B1分解与错误顺序；request-local统计；sharedtext/vision/count接线；证实B2/sharedcache/newCLI/模型变化没有混入。

## 测试结果

按G0–G7列状态与原始证据路径/hash。固定case、finitecut、fuzzseed/n、prepared/errors比较、mutation sanity、原CTest及skip原因。不能将SKIP汇成PASS。

## 性能

| 环境/lane | inputhash/resourcehash | 实际bytes/P/H/Q | 样本数 | p50/p90 | main/local工作量 | oracle来源 |
|---|---|---|---:|---|---|---|

CPU函数、HTTP首字、生产窗口分别列表。时间总和取逐条sum，不能用中位数拼接成真实单请求。估算与实测标签分开。

## 发布与回滚

授权依据、实际执行时间、新旧服务状态、回滚smoke、恢复流量结果；未发布写READY_NOT_DEPLOYED。没有生产shadow。full_reset只报告另案线索，不把未经验证的缓存调整计成tokenizer收益。

## 后续决定

B2是否满足12文档的重评条件；不满足则DEFERRED并结束首期。完整未验证项与风险列表，不将预测1秒首字写成保证。
