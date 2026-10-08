# 07 资源预算、实验隔离与生产保护

## 1. 固定资源与执行目录

默认实验根由 `LAB_ROOT` 指定，必须不位于生产源码目录、模型目录、systemd/NGINX目录或用户生产cache。根下：

```text
LAB_ROOT/
  source-baseline/       # 44a2c6c的独立只读基线副本
  source-candidate/      # 新分支开发副本
  ced-research/          # 导出数据的训练/评估工具，不进入runtime
  build-baseline/
  build-candidate/
  data/                 # 只保存自有Teacher样本
  predictors/
  runs/P0/ ... runs/P8/
  cache/                # 单独实验namespace
  maintenance.json      # 非secret的恢复记录
```

单卡只允许一个GPU工作进程集合。native与candidate端口分别18042和18041，均loopback；需复现兼容层时用临时18045/18044，不占生产18030/18343/28343。数据owner-only，权重bind mount只读。

如果机器不能直接GitHub，使用已存在的本地源码只读clone/bundle到实验根；固定SHA检查。不能因网络不可达就擅自更换镜像或下载另一个模型。

## 2. 预检只读命令

```bash
nvidia-smi --query-gpu=name,uuid,driver_version,memory.total,memory.used,temperature.gpu,power.limit --format=csv
systemctl is-active openclaw-qwen38-ninfer.service
systemctl is-enabled openclaw-qwen38-ninfer.service
docker image inspect ninfer-4090:44a2c6c --format '{{.Id}}'
stat --format='%s %Y' /data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer
free -m
df -h
```

SHA全文件扫描每个维护批次至多一次并缓存受信metadata；不能每次请求读17GiB文件。不要输出docker完整Env、NGINX配置、secret header、sudo/SSH密码。

CMake必须在验证的CUDA13.2开发容器内调用，不能误用宿主12.3；记录容器image ID和nvcc版本。GPU驱动API最大版本不是nvcc版本。[S02][U01]

## 3. 显存预算

已有22594MiB idle使用量只剩1970MiB。必须为可变workspace、运行峰值和系统波动留≥512MiB余量。

| 新开销 | v1设计预算 |
|---|---:|
| Predictor BF16 weights | ≤512MiB，目标<256MiB |
| StateOnly新增scratch | ≤256MiB |
| Predictor中间激活/输出 | ≤128MiB，按head/block流式消费 |
| MTP合成额外staging | ≤128MiB，尽量复用既有buffer |
| 新增steady+peak总量 | 建议≤1024MiB；最终以实测峰值为准 |

禁止一次输出所有late层×2048token的完整张量；CED16这种输出 alone 约数百MiB。禁止常驻整个200K的h_split与h_final；chunk消费并释放。原模型所有weights与KV/GDN仍必须保留。

不满足262144 native capacity与≥512MiB余量时，不得静默把context减半。可在报告中提出实验性小窗口结果，但P8要标记“不满足原部署容量目标”，不能发布为原服务的替代。

## 4. 磁盘/内存/训练预算

默认Teacher数据128GiB、checkpoints8GiB、logs8GiB；至少剩余max(64GiB,初始可用量20%)。Host cache沿用默认16GiB，但训练和Teacher导出分时，不与多份L2图像争用RAM。RAM余量低于8GiB或发生持续swap时停止该轮。

Predictor rank/label上限见04。不存在“全部在4090上联合蒸馏27B”的隐藏需求。

## 5. 维护保护任务的正确行为

P0需要实现一个guard，默认dry-run；只有明确授权才允许暂停 `openclaw-qwen38-ninfer.service`。guard记录进入前active/enabled状态，不改变enable状态，不擅自启用旧WORK/TEXT。

1. 先验证实验命令、路径、资源、工具权限；拿独占lock。
2. 原子写maintenance记录（unit、原状态、时间、lab run id）。
3. 原unit active且获授权才stop；确认退出及GPU释放；不kill不明GPU进程。
4. 启动外部watchdog，再运行实验；SIGINT/SIGTERM/实验超时都触发收尾。
5. 只停止属于当前run的实验进程/容器，恢复原active状态，检查health与原model id，再释放lock。
6. 无root权限、unit恢复失败、GPU没有释放则明确失败。不能把sudo密码保存到脚本。

shell trap不能保证SIGKILL/机器掉电恢复。单独watchdog必须测试parent death；整机重启后通过原unit策略与maintenance记录检查恢复，不能宣称绝对保证。没有可靠恢复机制时，只在生产已经由用户停好的环境运行GPU实验。

**本包现在不执行上述维护动作。** P0开发的guard必须先用mock systemctl/docker做故障测试，真实暂停只在后续用户授权后进行。

## 6. 不改变的生产项

镜像tag `ninfer-4090:44a2c6c`、原容器、生产unit文件、NGINX、兼容层、模型SHA、原服务端口以及用户已有cache。不改变主机驱动、CUDA、功率上限、时钟和sudoers。性能试验记录功耗即可；调功率是另一项明确授权，不属于CED核心改造。

P8输出新tag建议和启动命令，但不自动切流。实验镜像名可为`ninfer-4090-ced:<candidate-short-sha>`，禁止覆盖基线tag。
