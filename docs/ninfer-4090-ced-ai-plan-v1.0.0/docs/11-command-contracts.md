# 11 现有命令与待开发命令的边界

## 1. 现在已有、经源码核对的构建入口

在符合依赖的CUDA13.2开发容器内、独立candidate源码根执行：

```bash
cmake -S . -B "$LAB_ROOT/build-candidate" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DNINFER_BUILD_QWEN3_8_27B=ON \
  -DNINFER_BUILD_QWEN3_6_35B_A3B=OFF \
  -DBUILD_TESTING=ON \
  -DNINFER_BUILD_BENCHMARKS=ON
cmake --build "$LAB_ROOT/build-candidate" --parallel 4
ctest --test-dir "$LAB_ROOT/build-candidate" -N
```

`BUILD_TESTING`默认OFF，不显式打开会造成没有测试。[S02] 真实GPU测试必须在guard授权的窗口内执行，不是在生产仍占GPU时直接运行。

已确认的测试名包括：`ninfer_qwen3_8_27b_prefix_real_test`、`ninfer_qwen3_8_runtime_mechanisms_test`、`ninfer_continuation_cache_test`、`ninfer_openai_schema_test`、`ninfer_request_log_test`。真实制品测试可能exit77；这不算通过。[S11]

```bash
ctest --test-dir "$LAB_ROOT/build-candidate" \
  --no-tests=error --output-on-failure \
  -R 'ninfer_(public_api|openai_schema|request_log)_test'
```

配置和运行artifact真实测试所需环境由P0读取实际测试源/README后固化到resolved manifest，不能猜环境变量名。

## 2. P0要实现的统一runner CLI

```text
python3 tools/ced_lab/run_phase.py
  --phase P0|P1|P2|P3|P4|P5|P6|P7|P8
  --config ABSOLUTE_RESOLVED_JSON
  --out ABSOLUTE_NEW_RUN_DIR
  [--task Pn-Txx --checks local]
  [--subphase P7A|P7B]
```

`--task --checks local`只执行当前Task注册的局部检查，不写PASS phase gate；不带它们执行完整phase，必须收集全部required suite。P7A/B顺序由runner检查上一个子Gate。

配置缺失、非法输出目录、已存在run目录、没有测试映射、缺GPU/依赖/制品必须明确失败。输出路径新建且不可覆盖旧报告。run_phase内部用argv数组执行命令，并在GPU动作前调用guard。

每个Task在完成时维护`suites.json`的该task映射：已有CTest target或明确Python测试文件、是否GPU、artifact/profile要求、最小case数、输出parser。新Task未实现时该映射应明确NOT_IMPLEMENTED，不能用echo或空测试占位。

## 3. 统一产物

```text
run_manifest.json   # source / build / base / predictor / config / GPU / versions
commands.jsonl      # argv, started_at, ended_at, returncode, timed_out
raw/                # non-secret stdout/stderr, CTest results, raw timings
metrics.jsonl       # per request unrounded numbers and route/provenance
checks.json         # required check ids and actual counts
quality.json        # assertions, task outcomes, seed/repo grouping
restore.json        # protected resources restored / unchanged
phase-report.md

gate.json           # status + scope + evidence links, never bare “PASS”
```

`gate.json`须引用当前baseline与candidate SHA；有预测时必须有PredictorSHA。每个check包含cases、passed、failed、skipped、evidence文件列表。0 cases、skip、无raw文件或required metrics缺失不能PASS。

## 4. P4/P5完成后才存在的新启动例子

以下代码**不是现有44a2c6c可直接运行的功能**。从P4/P5实现完成并测试后使用：

```bash
"$LAB_ROOT/build-candidate/apps/ninfer-serve" \
  /data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer \
  --host 127.0.0.1 --port 18041 \
  --max-context 262144 --kv-capacity 262144 \
  --max-concurrency 1 --prefill-chunk 1024 --kv-dtype rk4v4-e8 \
  --late-state-prefill auto \
  --late-state-predictor "$LAB_ROOT/predictors/ced16-r256.ninfer" \
  --late-state-split 48 --late-state-tail 2048 \
  --late-state-min-uncached 32768 --late-state-qualified-context 200000 \
  --continuation-cache off --no-prefix-reuse
```

这是P4 no-spec冷试验；没有`--spec`表示不启用投机，不使用一个虚构`--spec off`值。P5资格化后才加`--spec mtp --draft-tokens 3 --lm-head-draft`；warm suite改为`--continuation-cache l1-l2`并去掉`--no-prefix-reuse`。所有server只在guard内部启动。

## 5. 报告退出语义

进程退出码0只能表示对应范围PASS。Local PASS不等于Phase PASS；Phase PASS不等于Production qualification。必须同时输出`scope`和`production_quality_proven`。

P0-P8中所有新命令都需`--help`、错误输入测试、超时测试和no-GPU返回测试。任务中提及的具体实现测试不能用“pytest空目录通过”替代。
