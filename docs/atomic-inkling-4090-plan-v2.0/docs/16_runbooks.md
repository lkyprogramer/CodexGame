# 16 · 可执行运行手册

## 0. 命令分级

| 标签 | 含义 |
|---|---|
| PACK_READY | 本包已有工具；可立即在有Python的环境运行 |
| UPSTREAM_T00 | 上游已有构建/CLI接口；需目标机、工具链、固定源与资产 |
| PLANNED_AFTER_T01 | 本方案要求后续创建的实验接口，现在不能当现成功能调用 |
| RESEARCH_ONLY | 独立环境的来源复现，不属于主力服务启动 |

以下命令不是本次已经执行的4090记录。不要整篇复制为一个自动脚本；先满足每节前置条件，保存实际输出。

## 1. 文档包辅助工具（PACK_READY）

在解压后的包根目录：

~~~bash
python3 -B -m unittest discover -s tests -v
python3 tools/preflight.py --help
python3 tools/paired_stats.py --help
~~~

预期：辅助工具测试通过。它不加载模型，不证明GPU能力。在真正目标机采集：

~~~bash
mkdir -p evidence/inventory
python3 tools/preflight.py --output evidence/inventory/hardware.json
~~~

检查 `machine_match`、每个probe的错误、driver/nvcc差异、实际可用资源。MATCH只识别GPU型号，不代表预算、PCIe带宽或生产状态合格。

## 2. 固定源码（UPSTREAM_T00）

由执行者设置一个**新的空工作目录**，不要覆盖已有项目。示例在当前实验父目录创建 `atomic-engine-lab`：

~~~bash
git clone --no-checkout https://github.com/AtomicBot-ai/atomic-engine.git atomic-engine-lab
cd atomic-engine-lab
git checkout --detach fb69fff02101b048a0a165a3b502712dd2ca978f
git switch -c atomic-inkling-4090
git rev-parse HEAD
git status --short
~~~

预期HEAD完全匹配；工作树干净。先读本地AGENTS/构建说明。若已有同名目录，停止并选择新目录，不执行reset --hard或clean来“修复”。后续升级源另立baseline，不自动git pull。

## 3. 目标机SM89构建（UPSTREAM_T00）

~~~bash
cmake -S . -B build-inkling4090 \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
  -DLLAMA_BUILD_TESTS=ON -DLLAMA_BUILD_TOOLS=ON \
  -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON \
  -DLLAMA_BUILD_APP=OFF -DLLAMA_BUILD_UI=OFF -DLLAMA_OPENSSL=OFF \
  -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DGGML_METAL=OFF -DGGML_BLAS=OFF -DGGML_CCACHE=OFF
cmake --build build-inkling4090 --parallel 8
ctest --test-dir build-inkling4090 --output-on-failure --no-tests=error
./build-inkling4090/bin/llama-server --help > server-help.txt
./build-inkling4090/bin/llama-bench --help > bench-help.txt
sha256sum build-inkling4090/bin/llama-server build-inkling4090/bin/llama-bench
~~~

保存CMakeCache、build日志、driver/compiler/nvcc版本与实际test count。未知CMake选项warning要处理；现有CTest并不覆盖本方案新增的Inkling资格测试。CPU兼容与CUDA Toolkit/driver冲突在T00解决，不擅自更新整机驱动。

## 4. 下载已核实的启动锚点（UPSTREAM_T00）

此处仅为固定README中已核实文件，便于启动；不意味着IQ2达到主力质量。

~~~bash
hf download AtomicChat/Inkling-2-Mini-GGUF Inkling-2-Mini-AD-IQ2_M.gguf \
  --revision 309509848b3151419aa26d069eb03db57fd29a00 \
  --local-dir .work/models/mini-anchor
hf download AtomicChat/Inkling-2-Mini-GGUF dspark-Inkling-2-Mini-Q8_0.gguf \
  --revision 309509848b3151419aa26d069eb03db57fd29a00 \
  --local-dir .work/models/mini-anchor
sha256sum .work/models/mini-anchor/Inkling-2-Mini-AD-IQ2_M.gguf \
  .work/models/mini-anchor/dspark-Inkling-2-Mini-Q8_0.gguf
~~~

先检查磁盘余量与所需CLI；不在本轮文档生成环境下载模型。更高精度候选先枚举固定revision文件，生成锁文件后下载。不要虚构IQ3/Q4文件名或用漂移的main。

## 5. 普通CUDA串行smoke（UPSTREAM_T00，待T02资格）

在目标机**已提供实验窗口**、GPU无冲突且 `--help` 确认参数存在后，使用独立端口。这里没有engine budget，也没有spec，不能据此声称离散预算已支持Inkling。

~~~bash
./build-inkling4090/bin/llama-server \
  -m .work/models/mini-anchor/Inkling-2-Mini-AD-IQ2_M.gguf \
  --device CUDA0 -ngl all -fit off \
  -c 4096 -b 256 -ub 128 -np 1 \
  -fa on -ctk q8_0 -ctv q8_0 \
  --temp 0 --seed 42 --cache-ram 0 --ctx-checkpoints 0 --metrics \
  --alias inkling4090-candidate --host 127.0.0.1 --port 18081
