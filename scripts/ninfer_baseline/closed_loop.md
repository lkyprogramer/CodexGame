# Isolated Pi Java fixture runner

Profile: `ISOLATED_PI_FIXTURE`. Three reused business fixtures plus seventeen **synthetic business-contract** Java repair tasks,
three repetitions each. This is a fresh read/edit/test control benchmark and is
**not equivalent to historical sol-pi sessions**, long-context coding, or their
extension/context transforms. Historical tools are never replayed.

Requirements frozen in code: Node v22.19.0 and installed Pi 1.3.0. Java and javac are frozen to `/Users/luo/.sdkman/candidates/java/25.0.1-open`;
versions and launcher binary hashes are recorded in every run identity.
`prepare` and dry-run perform no model calls. `run` performs model calls only
when dry-run is absent. Only an unauthenticated `http://127.0.0.1:PORT/v1`
endpoint is accepted; the generated Pi model registry uses a non-secret literal
placeholder because Pi requires a credential to make custom models available.
No user credentials, settings, extensions, context files, skills or MCP servers
are copied or loaded.

```sh
NODE=/Users/luo/.nvm/versions/node/v22.19.0/bin/node
"$NODE" scripts/ninfer_baseline/closed_loop.mjs prepare /tmp/pi-fixture-baseline
BASELINE_DRY_RUN=1 "$NODE" scripts/ninfer_baseline/closed_loop.mjs run \
  /tmp/pi-fixture-baseline business-pagination 1 http://127.0.0.1:18030/v1 MODEL_ID
```

Use another root for actual runs: each case/repeat directory is exclusive and
will not overwrite a dry-run or completed result. Read `manifest.json` for all
20 case IDs. Call `run` serially for each case with repetitions 1, 2, 3. The
caller controls forwarding and server identity capture; this script does not
start services, use SSH, or modify remote state. Keep engine identity evidence
alongside the resulting root before comparing baselines.

Environment budgets: `BASELINE_TIMEOUT_MS=600000`, `BASELINE_MAX_TURNS=24`,
`BASELINE_MAX_TOOLS=60`, `BASELINE_MAX_TOKENS=32768`, `BASELINE_THINKING=medium`.
Default sampling is production-like (`temperature=1`, `top_p=0.95`, `top_k=20`,
`presence_penalty=0`, `preserve_thinking=true`). Three fixed request seeds
1701 / 2901 / 4101 map to repetitions 1 / 2 / 3; the same seed is reused across
turns in one case, and this does not promise server determinism.
`BASELINE_SAMPLING_PROFILE=GREEDY BASELINE_THINKING=off` selects an explicitly
separate greedy profile. These settings are a separate profile from the
historical session payload benchmark. Freeze any overrides before a complete
20 × 3 run; do not mix settings when aggregating. Output, sampling and thinking overrides are recorded per run.

Every run uses a fresh /tmp workspace, HOME, TMPDIR, PI_CODING_AGENT_DIR and
settings/model registry. All fixture source, tests, tasks and verification
scripts are hashed. Pi runs with `--no-extensions` plus one explicitly supplied,
frozen budget extension; all discovery remains disabled. Its pre-tool gate
allows only reads inside the fixture, writes/edits under src/main/, and bash
commands exactly `./verify.sh` or `bash verify.sh`. It blocks modified tests and
external commands before execution. This is a narrow fixture policy, not an OS
security sandbox. The parent enforces a wall timeout with SIGKILL to the detached
process group, covering javac/java descendants. Pi turn/tool budgets abort the
agent and record a distinct hard-budget stop. Ordinary tool-policy denials
return an error tool result to the model without aborting the run. Legacy fixture
verification has a 30 s process-group timeout; QCB uses its separate hidden grader.
External Java tasks use a frozen, offline Docker public-compile entry through
`verify.sh`, with no hidden test mounts. Final external grading allows 450 s
outside the container (420 s inside), within the 2400 s parent and 1800 s Pi
budgets. Each explicit recovery attempt has its own identity/header; previous
aborted evidence and partial scores remain intact.

`runs/CASE/repeat-N/` contains identity.json, raw pi.jsonl, stderr.log,
changes.patch, verify.log, optional budget-events.jsonl, final workspace and
summary.json. Identity records fixture/CLI/extension hashes, Pi/Node versions,
arguments and sampling. Summary includes protected test hashes (also rechecked after verification), test completion
markers, an exit/halt-call guard, final source
hashes, Pi/verification exits, timeout/policy status, elapsed wall time, all
assistant-message usage **summed once per final message**, costs and tool counts.
The cost fields are provider-reported values (zero-priced local model), not
estimated hardware cost. Streaming usage deltas are excluded to avoid double
counting. Hard-budget/length stops and ordinary policy denials are recorded separately;
a denial alone does not change a completed test result. Raw output and patch hashes are saved.

Offline validation:

```sh
/Users/luo/.nvm/versions/node/v22.19.0/bin/node --test \
  scripts/ninfer_baseline/test_closed_loop.mjs
```

