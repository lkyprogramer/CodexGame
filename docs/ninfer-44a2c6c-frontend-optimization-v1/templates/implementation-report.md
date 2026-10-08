# NInfer Frontend Tokenization implementation report

## 1. 发布结论
明确RELEASE / DO_NOT_RELEASE / CPU_ONLY，并说明未通过或未运行Gate。

## 2. 身份
base SHA、overlay SHA、candidate SHA、构建镜像digest、运行镜像digest、artifact SHA、六资源SHA、CPU/GPU/工具链、mode及采样。

## 3. 源码原因与改动
分别说明边界重复编码、一次主编码/局部边界、跨请求cache。声明没有改动的模型/GPU/协议范围。

## 4. 正确性
synthetic/real-resource/metadata/errors/并发/媒体fallback样本量；所有mismatch和skip。独立oracle如何构建。

## 5. 性能
legacy/B1/B2逐对指标、work放大量、long-warm独立统计、短请求无回归、剩余耗时。不得拼接不同p50或引用其他硬件headline。

## 6. 4090与实际Agent
HTTP首个非空delta、GPUcache/计算token、decode、taskverify、request_error、回滚演练。

## 7. 限制和后续
哪些输入fallback，哪些实际数据未取得，是否值得默认启用B2。不要把预测写成实测。
