# 源码地图与证据等级

证据分为：U=用户实测/机器事实，S=已读取源码/模型卡，D=本方案设计，R=需要目标机运行确认。D/R不能写成S或U。

| 阅读点 | 决定的设计 |
|---|---|
| Kern `Cargo.toml` | CUDA API固定13.0、runtime无Python、serve独立workspace |
| `tools/handwritten.py` / `tools/build_kernels.sh` | 需要SM89专属artifact cache key与构建目标白名单 |
| `tools/gen_qwen35.py` / `tools/qwen_weights.py` | 模型几何、GDN/rope/拼接和source绑定 |
| `crates/kern-manifest/src/types.rs` / `verify.rs` / `protocol.rs` | 新typed Op与动态shape、数据流和caller合同 |
| `crates/kern-runtime/src/compile.rs` / `cubin.rs` / `weights.rs` | ABI、内核加载、weight binding、extern边界 |
| `crates/kern-runtime/src/pages.rs` / `prefix.rs` / `host.rs` | 页共享、state slot、checkpoint/host恢复 |
| `crates/kern-serve/src/lib.rs` / `scheduler.rs` / `tray.rs` | 默认并发、容量、仅greedy、末token提交、请求生命周期 |
| `docs/qwen38-bringup.md` | 旧schema历史记录、数值分叉与ABI陷阱；不能当当前CLI |
| dbirks model config | W4 group128/对称、BF16 activation、FP32 GDN |

本包生成环境无法联网clone完整仓库，已通过GitHub connector读取上述关键源/已有上下文，且不宣称已编译Kern。目标机T01必须验证固定SHA与实际文件；若发现与文档不符，记录差异并停止相关假设，不对着过时行号盲patch。

完整primary来源见 `references/sources.md`。用户报告来自 `d6f1461e-1648-4dbf-925a-7e087c9483ac.md`；本包只记录任务需要的非秘密生产身份，不打包原始可能含私人内容的报告。
