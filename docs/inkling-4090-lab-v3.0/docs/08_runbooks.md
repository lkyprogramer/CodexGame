# 08 · 命令手册

除特别说明外，命令都在 4090 上以 hhtele 用户执行。标 **W** 的步骤只能经 `lab_window.sh` 执行。下面的命令只做过 `bash -n` 语法检查，**没有在 4090 上运行过**；第一次执行时按实际输出修正本页。

## 0. 投放文档包（在本地开发机执行）

```bash
ssh 4090 'mkdir -p ~/inkling-lab-v3'
scp -r docs/inkling-4090-lab-v3.0 4090:inkling-lab-v3/pkg
```

## 1. T00 环境文件与驱动基线

```bash
mkdir -p ~/inkling-lab-v3/{evidence,toolchains,models,src,runs,logs}
cat > ~/inkling-lab-v3/env.sh <<'EOF'
export LAB=$HOME/inkling-lab-v3
export PKG=$LAB/pkg
export RUSTUP_HOME=$LAB/toolchains/rustup
export CARGO_HOME=$LAB/toolchains/cargo
export CUDA_HOME=$LAB/toolchains/cuda-12.8
export NVCC=$CUDA_HOME/bin/nvcc
export PATH=$CARGO_HOME/bin:$PATH
export ASTRAL_CUDA_ARCHS=89
export CARGO_BUILD_JOBS=6
export MODELS=$LAB/models
guard() { bash "$PKG/tools/driver_guard.sh" check "$LAB/evidence/driver-baseline.txt"; }
EOF
source ~/inkling-lab-v3/env.sh
bash "$PKG/tools/driver_guard.sh" snapshot "$LAB/evidence/driver-baseline.txt"
sha256sum "$LAB/evidence/driver-baseline.txt" | tee "$LAB/evidence/driver-baseline.sha256"
python3 "$PKG/tools/preflight.py" --output "$LAB/evidence/preflight.json"
```

`$CUDA_HOME/bin` 故意不加入 PATH：conda 环境可能带有自己的 gcc 或 python，加入后会遮蔽系统版本。各处一律显式使用 `$NVCC`。

## 2. T01 Rust（用户目录）

```bash
source ~/inkling-lab-v3/env.sh; guard
curl --proto '=https' --tlsv1.2 -fsSL https://static.rust-lang.org/rustup/dist/x86_64-unknown-linux-gnu/rustup-init -o "$LAB/toolchains/rustup-init"
chmod +x "$LAB/toolchains/rustup-init"
"$LAB/toolchains/rustup-init" -y --no-modify-path --profile minimal --default-toolchain none
rustup toolchain install 1.100.0 --profile minimal -c rustfmt -c clippy
cargo +1.100.0 --version; guard
```

static.rust-lang.org 实测约 2 MB/s；如果太慢，设 `RUSTUP_DIST_SERVER=https://rsproxy.cn`（实测约 14 MB/s）。

## 3. T02 CUDA 12.8.1 编译工具（conda，用户目录）

```bash
source ~/inkling-lab-v3/env.sh; guard
CONDA=$HOME/anaconda3/bin/conda
CUDA_PKGS="cuda-nvcc cuda-cudart-dev cuda-nvrtc-dev cuda-cccl libcublas-dev cuda-cuobjdump cuda-nvdisasm cuda-profiler-api cuda-driver-dev cuda-nvml-dev"
$CONDA create --dry-run --json -p "$CUDA_HOME" --override-channels --strict-channel-priority \
  -c nvidia/label/cuda-12.8.1 -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge $CUDA_PKGS > "$LAB/logs/cuda-dryrun.json"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); [print(a["name"], a["version"], a.get("channel", "")) for a in d["actions"]["LINK"]]' \
  "$LAB/logs/cuda-dryrun.json" | tee "$LAB/logs/cuda-dryrun.txt"
bash "$PKG/tools/driver_guard.sh" scan "$LAB/logs/cuda-dryrun.txt"
```

人工检查 `cuda-dryrun.txt`：其中不能有 nvidia 驱动、内核模块或 `cuda-drivers` 一类的包（`cuda-driver-dev` 是链接用的 stub 库，允许）。确认后再执行安装：

```bash
source ~/inkling-lab-v3/env.sh; guard
$HOME/anaconda3/bin/conda create -y -p "$CUDA_HOME" --override-channels --strict-channel-priority \
  -c nvidia/label/cuda-12.8.1 -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge cuda-nvcc cuda-cudart-dev cuda-nvrtc-dev cuda-cccl libcublas-dev cuda-cuobjdump cuda-nvdisasm cuda-profiler-api cuda-driver-dev cuda-nvml-dev \
  2>&1 | tee "$LAB/logs/cuda-install.log"
bash "$PKG/tools/driver_guard.sh" scan "$LAB/logs/cuda-install.log"
"$NVCC" --version; guard
```

