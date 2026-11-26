# 生产监控（strata_monitor.py）

给 4090 上的生产服务 `openclaw-qwen38-next` 补上连续的时间序列：每分钟采样一次，每天汇总一次，磁盘占用有上限、数据按日期过期。

只用 Python 标准库，在 4090 上用 `/usr/bin/python3`（3.11）运行。只读 /proc、cgroup v2、nvidia-smi 和服务自己的 `/metrics`，只写 `data/` 目录；不改生产配置，不碰引擎、NGINX 和 unit。请求解析复用上一级目录的 `prodlog.py`，与本仓库 [`tools/prodlog.py`](../prodlog.py) 是同一份文件。

部署位置是 `/data/strata-data/prod-observe/monitor/`，放本脚本、测试和 `data/`。

## 安装与卸载

```bash
cd /data/strata-data/prod-observe/monitor
/usr/bin/python3 -I -B strata_monitor.py cron install   # 往 hhtele 的 crontab 写入带标记的一段
/usr/bin/python3 -I -B strata_monitor.py status         # 最近一次采样、磁盘占用、cron 是否在、最近日报的告警
/usr/bin/python3 -I -B strata_monitor.py cron remove    # 只删除这段标记；数据要另外 rm -r data
```

crontab 里有两行，都在 `nice -n 10` 下运行：

- 每分钟 `sample`。运行前先看 `data/monitor.log`，超过 1 MiB 就改名为 `monitor.log.1`。脚本即使启动就失败，日志也不会无限增长。
- 每天 00:17 `daily`。对每个已经结束的日期生成请求明细和日报，再压缩原始采样、执行保留策略。机器关着错过的日期，下次运行时会补上。

## 每分钟采什么

每次采样在 `data/samples/YYYY-MM-DD.jsonl` 里追加一行 JSON，按本地日期（US/Eastern）分文件。速率字段都是相对上一次采样算的：

| 块 | 内容 | 来源 |
|---|---|---|
| `host` | CPU 与 iowait（核数）、load1、MemAvailable、swap 已用、AnonHugePages、PSI（cpu/mem/io 每秒的停顿比例） | /proc |
| `unit` | 生产 unit 的 CPU 核数、内存、swap、PSI、磁盘读写 MiB/s | unit 的 cgroup |
| `engine` | PID 与启动时刻、RSS、匿名内存、swap、线程数、CPU 核数、本区间 major fault 数 | /proc/PID |
| `docker` | 每个容器的 CPU 核数和内存，也就是同机租户：gunicorn、redis、postgres | `docker-*.scope` cgroup |
| `gpu` | 温度、利用率、显存、功耗、SM/显存时钟、PCIe 代数与宽度、clock-event reasons、风扇 | nvidia-smi |
| `metrics` | live 的 state/queued/phase、running totals（requests、tokens、decode_ms…）、对话缓存计数 | 服务 `/metrics` |
| `log` | 引擎日志路径、inode、字节数 | 运行配置里的 `log` |

`mode` 取 `prod`、`lab` 或 `down`：

- `lab`：unit 之外有 strata 引擎，或者正在运行 `upgrade_gate.py`、`gate17.py`、`quant_quality.py`、`pisim.py`、`session_bench.py`、`chain_bench.py` 中的任何一个。这时不调用 nvidia-smi 和 `/metrics`，不干扰实验测量。
- 生产停机时仍记录日志大小，服务恢复后请求可以继续定时。

单个来源失败只记进这一行的 `errors`，其他字段照常写。失败的来源发生变化时，`monitor.log` 记一行。

2026-11-23 在 4090 上实测：

- 每次采样墙钟 0.12 s、CPU 0.11 s，进程峰值 RSS 30 MB。nvidia-smi 本身约 30 ms。
- 每行约 1.4 KB，每天约 2 MB 原始数据。

## 日报和请求明细

引擎日志没有逐请求的墙钟时间，只有 `engine started` 行带时间。为此，每次采样都记下日志的字节数。`daily` 用 `prodlog.py` 解析日志，看每个请求的 summary 行落在哪两次采样之间：

