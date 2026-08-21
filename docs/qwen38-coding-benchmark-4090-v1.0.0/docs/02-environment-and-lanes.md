# 02 · 环境与赛道

## Normalized 赛道

建议固定：Q4_K_M 或其他共同可用档、32K context、相同 KV 类型、MTP off、medium reasoning、temperature 0、同一 template contract。若某个模型只在自定义 template 下正常，可同时跑：

1. `normalized-common-template`：测可迁移权重行为；
2. `normalized-native-template`：测权重+必要模板；

但两者必须单列。

## Optimized 赛道

允许：作者推荐 template、medium/low/xhigh、MTP、coding-aware imatrix、IQ4/Q5、不同 context/KV。每个组合视为独立 deployable system：

```text
model weights + GGUF quant + template + server build + startup flags + request parameters
```

## 4090 记录项

- GPU 型号与显存；
- 驱动、CUDA runtime；
- CPU、RAM、操作系统；
- GPU power limit、温度区间；
- model offload 层数；
- context、batch/ubatch、KV 类型；
- flash attention；
- MTP/speculative 参数及 acceptance（若后端暴露）；
- llama.cpp/server commit 和构建选项。

## 长仓库档说明

`LC001..LC004` 的 `context_band` 是检索压力标签，不是 tokenizer 精确值。默认 Agent 工具只把读取内容放入对话；最终 prompt token 应以端点 usage 或服务日志为准。若要做“全文预填充”专项，使用 `scripts/build_context_bundle.py` 生成确定性拼接文件，并单独报告。


## 标准工具模式

正式 Suite 固定 `tool_mode=true`。Patch/Agent 使用受限读写/公开测试工具，Code Review 只使用读取与搜索工具。模型不支持 tool calling 时，这本身是 Coding Agent 兼容性结果。全文拼接只能作为独立非标准诊断，不能混入主榜。

Normalized 配置还禁止通过 `extra_body` 覆盖 sampling、seed、messages、tools 等受控字段；MTP 必须关闭。
