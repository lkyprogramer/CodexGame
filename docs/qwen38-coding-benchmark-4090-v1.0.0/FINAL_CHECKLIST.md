# 发布与横评最终检查表

## 基准包

- [ ] `python3 scripts/verify_release.py` 退出码为 0
- [ ] 48 个参考实现全部通过
- [ ] 48 个原始工作区全部未通过隐藏验证
- [ ] Patch/Agent 端到端工具循环与 Review 只读工具测试通过
- [ ] 超时会终止判题进程组，无遗留 Java/Python 子进程
- [ ] `MANIFEST.sha256` 校验通过
- [ ] ZIP 可在全新目录解压并再次验证

## 环境

- [ ] GPU、驱动、CUDA、操作系统和 CPU/RAM 已记录
- [ ] llama.cpp/server commit 与完整启动参数已记录
- [ ] GGUF 文件 SHA-256、量化、template 和 mmproj/MTP 已记录
- [ ] power limit、上下文、KV 类型和 GPU offload 已固定

## 实验

- [ ] Normalized 与 Optimized 分开运行和分榜
- [ ] 运行顺序使用 Latin-square/随机区组
- [ ] 每模型完成相同 warm-up
- [ ] 主横评至少 3 Seeds，决赛至少 5 Seeds
- [ ] 无人工修补、续写或选择性重跑
- [ ] JSONL 无重复 `(task, seed)`；中断仅通过 `--resume` 补齐
- [ ] API 故障按预定义规则统一重跑

## 报告

- [ ] Hard Success、Partial、Balanced Index、Worst Category 同时报告
- [ ] 每类别、每题和失败类型可追溯
- [ ] 成功任务耗时与失败任务耗时分开
- [ ] Token/reasoning/timings/MTP 缺失时标为 N/A，不伪造 0
- [ ] Public test failure 未被误计为 invalid tool call
- [ ] 配对 Bootstrap、McNemar 和 Holm 修正已执行
- [ ] “最佳”结论通过质量门槛和最差类别保护
- [ ] 限制、污染风险和私有回放结果已披露
