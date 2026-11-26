# 32 · AX01–AX28：自动kernel与局部后端验证手册

> **v2来源更新：** 本篇141文件/工具链与CI详细审计基于历史`5e5c77…`；当前main为`f35d6ccc2e03a54e73e3796f415f11313e439d50`，新增#1866写覆盖修复与1D限制，详见[40](40_upstream_refresh.md)。未来K00冻结新pin并重做相关资格；原证据保持原SHA，不冒充新运行结果。

**状态：28项AX全部NOT_RUN。** 原48项与GX01–GX20保持，v1.2共96项计划测试。本篇没有执行Lean/Rust/CUDA构建、GPU推理、benchmark或部署。K任务定义见[31](31_kernel_tasks.md)，源码事实见[27](27_cuda_rust_source_audit.md)，架构/搜索/SM89合同见[28](28_custom_backend_architecture.md)、[29](29_automated_kernel_optimization.md)、[30](30_sm89_kernel_program.md)。

## 1. 证据类型和通过含义

| 证据 | 能支持什么 | 不能支持什么 |
|---|---|---|
| 文档/源码/外部CI审计 | 固定版本、可定位能力和失败出口 | 本机工具已具备、4090实际执行或Inkling性能 |
| CPU schema/工具测试 | 输入拒绝、统计与状态记录逻辑 | 新kernel/完整模型GPU正确性 |
| Lean model/exporter检查 | 对记录的模型/IR/属性与假设成立 | 未覆盖编译链、ABI、CUDA全部并发、数值或业务质量 |
| SM89 compile / cubin materialize | 当前产物能编译并有明确架构/ABI | 实际launch、没有race、E2E收益 |
| 4090 source smoke | 指定例子在实际4090执行并检验输出 | Atomic bridge、Inkling R3/量化/128K与服务资格 |
| AX + 原TC/GX/PF/QC/SV | 实际已执行的同产物/同profile资格 | 未测试shape、不同前端/driver/算术/预算或生产G7 |

proof状态固定为`NOT_REQUESTED / NOT_RUN / PROVED_SCOPED / FAILED / UNKNOWN / UNSUPPORTED / ERROR`，资格初始为`NOT_ASSESSED`。proof各属性与run/task/gate是不同状态维度。普通C++路线可明确NOT_REQUESTED；verified路线必须列完整必要义务，UNKNOWN/ERROR/导出/skip不能变成PROVED_SCOPED。

所有实际执行保存：source/toolchain/model/contract/artifact/ABI指纹、实际device/driver/PTX target、完整argv与受控环境、退出码、expected/executed/failed/skipped counts、raw stdout/stderr、oracle、计时口径与资源。缺字段为null+reason，不用0/空字符串代替。negative test可因按预期拒绝而通过该断言；这不意味着被拒绝feature取得支持能力。

## 2. 新增测试目录

每项都要记录适用前端与profile。proof负例只对声明该证明属性的路线强制；不适用必须给范围证据，不能将其写成实际运行PASS。复用旧fixture可减少工作，但新增断言必须实际执行。

