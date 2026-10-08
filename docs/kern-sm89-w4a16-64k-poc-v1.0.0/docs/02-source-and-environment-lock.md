# 源码与环境冻结

## 基线

- Kern：`5188aaf8dc992ebe635f111d17c269969706da27`，schema v4。
- 可参考的 vLLM recipe：`kernel-sanders/qwen38-27b-rtx4090-vision@36317835f2224c620f4d604bd57bf0a70f14cade`。
- 用户生产 NInfer：`tensorninja/ninfer-4090@44a2c6c`；其自有兼容层属于生产，不改。
- Kern依赖：`cudarc=0.19.7` + `cuda-13000`；HF tokenizer库版本参考0.22.2。[S03]
- recipe Docker声明 vLLM0.27.1、torch2.13/cu130、Triton3.7.1。它们是候选来源，不是假定本机已安装；实际wheel、patch和库哈希写入环境锁。[S04]

## 目标机不能直连GitHub时

在联网机器克隆并确认完整SHA，保存：

```bash
git -C kern bundle create kern-pinned.bundle --all
sha256sum kern-pinned.bundle > kern-pinned.bundle.sha256
# 同时保存 reference recipe 的固定源码、Cargo vendor、wheelhouse 和构建后的镜像tar。
```

目标机：

```bash
sha256sum -c kern-pinned.bundle.sha256
KERN_GIT_BUNDLE=/data/offline/kern-pinned.bundle \
  POC_SOURCE_DIR=/data/kern-sm89-poc/source/kern bash scripts/setup_sources.sh
```

联网阶段可以下载所需 crates/wheels；目标机编译使用 `cargo build --locked --offline`。`kern-serve` 是独立workspace，也要单独 vendor 它的依赖，不能只准备根Cargo.lock。[S03]

## 必须冻结的四组身份

1. 源码：Kern、oracle、patchset、provider生成器。
2. 模型：每个safetensors/config/tokenizer/template文件SHA，选定tensor列表，派生/重排buffer SHA。
3. 工具链：镜像digest、nvcc、ptxas、Rust、cuBLAS、CUDA runtime、动态加载的真实库路径。
4. 执行合同：dtype、chunk、page、batch、spec、sampling、模板、最大窗口、workspace plan。

不要只锁“Qwen3.8”名字。`model_sha256` 在工具中是完整文件清单的内容digest；它不等于HF revision，两者都应记录。

## 本包刻意未填写的值

本机模型目录、HF最新精确revision、镜像digest尚未被这次生成环境读取，因此配置为null/待本机锁定。AI在T00/T02自动发现与冻结，不允许猜一个40位hash。不能下载时保持BLOCKED，并使用已有同源本地文件核验；不能偷偷改用另一个量化模型。
