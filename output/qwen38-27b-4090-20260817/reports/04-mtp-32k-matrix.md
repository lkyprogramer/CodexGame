# Case 04: 32K MTP 参数矩阵

## 矩阵结果

每个 lane 使用同一模型、单并发、Q4 KV、相同请求；每个性能 prompt 3 次正式采样，另保留 strict JSON 和 patch review 样本。

| lane | 256 decode | 1024 decode | 2048 decode | median acceptance | peak VRAM |
|---|---:|---:|---:|---:|---:|
| `qwen38_no_spec_ctx32` | 44.78 | 44.69 | 44.64 | n/a | 17702.00 MiB |
| `qwen38_mtp_n1_p075_ctx32` | 51.29 | 54.33 | 59.80 | 0.97 | 18424.00 MiB |
| `qwen38_mtp_n2_p075_ctx32` | 53.87 | 57.99 | 65.86 | 0.89 | 18580.00 MiB |
| `qwen38_mtp_n3_p075_ctx32` | 56.11 | 61.98 | 72.44 | 0.87 | 18732.00 MiB |
| `qwen38_mtp_n4_p075_ctx32` | 53.63 | 60.89 | 75.75 | 0.82 | 18886.00 MiB |
| `qwen38_mtp_n2_p000_ctx32` | 71.88 | 77.58 | 85.40 | 0.65 | 18580.00 MiB |

## 质量与格式