| ID | 场景与输入 | 必须满足的oracle/失败行为 | 衔接 |
|---|---|---|---|
| AX01 | source/依赖/compiler/flags/contract变一byte，旧manifest与缓存仍在 | identity失效；旧artifact/proof/资格不复用；缺hash不能通过 | TC01、GX01 |
| AX02 | SM89配置夹TMA/PDL/cluster/不支持MMA、超shared/register/launch资源 | 明确静态/编译/准入拒绝；实际target可核对；跳过分支不算能力 | TC02、GX18 |
| AX03 | 0/1、tile±1、大shape、负数转unsigned、length×stride溢出 | 不产生越界地址；0按合同no-op/拒绝；机器整数溢出在launch前拒绝 | TC07、TC20 |
| AX04 | 非连续stride、misalignment、子view/部分overlap、错quant layout/scale | 只接受声明布局与alias；不静默reinterpret或重排精度 | GX08、GX09 |
| AX05 | 生成器改R/quant/sampler、容差、mask/barrier、oracle、search budget | 权限/schema/policy拒绝；候选不能修改判分和产品目标 | TC01、GX20 |
| AX06 | 重复候选换名、搜索超额/超时、并行GPU runner、历史NO_BENEFIT路线 | content去重、总预算和单卡租约生效；无新trace不重启旧路线 | PF02、GX19 |
| AX07 | proof缺失/NOT_RUN/timeout/UNKNOWN/UNSUPPORTED/ERROR、零义务、Lean缺失 | 不得获得PROVED_SCOPED；必要proof未完成不得授verified资格 | proof维度 |
| AX08 | 正确proof配错IR/PTX/cubin/flags/symbol/ABI/旧模板 | artifact binding失败；module load前拒绝；哈希关联不冒充编译证明 | TC01、GX01 |
| AX09 | verified/emitted IR脱离同次冻结构建、被未登记替换、unsupported/unknown操作、export-only或device-debug | 缺绑定/旁路被拒绝；正常后续优化不要求两IR字节相等；inspection不算证明，局部属性不外推 | compiler维度 |
| AX10 | 未允许axiom/TCB、shape/alias前提不满足、整数语义不一致、float路由无动态index合同 | 拒绝或保留UNKNOWN；range与路由内容分证；假设有可执行guard | proof/route维度 |
| AX11 | C++/Rust参数宽度/packing/ABI version/symbol/设备地址归属错配 | launch前拒绝；两前端按同语义做实际ABI roundtrip | TC01 |
| AX12 | shim创建/销毁借用context/stream/arena、线程current-context错配 | 唯一owner规则成立；异常恢复宿主context；下请求无影响 | TC15、GX13 |
| AX13 | enqueue后立即Drop/free/cancel，pinned输入提前复用 | lease保留到末次使用event完成；无提前回收或无限泄露 | TC15、TC19、GX07 |
| AX14 | copy stream省event/wait、写lease重叠、staging提前覆盖 | 顺序与范围oracle能抓到；合法依赖链才准入，不能靠default stream偶然同步 | TC15、GX07 |
| AX15 | graph重放中module unload/换kernel/arena generation变/capture失败 | 旧图安全退役；新key重新资格；没有过期函数/地址引用 | TC23、GX13 |
| AX16 | enqueue成功后异步错误，下一API才见错误 | 不误报READY；sticky fault禁token/tool commit；不原位fallback污染context | TC19、GX12 |
| AX17 | 最后kernel/event超时、GPU未确认停止、迟到完成、旧epoch恢复 | 不复用地址/ticket；drain或隔离重建，同预算由committed prefix恢复 | TC19、GX12 |
| AX18 | sanitizer检测错误但app exit0、过滤全部kernel、零case、子进程漏跟踪、GPU skip | runner非零且清点真实覆盖；缺日志或无执行不能PASS | GX20 |
| AX19 | global越界/misalignment、arena slice越界但仍在同allocation内 | memcheck加slice/canary/独立范围oracle，不能声称工具覆盖全部逻辑边界 | TC07、GX08 |
| AX20 | shared race、未初始化有效数据、divergent barrier、cp.async等待/复用错误 | 各工具与针对性oracle能失败；global/跨stream问题不由racecheck兜底 | TC15、GX07 |
| AX21 | 极值/近零/合法-inf mask/NaN/near-tie、稀疏或集中expert、动态ID越界/重复、offset/scatter错配、尾块 | E精确映射；N冻结误差/route；非法index不越界且禁commit；有效NaN/Inf FAIL | TC05、GX09、GX11 |
| AX22 | 同physical weight不同visit、每loop KV/conv/controller、B变化 | 保留真实24/48映射与全部有效状态；局部证明不替代模型oracle | TC04、TC08–10、GX03 |
| AX23 | 每已资格k的拒绝位置、EOS/stop/cancel/max_new后save/restore/续写 | 与独立重算oracle一致；无suffix状态泄露，RNG不盲回拨 | TC11–14、TC18–21、GX17 |
| AX24 | module/graph/workspace/repack/pinned/staging同时存活，context增长及JIT/编译峰值 | 原ledger+NVML/PSS满足GPU/host预算与保留量；无swap/隐藏副本 | PF07、GX04、GX15 |
| AX25 | profiler/无profiler、冷/热、首次JIT/capture/repack与steady-state | 分账但请求E2E包含实际成本；正式PF不混profile/sanitizer计时 | PF01–04、GX19 |
| AX26 | 看holdout后换赢家、重复case冒充n、多candidate逐个95%CI挑最好、丢timeout | 拒绝违规结论；独立集或预登记校正，失败惩罚与完整配对保留 | PF02、PF05、GX19–20 |
| AX27 | registry旧driver/module/ABI/layout、未知shape、budget/graph变化 | 完整key不匹配不选候选；只在预提交且状态干净时走原合法fallback | TC17、TC23、GX01 |
| AX28 | 禁用candidate、epoch切换、worker重建、连续load/unload/取消/soak | 同预算合格回退；无重复tool副作用或lease泄露；原8h服务门不减少 | TC19、TC21、SV、GX13 |

