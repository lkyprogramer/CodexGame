> 历史实验规范与记录。后续探索的当前阶段见 [NEXT_ACTIONS](../plans/NEXT_ACTIONS.md)；本文原口径用于解释原报告，不覆盖 frontier 新阶段合同。

# 每项 Review 与交付模板

## 源码Review

- 是否基于固定main，是否保留新的declared_only、预算、取消、NaN等已有修复？
- diff中是否夹带旧主线、另一个PR或不必要的格式化？
- gate是否默认关闭，off是否完整回到A0？是否明确报告fallback原因？
- buffer谁拥有，异步DMA谁等待，graph capture地址是否保持，错误时谁释放？
- cache命中验证是否包含模型、tokenizer、位置、KV格式、递推状态、draft状态与配置身份？
- 与其他同类PR的重叠是否已显式说明？

## 实测Review

检查raw JSONL与日志，不只看报告均值。确认短输出不是质量退化；检查prefill复用是否造成虚假tps；检查CPU/PCIe份额、expert slots和MTP接受率是否变化导致归因错误。每个明显离群点都保留且解释，不能删除再计算。

## DECISION.md

```text
PR / base SHA / candidate SHA / feature head:
实际模型与硬件:
机制适用性:
实现差量与未实现部分:
A0/A1/B配置差异:
CPU测试、CUDA测试、未测试项:
主指标与CI:
质量/工具授权/Java结果:
内存/显存/稳定性:
已知负收益与边界:
结论: ADOPT_CANDIDATE | NO_BENEFIT | NOT_APPLICABLE | BLOCKED | REGRESSION
回退方式:
下一步留出验证:
```

源码补丁使用base到candidate的最小diff另存，不能把参考head整包当作最终补丁。最终建议必须附可重放命令、配置和原始结果目录。
