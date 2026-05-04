# Nemotron IQ4_XS vs 27B UD-Q4_XL Final Evaluation

## Direct conclusion

- `Nemotron-Cascade-2-30B-A3B-IQ4_XS` is **not a drop-in replacement** for the current `27B UD-Q4_K_XL` executor baseline.
- Under the same 64K executor profile, Nemotron is **much faster** on coding/review prompts, but its **first-pass agentic contract stability is weaker**.
- `enable_thinking=true` is **not worth making the default** for Nemotron in this setup.

## What the run proved

- Model download to 4090 succeeded:
  - file: `nvidia_Nemotron-Cascade-2-30B-A3B-IQ4_XS.gguf`
  - size: `18166698432`
  - sha256: `871a80bfd682289f2efa1b4fdee899576b5a768681f2b2ad74a15b59af6a510e`
- Both main models completed the full executor comparison window.
- The live 35B uncensored public service was restored after the run.

## Coding / review result

Both models were stable on the 22-task coding round:

- `27B UD-Q4_XL`: `22 / 22` HTTP 200
- `Nemotron IQ4_XS`: `22 / 22` HTTP 200

But Nemotron was materially faster:

- avg elapsed: `25388.13 ms -> 6287.40 ms`
- avg tok/s: `42.32 -> 209.26`

Observed behavior:

- Nemotron produced complete answers across all 22 tasks.
- Content length stayed healthy and did not collapse.
- There was no reasoning/body split because this run kept `--reasoning-format none`.

Interpretation:

- For review-style and coding-analysis prompts, Nemotron looks **strong and efficient** on 4090.
- This run shows it is absolutely usable in the executor profile.
- This run does **not** yet prove it should replace the 27B baseline, because executor replacement is gated by agentic delivery, not by coding speed alone.

## Agentic result

First-attempt stability:

- `27B UD-Q4_XL`
  - JSON parse: `8 / 8`
  - validation pass: `7 / 8`
- `Nemotron IQ4_XS`
  - JSON parse: `6 / 8`
  - validation pass: `5 / 8`

Best-of-2 stability:

- `27B UD-Q4_XL`
  - JSON parse: `8 / 8`
  - validation pass: `7 / 8`
- `Nemotron IQ4_XS`
  - JSON parse: `8 / 8`
  - validation pass: `7 / 8`

Important failure pattern:

- Nemotron recovered to parity after retry, but it was less stable on the first attempt.
- Representative issues were JSON formatting failures:
  - `JSONDecodeError('Expecting value ...')`
  - `JSONDecodeError('Extra data ...')`
  - `JSONDecodeError('Unterminated string ...')`
- The shared hard task remained the same on both models:
  - `agentic_ts_restore_bootstrap_patch`

Interpretation:

- Nemotron is **good enough for guarded agentic use**.
- Nemotron is **not better than 27B as a raw first-pass executor**.
- If the goal is the safest default executor baseline, 27B still has the cleaner argument.

## Thinking appendix

Nemotron with `enable_thinking=true` still completed all 22 coding tasks:

- success: `22 / 22`
- avg elapsed: `6939.81 ms`
- avg tok/s: `209.10`
- avg content length: `4901.68`

This is only a mild quality/verbosity shift, not a clear win:

- it was slower than non-thinking Nemotron
- throughput was effectively unchanged
- content got longer, but not clearly better from these aggregate metrics

Most important caveat:

- the smoke test already showed the model leaking its own internal deliberation into `content`, including a literal `</think>` tail
- that is acceptable for exploratory testing, but poor as a default executor/chat contract

Interpretation:

- `enable_thinking=true` is interesting for manual exploration
- it is **not a good default** for this service profile

## Final recommendation

For the current 4090 executor baseline:

- keep `Qwen3.5-27B-UD-Q4_K_XL` as the default raw executor baseline
- keep `Nemotron-Cascade-2-30B-A3B-IQ4_XS` as a strong candidate for:
  - fast coding/review analysis
  - guarded use with retries / output validation
- do not enable `thinking=true` by default for Nemotron

If Nemotron is revisited later, the most valuable follow-up is:

1. test it behind a guardrail layer that auto-retries JSON contract failures
2. compare a guarded Nemotron run against the current guarded 27B executor
