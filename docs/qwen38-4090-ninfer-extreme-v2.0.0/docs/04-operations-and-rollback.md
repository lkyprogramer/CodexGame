# 维护窗口、权限、日志与恢复

## 1. 两阶段准备

CPU准备（读取docs、hash、分支、构建、JDK夹具）不暂停生产。GPU测试在维护批准后取得remote lease。`run_qualification.sh`只有`ALLOW_PRODUCTION_PAUSE=1`才申请lease；默认plan `ready:false`先被拒绝。

GPU host安装本包工具到`~/qwen38-extreme-v2`，不是root拥有的`/data/kern-*`。本包不自动部署文件到该路径，控制AI按T00/T01审阅后的scp/rsync步骤执行，并核对包SHA。

## 2. sudo处理（2026-09-09 已配置）

禁止密码写在json、env、argv、log或git。管理员已为**确切的**两条命令配置免密（`/etc/sudoers.d/qwen38-extreme-lab`，0440）：

```text
hhtele ALL=(root) NOPASSWD: /usr/bin/systemctl stop openclaw-qwen38-ninfer.service, /usr/bin/systemctl start openclaw-qwen38-ninfer.service
```

验证方法与结果见`22 §1.2`：规则在`sudo -n -l`列表中排在原有带密码`(ALL : ALL) ALL`之后（sudo最后匹配生效）；`sudo -n systemctl start <unit>`对已active的unit是no-op且免密成功；`sudo -n -v`仍要密码。**注意**`sudo -n -l <命令>`在存在任一NOPASSWD条目后对所有被允许的命令都打印路径，它只证明"允许"，不证明"免密"——remote_guard用它做预检可以，验证免密要看真实no-op命令。

旧`~/qwen38-dflash2-20260819/launch/sudo-wrap.sh`（喂密码）本包不用；是否删除/轮换由用户处理。本包remote_guard仅sudo命名unit的stop/start，实验命令以普通hhtele运行。不自动授予NOPASSWD:ALL、CAP_SYS_ADMIN给任意Python、也不改全局驱动profiling权限。

## 3. remote_guard行为

`tools/remote_guard.py`在GPU host持有fcntl锁，写`~/.cache/qwen38-extreme/maintenance.json`。先核对stop/start权限，再记录初始active状态，暂停现网。`ExecStop=docker rm -f`异步释放显存，因此guard**轮询**`nvidia-smi memory.free`最多30秒直到≥20000MiB（`wait_gpu_free`），超时才拒绝继续，不杀未知PID；释放后的free值写入journal。

Mac controller持有SSH管道，每15秒PING。EOF、RELEASE、90秒无心跳或TTL到期：只停止带`qwen38.lab.run=<run_id>`标签的实验容器，再恢复**原本active**的生产unit。候选启动必须带该label，否则不准纳入自动计划。

恢复判定要求`systemctl is-active`且**18343与18030两个端口**的`/v1/models`都返回`openclaw/Qwen3.8-27B-WORK`（120秒内）：systemd跟踪的是`production-18343.sh`最后`exec`的proxy进程，若容器被绕过systemd直接`docker rm`，unit仍active、18343仍开、GPU却空，只查18343会误判。恢复后还要由控制端做一个无敏感信息的smoke。任何恢复问题使结果不能发布。

## 4. 异常与人工恢复

SIGKILL、断电、主机重启不可能靠进程finally保证恢复。遗留journal阻止新的维护覆盖。先核对时间、run_id、实验容器归属，再执行：

```bash
python3 tools/remote_guard.py --run-id 已有journal中的ID --recover
```

若候选不受Docker label管理，应在T01提供明确PID清单与kill-own-process清理器；否则不允许自动运行。不要`pkill ninfer`、`docker stop $(docker ps -q)`或批量停止所有ssh。

## 5. ncu权限

NVIDIA官方允许单次授权的管理员/能力路径，R610增加更细的能力权限。[S15] 本机实操：hhtele在docker组，`nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04`镜像自带`ncu`，宿主只有`nsys`。

```bash
docker run --rm --gpus all --cap-add=SYS_ADMIN -v "$LAB":/lab -w /lab \
  nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04 ncu --set basic -k <kernel-regex> <binary> <args>
```

先用一个无业务数据的tiny kernel确认计数器可读；只给经过hash审阅的profiler容器/命令这个capability。`RmProfilingAdminOnly=1`与`perf_event_paranoid=3`都**不改**（后者只影响nsys CPU采样，CUDA trace不受影响）。NCU运行计入diagnostic，不计perf ABBA。Nsight Systems/CUDA events先确定热点，NCU只抓目标1–3 kernels。

## 6. 凭证和数据

输入report指出历史orchestrator日志可能含credential。此包不复制raw *.log/*.out。先在原项目清理/轮换可能暴露的secret（由用户/管理员处理），再建立0600私有采集目录。脱敏是尽力过滤，不等于DLP保证；上传外部前人工审阅。helper默认只保存usage/timings和结构摘要，不保存完整模型思考内容。

恢复过程始终尝试清理、拉回原服务、验证模型端点，即使其中某一步失败也不跳过后续恢复尝试。失败仍返回RECOVERY_REQUIRED，不能被一次systemctl成功覆盖。SSH/controller自身被SIGKILL的场景仅靠远端EOF/心跳期限恢复；断电/主机故障需人工恢复。
