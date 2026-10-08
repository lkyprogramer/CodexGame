# 源码落点、构建与 donor 纪律

## 1. 固定worktree

使用现有`~/ninfer-4090`的只读源作参考；新clone/worktree单独建，不改生产源码。若输入归档不是git目录，先从固定远端commit恢复，再逐文件比对关键附件snapshot（`tools.source_audit`）。不能因目录名或PINNED_COMMIT文字正确就认定工作树没有改动。

```bash
git clone https://github.com/tensorninja/ninfer-4090.git ninfer-extreme-lab
cd ninfer-extreme-lab
git checkout --detach 44a2c6c3392c9d51e76a895ed97bf1867530d252
git switch -c lab/extreme-v2-observe
```

上游donor单独目录/remote固定`b88c0f6...`。对SHA不存在、网络失败、diff冲突显式BLOCKED，不静默改用main。

## 2. 容器内构建（已有13.2 devel，先记录image ID）

此命令在具备CMake≥3.28、Ninja、C++20、nvcc13.2、FFmpeg60+开发库、libcurl7.85+及项目third_party的**实验开发镜像**中执行；裸CUDA devel不自动包含全部依赖。T00检查并基于原NInfer Dockerfile生成可重建image，禁止在宿主全局apt/pip替换库。

```bash
cmake -S . -B build-sm89 -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DBUILD_TESTING=ON -DNINFER_BUILD_BENCHMARKS=ON \
  -DNINFER_BUILD_QWEN3_8_27B=ON -DNINFER_BUILD_QWEN3_6_35B_A3B=OFF
cmake --build build-sm89 -j 4
ctest --test-dir build-sm89 -N
```

在未有GPU lease时只执行纯CPU测试。已有op test的exit77表示SKIP不是PASS，发布脚本必须识别CTest的skipped条目。新C++测试通过`tests/CMakeLists.txt::ninfer_add_test/ninfer_add_op_test`注册，不假设有一个叫ninfer_tests的统一binary。

## 3. 主要源码入口

- 统计/采样：`src/runtime/contract/sampling.*`、`src/ops/{wrapper,launcher,kernel}/speculative_round.*`、`tests/ops/test_speculative_round.cpp`。
- MTP状态：`src/targets/qwen3_8/impl/runtime/mtp_impl.h`、`speculative_target_impl.h`、`impl/state/round_state.cpp`。
- DFlash骨架：`.../runtime/dflash_impl.h`、`dflash_context_impl.h`；新DFlash2不假定直接复用所有几何。
- Attention：`src/ops/launcher/gqa_attention_decode.cu`、`src/ops/kernel/gqa_attention_decode_i8.cuh`、`gqa_attention_prefill_i8.cuh`。
- Kernel tests：`tests/ops/test_gqa_attention.cpp`、`gdn_ref.h`、`op_check.h`；bench target在`bench/CMakeLists.txt`登记。
- Cache：`tests/test_continuation_cache.cpp`等先定位owner，再补边界policy，不在多个层复制frontier事实。

具体新文件、函数、测试由每个任务卡列出。新增路径是**计划产物**，不是声称当前源码已有。

## 4. 三类donor

DFlash2：算法+部分算子+binding+state语义；Suffix：数据结构/算法参考，先做独立chain；Sage/FlashInfer：d256合法tile/primitive参考，必须重新验证SM89/codec/mask。逐文件保留NOTICE/许可证，不把捕获来的cubin当无来源自由物料。

不要抄Windows DirectStorage/D3D12路径，不合并rk2专有优化，不把Blackwell PDL/TMA/FP4组件拉入sm89。算法新颖性/项目星数不构成代码质量验收。
