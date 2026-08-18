# Qwen3.8-27B RTX 4090 最终对比结论

## 最终决策：推荐灰度，不立即替换

本轮保留 18 个 lane、106 个独立 case 报告；每个 case 均包含 request/response/result、GPU CSV、服务日志和人工格式/质量评分。

## 依据

### 下载与构建

- 4090 通过 `hf-mirror.com` 成功下载 Q4 XL，`17,923,394,624` bytes，SHA256 `bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372`，平均约 26MiB/s。
- llama.cpp 使用本机下载 ZIP 的固定 commit `4df29be4f4c3673f428170fda944a5b19f743bb8`，通过 SCP 传输，4090 未访问 GitHub；CUDA 12.3、架构 89、Release 构建成功。

### 性能

- no-spec 长输出约 44.6 tok/s。
- MTP `n=4,p-min=.75` 长输出约 75.8 tok/s，约为 no-spec 的 1.70x；`n=2,p-min=0` 约 85.4 tok/s，约 1.91x，但 acceptance 较低，不作为默认。
- 真实三轮 agent trace：工具调用、工具结果回灌、JSON 诊断和 patch review 均成功；工具首轮 decode 约 90.9 tok/s。
- prompt cache：8K 前缀 exact warm 的 prompt 时间约降低 20x，连续重复 5 次稳定；增量和相似 prompt 的复用范围符合预期。

### 质量与协议风险

- `enable_thinking=false` 后 short/strict JSON 通过；若保持 `reasoning auto` 默认，首轮短请求可能正文为空，这是部署硬门禁。
- matrix patch review 多数带 markdown fence，严格 JSON 失败；agent trace 的 patch review 通过，说明提示词/历史形状敏感。OpenClaw 灰度必须启用 response schema/grammar、fence 清理或失败重试，并记录失败样例。
- reasoning low/xhigh 能区分 reasoning_content/content，但 xhigh 不应成为默认。

### 显存与长上下文

- 64K MTP n=2 q8 KV 约 20.6GB，适合作为首个灰度配置。
- 96K 约 22.1GB，需监控；112K 约 22.7GB。
- 124.8K 实际 prompt、131K ctx 峰值 `23,552 MiB`，仅剩约 665MiB，超过 `23,500 MiB` 生产门禁；128K 只能作为极限实验，不建议默认上线。

## 推荐灰度配置

```text
Qwen3.8-27B-UD-Q4_K_XL.gguf
ctx-size=65536
np=1
fa=on
ctk/ctv=q8_0
spec-type=draft-mtp
spec-draft-n-max=4
spec-draft-p-min=0.75
spec-draft-ngl=99
enable_thinking=false
cache-prompt=true
cache-ram=2048
cache-reuse=256
slot-prompt-similarity=0.10
```

首轮灰度建议保留 Qwen3.6 18343 生产服务作为回滚，Qwen3.8 只在独立端口或少量 OpenClaw 请求上运行；不自动改 systemd/NGINX。

## 回滚与恢复

本轮没有切换生产 launcher。最终验证：`openclaw-qwen36-mtp4-128k.service` 为 `active + enabled`，18343 返回 200，28343 无 token 为 401、正确 token 为 200，19343 无残留测试进程。

## 报告索引

- [00-preflight-production-baseline.md](00-preflight-production-baseline.md)
- [01-model-download-hf-mirror.md](01-model-download-hf-mirror.md)
- [02-llama-cpp-zip-build.md](02-llama-cpp-zip-build.md)
- [03-qwen38-smoke-32k.md](03-qwen38-smoke-32k.md)
- [03a-qwen38-initial-reasoning-failure.md](03a-qwen38-initial-reasoning-failure.md)
- [04-mtp-32k-matrix.md](04-mtp-32k-matrix.md)
- [05-openclaw-agent-trace.md](05-openclaw-agent-trace.md)
- [06-prompt-cache-cold-warm.md](06-prompt-cache-cold-warm.md)
- [07-long-context-limit.md](07-long-context-limit.md)
- [08-reasoning-profiles.md](08-reasoning-profiles.md)
- [09-qwen36-vs-qwen38-comparison.md](09-qwen36-vs-qwen38-comparison.md)
