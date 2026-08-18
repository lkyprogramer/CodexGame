# S7 恢复与部署落点

| 项 | 结果 |
|---|---|
| `openclaw-qwen36-mtp4-128k.service` | active + enabled |
| `127.0.0.1:18343/v1/models` | 200 |
| `127.0.0.1:28343/v1/models` 无 token | 401 |
| `28343` 配置 token | 200 |
| 19343 上 llama-server | 无残留测试服务 |
| GPU | 约 22078 MiB，现网 3.6 128K |
| NGINX / 3.6 ExecStart | **未改** |

旁路单元（已安装、**disabled / inactive**）：

```text
/etc/systemd/system/openclaw-qwen38-work-64k.service
Conflicts=openclaw-qwen36-mtp4-128k.service
ExecStart=/home/hhtele/qwen38-27b-4090-20260818/launch/work-balanced.sh
监听 127.0.0.1:19343
```

单卡不能同时跑 3.6 和 3.8。启用旁路的正确顺序：

```bash
sudo systemctl stop openclaw-qwen36-mtp4-128k.service
sudo systemctl start openclaw-qwen38-work-64k.service
# 用完
sudo systemctl stop openclaw-qwen38-work-64k.service
sudo systemctl start openclaw-qwen36-mtp4-128k.service
```

不要 `enable` 3.8 单元，否则开机可能和 3.6 抢卡。
