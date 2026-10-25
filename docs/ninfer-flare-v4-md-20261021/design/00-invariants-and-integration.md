# 性能改造不可变边界

当前仅纯文本OpenAI Chat Completions性能；不新增协议、图像/决策/UI功能，不删除已有实现。公共schema/持久格式/缓存身份只有被选优化实际需要时才改，并保留旧格式拒绝与回退隔离。

使用同一个既有执行器、sampler、processor、RNG、许可和提交权威，不建立平行实现。当前P4研究树与完整资格分开。独立源码集成评审与必要构建针对同一集成候选，未改路径的证据直接复用；不为完整上游、35B、多协议或UI扩展验收。

[Target采样](08-target-sampling-and-baseline.md)、[生命周期](03-scratch-graphs-overlap.md)、[必要验收](05-validation-and-qualification.md)与[范围](09-chat-completions-only-scope.md)共同适用。保留所有历史失败、18处G1差异、C1附件缺口和未知值，不把候选资格当生产发布。
