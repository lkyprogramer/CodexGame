# Case 00: 环境与生产基线

## 结论

测试前生产服务为 `active + enabled`，直接接口返回 200；测试窗口由 wrapper 停止服务，所有已执行 lane 完成后恢复。最终恢复验证为 `active + enabled`，18343 返回 200，28343 无 token 返回 401、配置 token 返回 200，未残留 19343 测试进程。

## 关键证据

- 4090、driver、显存、功耗上限和 `/data` 磁盘：`raw/remote/qwen38-27b-4090-20260817/logs/production-preflight.txt`
- 生产服务恢复与端口鉴权：`raw/remote/qwen38-27b-4090-20260817/logs/production-restore-verification-final.txt`
- 生产 baseline 请求：`raw/remote/qwen38-27b-4090-20260817/raw/baseline-production-qwen36-smoke`、`raw/remote/qwen38-27b-4090-20260817/raw/baseline-production-qwen36-agent`

```text
timestamp=2026-08-16T22:43:14-04:00
active
enabled
# /etc/systemd/system/openclaw-qwen36-mtp4-128k.service
[Unit]
Description=OpenClaw Qwen3.6 27B MTP4 128K on llama.cpp
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=hhtele
WorkingDirectory=/home/hhtele/llama.cpp-mtp-unsloth-20260513
ExecStart=/opt/llama.cpp/run-openclaw-qwen36-mtp4-128k.sh
Restart=always
RestartSec=5
StandardOutput=append:/var/log/llama/openclaw-qwen36-mtp4-128k.log
StandardError=append:/var/log/llama/openclaw-qwen36-mtp4-128k.err.log
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
--- processes ---
1652110 bash -c set -o pipefail; cd /home/hhtele/llama.cpp-qwen38-20260817; cmake -S . -B build -DBUILD_SHARED_LIBS=OFF -DLLAMA_BUILD_UI=OFF -DLLAMA_BUILD_WEBUI=OFF -DGGML_CUDA=ON -DGGML_CUDA_FA=ON -DGGML_CUDA_GRAPHS=ON -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc -DCMAKE_CUDA_ARCHITECTURES=89 -DCMAKE_BUILD_TYPE=Release 2>&1 | tee /home/hhtele/qwen38-27b-4090-20260817/logs/llama-cmake-reconfigure.log; cmake --build build --config Release -j"$(nproc)" --target llama-server llama-cli llama-bench 2>&1 | tee /home/hhtele/qwen38-27b-4090-20260817/logs/llama-build-final.log; echo BUILD_FINAL_RC=${PIPESTATUS[0]}
1652140 cmake --build build --config Release -j32 --target llama-server llama-cli llama-bench
1652143 /usr/bin/gmake -f Makefile -j32 llama-server llama-cli llama-bench
1652145 /usr/bin/gmake -s -f CMakeFiles/Makefile2 llama-server
1652148 /usr/bin/gmake -s -f CMakeFiles/Makefile2 tools/server/CMakeFiles/llama-server.dir/all
1653455 bash -c set -o pipefail; ROOT=/home/hhtele/qwen38-27b-4090-20260817; { echo "timestamp=$(date -Is)"; systemctl is-active openclaw-qwen36-mtp4-128k.service; systemctl is-enabled openclaw-qwen36-mtp4-128k.service; systemctl cat ope
```

## 生产 baseline 人工评分

| lane/case | format | quality | auto checks |
|---|---:|---:|---|
| `baseline-production-qwen36-smoke/short_ok` | 5 | 5 | exact_ok=True |
| `baseline-production-qwen36-smoke/strict_json` | 5 | 5 | json_valid=True |
| `baseline-production-qwen36-agent/agent_safety` | 3 | 4 | contains_ok=True, markdown_fence=True |
| `baseline-production-qwen36-agent/json_tool_plan` | 5 | 5 | json_valid=True |
| `baseline-production-qwen36-agent/patch_output` | 3 | 4 | contains_ok=True, markdown_fence=True |
| `baseline-production-qwen36-agent/patch_review` | 3 | 3 | markdown_fence=True |

恢复证据摘要：

```text
timestamp=2026-08-16T23:10:56-04:00
active=active
enabled=enabled
direct_models_http=200
nginx_no_token_http=401
nginx_configured_token_http=200
test_19343_processes=
ocr_processes=
21866, 2351, 0, 8.37, 47

```
