# 机器、环境与生产隔离

## 已确认与待测事实

| 信息 | 来源 | 处理 |
|---|---|---|
| Driver/KMD610.57.04、CUDA UMD13.3 | 用户最新消息 | 当前基线，不再使用545驱动假设 |
| 4090 24GB、RAM64GB、SSD600GB | 用户 | 容量上限，空闲量仍需实测 |
| Debian12、Docker、现网NInfer路径 | 用户部署报告[S00] | 先只读核对，再执行 |
| Toolkit/nvcc/cuBLAS版本 | 尚无最新运行输出 | 用预检确认，不能从nvidia-smi推导 |
| GPU UUID、PCIe链路、功耗、温度 | 需本机测量 | 纳入每次基准证据 |

当前610驱动并不意味着需要安装13.3 Toolkit。Kern固化 CUDA13.0 API，参考vLLM环境使用13.0用户态；可选择固定13.0.1开发容器，保留宿主既有Toolkit。新驱动兼容旧CUDA应用的一般规则适用，但最终以设备探针和实际二进制为准。[S03][S06]

## 只读检查

```bash
bash scripts/preflight.sh
nvidia-smi
nvcc --version
systemctl is-active openclaw-qwen38-ninfer.service
docker image inspect ninfer-4090:44a2c6c --format '{{.Id}}'
```

不要打印 `docker inspect` 完整环境或 nginx配置，可能包含鉴权信息。不要将密码写进变量、脚本、日志。无需额外安装 `cuda-compat`，尤其不要用旧 compat 库覆盖宿主610提供的 libcuda。[S06]

## 生产白名单

生产 unit：`openclaw-qwen38-ninfer.service`。
保护端口：18030、18343、28343。candidate/oracle 只用18041/18042，默认 loopback。
保护模型：`/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer`。
SHA：`eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`。

不得复制“latest”覆盖现有模型；不得启用WORK/TEXT unit作为评测结束后的自动恢复目标。当前默认是NInfer，回退WORK是另一项用户操作。[S00]

## 维护窗口

```bash
python3 scripts/guard_gpu.py --allow-production-pause --timeout 3600 -- \
  bash work/commands/run_candidate_checks.sh
```

此脚本只停止白名单服务，只在它原来 active 时恢复。它不会杀未知GPU进程。若停止后仍有进程占卡，退出并恢复生产。GPU0的文件锁只能约束本套工具，不能阻止别人的程序，因此仍检查 `nvidia-smi`。

必须让 candidate 以前台进程运行，容器用 `--rm --init`；禁止 detached daemon。任务内也必须注册自己的后台子进程清理。若 guard 被SIGKILL/机器掉电，读取 `.state/gpu-lease.json`，确认guard/child已结束，再人工 `sudo systemctl start openclaw-qwen38-ninfer.service` 并检查18343。finally/trap不可能覆盖断电。

评测模型进程用普通用户。测试Pi最好放在只挂载其工作目录的容器中；哈希保护测试文件是评测完整性措施，不是操作系统沙箱。


### 容器退出与恢复边界

前台`docker run`客户端被杀不构成“容器一定已退出”的证明。T22的candidate supervisor必须使用唯一名称和`kern-poc-run=<run_id>` label记录自己创建的容器；finally中按名称+label核对后执行`docker stop --time 10`，再等待该容器退出/移除。禁止处理标签或owner不匹配的容器。原始PID/容器ID写进run日志；回到生产前确认本次候选不再占GPU。不能以`--rm`替代这个生命周期测试。


若上次journal仍标记`restore_required=true`，下一次guard会拒绝覆盖它。先确认旧guard/候选进程已经退出，恢复并验证NInfer，再归档该journal；不要删除它来绕过一次尚未完成的恢复。