| lane/case | format | quality | auto checks |
|---|---:|---:|---|
| `qwen38_no_spec_ctx32/long_1024_r1` | 4 | 4 | none |
| `qwen38_no_spec_ctx32/long_1024_r2` | 4 | 4 | none |
| `qwen38_no_spec_ctx32/long_1024_r3` | 4 | 4 | none |
| `qwen38_no_spec_ctx32/long_2048_r1` | 4 | 4 | none |
| `qwen38_no_spec_ctx32/long_2048_r2` | 4 | 4 | none |
| `qwen38_no_spec_ctx32/long_2048_r3` | 4 | 4 | none |
| `qwen38_no_spec_ctx32/patch_review_r1` | 3 | 3 | markdown_fence=True |
| `qwen38_no_spec_ctx32/short_256_r1` | 4 | 4 | contains_ok=True |
| `qwen38_no_spec_ctx32/short_256_r2` | 4 | 4 | contains_ok=True |
| `qwen38_no_spec_ctx32/short_256_r3` | 4 | 4 | contains_ok=True |
| `qwen38_no_spec_ctx32/strict_json_r1` | 5 | 5 | json_valid=True |
| `qwen38_mtp_n1_p075_ctx32/long_1024_r1` | 4 | 4 | none |
| `qwen38_mtp_n1_p075_ctx32/long_1024_r2` | 4 | 4 | none |
| `qwen38_mtp_n1_p075_ctx32/long_1024_r3` | 4 | 4 | none |
| `qwen38_mtp_n1_p075_ctx32/long_2048_r1` | 4 | 4 | none |
| `qwen38_mtp_n1_p075_ctx32/long_2048_r2` | 4 | 4 | none |
| `qwen38_mtp_n1_p075_ctx32/long_2048_r3` | 4 | 4 | none |
| `qwen38_mtp_n1_p075_ctx32/patch_review_r1` | 3 | 3 | markdown_fence=True |
| `qwen38_mtp_n1_p075_ctx32/short_256_r1` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n1_p075_ctx32/short_256_r2` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n1_p075_ctx32/short_256_r3` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n1_p075_ctx32/strict_json_r1` | 5 | 5 | json_valid=True |
| `qwen38_mtp_n2_p075_ctx32/long_1024_r1` | 4 | 4 | none |
| `qwen38_mtp_n2_p075_ctx32/long_1024_r2` | 4 | 4 | none |
| `qwen38_mtp_n2_p075_ctx32/long_1024_r3` | 4 | 4 | none |
| `qwen38_mtp_n2_p075_ctx32/long_2048_r1` | 4 | 4 | none |
| `qwen38_mtp_n2_p075_ctx32/long_2048_r2` | 4 | 4 | none |
| `qwen38_mtp_n2_p075_ctx32/long_2048_r3` | 4 | 4 | none |
| `qwen38_mtp_n2_p075_ctx32/patch_review_r1` | 3 | 3 | markdown_fence=True |
| `qwen38_mtp_n2_p075_ctx32/short_256_r1` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n2_p075_ctx32/short_256_r2` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n2_p075_ctx32/short_256_r3` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n2_p075_ctx32/strict_json_r1` | 5 | 5 | json_valid=True |
| `qwen38_mtp_n3_p075_ctx32/long_1024_r1` | 4 | 4 | none |
| `qwen38_mtp_n3_p075_ctx32/long_1024_r2` | 4 | 4 | none |
| `qwen38_mtp_n3_p075_ctx32/long_1024_r3` | 4 | 4 | none |
| `qwen38_mtp_n3_p075_ctx32/long_2048_r1` | 4 | 4 | none |
| `qwen38_mtp_n3_p075_ctx32/long_2048_r2` | 4 | 4 | none |
| `qwen38_mtp_n3_p075_ctx32/long_2048_r3` | 4 | 4 | none |
| `qwen38_mtp_n3_p075_ctx32/patch_review_r1` | 3 | 3 | markdown_fence=True |
| `qwen38_mtp_n3_p075_ctx32/short_256_r1` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n3_p075_ctx32/short_256_r2` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n3_p075_ctx32/short_256_r3` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n3_p075_ctx32/strict_json_r1` | 5 | 5 | json_valid=True |
| `qwen38_mtp_n4_p075_ctx32/long_1024_r1` | 4 | 4 | none |
| `qwen38_mtp_n4_p075_ctx32/long_1024_r2` | 4 | 4 | none |
| `qwen38_mtp_n4_p075_ctx32/long_1024_r3` | 4 | 4 | none |
| `qwen38_mtp_n4_p075_ctx32/long_2048_r1` | 4 | 4 | none |
| `qwen38_mtp_n4_p075_ctx32/long_2048_r2` | 4 | 4 | none |
| `qwen38_mtp_n4_p075_ctx32/long_2048_r3` | 4 | 4 | none |
| `qwen38_mtp_n4_p075_ctx32/patch_review_r1` | 3 | 3 | markdown_fence=True |
| `qwen38_mtp_n4_p075_ctx32/short_256_r1` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n4_p075_ctx32/short_256_r2` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n4_p075_ctx32/short_256_r3` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n4_p075_ctx32/strict_json_r1` | 5 | 5 | json_valid=True |
| `qwen38_mtp_n2_p000_ctx32/long_1024_r1` | 4 | 4 | none |
| `qwen38_mtp_n2_p000_ctx32/long_1024_r2` | 4 | 4 | none |
| `qwen38_mtp_n2_p000_ctx32/long_1024_r3` | 4 | 4 | none |
| `qwen38_mtp_n2_p000_ctx32/long_2048_r1` | 4 | 4 | none |
| `qwen38_mtp_n2_p000_ctx32/long_2048_r2` | 4 | 4 | none |
| `qwen38_mtp_n2_p000_ctx32/long_2048_r3` | 4 | 4 | none |
| `qwen38_mtp_n2_p000_ctx32/patch_review_r1` | 3 | 3 | markdown_fence=True |
| `qwen38_mtp_n2_p000_ctx32/short_256_r1` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n2_p000_ctx32/short_256_r2` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n2_p000_ctx32/short_256_r3` | 4 | 4 | contains_ok=True |
| `qwen38_mtp_n2_p000_ctx32/strict_json_r1` | 5 | 5 | json_valid=True |

## 结论

- no-spec 长输出约 44.6 tok/s。
- `n=2,p-min=0` 长输出最快，约 85.4 tok/s，但全矩阵 acceptance 中位数约 0.65，短输出 acceptance 更低，不能只按速度选型。
- `n=4,p-min=0.75` 在 2048 输出约 75.8 tok/s，显存约 18.9GB，属于更平衡的候选；`n=2,p-min=0.75` 约 65.9 tok/s、格式表现相同。
- 所有 matrix patch review 都有 markdown fence，严格 JSON 断言失败；OpenClaw 若依赖 schema/grammar，需要在 API 层显式 `response_format` 或后处理门禁。

完整 raw：`raw/remote/qwen38-27b-4090-20260817/raw`；矩阵汇总：`raw/remote/qwen38-27b-4090-20260817/results/mtp-matrix-summary.json`。
