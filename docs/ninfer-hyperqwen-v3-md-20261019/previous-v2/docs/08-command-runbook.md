> V3 继承资料：P0—P6 的任务目标和上游合入顺序继续有效。命令依赖须先按根目录 `support/REHYDRATE.md` 恢复。

# 08｜命令手册与执行注意

命令在用户的独立开发/测试目录执行。本包没有连入你的主机。所有大写环境变量先按现场填写；不包含 API key 实值。已存在 target 与本计划拟新增 target 严格区分。

## 1. 获取固定源码（不会操作生产目录）

```bash
export PACK=/path/to/ninfer-upstream-merge-20261015
export WORK=/path/to/isolated-ninfer-work
export OUT=/path/outside/repository/ninfer-merge-evidence
mkdir -p "$WORK" "$OUT"
cd "$WORK"
git clone --branch b0-scanner https://github.com/lkyprogramer/ninfer-4090.git repo
cd repo
git remote add upstream https://github.com/tensorninja/ninfer-4090.git
git fetch upstream tensorninja
export SRC="$PWD"
export O=e0b05f7cb46adae2787be2ccbe605e1b0c9b3923
export U=5b99996bc7c1fe6ff27f271a205eb605302ec8bb
export B=44a2c6c3392c9d51e76a895ed97bf1867530d252
git cat-file -e "$O^{commit}"
git cat-file -e "$U^{commit}"
python3 "$PACK/scripts/source_audit.py" --repo "$SRC" \
  --out "$OUT/P0-source-audit" --merge-probe
```

若已有独立克隆，复用并先审计，不能重新 clone 覆盖原目录。若远端 HEAD 已前进，仍使用本包 SHA；要改目标则重新生成差异与计划，不能只改 source-lock 里的一个字段。

## 2. 建立开发 worktree

```bash
git -C "$SRC" worktree add -b integrate/upstream-20261015 \
  "$WORK/integrate" "$O"
export INTEGRATE="$WORK/integrate"
git -C "$INTEGRATE" config rerere.enabled true
git -C "$INTEGRATE" status --short
```

禁止对生产工作区运行 reset --hard/clean -fd。没有明确记录的脏改动先保留并分类。rerere 只能复用已审核解析，不能把自动复用当成新的 review。

## 3. 里程碑 import

每次 import 前前一 Phase gate 必须通过，工作树必须干净。以下展示 P1，后续 SHA 取 source-lock。

```bash
cd "$INTEGRATE"
git merge --no-ff --no-commit 94cdb5a975e514935ed4be214ee7f776a8683635
# A nonzero return due to conflicts is expected here, not an instruction to ignore other errors.
git diff --name-only --diff-filter=U
git ls-files -u
# Resolve using docs/03-conflict-resolution.md; retain all tracked custom dispositions.
# Stage only reviewed resolutions. Never run checkout --theirs . or checkout --ours .
git diff --cached --check
# Commit only when the unmerged-index list is empty; this is an unqualified phase-base.
git commit -m "merge: import upstream frontend and cache milestone"
```

该 import commit 可以暂时存在待修复测试/接口问题，但必须明确标为未资格化，不部署。Phase 内任务从这个固定实验基点建工作树并行，最终统一集成、编译、review 和测试。通过 gate 后才形成 release-candidate tag。禁止把中间 import commit 直接作为生产版本。

## 4. CMake 主构建和测试

以下选项与仓库 Dockerfile/CMake 使用保持一致；需要 CUDA 工具链和相关依赖。并行度按内存与编译资源控制，不把所有宿主 CPU 默认打满。

```bash
export BUILD="$WORK/build-merge-27b"
cmake -S "$INTEGRATE" -B "$BUILD" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DNINFER_BUILD_APPS=ON -DBUILD_TESTING=ON \
  -DNINFER_BUILD_BENCHMARKS=ON \
  -DNINFER_BUILD_QWEN3_8_27B=ON -DNINFER_BUILD_QWEN3_6_35B_A3B=OFF
cmake --build "$BUILD" --parallel 4
ctest --test-dir "$BUILD" --show-only=json-v1 > "$OUT/ctest-inventory.json"
ctest --test-dir "$BUILD" --output-on-failure \
  -R 'ninfer_qwen3_8_(frontend|tokenizer_work|tokenization_equivalence|encoding_restart|boundary_encoding|legacy_oracle)_test' \
  --output-junit "$OUT/frontend.junit.xml"
python3 "$PACK/scripts/check_junit.py" "$OUT/frontend.junit.xml" \
  --require '^ninfer_qwen3_8_frontend_test$' \
  --require '^ninfer_qwen3_8_tokenizer_work_test$' \
  --require '^ninfer_qwen3_8_tokenization_equivalence_test$' \
  --require '^ninfer_qwen3_8_encoding_restart_test$' \
  --require '^ninfer_qwen3_8_boundary_encoding_test$' \
  --require '^ninfer_qwen3_8_legacy_oracle_test$'
```

从 P4 起，使用新的 BUILD 目录分别构建 35B-only 和 both-packages；不要在同一 build 目录来回覆盖选项后声称拥有三种产物。

## 5. 真实模型测试：已核实的环境变量

上游 `test_engine_prefix_real.cpp` 使用 `NINFER_QWEN3_8_27B_WEIGHTS`，不是凭经验猜测的 ARTIFACT/MODEL 变量；未设置时返回 77。这个测试的 context 只有 4096，长上下文要另跑。