conda-forge 走清华镜像（实测约 9 MB/s；官方源约 0.4 MB/s，第一次安装卡了 40 多分钟）；阿里云没有 conda-forge 镜像（404）。nvidia 频道国内镜像不全，仍用官方源。只在命令行指定频道，不改 `~/.condarc`。求解失败时，保存原始输出并停下，**不要**改用 runfile 或 apt。

## 4. T03 资产（ModelScope + aria2c）

```bash
source ~/inkling-lab-v3/env.sh
F="$PKG/tools/ms_fetch.py"
python3 "$F" plan --model unsloth/Inkling-2-Mini-GGUF --hf-revision 8078d149286eec7193795413b9e0643da6d11fa1 --out "$MODELS/unsloth" --strip-suffix _file \
  --include 'Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf_file' --include 'Mainline_Support/Inkling-2-Mini-UD-Q8_K_XL.gguf_file' \
  --include 'Mainline_Support/dspark-Inkling-2-Mini-Q8_0.gguf_file' \
  --expect 'Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf_file=e64276656f072e9b2197a61723667cbdb71da66a716ffd966e572c21088f3cd3' \
  --expect 'Mainline_Support/Inkling-2-Mini-UD-Q8_K_XL.gguf_file=2da51788d43a17e1f033bec420fa83ba9cb87ac1f0130dc9135a4d2ed2678b68' \
  --expect 'Mainline_Support/dspark-Inkling-2-Mini-Q8_0.gguf_file=3da00cf7c31bbe5662b3c0d373ecf782d74d32ef43990acc158ce60c2add72e0'
python3 "$F" plan --model thinkingmachines/Inkling-2-Mini --hf-revision c9d028302cd0f035fdf8e7e91f089a4ce94d2195 --out "$MODELS/inkling-native" \
  --exclude 'model-00001-of-00001.safetensors' \
  --expect 'mtp.safetensors=7c3b651317f01f73bcf4e1dceba66ef8b7e1a1eac6bc171e882e690a4b10a1d2'
python3 "$F" plan --model thinkingmachines/TML-d24-varloop-research --hf-revision 91a57fe2b779bbd12c0f74d1f518cbd5b84e8d0d --out "$MODELS/varloop-native" \
  --expect 'model-00001-of-00001.safetensors=79e60b65c4f2a2a5acdb8e3c7b6994bf00da5477f45d18027afbfad752a64595' \
  --expect 'mtp.safetensors=905d548692b1eb1d1aa278b8798db66ff88d94d0fc7609bf77baab90e99c76c7'
for d in unsloth inkling-native varloop-native; do
  aria2c --input-file="$MODELS/$d/.ms_fetch/aria2.txt" -x 8 -s 8 -j 1 --continue=true \
    --auto-file-renaming=false --check-integrity=true --console-log-level=warn --summary-interval=60
  python3 "$F" verify --out "$MODELS/$d" --lock "$MODELS/models.lock.json"
done
```

`plan` 拉取 ModelScope 文件列表：`--expect` 与 ModelScope 的 Sha256 不一致时，直接失败，不下载。`verify` 逐个文件重算 SHA256，结果合并写入 lock。

## 5. T04/T05 Astral

```bash
source ~/inkling-lab-v3/env.sh; guard
git clone https://github.com/syntheticminds-lab/Astral-Inference-Server "$LAB/src/astral"
cd "$LAB/src/astral" && git checkout -b inkling-4090 49a0a2bee3270ad7518cebe7a059496b250180d1
# T04: CPU 侧测试，隐藏 GPU，避免与生产争用显存
CUDA_VISIBLE_DEVICES= nice -n 10 cargo test --workspace 2>&1 | tee "$LAB/logs/t04-cargo-test.log"
# T05: GPU kernel 构建（sm_89）
nice -n 10 cargo build --release 2>&1 | tee "$LAB/logs/t05-build.log"
./target/release/astral version | tee "$LAB/evidence/astral-version.txt"
for f in target/release/build/astral-kernels-src/*/out/*.fatbin; do echo "== $f"; "$CUDA_HOME/bin/cuobjdump" --list-elf "$f"; done | tee "$LAB/evidence/fatbin-elf.txt"
guard
```

## 6. T06 llama.cpp 参考