- `t`：之后第一次采样的时刻，也就是完成时间的上界；
- `t_after`：之前一次采样的时刻，也就是下界。

两者通常只差 1 分钟。日志换了文件（切换版本树）或变短时，区间不跨过去，次数记在日报的 `requests.log` 里。引擎启动要几分钟，换文件时不会丢请求。

`data/requests/YYYY-MM-DD.jsonl.gz` 每行是一个请求：prodlog 的全部字段，加上 `t`、`t_after` 和 `ctx`。`ctx` 统计请求可能运行的时间窗口，即从 `t_after` 减去请求自身耗时到 `t`：

- 同机租户 CPU：按与窗口重叠的时长加权的均值，以及最大值；
- 主机 CPU；
- 引擎 major fault，取重叠采样的合计，是上界；
- unit 内存停顿；
- swap；
- GPU 温度。

`data/reports/YYYY-MM-DD.json` 包括：

- 覆盖率与缺口，以及各 `mode` 的分钟数；
- prodlog 汇总：按 prompt 长度分段的 decode tok/s、接受率、ms/window、CPU 条目等；
- `/metrics` totals 的当日增量，用来和日志计数交叉核对；
- host、unit、engine、docker、gpu 各项的分位数和极值；
- 每小时一行；
- `contention`：按租户 CPU 是否达到 1 核分两组，比较 decode 速度和每个 CPU 专家条目的耗时；
- `warnings`。

告警阈值在 `WARN` 里，触发条件如下：

- 覆盖率低于 95%；
- MemAvailable 低于 3072 MiB，与 upgrade_gate 的护栏相同；
- swap 剩余不到 10%；
- GPU 温度达到 85 °C；
- 生产分钟里出现 `hw_slowdown`、`sw_thermal`、`hw_thermal` 或 `hw_power_brake`；
- unit 内存 full stall 超过 5 s；
- 引擎重启；
- 日志换文件或被截短；
- 日志里定时的请求比 `/metrics` 计数少 2 个以上；
- 某个 prompt 分段的 decode 中位数低于前 7 天中位数的 0.85 倍，且当天该段至少有 10 个请求；
- 采样出错。

## 磁盘占用和过期

| 内容 | 保留 | 大小 |
|---|---|---|
| 原始采样 | 当天的保持 `.jsonl`，日报生成后 gzip；保留 30 天 | 每天约 2 MB 原始，gzip 后约 0.2 MB |
| 请求明细 | 180 天 | 每天约 10 KB |
| 日报 | 180 天 | 每天约 10 KB |
| `monitor.log` | 不超过 1 MiB，另留一份轮换 | — |

另有两道硬上限：

- 单日原始文件最多 20 MB。超过后当天不再写入，`monitor.log` 记一次。
- 整个 `data/` 最多 200 MB。超过时依次删除最旧的原始采样、请求明细和日报，直到 180 MB 以下；当天和前一天的原始采样不删。

保留期按文件名里的日期计算，不看 mtime。预计稳态在 10 MB 以内。

## 查询

```bash
cd /data/strata-data/prod-observe/monitor
zcat data/requests/2026-11-24.jsonl.gz | python3 -c "import json,sys; [print(r['t'], r['prompt'], r['generated'], r['decode_ms'], r['ctx']['cotenant_cpu_mean']) for r in map(json.loads, sys.stdin)]"
python3 -c "import json; r=json.load(open('data/reports/2026-11-24.json')); print(r['warnings']); print(json.dumps(r['contention'], indent=1))"
```

## 测试

在本目录运行 `python3 -B -m unittest test_strata_monitor`，共 12 项。测试用临时目录里的假 /proc 和 cgroup 树，不读真实系统。覆盖：

- 速率；
- lab 与停机模式；
- 来源失败；
- 单日上限；
- 跨午夜的请求定时与上下文；
- 日报告警；
- 保留期与总上限；
- cron 行（不能含 `%`）；
- 各个解析器。