```bash
export MODEL=/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer
export NINFER_QWEN3_8_27B_WEIGHTS="$MODEL"
# Do not set NVFP4 weights to the groupwise artifact.
ctest --test-dir "$BUILD" --output-on-failure \
  -R '^ninfer_qwen3_8_27b_prefix_real_test$' \
  --output-junit "$OUT/prefix-real.junit.xml"
python3 "$PACK/scripts/check_junit.py" "$OUT/prefix-real.junit.xml" \
  --require '^ninfer_qwen3_8_27b_prefix_real_test$'
```

tokenizer_real/decision/LoRA 等其他真实测试的环境变量与命令，必须由 P0/P4 从对应 source 的 getenv/CLI 和 CTest inventory 核实，再写入 run manifest；本包不为未核实变量编造名字。

## 6. G1 单独执行

先把 O 原始构建和 candidate 构建分开。原有驱动名称与选项已经核实。资源、cases 和 toggle 必须由 P0 manifest 提供，以下命令要求它们已存在。

```bash
export RESOURCES=/path/to/pinned/frontend-resources
export CASES=/path/to/original-g1-cases.jsonl
export TOGGLE=/path/to/pinned/thinking-toggle-template.jinja
for impl in legacy candidate; do
  "$BUILD/tests/ninfer_qwen3_8_g1_diff" \
    --impl "$impl" --profile real --resources "$RESOURCES" \
    --cases "$CASES" --toggle-template "$TOGGLE" \
    --seed 20260925 --fuzz 20000 \
    --output "$OUT/g1-real-$impl.jsonl" \
    --summary "$OUT/g1-real-$impl-summary.json"
  "$BUILD/tests/ninfer_qwen3_8_g1_diff" \
    --impl "$impl" --profile synthetic --resources "$RESOURCES" \
    --cases "$CASES" --seed 20260925 --fuzz 20000 \
    --output "$OUT/g1-synthetic-$impl.jsonl" \
    --summary "$OUT/g1-synthetic-$impl-summary.json"
done
```

P1 会实现/核对结果对齐器与新 boundary suite。不能仅看以上程序都返回 0 就认定两份 JSONL 一致；summary 的 applied/rows/hash 与逐 case 差异都要检查。新 suite 不替代旧 suite 的身份。

## 7. 无权重生产镜像

```bash
cd "$INTEGRATE"
export CANDIDATE_SHA="$(git rev-parse --short=12 HEAD)"
docker build -f Dockerfile.sm89-nobake \
  --label org.opencontainers.image.revision="$(git rev-parse HEAD)" \
  -t "ninfer-4090:merge-$CANDIDATE_SHA" .
docker image inspect "ninfer-4090:merge-$CANDIDATE_SHA"
```

这只构建镜像，不启动第二个模型。启动命令从现场 prod-captured profile 复制并按阶段仅改变明确因素；不要复制上游 baked-model Dockerfile 的默认参数。生产 image 的 ENTRYPOINT 已是 ninfer-serve，不能在其后又重复添加程序名。

## 8. Web 构建（可选发布物、完整源码验收需测试）

实际 packageManager 为 `bun@1.3.5`；scripts 中 test 是 bun test，build 是 tsc/vite。按仓库 lockfile 安装，不替换为未锁定的 npm 依赖版本。[S24]

```bash
cd "$INTEGRATE/apps/web"
bun install --frozen-lockfile
bun run typecheck
bun test
bun run build
```

真实浏览器 smoke 由 P5 新增，不能把单元测试写成已经做过浏览器验证。它不强迫生产无 dashboard 镜像包含 web。

## 9. 指标与 phase gate

```bash
python3 "$PACK/scripts/compare_metrics.py" \
  --baseline "$OUT/baseline.normalized.jsonl" \
  --candidate "$OUT/candidate.normalized.jsonl" \
  --out "$OUT/performance-gate.json"
# P4 only: add --allow-change kv_dtype for the declared codec migration.
python3 "$PACK/scripts/phase_gate.py" --plan "$PACK/plans/tasks.json" \
  --evidence "$OUT/P1/phase-result.json" --out "$OUT/P1/gate.json"
```

phase-result 中的每个 check 需引用同一 evidence root 下真实文件及 SHA256；必测 JUnit 重新解析；GPU 阶段需要 GPU UUID/模型 SHA 和实际执行记录；前一阶段 gate 也需存在。脚本只能核查证据一致性，不能替代 reviewer 的语义判断。

## 10. 严格证据绑定与工具自身的边界

`plans/tasks.json`启用strict_evidence。每phase有不可删的required_checks；每条check必须有id、正确kind、该集成source_commit、真实相对路径和sha256，reviewed_commit必须匹配集成提交。JUnit required名单由plan提供，不能从结果中删掉必测或把kind改成manual。每task commit和GPU模型SHA也要有效。raw目录只能在phase evidence根内，上一gate复制到inputs/previous-gate.json。

manual表示需要审查有哈希的原始/结构化证据，不等于自动相信一行PASS。该脚本不解析每种领域报告，也不能检测伪造GPU UUID；最终正确性依赖实际raw和review。新增测试/业务命令由各task实现或从源CLI核实；本包没有假装提供了完整NInfer测试框架。

`data/test-matrix.csv`把每个task的验证断言映射为独立V编号，全部PENDING。`profiles/production-capture.template.json`是待填模板，故意没有可直接启动的猜测参数。`profiles/benchmark-rules.json`是建议阈值，P0冻结后每次比较加`--rules`引用同一文件。