~~~

若该KV格式/FA/模型op不支持，保存错误并标该能力行BLOCKED；F16或其他参数是新profile，不偷偷改完继续沿用q8标签。目标4090上生产Strata占满显存；只通过[43 §9](43_upstream_llamacpp_4090_site.md)的窗口包装脚本停启生产，禁止用pkill或直接kill生产进程。

另一个终端只做API可用性smoke：

~~~bash
curl --fail --silent --show-error http://127.0.0.1:18081/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"inkling4090-candidate","messages":[{"role":"user","content":"Return exactly the integer result of 17 + 25."}],"temperature":0,"max_tokens":128,"stream":false}'
~~~

这不是性能或质量基准；后续工具调用、reasoning和模板必须通过对应测试。

## 6. 正式实验入口（PLANNED_AFTER_T01）

以下文件/工具由T01及后续任务创建。先 `test -f` / `--help`，不存在必须返回BLOCKED，不能用伪输出补齐。

~~~bash
python3 tools/inkling-lab/lab.py validate --manifest profiles/mini-fixed-r3-serial.json
python3 tools/inkling-lab/lab.py qualify --suite G1 \
  --manifest profiles/mini-fixed-r3-serial.json --out evidence/T02
python3 tools/inkling-lab/lab.py run \
  --manifest profiles/mini-r3-ar-vs-dspark-paired.json --out evidence/T06-paired
python3 tools/inkling-lab/lab.py compare \
  --baseline evidence/T06-paired/baseline \
  --candidate evidence/T06-paired/candidate --out evidence/T06-compare
~~~

上述paired manifest是T01创建的成对实验输入，结构示例见manifests/pair-plan-example.json。run内部按共同的预生成AB/BA schedule交错启动baseline/candidate，生成所示两个子目录，并保持相同case/pair/stratum、P/N、cache条件。不是先运行全组A再全组B。G1的evidence/T02只作正确性资格，不能用作性能baseline。

manifest字段是本方案实验协议，不是Atomic CLI参数名。lab必须根据固定二进制 `--help` 和源码生成/校验真实argv，并保存最终argv。`candidate_k`、`loopcd_omega`、`kv_policy`等不得被当成已经存在的 `--...` 开关。

## 7. 配对统计（PACK_READY）

原始实验转换成单一stratum的CSV，保留pair/case关联与来源：

~~~bash
python3 tools/paired_stats.py \
  --input evidence/pairs-java-cold.csv \
  --bootstrap 10000 --seed 20261125 \
  --output evidence/stats-java-cold.json
~~~

表头见tools/README。不得把tok/s填进ms字段。低于30独立case只给描述值，不给CI；重复运行不增加case数。该工具不计算业务非劣、p95或最终发布门，不能用输出存在代替G3/G5。

## 8. 测试运行与失败

新增C++测试在对应任务注册后可用：

~~~bash
ctest --test-dir build-inkling4090 -R '^test-inkling-state$' \
  --output-on-failure --no-tests=error
~~~

固定源没有这个测试时“没有测试”是正确的未实现状态。日志要含测试数量，异常、timeout、skip原因。自动比较器拒绝没有raw data的PASS。

RESEARCH_ONLY命令见11/12。2DSD应固定S44实验分支，核查40所列runner/资产/SM89边界；不能把模型卡或诊断脚本输出冒充完整资格；Ouro reference环境与Atomic环境分开，CUDA依赖不满足时记录阻塞，不擅自换驱动。

## v1.2补充入口

本包新增[32内核运行手册](32_kernel_validation_runbook.md)：已核对的cuda-oxide源码命令、仅inspection的lean-export、实际SM89 launch、sanitizer与未来NEW kernel-search runner分列。它们不由本包自检自动执行。源码build/proof通过、编译-only/arch-skipped和目标GPU执行必须独立记账。

## v2缓存与Magnitude入口

L00后拟提供cache-run，见38；Magnitude M任务见42。当前仅包内preflight/paired_stats/helper tests可直接执行。未实现后端、语义验证器或未连接目标机时保持NOT_RUN/BLOCKED。源码下载、模型运行、安装依赖与部署均需处在后续实际工程授权范围。

## v2.1 · mainline对照与4090窗口

现场Toolkit是 `/usr/local/cuda-12.3`，§3构建前先 `export PATH=/usr/local/cuda-12.3/bin:$PATH`；生产在跑时可用内存约9 GiB，构建默认放进停服窗口。mainline b12751及PR变体（L0–L3）的固定构建、SM89算子检查、下载集和带自动恢复的停服包装见[43 §9](43_upstream_llamacpp_4090_site.md)。§4的AtomicChat IQ2_M锚点降为可选；主线smoke改用mainline布局的IQ4级文件，同一文件分别由Atomic A0与mainline L0加载做跨引擎对照。
