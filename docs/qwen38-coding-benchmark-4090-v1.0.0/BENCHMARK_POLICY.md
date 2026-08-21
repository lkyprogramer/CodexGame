# 基准治理与实验纪律

## 冻结规则

- 发布版本内的题面、隐藏测试、参考实现、权重和 Suite 不得修改。
- 任何修正必须提升版本号，并在 CHANGELOG 记录受影响题目。
- 同一横评报告只能使用同一个基准版本。

## 数据隔离

待测模型只允许看到：题面、工作区、公开测试输出和受限工具结果。禁止把 `hidden_tests/`、`reference/`、Rubric、历史答案或其他模型补丁放进上下文。执行器只复制 `workspace/` 到临时目录。

## 可比性

Normalized 赛道必须固定：

- 同一 GGUF 精度档，或明确报告无法对齐；
- 同一 server commit/build；
- 同一 system prompt 与 tool schema；标准 Suite 固定 tool mode，Review 只读；
- 同一 reasoning effort；
- 同一 sampling 与 max tokens；
- 同一上下文上限和 KV 类型；
- MTP 关闭；`extra_body` 不得覆盖受控 sampling/messages/tools/seed 字段；
- 同一题目、Seed、超时和 tool budget。

Optimized 赛道允许模型特定配置，但必须逐项披露。不能用 Optimized 结果证明某个 finetune 权重本身更强。

## 运行纪律

- 固定 GPU power limit、风扇/散热条件和后台负载；
- 每个模型执行相同 warm-up；
- 使用 Latin-square 或随机区组轮换模型顺序；
- 任务间不共享对话和 KV cache；
- 不手工补救模型输出；失败就是失败；
- API/服务器异常与模型无效输出分开统计；公开测试失败与非法工具调用分开统计；
- 至少 3 Seeds 才做主排名，5 Seeds 用于决赛；已有 JSONL 默认拒绝追加，续跑仅用 `--resume` 补缺失键。

## 报告纪律

- 不用单个平均分掩盖最差类别；
- 不以 tok/s 抵消明显质量回退；
- 不把作者自报 benchmark 当作本地结果；
- 不把 Template-only 变体描述为新模型；
- 不把目录字节数表述成精确 token；
- 所有“更优”结论必须说明效应量、区间、非劣性和限制。
