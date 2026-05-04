# Nemotron Thinking Specialized Final Evaluation

## Direct conclusion

- Under this specialized task set, `enable_thinking=true` did **not** show a clear problem-solving advantage over `enable_thinking=false`.
- The main effect of `thinking=true` was:
  - slightly longer outputs
  - slightly slower latency
  - no meaningful throughput gain
- With `--reasoning-format none`, `thinking=true` still leaks internal reasoning into `content`.
- With parser support enabled, that leakage is cleaned up, but the sampled tasks still did not show a clear quality jump.

## What was tested

Main comparison:

- `bench/nemotron-iq4-xs-no-think`
- `bench/nemotron-iq4-xs-think`
- both on the same 128K profile
- both with `--reasoning-format none`

Task families:

- `longctx`
  - long-context restore analysis
  - long-context metrics contract analysis
  - long-context Java change-impact analysis
- `multi_round`
  - three-round self-repair on restore
  - three-round self-repair on outbox ordering
  - three-round self-repair on reconnect circuit breaker
- `planning`
  - boot restore implementation planning
  - metrics exposure planning
  - reconnect fault-injection planning

Control round:

- `bench/nemotron-iq4-xs-think-parser-control`
- `enable_thinking=true`
- parser enabled
- 3 representative tasks:
  - one `longctx`
  - one `multi_round`
  - one `planning`

## Main comparison result

Both profiles completed all 9 main tasks:

- `no-think`: `9 / 9`
- `think`: `9 / 9`

Aggregate metrics:

- avg elapsed_ms:
  - `22855.60 -> 23205.54`
- avg predicted_per_second:
  - `175.74 -> 175.64`
- avg content_length:
  - `5175.00 -> 5846.89`

By family:

- `longctx`
  - no-think: `30401.69 ms`, `5783.33` chars
  - think: `30503.45 ms`, `6535.00` chars
- `multi_round`
  - no-think: `27560.00 ms`, `4080.00` chars
  - think: `28329.60 ms`, `4670.67` chars
- `planning`
  - no-think: `10605.11 ms`, `5661.67` chars
  - think: `10783.57 ms`, `6335.00` chars

Interpretation:

- The model did not become materially better at finishing the tasks.
- It mostly became more verbose.
- The long-context tasks did not show a distinct reasoning gain.
- The multi-round tasks did not show a cleaner convergence pattern from the aggregate results.
- The planning tasks did not become obviously more decision-complete from the aggregate results.

## Qualitative read

Representative output differences:

- `longctx_restore_bootstrap`
  - no-think: answer starts directly with bug, root cause, and patch framing
  - think: answer begins with self-talk / internal analysis before converging
- `multi_restore_self_repair`
  - no-think: final answer is already shaped like an implementation plan
  - think: more narrative setup, but not clearly better plan quality
- `plan_metrics_exposure`
  - no-think: concrete enough, though a bit eager to invent protocol shape
  - think: longer and more discursive, but not clearly more grounded

The key pattern is consistent:

- `thinking=true` adds words
- it does not add an obvious jump in solution quality on these tasks

## Reasoning-format impact

This round explicitly checked the `--reasoning-format none` concern.

Smoke tests:

- `thinking=true + reasoning-format none`
  - `content` contained internal reasoning plus a literal `</think>` tail
- `thinking=true + parser enabled`
  - `content` was clean
  - `reasoning_content` held the internal reasoning separately

So yes, `--reasoning-format none` materially affects presentation and contract cleanliness.

But the control round still matters:

- parser-enabled `thinking=true` on 3 sampled tasks did not show a clear speed or quality improvement over the main `thinking=true` profile
- it mostly cleaned the output contract

Interpretation:

- `--reasoning-format none` can make `thinking=true` look worse than it really is at the output-contract layer
- but even after isolating that variable, this benchmark still does not show a decisive “thinking helps solve the task better” effect

## Final recommendation

For this Nemotron IQ4_XS setup on 4090:

- default profile:
  - keep `enable_thinking=false`
- if you want cleaner reasoning experiments:
  - use `enable_thinking=true` **with parser enabled**
  - treat it as an analysis/debug profile, not the default executor profile

Current evidence does **not** justify enabling thinking by default for:

- long-context analysis
- multi-round repair
- complex planning

If thinking is revisited later, the most valuable next test is not more of the same benchmark. It is:

1. human-scored review of answer quality on 3 to 5 hard tasks
2. compare final plans against a strict rubric for completeness and correctness
3. separate “better answer” from “longer answer”
