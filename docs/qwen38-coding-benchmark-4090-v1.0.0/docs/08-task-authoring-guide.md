# 08 · 新题编写规范

## 必需文件

```text
tasks/ID/
├── task.json
├── prompt.md
├── workspace/
├── hidden_tests/verify.py
├── hidden_tests/...
└── reference/...
```

## 题目质量门槛

- 原始 workspace 必须稳定失败；
- reference 必须稳定通过；
- 至少一个隐藏边界测试不是题面示例的机械复述；
- 不依赖网络和随机外部状态；
- 测试验证行为，不验证特定实现文本；
- 错误修复不得要求无关大重构；
- 题面足以推导 contract，但不泄漏答案位置；
- 参考实现仅代表一个可行解，不应通过字符串匹配判定补丁。

## 难度

1：直接边界；2：单文件多规则；3：需设计/定位；4：跨文件或复杂状态；5：并发、事务、安全、长上下文或高歧义工程任务。

## 防泄漏

执行器只复制 workspace。不要在公开 README、注释、文件名中出现“correct/fix/hidden answer”。`verify_release.py` 会扫描典型泄漏路径，但人工审查仍必须进行。