```bash
source ~/inkling-lab-v3/env.sh; guard
mkdir -p "$LAB/src/llama.cpp" && cd "$LAB/src/llama.cpp"
git init -q && git remote add origin https://github.com/ggml-org/llama.cpp
git fetch --depth 1 origin 532d67426bb874f06a8acc6959af81b34206f7f9 && git checkout -q --detach FETCH_HEAD
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DCMAKE_CUDA_COMPILER="$NVCC" -DCUDAToolkit_ROOT="$CUDA_HOME" -DLLAMA_CURL=OFF
nice -n 10 cmake --build build -j 8 --target llama-server llama-perplexity llama-eval-callback llama-tokenize
guard
```

llama.cpp 需要 `CUDA::cuda_driver`（链接用的 stub）和 `nvml.h`，所以 T02 的包列表包含 `cuda-driver-dev` 与 `cuda-nvml-dev`；缺这两个包时，CMake 报 "CUDA::cuda_driver not found"，编译报 "nvml.h: No such file"（2026-11-26 实际遇到）。运行时 `libcuda.so.1` 仍解析到系统驱动的库，已用 `ldd` 确认。T06 的验收还包括：用 `--help` 核对 W1 脚本中用到的每个 llama.cpp 参数。

## 7. W1（T07–T10，约 60 分钟）

先写好 `$LAB/runs/w1.sh`（模板如下，按 T06 核对后的参数调整），然后与用户确认停服时间。2026-11-26 实际执行的版本在 [`tools/w1/`](../tools/w1/)：`w1.sh` 在模板基础上增加了驱动 check、`tokparity.py`（`llama-tokenize` 对 HF tokenizer）和 llama-server 贪心对照；`v2.sh` / `v2.py` 是 V2 的 chat 模板分词对照。Strata 停止期间直接运行 `bash $LAB/runs/w1.sh`。

```bash
#!/usr/bin/env bash
set -uo pipefail
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
AST="$LAB/src/astral/target/release/astral"; LL="$LAB/src/llama.cpp"
OUT="$LAB/runs/w1/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$OUT"
nvidia-smi --query-gpu=memory.used,clocks.sm,clocks.mem,temperature.gpu,power.draw --format=csv > "$OUT/gpu-start.csv"
"$AST" version > "$OUT/version.txt" 2>&1
"$AST" hw --bench > "$OUT/hw.json" 2>&1
"$AST" selftest > "$OUT/selftest.txt" 2>&1; echo "selftest rc=$?" >> "$OUT/STATUS"
"$AST" gguf-info "$A1" --tensors > "$OUT/gguf-info.txt" 2>&1; echo "gguf-info rc=$?" >> "$OUT/STATUS"
(cd "$LAB/src/astral" && bench/golden_llamacpp.sh "$A1" "$LL" "$OUT/golden") > "$OUT/golden.txt" 2>&1
G=$(ls -d "$OUT"/golden/*-golden | tail -1)
"$AST" verify-embd "$A1" "$G/eval_callback.log" > "$OUT/verify-embd.txt" 2>&1; echo "verify-embd rc=$?" >> "$OUT/STATUS"
"$AST" verify-model "$A1" "$G/eval_callback.log" > "$OUT/verify-model.txt" 2>&1; echo "verify-model rc=$?" >> "$OUT/STATUS"
"$LL/build/bin/llama-tokenize" -m "$A1" -p "The capital of France is" --ids --log-disable > "$OUT/ids.txt" 2>&1
IDS=$(tail -1 "$OUT/ids.txt" | tr -d '[],')
"$AST" generate "$A1" 128 $IDS > "$OUT/astral-generate.txt" 2>&1; echo "generate rc=$?" >> "$OUT/STATUS"
nvidia-smi --query-gpu=memory.used,clocks.sm,clocks.mem,temperature.gpu,power.draw --format=csv > "$OUT/gpu-end.csv"
```

```bash
source ~/inkling-lab-v3/env.sh
bash "$PKG/tools/lab_window.sh" 60 bash "$LAB/runs/w1.sh"
```

llama.cpp 侧的 128 token 贪心序列与分词对照（V2/V5），在 W1 或 W2 中用 `llama-server` 的 `/completion`（token 数组作 prompt，`temperature` 0，`n_predict` 128）补齐，参数以 T06 核对结果为准。

## 8. 性能统计

`paired_stats.py` 的输入是每行一个配对的 CSV，表头固定为 `pair_id,case_id,stratum,baseline_ms,candidate_ms`。decode 速度换算成每 token 毫秒（1000 / tok/s）后填入；一个 stratum 一个文件。

```bash
python3 "$PKG/tools/paired_stats.py" --input "$LAB/runs/t14/decode_ms.csv" --output "$LAB/runs/t14/decode_stats.json"
```
