# 内存账：先证明装得下，再跑64K

## 精确的KV公式

源模型16层Full Attention、4个KV头、每头256维、K和V、BF16每值2字节：[S05]

`bytes/token = 16 × 4 × 256 × 2 × 2 = 65,536 = 64 KiB`。

64K输入对应4GiB KV；本PoC池计划73,728 tokens对应4.5GiB。不能用4GiB输入账忽略输出、page rounding与pad。

GDN参考布局每层3,211,264B，48层每sequence约147MiB。runtime显存预算需要active、null、pad、checkpoint所用全部slot。**新增checkpoint首先是GPU slot，不是“64GB RAM里随便留300MB”。** park到host才转移placement，而且存在复制/页共享费用。[S01]

## 预算工具

```bash
python3 -m poc_tools.cli weights /data/path/to/W4A16 --out results/weights.json
python3 -m poc_tools.cli memory --weight-gib 16.0 --capacity 73728 \
  --slots 4 --workspace-gib 1.0 --out results/memory-estimate.json
```

`16.0`只是算例，必须替换为实际被绑定的device weight bytes。safetensors文件大小不等于device占用：重排、padding、衍生表、临时双份buffer都会增加峰值。反之，vision/MTP不被provider引用时不应加载到device。

## 强制检查

- 先按tensor+workspace+state+graphs+headroom逐项核对；目标留1GiB，硬底线留512MiB。
- `vars.tokens.max` 默认512，不把prefill chunk轴误设成64K；`seqs.max`只保留需要的batch上界。
- logits只输出最后一行或当次验证需要的行，不保留 `[65536,vocab]`。
- 根runtime的所有上界分配与kern-serve `max_seqs` 默认256分别检查；**只传max_seqs=1并不自动缩小manifest里所有workspace**。[S07]
- 使用 `Capacity{tokens,seqs}` 算实际allocator开销；页对齐后池不能少于请求+输出。
- 不把host页缓存、CPU offload、Unified Memory页面换出当成显存内成功。

## 若P0内存不够

顺序：删未引用加载 → 收紧workspace轴和临时生命周期 → chunk512降256 → 移除多余graph/batch capture → 减少checkpoint保留数量。每步重新审计峰值。

仍不足时，不悄悄压GDN或KV。建立单独`p0-q8-kv`派生profile，oracle使用相同Q8 codec/scales，重新走数值与质量门。再量化embed/lm_head属于P1另一条路线。优先保留语言权重质量，不为了凑一个“64K通过”偷偷删层/截断输入。

200K低比特KV属于后续；本包四bit预算功能只是估算器，没有实现任何四bit attention kernel。
