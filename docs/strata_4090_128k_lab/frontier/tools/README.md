# 离线证据工具

这些工具只检查文档、手工整理的证据和统计输入。它们使用 Python 3.10+ 标准库，不连接网络，不启动进程、模型、SSH 或 GPU，不包含线上适配器，也没有 `--execute`。所有示例数据均为 **SYNTHETIC：合成数据，没有执行硬件实验**。

以下命令均在文档包根目录运行。`-B` 避免产生影响清单的 Python 字节码文件。

```bash
python3 -B -m unittest discover -s tests -v
python3 -B tools/validate.py --root .
python3 -B tools/headroom.py --input fixtures/headroom_synthetic.json
python3 -B tools/paired_stats.py --input fixtures/paired_synthetic.json
python3 -B tools/paired_stats.py --input fixtures/p24_rounded_synthetic.json
python3 -B tools/verify_manifest.py --root . --manifest MANIFEST.sha256
```

`--input` 是 JSON 文件路径；`--root` 是文档包根目录；`--manifest` 是根目录内已有 SHA256 清单路径。所有命令默认把 JSON 结果写到标准输出，均可指定 `--output /绝对路径/新结果.json`。输出文件必须不存在；工具绝不覆写已有文件或输入。输出文件的父目录应已存在。为保持打包清单稳定，把运行结果放在包外，或者使用标准输出。

## 状态与退出码

| 退出码 | 状态 | 含义 |
|---|---|---|
| 0 | `PACKAGE_VALID` / `MANIFEST_VALID` | 文档或字节完整性检查通过，不表示实验有效。 |
| 0 | `RESEARCH_RESULT_ONLY` | 给定假设下的暴露时间与条件估算，不是性能通过。 |
| 0 | `PERFORMANCE_GATE_ONLY` | 这份输入的性能统计门通过；质量仍为 `NOT_EVALUATED`，部署仍为 `false`。 |
| 1 | `INSUFFICIENT` | 无依赖证据或仍有未知区间，不能认定关键路径资格。 |
| 1 | `NO_QUALIFIED_CANDIDATE` / `PERFORMANCE_GATE_NOT_MET` | 给定输入未达资格或统计门。 |
| 2 | `INVALID_INPUT_OR_EXPERIMENT` | 文件、结构、有效性或完整性有误；不输出可用于推断的统计量。 |

命令行参数本身错误由 Python `argparse` 报告并以 2 退出。合成数据即便得到 `PERFORMANCE_GATE_ONLY`，也只说明算术与门控分支按预期运行。

## `headroom.py`：暴露区间并集与条件收益

完整示例见 [headroom_synthetic.json](../fixtures/headroom_synthetic.json)。必需输入结构：

```json
{
  "schema_version": 1,
  "synthetic": true,
  "window_ms": 1000,
  "critical_exposed_intervals": [[100, 300], [200, 400], [500, 550]],
  "measured_kernel_speedup": 2.0,
  "added_overhead_ms": 20,
  "dependency_verified": true,
  "unknown_intervals": []
}
```

时间均为同一观测窗口内的毫秒，区间满足 `0 <= start < end <= window_ms`。输入应来自人工审阅过的依赖关系与时间线；`dependency_verified=true` 是审阅者声明，计算器不能自行证明因果。GPU wait 总和、累计 kernel 时间、可能重叠的 copy/refill 时间不能直接替代可归因的暴露区间。未知成本应列为 `unknown_intervals`；存在任何未知区间或依赖声明为 `false` 时，结果一律为 `INSUFFICIENT`。

工具先求区间并集。示例的已知暴露时间是 `350 ms`，而不是各区间长度相加的 `450 ms`。令窗口为 `T`、并集暴露时间为 `E`、`f=E/T`、给定局部加速比为 `s`、新增开销为 `h`：

- 乐观时间比：`1-f`，假设暴露成本全部消失且没有新增开销。
- 有限加速条件时间比：`1-f+f/s+h/T`，保留未优化工作且采用输入的局部加速比和开销。
- 时间改善比例为 `1-time_ratio`；整体加速比为其倒数。若乐观时间比为零，JSON 的 `speedup` 使用 `null` 表示无有限上界。

