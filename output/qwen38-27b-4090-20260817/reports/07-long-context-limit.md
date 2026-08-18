# Case 07: 长上下文极限

## 结果

| lane | actual prompt tokens | marker | 1024 decode | 2048 decode | peak VRAM | temp |
|---|---:|---|---:|---:|---:|---:|
| `qwen38_mtp_n2_p075_ctx65536` | 40047 | PASS | 79.16 | 79.17 | 20600.00 MiB | 76.00 C |
| `qwen38_mtp_n2_p075_ctx98304` | 60036 | PASS | 71.33 | 44.47 | 22076.00 MiB | 81.00 C |
| `qwen38_mtp_n2_p075_ctx112000` | 68391 | PASS | 68.49 | 68.48 | 22698.00 MiB | 82.00 C |
| `qwen38_mtp_n2_p075_ctx131072` | 80019 | PASS | 64.91 | 64.86 | 23552.00 MiB | 83.00 C |
| `qwen38_mtp_n2_p075_ctx131072_exact` | 124831 | PASS | 54.33 | 50.69 | 23552.00 MiB | 82.00 C |

`ctx-size=131072` 的普通 lane 因 ASCII 合成 prompt 密度较低，实际 prompt 约 80K；因此追加了 `ctx131072_exact` lane，实际 prompt `124831` tokens，接近 128K，marker recall、1024/2048 输出均通过。

## 资源结论

- 64K：约 20.6GB，较安全。
- 96K：约 22.1GB。
- 112K：约 22.7GB。
- 124.8K 实际 prompt：`23552 MiB`，只剩约 665MiB，超过预设 `23500 MiB` 门禁但未 OOM。
- 128K 级别只能作为极限实验，不应作为默认 OpenClaw 生产配置；建议默认 64K，经过业务 trace 验证后再考虑 96K。

## 证据

- 64K-131K raw：`raw/remote/qwen38-27b-4090-20260817/raw` 下 `qwen38_mtp_n2_p075_ctx*`
- context 汇总：`raw/remote/qwen38-27b-4090-20260817/results/ctx-summary.json`
- exact max console：`raw/remote/qwen38-27b-4090-20260817/logs/case07-context-max-console.log`
