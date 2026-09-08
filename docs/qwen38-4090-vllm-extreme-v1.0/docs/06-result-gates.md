# Result Gates and Promotion Decision

## Mandatory gates

### Capacity

- Deep benchmark actual `prompt_tokens >= 185000`.
- Server returns a valid completion; no truncation/error/OOM.
- Hidden retrieval marker is present in the answer.

### Long-context speed

- Deep-context sustained decode `>= 20 tok/s`.
- 64K decode target `>= 50 tok/s` (warning below 60).

### Cache/Agent-loop behavior

At least one of these must hold for the growing append request:

- provider reports `cached_tokens >= 50%` of the old prefix; or
- append-turn TTFT improves by >=50% versus a comparable cold 100K request.

Exact-repeat cache success alone does not satisfy this gate.

### Java Agent quality

- 3/3 protected Java tasks pass for `GO`.
- 2/3 produces `GO_WITH_CAVEATS` only if the failed case is not the long reconnect case.
- Any test modification => automatic failure.

### Stability

- no server restart;
- no CUDA illegal-memory-access;
- no corrupted/non-JSON server response;
- suite duration <= 3600 seconds.

## Decision

```text
GO
  all mandatory gates pass

GO_WITH_CAVEATS
  capacity + >=20 tok/s pass,
  but one non-critical Java task or cache target is marginal

NO_GO
  <185K actual prompt,
  <20 tok/s at deep context,
  retrieval failure,
  long Java Agent task failure,
  CUDA/runtime instability,
  or silent truncation
```

## Comparison against existing WORK

After the new profile is `GO`, run the same Pi fixtures against the existing llama.cpp endpoint by changing only `SERVER_URL`, `MODEL_ID`, and the Pi provider config. Compare:

```text
successful tasks / hour
p50 task wall time
100K growing-turn TTFT
185K decode tok/s
```

Do not switch the daily driver based on raw short-prompt tok/s alone.