输出字段 `realistic` 是上述有限加速条件模型，**不是实测整请求收益，也不是跨调度和负载条件的普遍保证**。示例的有限加速改善为 `15.5%`。乐观改善或有限加速条件改善低于 `4%`，返回 `NO_QUALIFIED_CANDIDATE`。另输出暴露比例是否达到 `8%` 的优先审阅值；达到该值也不构成实施许可。依赖证据、源代码差异、质量门和真实配对实验仍需独立处理。

## `paired_stats.py`：六对配对时间统计

完整示例见 [paired_synthetic.json](../fixtures/paired_synthetic.json)。数据声明及人工证据审阅是必需的前提；本工具不能根据文件内容验证真实启动记录、预登记时间或请求哈希对应的请求字节。

顶层必需字段为整数 `schema_version=1`、布尔 `synthetic`、`preregistration` 和 `pairs`。预登记结构：

```json
{
  "pair_ids": ["r1", "r2", "r3", "r4", "r5", "r6"],
  "order": ["AC", "CA", "CA", "AC", "AC", "CA"],
  "request_sha256": "64位十六进制请求哈希",
  "fixed_output_tokens": 2048,
  "aa_noise": 0.01,
  "primary_metric": "ttft_ms"
}
```

`A` 表示 baseline，`C` 表示 candidate。 本工具是通用计算器；本包当前warm campaign已固定`primary_metric=decode_ms`，下方/fixture的TTFT演示不允许覆盖该预登记。warm输入须先通过开跑前资格门，实际完整请求hash不能被recipe hash替代。`aa_noise` 是实验前冻结的 A/A 相对时间噪声比例，取值必须有限且处于 `[0,0.5)`；不得在看到候选结果后修改。主指标可取 `ttft_ms`、`wall_ms` 或 `decode_ms`，必须预登记。每项配对具有 `pair_id`、`order`、`baseline` 和 `candidate`。每一臂的必需结构为：

```json
{
  "engine_id": "A1",
  "fresh_engine": true,
  "run_valid": true,
  "failure_kind": "none",
  "request_sha256": "与预登记完全一致的64位十六进制哈希",
  "output_tokens": 2048,
  "metrics": {"ttft_ms": 1000, "wall_ms": 3000, "decode_ms": 2000}
}
```

必须恰好六对，按预登记顺序列出，且十二个 `engine_id` 全部唯一。缺失或重复配对、顺序变化、缺少 `run_valid=true`、`fresh_engine` 非真、任何 `failure_kind` 非 `none`、请求哈希不符、输出 token 数不一致、非正或非有限时间，均拒绝整份实验。失败不允许删除、替补或只分析幸存样本。这里的 token 数是实验记录的实际 token 数，不能用 SSE chunk 数替代。基础设施失败也需要保留原始记录；把失败记录删除后重组“六对”不符合本协议，即使伪造的输入能够通过结构检查。

对每个时间指标，计算六个 `log(candidate_time / baseline_time)`，对六个配对索引的所有 `6^6=46656` 个有放回重采样求平均，排序后在秩 `(N-1)*q` 处线性插值，取 `q=0.025/0.975` 并指数变换。点估计为配对时间比的几何均值；改善比例为 `1-ratio`。三个门同时满足时才返回 `PERFORMANCE_GATE_ONLY`：

- 主指标时间比 CI 上界 `<= 1-max(0.04, 2*aa_noise)`。
- `ttft_ms`、`wall_ms`、`decode_ms` 中其余两个非目标指标的时间比 CI 上界分别 `<= 1.02`。

因此主指标为 TTFT 时，检查 wall 与 decode 的非劣门；主指标为 decode 时，检查 TTFT 与 wall 的非劣门；主指标为 wall 时，检查 TTFT 与 decode 的非劣门。输出 `primary_metric` 明示选定指标，`gates.primary` 是其改善门，另外两个 `gates` 项以非目标指标名为键。decode 加快不能掩盖 TTFT 回退。

