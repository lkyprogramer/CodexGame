# Luce DFlash Qwen3.6-27B 4090 部署验证报告

## 结论

DFlash 加速链路已经验证成立。README `4a` 的 `scripts/run.py` one-shot streaming generate 已验证成功；但当前验证版 OpenAI-compatible API server 不能直接替换线上服务。

- Qwen3.6 Q4_K_M + Qwen3.5 DFlash draft 在 HumanEval 10 prompt 上平均 `72.95 tok/s`。
- Qwen3.6 Q5_K_XL llama-server baseline 同组平均 `30.50 tok/s`。
- DFlash 相对 Q5 baseline 约 `2.39x`。
- README 预期 Qwen3.6 Q4_K_M DFlash 约 `60-80 tok/s`，本机结果落在预期区间。
- `scripts/run.py --prompt ...` 的 CLI token streaming 可用。
- `/v1/models` 可用，但 `scripts/server.py` 的 OpenAI-compatible chat 非流式返回空正文，SSE streaming 触发 `BrokenPipeError`，API 层不满足上线替换条件。

## 文件与校验

- Target: `/data/models/qwen/Qwen3.6-27B-Q4_K_M.gguf`
  - sha256: `5ed60d0af4650a854b1755bd392f9aef4872643dc25a254bc68043fa638392a0`
- Draft: `/data/models/qwen/dflash-draft/model.safetensors`
  - sha256: `1e44cae31ebda1940da56318c129509df468a1a6508a8f816a03e0c5c8661b77`

## 构建

- 部署目录：`/home/hhtele/lucebox-hub-dflash-qwen36/dflash`
- CUDA: 12.3
- GPU arch: `sm_89`
- 构建目标：`smoke_load_target`、`smoke_load_draft`、`test_generate`、`test_dflash`
- 构建状态：成功

## Smoke

- `smoke_load_target`: 成功，target 加载约 `14.99 GiB` GPU，tok_embd CPU-only。
- `smoke_load_draft`: 成功，draft 加载约 `3.22 GiB`。
- README `4a` one-shot streaming generate：成功。使用本地 tokenizer 后，`scripts/run.py --prompt "def fibonacci(n):"` 路径可边生成边向 stdout 输出 token。
- 短生成：64 tokens，`49.90 tok/s`。

## HumanEval 性能

| Path | Quant | Engine | Mean tok/s | Notes |
|---|---:|---|---:|---|
| Qwen3.6-27B Q4_K_M + DFlash draft | Q4_K_M + safetensors draft | Luce DFlash | 72.95 | accept `32.6%`, avg commit `5.22` |
| Qwen3.6-27B Q5_K_XL | UD-Q5_K_XL | llama-server | 30.50 | no `<think>` pollution |

## API Smoke

- `GET /v1/models`: 成功。
- non-streaming `/v1/chat/completions`: HTTP 200，但返回空正文。
- streaming `/v1/chat/completions`: 未收到 chunk，server log 记录 `BrokenPipeError`。

判断：README `4a` 的 CLI streaming generate 是可用的；这里失败的是 `scripts/server.py` 的 OpenAI-compatible HTTP/SSE 包装层。API server 只能作为验证用途，不能直接作为线上 OpenAI-compatible 服务替换。

## 恢复与清理

- GCP 中转大文件已删除，释放：Q4 GGUF `16817244384` bytes，draft `3460432504` bytes。
- 当前默认服务已恢复并返回别名：`hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M`。

## 后续建议

1. 进入 coding/agentic 质量评测前，先修 DFlash API server 的正文输出与 streaming BrokenPipe。
2. 性能评估可继续使用当前 DFlash 二进制路径，不建议现在切换线上默认服务。
3. token 已用于中转上传，建议在 ModelScope 侧轮换或撤销。