建议kernel边界集至少含每个实际合法dtype/layout的0/1、tile−1/tile/tile+1、非整块尾、极值与near-tie；B1及已经资格的B2/4/8、prefill代表ubatch分别测。非法shape需验证拒绝，不为了填表启用未知B。状态/质量样本数量继续依13/14，不以几个kernel输入替代。

## 3. PACK_READY：本包当前可运行的辅助工具

从文档包根目录运行：

```bash
python3 -B -m unittest discover -s tests -v
python3 tools/preflight.py --help
python3 tools/paired_stats.py --help
```

这些只检查现有包内辅助工具，不编译cuda-rust、不调用Lean、不加载模型。不要把工具测试数作为96项资格的已执行数。`tools/inkling-lab/`、新C++测试和K计划中的profile仍为NEW，须先实施对应任务。

## 4. SOURCE_REFERENCE：固定上游的现有命令

### 4.1 前提、工作目录与锁

由T00/K00先提供隔离的完整源码checkout与依赖锁。新工作目标是[S45固定提交](https://github.com/NVIDIA/cuda-rust/tree/f35d6ccc2e03a54e73e3796f415f11313e439d50)。下方命令入口最初在历史S22读取，K00须在S45重新确认接口、依赖锁和#1866相关测试，不能仅替换SHA后沿用旧资格。本段是未来执行手册，本次未执行；不包含自动安装、`cargo oxide update`、驱动升级或生产切换。

```bash
: "${CUDA_RUST_REFERENCE:?Set the absolute path of the pinned isolated checkout}"
git -C "$CUDA_RUST_REFERENCE" rev-parse HEAD
git -C "$CUDA_RUST_REFERENCE" status --short
```

HEAD必须是锁定SHA，工作树改动必须为单独记录的观察/负例patch，否则停止。T00核实27的实际rustc/LLVM/CUDA/Lean与可选Tile条件；旧Atomic构建无需跟着升级。下面shell块按Linux/bash语法，现场为其他OS时先做等价且可审查的环境/argv计划，不能假设已支持。

以下命令从`$CUDA_RUST_REFERENCE/cuda-oxide`运行。`cargo oxide`在该workspace由现有alias提供；doctor本身可能触发alias工具构建，仍须先满足锁定依赖。保存版本输出，不依赖`nvidia-smi`中的CUDA上限推断实际nvcc。

```bash
cd "$CUDA_RUST_REFERENCE/cuda-oxide"
rustc --version --verbose
cargo --version
nvcc --version
cargo oxide doctor
```

这类探测输出只进入环境/能力记录，exit0不授GPU模型资格。

### 4.2 Lean数学模型、exporter与负例

[现有Justfile](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/Justfile)和[实际CI配置](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/.github/workflows/unit-tests.yml)提供以下入口。正式资格禁止继承`CUDA_OXIDE_LEAN_EXPORT_ONLY`；两次调用都要求Lean且禁用Lean缓存：

```bash
env -u CUDA_OXIDE_LEAN_EXPORT_ONLY \
  CUDA_OXIDE_REQUIRE_LEAN=1 CUDA_OXIDE_NO_LEAN_CACHE=1 \
  python3 oxide-proofs-preview/check.py
env -u CUDA_OXIDE_LEAN_EXPORT_ONLY \
  CUDA_OXIDE_REQUIRE_LEAN=1 CUDA_OXIDE_NO_LEAN_CACHE=1 \
  python3 oxide-proofs-preview/check-exporter.py
env -u CUDA_OXIDE_LEAN_EXPORT_ONLY \
  CUDA_OXIDE_REQUIRE_LEAN=1 CUDA_OXIDE_NO_LEAN_CACHE=1 \
  cargo test --locked -p lean-exporter --all-targets
```

保存actual test/negative/failed/skipped数、Lean/proof库hash、实际义务和axiom清单。`check.py`只检查数学模型，不能单独证明Rust/MIR提取；exporter与编译管线也要检查。当前pin已合入hardening，历史负例是回归测试，不能称这些漏洞仍存在。

`cargo oxide lean-export`是现有inspection命令，会设置export-only并跳过真正Lean验证/检查擦除，且会处理inspection产生的PTX；**不把它列入资格成功链**。`#[verify]`路径不使用`--device-debug`绕过；需要调试位置时按实际支持的lineinfo方案记录。CPU模型/exporter通过仍不是SM89 GPU通过。[27](27_cuda_rust_source_audit.md)

### 4.3 现有safe_vecadd显式SM89构建

[safe_vecadd](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/cuda-oxide/examples/safe_vecadd/src/main.rs)包含DisjointSlice和plain mutable slice两种kernel，宿主检查1000元素输出；适合作为有限前端资格入口。它不是Inkling算子或性能基准。

K00应为本次run分配**新的、未复用**构建输出路径，确保Cargo实际重新编译kernel；只设置NO_LEAN_CACHE而复用已完成build不能保证验证重跑。路径由冻结计划提供，不能覆盖生产输出：

```bash
: "${OXIDE_AUDIT_BUILD:?Set a new absolute build directory for this frozen run}"
env -u CUDA_OXIDE_LEAN_EXPORT_ONLY \
  CUDA_OXIDE_REQUIRE_LEAN=1 CUDA_OXIDE_NO_LEAN_CACHE=1 \
  CARGO_INCREMENTAL=0 CARGO_TARGET_DIR="$OXIDE_AUDIT_BUILD" \
  cargo oxide build safe_vecadd --arch sm_89 --materialize-cubin
```

`build`、`--arch`和`--materialize-cubin`均有[固定源码/CI入口](https://github.com/NVIDIA/cuda-rust/blob/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b/.github/workflows/examples-compile.yml)，上游CI对应safe例子使用的其他架构不能替代本次SM89实测。即使SM89 PTX可生成，materialize路径失败也须按实际错误报告，不降目标架构或自动换工具链。

收集：完整编译stderr/stdout、实际verifier调用与义务数、源/verified/emitted IR、PTX/CUBIN与`.oxart`清单、symbol/ABI、compiler/ptxas/libdevice等hash、实际target/PTX version及资源报告。宿主程序打印“Lean proved”摘要不能替代这批编译证据；源码注释中的检查删除数量也不作为本次观测值。

### 4.4 现有例子的目标GPU执行

在已授权隔离窗口中，将T00锁定的4090 UUID传入。例子内部选择device0，显式可见设备映射必须保存：

```bash
: "${OXIDE_GPU_UUID:?Set the RTX4090 UUID from the locked T00 inventory}"
CUDA_VISIBLE_DEVICES="$OXIDE_GPU_UUID" \
  "$OXIDE_AUDIT_BUILD/release/safe_vecadd"
```

必须核对本次实际设备=RTX4090/CC8.9、实际加载artifact hash/target、两个预期kernel的真实launch、D2H与输出断言、没有skip/仅PTX检查分支。必要时用独立诊断trace核实launch，诊断计时不作性能数据。源码参考binary拥有自己的context，这是隔离source smoke；生产Atomic接入由K04借用原context，不直接把这个宿主程序嵌进引擎。

不使用`safe_gemm_sol_final`在4090的exit0充当GEMM执行：固定源码在不支持tcgen05的设备上存在仅检查PTX或打印说明后成功返回路径。任何测试的原始覆盖记录保存`expected_kernel_count / executed_kernel_count / skipped_kernel_count / skip_reason`，未实际执行对应feature就不得授该GPU能力。这些是`artifacts.raw_execution`指向的raw记录字段，映射到候选Schema的`execution.kernel_launch_count / reason_code`，不向封闭的execution对象添加未声明字段。[27](27_cuda_rust_source_audit.md)

## 5. 动态安全检查：工具现有，Atomic候选harness待实现

[Compute Sanitizer官方文档](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/)区分memcheck、racecheck、initcheck、synccheck。先memcheck，其余不能替代内存越界检查。默认`error-exitcode`可能在应用成功而工具发现错误时仍为0，因此显式设置非零退出值。

下面是现有工具对上一节已构建source例子的命令，仍仅在目标机授权执行后产生证据，不代表本次已运行：

```bash
CUDA_VISIBLE_DEVICES="$OXIDE_GPU_UUID" compute-sanitizer \
  --tool memcheck --error-exitcode 86 "$OXIDE_AUDIT_BUILD/release/safe_vecadd"
CUDA_VISIBLE_DEVICES="$OXIDE_GPU_UUID" compute-sanitizer \
  --tool racecheck --error-exitcode 86 "$OXIDE_AUDIT_BUILD/release/safe_vecadd"
CUDA_VISIBLE_DEVICES="$OXIDE_GPU_UUID" compute-sanitizer \
  --tool initcheck --error-exitcode 86 "$OXIDE_AUDIT_BUILD/release/safe_vecadd"
CUDA_VISIBLE_DEVICES="$OXIDE_GPU_UUID" compute-sanitizer \
  --tool synccheck --error-exitcode 86 "$OXIDE_AUDIT_BUILD/release/safe_vecadd"
```

最小vecadd没有覆盖所有shared/barrier/cp.async或Atomic状态风险，不能从四工具零报告外推这些能力。K05需用NEW Atomic候选harness和AX19/20故障fixture执行相应路径；argv、kernel筛选、child process跟踪、expected/executed counts写入冻结manifest。测试仅在隔离worker故意注入非法GPU操作，不能污染旧服务context。

`racecheck`主要报告shared-memory hazard；不能覆盖全部global/host/FFI并发。版本支持时记录并启用stream-ordered allocation race检查，仍需arena子区间canary/范围oracle、event/lease/epoch与graph寿命测试。缺工具/权限/覆盖保留BLOCKED/缺项，不能改成skip后全套PASS。不要为让sanitizer通过强制串行化生产异步路径，再把串行结果冒充原并发资格。

## 6. Profiling、探索与正式统计

### 6.1 定位热点的诊断采样

先使用已安装[Nsight Systems](https://docs.nvidia.com/nsight-systems/UserGuide/index.html)的CUDA/NVTX时间线定位完整请求关键路径；再以[Nsight Compute](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html)只采少量kernel的launch、访存、寄存器/occupancy、scheduler/stall。具体支持选项由T00验证，所有实际argv保存。

Compute的replay/cache/clock会改变观测条件；本方案不授权锁频/改power limit，采样默认显式`--clock-control none`并记录实际温度/功耗/频率。cache/replay双方一致；观察真实priming时按工具支持选择application/range replay与`--cache-control none`。Systems先graph-level，只有需要节点原因时对小范围node trace，避免把高开销采样当正常运行。

**正式PF/G3计时不挂profiler或sanitizer。** profiler给出因果假设，monotonic请求/Agent计时给产品结论；不能将所有重叠kernel时间加总为wall time，也不能把理论occupancy最大当最优配置。

### 6.2 探索和确认

搜索限额为看数据前冻结的策略提案：一个热点family、总≤24个不同候选、≤4个进入GPU微基准、≤2个进入完整E2E探索、最终1个冻结配置进入holdout。初始与最多两轮有profiler依据修正共享总预算。CPU2h/GPU4h和单候选compile/proof5min只可作为初始提案，由T00与计划在看数据前确定；不代表已跑、承诺耗时或费用授权。

每primary cell探索12pairs；确认≥30独立case、≥3时间块、≥10000次case/stratum配对bootstrap。同case多seed/重复不是新增独立n。按预生成均衡AB/BA与每5对anchor，固定prefix/process/OS cache条件、P/N、质量、实际完整能力key与允许差异。保留失败/timeout/全部回退，按原wall budget计惩罚。[14](14_benchmarks.md)

先冻结唯一winner、代码/产物/shape dispatch再开holdout；同时多winner或确认后重选，须预登记多重比较/序贯规则或新独立集，不能给每个候选95%CI后只报最好者。报告探索与确认差异，不能以“搜了很多次总有一快”作为收益证据。

原门保持：单项主要请求中位数至少降5%且CI支持正收益；主力迁移真实任务中位数至少降10%；关键层p95退化≤5%并满足绝对SLO；质量150 Java/300工具、重大错误零容忍；tail每cell≥200requests、soak≥8h且≥200requests。样本不足保持BLOCKED/INSUFFICIENT_EVIDENCE，不为限额删质量或长context。预算用尽未达门可NO_BENEFIT，不能等价解释为真实效应严格为0。

## 7. PLANNED：新runner和Atomic资格命令

下列文件/命令依[31](31_kernel_tasks.md)对应任务实施后才存在。执行前切回Atomic实验工作树，不在cuda-rust-reference目录调用。所有profile从固定资产/实际shape构造；文档命令不是给上游CLI新增虚构flag。

### 7.1 K01/K03工具和搜索

```bash
python3 -m unittest discover -s tests/inkling_lab -p test_kernel_contracts.py -v
python3 -m unittest discover -s tests/inkling_lab -p test_kernel_search.py -v
python3 tools/inkling-lab/kernel_search.py \
  --plan profiles/kernel-search-plan.json --out evidence/K03-search
```

`kernel_search.py`是NEW独立controller，输入SearchPlan、输出candidate/build/proof/raw records，复用T01验证和run能力；不宣称原`lab.py`已支持某个未定义search kind。K03最初只准build/proof阶段；只有K04/K05前置资格具备且plan明确列出时，runner才能进一步排队执行目标GPU阶段。未实现的stage返回2，不用空结果伪造完整闭环。

### 7.2 K04/K05运行与正确性

```bash
ctest --test-dir build-inkling4090 -R '^test-inkling-kernel-bridge$' \
  --output-on-failure --no-tests=error
python3 tools/inkling-lab/lab.py validate --manifest profiles/kernel-candidate.json
python3 tools/inkling-lab/lab.py qualify --suite G2 \
  --manifest profiles/kernel-candidate.json --out evidence/K05-correctness
python3 tools/inkling-lab/lab.py qualify --suite G4 \
  --manifest profiles/kernel-candidate.json --out evidence/K05-capacity
```

K04/K05注册的runtime harness须真实调用候选并保存同artifact的sanitizer与E/N/模型状态证据。缺harness/fixture/硬件返回BLOCKED；G2/G4不能因上游进程exit0就通过。G2和sanitizer运行的时延不得作为G3性能基线。

### 7.3 K06配对确认与registry

```bash
python3 tools/inkling-lab/lab.py validate --manifest profiles/kernel-paired.json
python3 tools/inkling-lab/lab.py run \
  --manifest profiles/kernel-paired.json --out evidence/K06-paired
python3 tools/inkling-lab/lab.py compare \
  --baseline evidence/K06-paired/baseline \
  --candidate evidence/K06-paired/candidate --out evidence/K06-compare
python3 -m unittest discover -s tests/inkling_lab -p test_kernel_registry.py -v
```

paired profile沿原pair-plan合同，冻结A/B各自完整key、共同schedule、fixed factors和allowed differences。相同目标不等于完整key必须相同；算术变化沿原N/Q分类。registry只引用真实通过的独立gate，code hash、driver、shape、layout、proof假设或budget/graph变更使旧资格失效。test工具与registry审查不执行生产G7。

## 8. 原始记录、故障恢复与退出

每run保留`manifest.json / raw.jsonl / metrics.json / stdout.log / stderr.log / artifacts.sha256`及独立gate。K证据额外保存SearchPlan、CandidateSpec、toolchain/dependency lock、verified/emitted IR、proof/checker/axiom记录、PTX/cubin/ABI、resource report、实际launch/skip、module/graph/arena generation、ticket/event/lease和stop registry链接。不要只交汇总表。

原lab退出码：0指定操作真实完成且检查通过；1执行失败；2缺能力/环境/未实现；3输入/版本合同非法。proof UNKNOWN/ERROR作为原因独立记录，不新增伪成功退出。CPU工具或source proof成功可在其实际scope记录结果，不能用`target_4090`标签；只有实际4090推理证据进入对应GPU能力。

首个越界、NaN、模型/循环状态污染、错误工具提交、静默截断、OOM/swap或余量违规立即停止性能计分。enqueue后错误sticky，禁止token/tool commit；drain/退役context，device context损坏则隔离worker重建，从同预算合格profile的committed prefix恢复，不重复已完成工具副作用。未知GPU完成状态不能释放buffer或卸载仍被graph引用的module。

仅compile、仅proof、仅作者CI、仅微基准或source smoke都不能授完整Inkling能力。最多两轮有因果证据修正后仍无净益结案；旧失败和历史NO_BENEFIT保留，重新开启需要新证据与新experiment_id。最终交付仍沿T12与G7边界。
