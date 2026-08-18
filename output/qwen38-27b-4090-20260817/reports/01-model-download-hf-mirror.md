# Case 01: hf-mirror 模型下载

## 结果

- 仓库：`unsloth/Qwen3.8-27B-GGUF`
- 文件：`Qwen3.8-27B-UD-Q4_K_XL.gguf`
- 镜像：`https://hf-mirror.com/`
- mirror commit：`f1bfb127c64f7072bdd2cad55f258b9c8b2910fe`
- Range：支持，`x-linked-size=17923394624`
- 文件大小：`17923394624` bytes
- SHA256：`bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372`（与 mirror `x-linked-etag` 一致）
- 下载时间：`2026-08-16T22:19:24-04:00` 至 `2026-08-16T22:30:12-04:00`
- aria2 平均速度：`26 MiB/s`
- 断点续传：本次无中断，使用 `-c -x 8 -s 8`

## 证据

- Range/环境响应：`raw/remote/qwen38-27b-4090-20260817/logs/model-download-preflight.log`
- aria2 完整记录：`raw/remote/qwen38-27b-4090-20260817/logs/model-download-aria2.log`
- 速度与结束状态：`raw/remote/qwen38-27b-4090-20260817/logs/model-download-meta.log`
- SHA256：`raw/remote/qwen38-27b-4090-20260817/logs/model.sha256`

## 结论

4090 可直接通过 hf-mirror 下载，未访问 Hugging Face 原站；模型大小和校验值符合预期，可用于后续测试。
