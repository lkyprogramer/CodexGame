# WORK vs NInfer comparison

thinking=medium  RESULTS_ROOT=/Users/luo/Documents/github/CodexGame/output/qwen38-4090-compare/results/medium

| backend | java | tasks/h | p50 wall s | tools/task | 4k decode | 64k decode | 185k prompt | 185k decode | 185k TTFT | append TTFT | append cached | capacity | deep≥20 | append cache |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| ninfer | 3/3 | 41.86 | 31.0 | 12.0 | 127.09 | 110.59 | 184415 | 98.53 | 94.058 | 3.632 | 99697 | False | True | True |
| vllm | 3/3 | 20.69 | 48.0 | 13.0 | 57.83 | 63.71 | 184415 | 53.07 | 65.824 | 5.015 |  | False | True | True |
| work | 3/3 | 35.29 | 32.0 | 9.0 | 77.59 | 60.24 | 184415 | 38.35 | 133.791 | 4.994 | 99695 | False | True | True |
