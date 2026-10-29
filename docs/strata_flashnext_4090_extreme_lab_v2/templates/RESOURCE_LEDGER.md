# 资源账模板

| resource | owner | format/shape | bytes reserved | bytes used | aliases | lifetime | last reader | release/event | measured/estimated |
|---|---|---|---:|---:|---|---|---|---|---|
| dense weights | 待填 | 待填 | | | | | | | |
| expert hot slots | | | | | | | | | |
| KV / index / page metadata | | | | | | | | | |
| GDN / conv / MTP state | | | | | | | | | |
| verify graphs / scratch | | | | | | | | | |
| prefill region | | | | | | | | | |
| host native / prepack | | | | | | | | | |
| pinned / snapshot / allocator retained | | | | | | | | | |

峰值按同时live范围计算，alias不重复相加；reserved与used不混。另填MemAvailable最小值、VRAM余量、swap和allocation失败。
