# 文本档运维

## 当前状态（部署结束时）

- **活着的是 WORK**：`openclaw/Qwen3.8-27B-WORK`，112128 ctx。
- TEXT unit **installed + disabled**，不随开机。
- NGINX 28343 未改。

## 切换

```bash
# → TEXT
sudo systemctl stop openclaw-qwen38-work-64k.service
sudo systemctl start openclaw-qwen38-text.service

# → WORK
sudo systemctl stop openclaw-qwen38-text.service
sudo systemctl start openclaw-qwen38-work-64k.service
```

确认：

```bash
curl -sS http://127.0.0.1:18343/v1/models
# TEXT: id=openclaw/Qwen3.8-27B-TEXT  n_ctx=170240
# WORK: id=openclaw/Qwen3.8-27B-WORK  n_ctx=112128
```

调用仍走 `http://192.168.10.29:28343/v1`（Bearer）或本机 18343。`model` 字段改成当前 alias。

## 路径

```text
模型  /data/models/qwen/qwen38-hauhau/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf
脚本  /home/hhtele/qwen38-hauhau-text-20260820/launch/production-text-18343.sh
unit  /etc/systemd/system/openclaw-qwen38-text.service
日志  /var/log/llama/openclaw-qwen38-text.log
     /var/log/llama/openclaw-qwen38-text.err.log
二进制 与 WORK 相同 llama.cpp-qwen38-20260817
```

## 启动要点

- `-c 170000`，`-ctk/-ctv q4_0`
- MTP `n-max 2`，无 p-min，无 mmproj
- 默认 `enable_thinking=false`，presence 1.5
- 单次请求仍可打开思考

不要双开。不要 `enable` TEXT 除非你改开机默认。
