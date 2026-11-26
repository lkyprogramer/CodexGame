# 文档辅助工具

这两个工具用于生成可审计的统计摘要与目标机器清单，不实现引擎，不代表任何 GPU 性能、质量或上线资格已经通过。只依赖 Python 3 标准库，建议 Python 3.8 或更新版本。

## paired_stats.py：配对延迟的 case 等权统计

在规划包根目录运行：

```bash
python3 tools/paired_stats.py \
  --input /path/to/single-stratum-pairs.csv \
  --bootstrap 10000 --seed 20261125 \
  --output /path/to/paired-statistics.json
```

CSV 表头必须按以下顺序完全匹配，不能缺列、重复列或增加列：

```csv
pair_id,case_id,stratum,baseline_ms,candidate_ms
```

每行是一对使用同一个 case、同一 stratum 的基线与候选延迟，单位均为毫秒。pair_id 全文件唯一；同一个 case_id 可以有多个不同 pair_id 的重复测量。标识符首尾空白会被去除；空标识符、空数据、非正延迟、NaN/Infinity、字段数错误和混合 stratum 都会被拒绝。不同 stratum 必须分别运行。数字结果若超出浮点数可表达的有限范围，也会报错。

计算步骤：

1. 每对测量计算 log(baseline_ms / candidate_ms)。
2. 同一 case 的所有配对先取 log 效应的平均值。
3. 对独立 case 等权取平均，再取指数，得到 gmean_speedup。
4. 以 case 为抽样单位，有放回抽取相同数量的 case；从 bootstrap 的平均 log 效应分布取2.5%和97.5%分位点，再指数转换。

重复测量多的 case 不会获得更大权重，也不会冒充更多独立样本。bootstrap 不按 CSV 行抽样。case_id 排序和固定 seed 保证同一数据可重现。

主要输出字段：

| 字段 | 含义 |
|---|---|
| evidence_kind | 固定为 derived_statistics |
| case_count / pair_count | 独立case数 / 全部配对测量数 |
| gmean_speedup | 大于1表示候选延迟较低 |
| latency_reduction | 1−1/gmean_speedup；小数比例，0.10表示降低10%，负数表示退化 |
| speedup_ci95 | case bootstrap的95%区间；不足30个case时为null |
| latency_reduction_ci95 | 对speedup区间做同一单调变换；不足30个case时为null |
| evidence_status | INSUFFICIENT_EVIDENCE或INTERVAL_ESTIMATE_ONLY |
| qualification | 固定为NOT_ASSESSED，不输出PASS |
| bootstrap_requested / bootstrap_used | 请求次数 / 实际次数；不足30个case时实际为0 |
| seed / method | 随机种子与计算方法 |

**统计限制：** 工具只相信输入的 case_id 和分层标签，不能证明样本真正独立、配对随机化合理、样本数充分、噪声受控或原始计时真实。30个独立case只是本包禁止过早推断的最低数量，不是功效分析保证。低bootstrap次数增加Monte Carlo误差，正式比较保留默认10000次。区间仅针对这个预先选定stratum的case等权几何效应，不是算术平均延迟、单请求p95或整体业务成功率。多个stratum、多次挑选候选与重复看结果需要在实验设计中处理，工具不会自动做多重比较校正。

不足30个case仍输出描述性点估计，但95%区间为null，不产生置信结论。原始数据来自真实硬件、合成计时或mock，必须由外部实验记录明确标记；derived_statistics不能洗掉上游数据性质。

输入无效时退出非0，分析完成前不写输出，因此不会用错误结果覆盖已有JSON。输入与输出解析到同一路径时会拒绝，防止覆盖原始CSV。

## preflight.py：只读目标机器清单

应在真正的待测机器上运行：

```bash
python3 tools/preflight.py --output /path/to/hardware-inventory.json
```

采集内容：

- uname -a、lscpu、/proc/meminfo。
- nvidia-smi：GPU名称、总/空闲显存、driver版本、PCIe当前/最大代数及链路宽度。
- nvcc --version、lsblk的设备/容量/文件系统/挂载点、df文件系统余量。

外部命令均以参数数组执行，不经过shell，每项超时5秒。命令不存在、返回非0或超时都会记录在对应probes项中；/proc/meminfo不可读也单独记录。原始stdout/stderr与错误会写入JSON。未知GPU数值为null，不伪造为0；GPU query整体失败时machine_match为UNKNOWN。

machine_match只检查是否恰有一张桌面RTX4090，不认证CPU、内存容量、24GB实际可用量、PCIe带宽或其他产品条件。已识别的其他GPU、多GPU或4090 Laptop会明确标MISMATCH；MATCH只表示型号匹配，performance_qualification始终为NOT_RUN。evidence_kind固定为hardware_inventory。

工具只执行上列读取操作并写入指定JSON，不输出环境变量、不寻找token、不安装依赖、不运行kill命令、不终止已有业务进程、不改权限、不清cache，也不修改驱动或GPU配置。超时只结束本工具启动的探测子进程。输出中会包含主机标识与挂载路径，按实验资料处理。没有足够权限或工具时保留错误，由T00工程任务处理；本工具不会自动修复环境。

## 测试

```bash
python3 -m unittest discover -s tests -v
```

测试覆盖重复测量不改变case权重或bootstrap结果、独立case数量门槛、非法CSV/延迟、CLI写出与失败不覆盖、输入路径保护、真实缺命令/退出码/超时，以及受控GPU输出的匹配与未知值处理。测试中的GPU返回是明确的受控fixture，不是4090实测证据。不会在测试期间加载模型、安装CUDA或运行GPU基准。


## v2结构检查器

`check_document_package.py`检查当前版本的任务/测试/来源引用、JSON、Python语法、Markdown相对文件链接、围栏及shell语法；它不会构建引擎或执行文中命令。`check_cache_schema.py`使用已存在的jsonschema依赖构造8个正例、38个负例和11个预期被接受的语义边界案例。后一类专门证明Schema的局限，不能计为实际状态恢复或GPU测试通过。

```bash
python3 tools/check_document_package.py
python3 tools/check_cache_schema.py
```

两个检查器可选`--output /path/to/report.json`保存文档级观察。所有published/hash/owner/GPU示例均标明合成；没有引擎能力自授权。旧preflight/paired_stats及tests/test_tools.py保持原实现。
