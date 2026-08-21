# 15 · 常见问题与排查

## 1. `model.sha256 must be ...`

示例配置中的占位值没有替换：

```bash
python3 scripts/hash_model.py /absolute/path/model.gguf
```

把 64 位十六进制哈希和绝对路径写入 TOML。Suite 开始前只校验一次。

## 2. Endpoint 不接受 `reasoning_effort`

不同 llama.cpp/server 版本支持差异较大。三种处理方式只能选一种并创建独立 Config：

1. 升级到支持该字段的冻结版本；
2. 使用 endpoint 所需的等价 `extra_body` 非保留字段；
3. 把 `reasoning_effort` 设为空并在报告中说明由 Template/server 控制。

`extra_body` 不能覆盖 temperature、sampling、messages、tools、seed 等受控字段。

## 3. 模型不会调用工具

先检查：

- GGUF 内嵌 chat template 是否正确；
- server 是否启用 tool-call parser；
- 请求中的 `tools` 是否到达 endpoint；
- 原始响应是否把工具 JSON 当成普通文本；
- 模型原生 Template 与 common Template 是否兼容。

这属于模型/Template/Server 组合能力。不要手工把文本工具调用改造成真实调用后计分。可另用 `build_context_bundle.py` 做非标准单轮诊断，但不能混入标准榜。

## 4. Code Review 没有源码

标准 Runner 会给 Review 题 `list_files/read_file/search` 三个只读工具。若请求里没有，检查是否使用了本包的最新 Runner、`tool_mode=true` 且 tool budget 大于 0。

## 5. 已有结果文件导致报错

这是防重复机制：

```bash
qcb run ... --resume      # 跳过已有 task/seed
qcb run ... --overwrite   # 明确重建整份结果
```

不要把不同模型、Lane、Suite 或修改后的 Config 写进同一个 JSONL。

## 6. `endpoint_error`

查看：

- `final-response.txt`；
- `raw-responses.json`；
- server log；
- endpoint timeout；
- request body 中不支持的字段；
- 模型是否 OOM/崩溃。

只有基础设施错误可按预声明规则重跑；无 diff、错 JSON、tool budget 不是 infrastructure error。

## 7. OOM

记录发生阶段：load、prefill、decode。优先：

1. 确认桌面和其他进程占用；
2. 降低 context/KV；
3. 使用 Q4/IQ4 等较小量化；
4. 调整 batch/ubatch；
5. 关闭 MTP 对照；
6. 新建 Config，不能静默修改原 Config 后续跑。

Q6 权重能加载不代表适合多轮 Coding Agent。

## 8. Reasoning/Timings/MTP 全是 N/A

这表示 endpoint 未返回字段。检查 raw response 和 server telemetry。不要把 N/A 填 0，也不要仅凭 decode tok/s估算完整任务效率。

## 9. `patch_failed`

常见原因：路径前缀不对、上下文行与工作区不一致、输出了多个混杂 diff、模型先用工具修改后又输出基于旧文件的 patch。该失败属于模型行为，不人工修复。

## 10. 隐藏测试超时

Verifier 会终止整个判题进程组，避免 Java 子进程残留。审查 artifact 判断是补丁死锁/无限循环，还是宿主过载。前者计模型失败；后者按 infrastructure 规则处理。

## 11. 两模型无法比较

`compare_models.py` 要求：同 Lane、同 Suite、相同且唯一的 `(task, seed)` 集合。先检查 `--resume` 是否补齐，禁止仅取交集后宣称正式结论。

## 12. 排行榜结果与单项速度不一致

排行榜先执行 Hard/Worst/Invalid/完整配对质量门槛，再按 CBI 和效率排序。速度更快但质量回退的模型会被标为不合格，这是预期行为。