Tests exercise frozen fixtures, no-network dry-run and registry construction,
usage aggregation, pre-tool gates, process-group timeout, all 20 initial Java
compilation/behavioral failures and one corrected fixture's success. They do not
call an inference server. Actual model/tool protocol behavior and 20 × 3 results
require the authorized server run and are not claimed by these offline checks.


## Business corpus provenance and contracts

The arithmetic corpus is retained only in `closed_loop_smoke.mjs` and is
excluded from CASES and the 20 × 3 business baseline. The three java-agent
fixtures are copied from the existing qwen38-4090 comparison corpus, including
its verifier/tests/context; AGENTS discovery remains disabled. The seventeen
business-* fixtures are newly authored simulations. They exercise business
contracts, not a real DB, transaction manager, Redis, HTTP server or MyBatis
installation. Their results cannot qualify those integrations.

| Case | Contract |
|---|---|
| business-api-compatibility | Accept legacy orderId and newer id alias. Prefer id only when nonblank; preserve legacy fallback and reject requests missing both. Public resolve signature stays. |
| business-batch-failure | Batch import continues after each invalid row, records actual row IDs for failures, preserves success order, and never reports failed rows as accepted. |
| business-cache-invalidation | Product cache including negative lookups must reflect create/update/delete. Repository is an in-memory map, no Redis. |
| business-cursor-pagination | Cursor is lexicographic (createdAt,id); include IDs after cursor at equal timestamp, sort and limit. Pagination must neither duplicate nor omit tied rows. |
| business-exception-cause | Translate repository failures into IllegalStateException with order identity while preserving original cause and successful return. |
| business-expiry-instant | Token expiry is based on Instant: expired exactly at expiry or after; timezone display offset must not change validity. Fixed instants make test deterministic. |
| business-inventory-reservation | Atomic reservation validates positive quantity, rejects insufficient stock, and never oversells when two threads each reserve 4 from stock 5. No database/distributed lock claims. |
| business-json-serialization | Serialize nullable JSON string values with valid escaping for quotes, backslashes, LF, TAB and control U+0001. No Jackson dependency; explicit minimal string codec contract. |
| business-money-rounding | Invoice totals round HALF_UP once after summing precise decimal line amounts, not per line. Empty invoice is 0.00; no binary floating point. |
| business-mybatis-parameter-contract | Synthetic MyBatis-like named parameter binding contract WITHOUT MyBatis or JDBC: XML placeholder tenantId and id must map to same names, including null optional status. Preserve DTO and map signature; verify mapper.xml as contract evidence. |
| business-optimistic-lock | In-memory optimistic repository: stale version must fail without mutation; concurrent updates on same expected version have exactly one winner. Keep synchronized atomic check-and-write. |
| business-outbox-atomicity | In-memory transactional outbox simulation: failure to create event must not commit order, retries create exactly one order and one event; duplicate submit has no side effects. |
| business-pagination | Active orders sorted by ID. total counts filtered rows before pagination. Page is zero-based; reject negative page and nonpositive size. |
| business-resource-suppression | Resource close must run on success and failure. When work and close both fail, work exception is primary and close exception suppressed. Implement Java resource lifecycle, no external I/O. |
| business-soft-delete | Active usernames unique per tenant; deleted rows do not block recreation. Another tenant may use same name. Conflict must leave rows unchanged. |
| business-tenant-isolation | Lookup order by tenant AND order ID. IDs are only unique within tenant. Never fall back to another tenant when local row is missing. |
| business-transaction-rollback | In-memory transaction simulation: failed debit must restore balance and append no ledger row; successful transfer commits balance and ledger together. |
| java-agent-1-idempotency | Fix the concurrency/idempotency defect in this Java service. Reproduce the failure with `./verify.sh`, inspect the code, implement the smallest production-safe fix, and rerun tests. The public method signature and Reservation record must not change. Do not edit tests. Finish only after the verifier passes. |
| java-agent-2-retry-contract | A production retry wrapper violates its documented max-attempt contract and mishandles terminal failures. Start with `./verify.sh`, trace the behavior across RetryPolicy and RetryingClient, fix production code without changing public APIs, and verify. Do not edit tests. |
| java-agent-3-reconnect-loop | Investigate the reconnect regression. First run `./verify.sh`. Then inspect `logs/reconnect.log`, `docs/runtime-design-notes.md`, and the production classes under `src/main/java`. There are two interacting production defects: one in time/expiry semantics and one in state transition/reconnect behavior. Fix them without changing public APIs or tests. Run the verifier until it passes, then summarize the root cause briefly. |

The fixed verifier must exit zero AND print its fixed test completion marker.
Explicit exit/halt calls in production source disqualify a run; tests and verifier
are hashed again after execution. This is a practical controlled-fixture judge,
not a malicious-code sandbox. It does not prove arbitrary untrusted Java cannot
evade assertions through reflection/native code.

Offline provider serialization test uses installed Pi 1.3.0 openai-completions
`onPayload` to capture temperature/top_p/top_k/seed/max_tokens/reasoning_effort,
then throws before fetch. This proves client serialization; server acceptance
and actual sampler behavior require the 29-side request capture and server logs.
