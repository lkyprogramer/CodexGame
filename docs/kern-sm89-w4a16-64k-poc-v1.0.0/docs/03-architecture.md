# 新provider的架构与所有权

```text
Original W4A16 safetensors (read-only)
  └─ validated export/repack → packed tensors + provenance
       └─ gen_qwen38_sm89_w4a16.py → schema-v4 manifest
            └─ SM89 cubins + typed Op ABI
                 └─ kern-runtime
                      └─ KernScheduler + Pi frontend
```

模型知识放在 provider/生成器：层数、GDN布局、norm、rope、gating、tensor拼接、quant codec。runtime只处理类型、字节、ABI、状态租约与launch。不得在通用runtime里加入“model==qwen3.8”分支。[S01]

## 新增文件的合同

| 路径（相对Kern源码） | 职责 |
|---|---|
| `tools/sm89/artifact_key.py` | arch/toolchain/source/flags/shape共同定义制品身份 |
| `tools/sm89/export_packed.py` | 冻结oracle真正使用的重排weight/scales；分片流式导出 |
| `tools/sm89/capture_ops.py` | 小规模oracle捕获、ABI与tensor角色标注 |
| `tools/sm89/weight_contract.py` | group128/对称/pack/reorder的校验 |
| `tools/gen_qwen38_sm89_w4a16.py` | 新provider生成器；不覆盖GB300示例 |
| `tools/kernels-src/sm89/` | Ada专用入口与必要适配核 |
| `examples/qwen3.8-27b-sm89-w4a16.json` | 新manifest，no-spec，batch1 |
| `tests/sm89/` | provider、数值、内存与生命周期测试 |

以上是**要创建的代码路径**，不是声称仓库已经存在。现有修改热点见任务表和源码地图。

## Op合同与Runtime边界

把4bit weights放在合法typed packed buffer（通常i32）中，scales为独立buffer；类型通过不等于codec正确。只有provider知道pack规则。可把“W4 GEMM + activation/residual”封成一个逻辑Op，内部多次launch与scratch，不要求host层解释数学语义。

输入buffer、carry、state分别有不同生命周期。模型持久状态不得藏进临时scratch；scratch不得被当作下一HTTP轮的缓存。图captured pointers的稳定性由runtime负责，语义offset和页布局由provider负责。

## 不直接用原版Kern启动27B

当前发布Qwen包绑定GB300的sm103制品与约50GiB BF16权重。更改环境变量不能让这些bytes在4090上变成正确高性能实现；必须重新生成全部被引用模块，确认ABI、shared memory和tensor layout。[S01][S02]
