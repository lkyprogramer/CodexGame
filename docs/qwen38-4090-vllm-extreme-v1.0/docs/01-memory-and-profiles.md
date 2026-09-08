# RTX 4090 Memory and Serving Profiles

## Machine budget

```text
GPU VRAM       24 GiB
Host RAM       64 GiB
SSD            600 GiB
GPU arch       Ada SM89
```

Disk planning:

```text
Upstream source/build tree               < 2 GB excluding image cache
Docker image + Python/vLLM stack         ~10 GB class
W4A16 target                             ~20 GB class
Prepared fast target / derivative        ~1–3 GB incremental
DFlash2 draft                            ~1 GB class after W4A16 preparation
Compile/JIT caches                        several GB
Benchmark prompts/logs                    < 2 GB
Recommended free disk before setup       >= 100 GB
```

64 GiB host RAM is adequate for the preparation workflow, but avoid running unrelated memory-heavy jobs while preparing/serving.

## Profile A: huge-mtp — recommended qualification target

```text
SPEC=mtp
CTX=huge
PREFIX_CACHE=1
VISION=0
MAX_LEN=200000
DRAFT_TOKENS=3
GPU_UTIL=0.93
```

Intent:

- one active long-running Pi session;
- ~190K prompt + output headroom;
- KVarN KV capacity;
- MTP balances general long-context reasoning and decode speed.

## Profile B: huge-dflash2

```text
SPEC=dflash2
CTX=huge
PREFIX_CACHE=1
VISION=0
DFLASH_TOKENS=7
GPU_UTIL=0.93
```

Intent:

- large-file edit/copy/RAG workloads;
- higher capacity than the ordinary DFlash2 profiles;
- verify actual speed at deep context before promotion.

Do not enable `LOOKUP=1` by default. It is specialized for output that repeats the request.

## Profile C: long-mtp

```text
SPEC=mtp
CTX=long
PREFIX_CACHE=1
VISION=0
MAX_LEN=150000
```

Use when 150K is enough. FP8 KV is substantially faster than KVarN at deep context.

## Profile D: fast-dflash2

```text
SPEC=dflash2
CTX=fast
PREFIX_CACHE=1
VISION=0
```

Use for compacted Pi contexts (for example 16K–64K). This is the latency profile, not the 200K profile.

## Context sizing rule

Never equate `MAX_LEN` with usable context. The real gate is:

```text
actual prompt tokens + output tokens <= allocated token pool
```

The benchmark records actual API usage tokens and refuses to count a nominal context limit as success.