这是新包预登记的正式性能规则。它不同于 P24 的专项主指标门，不能把本工具结果冒充 P24 原报告的原始重算。无论结果如何，`quality=NOT_EVALUATED`、`deployment_approved=false`；相对质量非劣、六项历史绝对质量失败和生产保护不能被这个工具豁免。

### P24 舍入数字 sanity fixture

[p24_rounded_synthetic.json](../fixtures/p24_rounded_synthetic.json) 抄录 [P24 报告](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P24-HC-PAIRED-PERFORMANCE-20261029.md) 中六对已舍入 TTFT 秒数及 wall/decode 比值。wall 与 decode 的绝对时间是任意合成基数乘该比值，engine ID、有效性声明、输出数和请求哈希也都是演示字段。它仅用于检测比值方向、百分比口径和明显回归：预期 TTFT 比约 `0.991756`，decode 上界大于 `1.06`，新规则下结果为 `PERFORMANCE_GATE_NOT_MET`，退出码 1。

这不是 P24 的原始数据、独立新样本或完整 exact-raw 重算。精确枚举作用于输入的舍入合成数字，不恢复舍入前信息。

## `validate.py`：离线包结构

工具严格读取包内所有 `.json`：拒绝重复键、NaN、Infinity 和浮点溢出。固定检查 [policy.json](../config/policy.json) 的安全/资格/统计硬值、六项历史质量失败状态和禁止自动部署字段；检查 [LOCK.json](../sources/LOCK.json) 必需记录的完整 40 位 SHA，以及二进制 64 位 SHA256。它检查哈希格式和声明，不会向远端验证提交是否存在。

`config/task_dag.json` 的 `phases` 必须非空，每个 phase 必须有唯一 `id`、`depends_on` 列表和非空 `tasks`；每个 task 必须有全局唯一 `id`、`depends_on` 列表和已有的相对 `doc` 路径。phase 依赖只能引用 phase；task 依赖可以引用 task 或 phase。依赖某个 phase 会展开为该 phase 的所有 task，且 task 自动继承其所属 phase 的前序 phase 依赖。阶段图和展开的任务图都必须无环、无缺失依赖；阶段与任务 ID 不得重名。

`config/candidates.json` 中每个 candidate 必须有唯一 `id`、非空 `title/status`、属于政策列表的 `numerical_class` 和已有的相对 `doc`。工具不凭状态文字许可实施。

所有 `.md` 的普通行内 Markdown 相对链接及图片路径必须存在且不能逃逸包根目录；链接中的 fragment 不检查，外部 URL 不联网验证。这是针对本包格式的轻量检查器，不是完整 Markdown 解析器，不支持用其证明引用式链接、生成锚点或外部网页有效。结果 `PACKAGE_VALID` 只证明这些结构检查通过，`gpu_validation=NOT_RUN`。

## `verify_manifest.py`：打包前完整性

工具要求已有 UTF-8 清单，每行严格为 `64位SHA256`、两个空格、相对 POSIX 路径。清单自身位于包根目录内且不列入自身。清单必须恰好覆盖包内其他全部常规文件，不能遗漏或额外列出文件；拒绝路径穿越、绝对路径、重复项和符号链接，逐个重算 SHA256。输出 `MANIFEST_VALID` 后再创建 ZIP；校验后如改变任何文件，应重新生成并验证清单。

这是文件夹到打包步骤之间的完整性检查，不会自己创建 ZIP，也不证明签名、远端来源真实性或 ZIP 内容。不要把校验输出写进已封存的包内，否则包的文件集合随之变化。

## 可复现测试范围

[test_offline.py](../tests/test_offline.py) 用合成输入和临时目录验证区间重叠、unknown/因果拒绝、六对 exact bootstrap、无效记录、严格 JSON、输出不覆写、DAG 环/缺依赖、文档与政策变动、SHA 缺失及清单内容变化。测试不导入生产配置、不运行模型、不访问 GPU。它证明离线工具行为，不能证明硬件性能、质量、温度或生产恢复状态。
