# 机器、控制端与生产保护合同

## 1. 来源优先级

以下事实来自Claude实际巡检报告（2026-09-09文档，机器本地前一日晚间），并于2026-09-09由Claude只读SSH复核确认（完整表见`22-machine-verified-facts-and-revisions.md §2`）。启动任何实验时运行只读preflight，**observed与declared分列**，变化就重新锁定，不猜测。

| 项 | 已报事实 | 执行约束 |
|---|---|---|
| GPU | RTX4090、24564MiB、sm89 | 单卡互斥，不跑两套27B |
| CPU/总线 | Xeon Silver4216、16C32T、PCIe3 x16 | 不是Gen4；避免每轮搬完整KV |
| RAM |62.5GiB、可用约47GiB| Host cache、build、page cache总量一并看 |
| SSD |915GiB总、557GiB空闲|600GB不是硬盘标称总量；不默认全盘可用 |
| Driver/UMD |610.57.04/13.3|不升级，不把UMD当Toolkit |
| Toolkit |宿主12.3.107；本地Docker13.2 devel已有|编译使用已验证13.2 devel，记录image ID/digest |
| 系统 |Debian12、Python3.11.2、JDK17|辅助工具stdlib；GPU测试放容器 |
| Pi |**在Mac控制端**（`~/.nvm/versions/node/v22.19.0/bin/pi` v0.85.1），GPU主机无Pi|Pi、Java题与日志采集由Mac执行 |
| 网络 |GitHub/hf-mirror可达，HF主站不可达|在线先试，离线bundle备用 |
| 权限（2026-09-09已配置）|`/etc/sudoers.d/qwen38-extreme-lab`仅放行`systemctl stop/start openclaw-qwen38-ninfer.service`免密；hhtele在`docker`、`systemd-journal`组|remote_guard可直接`sudo -n`；不再申请任何扩权 |
| profiling |`RmProfilingAdminOnly=1`、`perf_event_paranoid=3`，均**不改**|ncu走`docker run --cap-add=SYS_ADMIN`（devel镜像自带ncu）；nsys仅CUDA trace |
| 空闲显存 |生产常驻22592MiB，free **1509MiB**|这是DFlash2显存账的起点（`22 §3`） |
| vLLM W4目录 |`~/qwen38-vllm/models/*`已`chown hhtele`，可逐shard哈希|仍是被recipe改写过的目录，只能作control，不是pristine oracle |

## 2. 不可更改的生产身份

- unit `openclaw-qwen38-ninfer.service`；container `ninfer-4090-prod`；image `ninfer-4090:44a2c6c`。同主机另有4个disabled的历史unit（executor、qwen36-mtp4-128k、qwen38-text、qwen38-work-64k），不动。
- 原生18030（127.0.0.1）、兼容18343、NGINX28343；模型名 `openclaw/Qwen3.8-27B-WORK`。生产健康以18343**和**18030的`/v1/models`同时返回该模型为准（unit可能在容器被绕过systemd删除后仍active）。
- artifact路径`/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer`，SHA见`configs/source-lock.json`。
- 生产保持262144容量、rk4v4-e8、MTP3、rolling-tool、preserve-thinking、medium、单并发及现有L1/L2，作为基线与回滚点。**候选profile的受保护容量是200192**（用户决策，`22 §1.1`），这不是生产配置的变更。
- 不改NGINX token，不重写已有模型，不删除旧镜像，不enable/disable任何unit。

## 3. 实验拓扑

```text
外部AI / Mac控制端（不能依赖本卡被停的NInfer）
 ├─ Pi + 原23文件Java夹具 + JDK17
 ├─ request采集 / ABBA编排 / 结果检查
 └─ SSH BatchMode + 显式GPU lease
           ↓
 hhtele@192.168.10.29
 ├─ 现网（维护窗口暂停，结束恢复）
 └─ 独立worktree + Docker候选18041 / oracle18042
```

Mac隧道使用新的本地18441/18442；同一卡上candidate/oracle仍串行，不因端口不同就同时加载。启动前验证端口空闲。隧道只绑定127.0.0.1，记录PID，由创建者结束；禁止`pkill -f ssh`、`pkill -f log_proxy`。

```bash
ssh -N -o BatchMode=yes -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
  -L 127.0.0.1:18441:127.0.0.1:18041 hhtele@192.168.10.29
```

## 4. 已有W4A16不能充当pristine oracle

`~/qwen38-vllm/models/Qwen3.8-27B-W4A16-AutoRound`已经被recipe改过（shard 6/7 有`.bak`/`.bak_embed`，`config.json.bak-*`，`model_extra_tensors.safetensors.bak-draft`）；HF revision元数据不代表实际shards未变。该目录2026-09-09已改为hhtele属主，T00可以逐shard哈希。vLLM只作为独立control，用该目录实测必须记录每shard和config的hash、HEAD/embedding/MTP精度。新实验不得原地prepare。若需pristine，在新目录重建并核验source SHA；`.bak`只有hash匹配才可用。

## 5. 工具前置

本包CPU脚本仅Python3标准库，不要求系统numpy/torch/cargo。原Java题需JDK17；Pi binary、Node22 PATH、Pi配置目录在`configs/local.example.json`显式设置。容器编译限`-j4`或按RAM观察调整，不能默认32线程把内存吃满。没有工具就BLOCKED，不自动安装到系统。
