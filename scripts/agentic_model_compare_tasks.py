#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent


AGENTIC_SYSTEM_MESSAGE = dedent(
    """\
    You are a senior software engineer completing an autonomous coding task.

    Use only the provided workspace snapshot.
    Return JSON only.
    Write the smallest safe set of file edits needed to make the task pass.
    Do not describe changes without also returning the file contents to apply.
    Do not invent files or APIs unless they are clearly required by the task.
    """
).strip()


@dataclass(frozen=True)
class WorkspaceFile:
    path: str
    content: str


@dataclass(frozen=True)
class AgenticTask:
    task_id: str
    description: str
    max_tokens: int
    workspace_files: tuple[WorkspaceFile, ...]
    validation_commands: tuple[str, ...]
    hidden_checklist: tuple[str, ...]
    system_message: str = AGENTIC_SYSTEM_MESSAGE

    def render_user_message(self) -> str:
        parts = [
            f"Task ID: {self.task_id}",
            f"Scenario: {self.description}",
            "",
            "Instructions:",
            "Apply the smallest safe fix.",
            "Return JSON in this shape:",
            '{"summary":"...","files":[{"path":"relative/path","content":"full file content"}]}',
            "Only include files that must change.",
            "",
            "Workspace snapshot:",
        ]
        for file in self.workspace_files:
            parts.append("")
            parts.append(f"=== File: {file.path} ===")
            parts.append(dedent(file.content).strip())
        return "\n".join(parts).strip() + "\n"

    def to_manifest_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "max_tokens": self.max_tokens,
            "validation_commands": list(self.validation_commands),
            "hidden_checklist": list(self.hidden_checklist),
            "workspace_files": [file.path for file in self.workspace_files],
        }


def _wf(path: str, content: str) -> WorkspaceFile:
    return WorkspaceFile(path=path, content=dedent(content).strip() + "\n")


def get_agentic_tasks() -> list[AgenticTask]:
    return [
        AgenticTask(
            task_id="agentic_python_reconcile_pkg",
            description="Complete a multi-file Python reconciliation package so the business discrepancy tests pass.",
            max_tokens=2200,
            workspace_files=(
                _wf(
                    "reconcile/models.py",
                    """
                    from dataclasses import dataclass

                    @dataclass(frozen=True)
                    class Row:
                        merchant_order_id: str
                        provider_txn_id: str
                        amount_cents: int
                        status: str


                    @dataclass(frozen=True)
                    class Discrepancy:
                        kind: str
                        merchant_order_id: str
                        provider_txn_id: str
                        detail: str
                    """,
                ),
                _wf(
                    "reconcile/matcher.py",
                    """
                    from __future__ import annotations

                    from collections import Counter
                    from typing import Iterable

                    from .models import Discrepancy, Row


                    def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
                        # TODO: implement real matching logic.
                        return []
                    """,
                ),
                _wf(
                    "reconcile/report.py",
                    """
                    from __future__ import annotations

                    from .models import Discrepancy


                    def render_summary(discrepancies: list[Discrepancy]) -> str:
                        # TODO: implement summary rendering.
                        return "no discrepancies"
                    """,
                ),
                _wf(
                    "reconcile/cli.py",
                    """
                    from __future__ import annotations

                    import csv
                    from pathlib import Path

                    from .matcher import find_discrepancies
                    from .models import Row
                    from .report import render_summary


                    def load_rows(path: Path) -> list[Row]:
                        rows: list[Row] = []
                        with path.open("r", encoding="utf-8-sig", newline="") as handle:
                            reader = csv.DictReader(handle)
                            for raw in reader:
                                if not raw:
                                    continue
                                merchant_order_id = (raw.get("merchant_order_id") or "").strip()
                                provider_txn_id = (raw.get("provider_txn_id") or "").strip()
                                if not merchant_order_id and not provider_txn_id:
                                    continue
                                rows.append(
                                    Row(
                                        merchant_order_id=merchant_order_id,
                                        provider_txn_id=provider_txn_id,
                                        amount_cents=int(raw["amount_cents"]),
                                        status=(raw.get("status") or "").strip(),
                                    )
                                )
                        return rows


                    def run(left_path: Path, right_path: Path) -> str:
                        discrepancies = find_discrepancies(load_rows(left_path), load_rows(right_path))
                        return render_summary(discrepancies)
                    """,
                ),
                _wf(
                    "tests/test_reconcile.py",
                    """
                    import unittest

                    from reconcile.matcher import find_discrepancies
                    from reconcile.models import Row
                    from reconcile.report import render_summary


                    class ReconcileTests(unittest.TestCase):
                        def test_detects_missing_amount_mismatch_and_duplicate(self) -> None:
                            left = [
                                Row("O-1", "P-1", 100, "SETTLED"),
                                Row("O-2", "P-2", 200, "SETTLED"),
                                Row("O-2", "P-2", 200, "SETTLED"),
                                Row("O-3", "P-3", 300, "REFUNDED"),
                            ]
                            right = [
                                Row("O-1", "P-1", 100, "SETTLED"),
                                Row("O-2", "P-2", 250, "SETTLED"),
                                Row("O-4", "P-4", 900, "SETTLED"),
                            ]
                            discrepancies = find_discrepancies(left, right)
                            kinds = sorted(item.kind for item in discrepancies)
                            self.assertEqual(kinds, ["amount_mismatch", "duplicate_left", "missing_left", "missing_right"])

                        def test_summary_mentions_counts(self) -> None:
                            left = [Row("O-1", "P-1", 100, "SETTLED")]
                            right = [Row("O-2", "P-2", 100, "SETTLED")]
                            summary = render_summary(find_discrepancies(left, right))
                            self.assertIn("missing_left=1", summary)
                            self.assertIn("missing_right=1", summary)


                    if __name__ == "__main__":
                        unittest.main()
                    """,
                ),
            ),
            validation_commands=("python3 -m unittest -q",),
            hidden_checklist=(
                "Requires coordinated edits across matcher/report rather than one-file explanation only.",
                "Must detect duplicate_left, missing_left, missing_right, and amount_mismatch.",
                "Should keep implementation small and deterministic.",
                "Passing tests is the primary success signal.",
            ),
        ),
        AgenticTask(
            task_id="agentic_python_restore_bootstrap",
            description="Fix a multi-file Python runtime restore flow so running state is not exposed before threads exist.",
            max_tokens=2200,
            workspace_files=(
                _wf(
                    "runtime/types.py",
                    """
                    from dataclasses import dataclass, field


                    @dataclass
                    class RuntimeState:
                        phase: str = "idle"
                        connected: bool = False
                        thread_ids: dict[str, str] = field(default_factory=dict)
                    """,
                ),
                _wf(
                    "runtime/threads.py",
                    """
                    from __future__ import annotations


                    class ThreadBootstrapper:
                        def __init__(self) -> None:
                            self.created: list[str] = []

                        def ensure_thread(self, agent_id: str) -> str:
                            thread_id = f"thread-{agent_id}"
                            self.created.append(thread_id)
                            return thread_id
                    """,
                ),
                _wf(
                    "runtime/session.py",
                    """
                    from __future__ import annotations

                    from dataclasses import dataclass


                    @dataclass(frozen=True)
                    class Snapshot:
                        agent_ids: list[str]
                    """,
                ),
                _wf(
                    "runtime/restore.py",
                    """
                    from __future__ import annotations

                    from .session import Snapshot
                    from .threads import ThreadBootstrapper
                    from .types import RuntimeState


                    def restore(snapshot: Snapshot, state: RuntimeState, bootstrapper: ThreadBootstrapper) -> RuntimeState:
                        state.phase = "running"
                        state.thread_ids = {}
                        for agent_id in snapshot.agent_ids:
                            if agent_id not in state.thread_ids:
                                state.thread_ids[agent_id] = bootstrapper.ensure_thread(agent_id)
                        state.connected = True
                        return state
                    """,
                ),
                _wf(
                    "tests/test_restore.py",
                    """
                    import unittest

                    from runtime.restore import restore
                    from runtime.session import Snapshot
                    from runtime.threads import ThreadBootstrapper
                    from runtime.types import RuntimeState


                    class RestoreTests(unittest.TestCase):
                        def test_does_not_expose_running_before_threads_exist(self) -> None:
                            state = RuntimeState()
                            bootstrapper = ThreadBootstrapper()
                            restore(Snapshot(agent_ids=["a1", "a2"]), state, bootstrapper)
                            self.assertEqual(state.phase, "running")
                            self.assertEqual(sorted(state.thread_ids), ["a1", "a2"])
                            self.assertEqual(len(bootstrapper.created), 2)

                        def test_existing_threads_are_not_recreated(self) -> None:
                            state = RuntimeState(thread_ids={"a1": "thread-a1"})
                            bootstrapper = ThreadBootstrapper()
                            restore(Snapshot(agent_ids=["a1", "a2"]), state, bootstrapper)
                            self.assertEqual(state.thread_ids["a1"], "thread-a1")
                            self.assertEqual(state.thread_ids["a2"], "thread-a2")
                            self.assertEqual(bootstrapper.created, ["thread-a2"])


                    if __name__ == "__main__":
                        unittest.main()
                    """,
                ),
            ),
            validation_commands=("python3 -m unittest -q",),
            hidden_checklist=(
                "Should preserve existing thread ids instead of recreating them blindly.",
                "Must not set running-visible state before thread restoration is effectively complete.",
                "Requires multi-file coordination across restore/types/threads.",
                "Passing tests should confirm idempotent bootstrap behavior.",
            ),
        ),
        AgenticTask(
            task_id="agentic_python_metrics_contract",
            description="Fix a small runtime/protocol/client package so metrics travel through session state instead of ad-hoc world state.",
            max_tokens=2200,
            workspace_files=(
                _wf(
                    "protocol/messages.py",
                    """
                    from __future__ import annotations

                    def make_session_state(phase: str, runtime: dict) -> dict:
                        return {
                            "type": "session.state",
                            "payload": {
                                "phase": phase,
                                "runtime": runtime,
                            },
                        }


                    def make_world_snapshot(tick: int, world: dict) -> dict:
                        return {
                            "type": "world.snapshot",
                            "payload": {
                                "tick": tick,
                                "world": world,
                            },
                        }
                    """,
                ),
                _wf(
                    "runtime/metrics.py",
                    """
                    class MetricsTracker:
                        def __init__(self) -> None:
                            self.turns_total = 0
                            self.invalid_output_count = 0
                            self.action_applied_count = 0
                            self.action_rejected_count = 0
                            self.queued_actions = 0

                        def snapshot(self) -> dict:
                            return {
                                "turns_total": self.turns_total,
                                "invalid_output_count": self.invalid_output_count,
                                "action_applied_count": self.action_applied_count,
                                "action_rejected_count": self.action_rejected_count,
                                "queued_actions": self.queued_actions,
                            }
                    """,
                ),
                _wf(
                    "runtime/server.py",
                    """
                    from __future__ import annotations

                    from protocol.messages import make_session_state, make_world_snapshot


                    def emit_state(phase: str, metrics_snapshot: dict) -> tuple[dict, dict]:
                        session_state = make_session_state(
                            phase,
                            {
                                "model": "local-qwen",
                                "tick_ms": 200,
                            },
                        )
                        world_snapshot = make_world_snapshot(10, {"tiles": []})
                        world_snapshot["payload"]["metrics"] = metrics_snapshot
                        return session_state, world_snapshot
                    """,
                ),
                _wf(
                    "client/state.py",
                    """
                    from __future__ import annotations


                    def reduce_client_state(message: dict, state: dict) -> dict:
                        if message["type"] == "session.state":
                            payload = message["payload"]
                            state["phase"] = payload["phase"]
                            state["runtime"] = payload["runtime"]
                        if message["type"] == "world.snapshot":
                            state["world"] = message["payload"]["world"]
                        return state
                    """,
                ),
                _wf(
                    "tests/test_metrics_contract.py",
                    """
                    import unittest

                    from client.state import reduce_client_state
                    from runtime.metrics import MetricsTracker
                    from runtime.server import emit_state


                    class MetricsContractTests(unittest.TestCase):
                        def test_metrics_live_in_session_state(self) -> None:
                            tracker = MetricsTracker()
                            tracker.turns_total = 9
                            tracker.queued_actions = 3
                            session_state, world_snapshot = emit_state("running", tracker.snapshot())
                            self.assertEqual(world_snapshot["payload"].get("metrics"), None)
                            self.assertEqual(session_state["payload"]["runtime"]["metrics"]["turns_total"], 9)
                            self.assertEqual(session_state["payload"]["runtime"]["metrics"]["queued_actions"], 3)

                        def test_client_reads_metrics_from_session_state(self) -> None:
                            tracker = MetricsTracker()
                            tracker.invalid_output_count = 4
                            session_state, _ = emit_state("running", tracker.snapshot())
                            state = reduce_client_state(session_state, {})
                            self.assertEqual(state["runtime"]["metrics"]["invalid_output_count"], 4)


                    if __name__ == "__main__":
                        unittest.main()
                    """,
                ),
            ),
            validation_commands=("python3 -m unittest -q",),
            hidden_checklist=(
                "Must move metrics into session.state/runtime rather than world snapshot.",
                "Requires edits across protocol, runtime, and client.",
                "Should use MetricsTracker.snapshot output as source of truth.",
                "Passing tests confirm protocol placement and client reduction logic.",
            ),
        ),
        AgenticTask(
            task_id="agentic_bash_log_triage",
            description="Produce a working Bash triage script that groups noisy logs into stable error signatures.",
            max_tokens=1800,
            workspace_files=(
                _wf(
                    "logs/app.log",
                    """
                    2026-03-08T10:00:01Z INFO healthcheck ok
                    2026-03-08T10:00:02Z ERROR OrderService failed to reserve inventory orderId=991 sku=abc code=INV-409
                    2026-03-08T10:00:03Z ERROR OrderService failed to reserve inventory orderId=992 sku=abc code=INV-409
                    2026-03-08T10:00:04Z ERROR PaymentGateway timeout providerTxnId=P-9001
                    2026-03-08T10:00:05Z ERROR PaymentGateway timeout providerTxnId=P-9002
                    2026-03-08T10:00:06Z WARN healthcheck latency 81ms
                    2026-03-08T10:00:07Z ERROR ProfileService duplicate email email=alice@example.com
                    """,
                ),
                _wf(
                    "scripts/triage.sh",
                    """
                    #!/usr/bin/env bash
                    set -euo pipefail
                    echo "TODO"
                    """,
                ),
                _wf(
                    "tests/test_triage.py",
                    """
                    import subprocess
                    import unittest
                    from pathlib import Path


                    class TriageScriptTests(unittest.TestCase):
                        def test_triage_groups_signatures(self) -> None:
                            repo_root = Path(__file__).resolve().parents[1]
                            script = repo_root / "scripts" / "triage.sh"
                            result = subprocess.run(
                                ["bash", str(script), str(repo_root / "logs" / "app.log")],
                                check=True,
                                capture_output=True,
                                text=True,
                            )
                            output = result.stdout.strip().splitlines()
                            self.assertTrue(any("OrderService failed to reserve inventory" in line and line.startswith("2 ") for line in output))
                            self.assertTrue(any("PaymentGateway timeout" in line and line.startswith("2 ") for line in output))
                            self.assertTrue(any("ProfileService duplicate email" in line and line.startswith("1 ") for line in output))
                            self.assertFalse(any("healthcheck" in line.lower() for line in output))


                    if __name__ == "__main__":
                        unittest.main()
                    """,
                ),
            ),
            validation_commands=("python3 -m unittest -q",),
            hidden_checklist=(
                "Must produce an actually runnable shell script, not just a plan.",
                "Should normalize volatile ids and suppress healthcheck noise.",
                "Output should be stable and count-sorted.",
                "Passing tests are the success criterion.",
            ),
        ),
        AgenticTask(
            task_id="agentic_ts_metrics_contract_patch",
            description="Apply the smallest multi-file TypeScript patch so runtime metrics live in session.state/runtime and the client reads them from there.",
            max_tokens=2200,
            workspace_files=(
                _wf(
                    "packages/protocol/src/messages.ts",
                    """
                    export type RuntimeState = {
                      model: string | null;
                      tickMs: number;
                    };

                    export type SessionStateMessage = {
                      type: "session.state";
                      payload: {
                        phase: "idle" | "running" | "paused";
                        runtime: RuntimeState;
                      };
                    };

                    export type WorldSnapshotMessage = {
                      type: "world.snapshot";
                      payload: {
                        tick: number;
                        world: Record<string, unknown>;
                      };
                    };
                    """,
                ),
                _wf(
                    "apps/game-runtime/src/runtime/metrics.ts",
                    """
                    export type RuntimeMetrics = {
                      turnsTotal: number;
                      invalidOutputCount: number;
                      actionAppliedCount: number;
                      actionRejectedCount: number;
                      queuedActions: number;
                    };

                    export class MetricsTracker {
                      private metrics: RuntimeMetrics = {
                        turnsTotal: 0,
                        invalidOutputCount: 0,
                        actionAppliedCount: 0,
                        actionRejectedCount: 0,
                        queuedActions: 0,
                      };

                      snapshot(): RuntimeMetrics {
                        return { ...this.metrics };
                      }
                    }
                    """,
                ),
                _wf(
                    "apps/game-runtime/src/runtime/sessionState.ts",
                    """
                    import type { SessionStateMessage, WorldSnapshotMessage } from "@codexgame/protocol";
                    import type { RuntimeMetrics } from "./metrics";

                    export function buildMessages(metrics: RuntimeMetrics): {
                      sessionState: SessionStateMessage;
                      worldSnapshot: WorldSnapshotMessage;
                    } {
                      return {
                        sessionState: {
                          type: "session.state",
                          payload: {
                            phase: "running",
                            runtime: {
                              model: "local-qwen",
                              tickMs: 200,
                            },
                          },
                        },
                        worldSnapshot: {
                          type: "world.snapshot",
                          payload: {
                            tick: 42,
                            world: {},
                            metrics,
                          },
                        } as unknown as WorldSnapshotMessage,
                      };
                    }
                    """,
                ),
                _wf(
                    "apps/game-client/src/state.ts",
                    """
                    export type ClientState = {
                      phase?: string;
                      runtime?: Record<string, unknown>;
                      world?: Record<string, unknown>;
                    };

                    export function reduceClientState(state: ClientState, message: any): ClientState {
                      if (message.type === "session.state") {
                        return {
                          ...state,
                          phase: message.payload.phase,
                          runtime: message.payload.runtime,
                        };
                      }
                      if (message.type === "world.snapshot") {
                        return {
                          ...state,
                          world: message.payload.world,
                          runtime: {
                            ...(state.runtime ?? {}),
                            metrics: message.payload.metrics,
                          },
                        };
                      }
                      return state;
                    }
                    """,
                ),
                _wf(
                    "tests/test_metrics_contract.mjs",
                    """
                    import test from "node:test";
                    import assert from "node:assert/strict";
                    import { buildMessages } from "../apps/game-runtime/src/runtime/sessionState.ts";
                    import { reduceClientState } from "../apps/game-client/src/state.ts";

                    test("metrics live in session.state runtime", () => {
                      const metrics = {
                        turnsTotal: 9,
                        invalidOutputCount: 4,
                        actionAppliedCount: 3,
                        actionRejectedCount: 1,
                        queuedActions: 2,
                      };
                      const { sessionState, worldSnapshot } = buildMessages(metrics);
                      assert.equal(worldSnapshot.payload.metrics, undefined);
                      assert.equal(sessionState.payload.runtime.metrics.turnsTotal, 9);
                    });

                    test("client reads metrics from session.state", () => {
                      const metrics = {
                        turnsTotal: 2,
                        invalidOutputCount: 1,
                        actionAppliedCount: 5,
                        actionRejectedCount: 0,
                        queuedActions: 3,
                      };
                      const { sessionState } = buildMessages(metrics);
                      const next = reduceClientState({}, sessionState);
                      assert.equal(next.runtime.metrics.queuedActions, 3);
                    });
                    """,
                ),
            ),
            validation_commands=("node --experimental-strip-types --test tests/test_metrics_contract.mjs",),
            hidden_checklist=(
                "Must move metrics into session.state/runtime rather than world.snapshot.",
                "Requires protocol, runtime, and client edits together.",
                "Should preserve client presentation-only role.",
                "Passing tests confirm protocol placement and client reduction.",
            ),
        ),
        AgenticTask(
            task_id="agentic_ts_restore_bootstrap_patch",
            description="Fix a multi-file TypeScript restore/bootstrap flow so running state is not exposed before thread restoration completes.",
            max_tokens=2200,
            workspace_files=(
                _wf(
                    "apps/game-runtime/src/runtime/types.ts",
                    """
                    export type RuntimePhase = "idle" | "restoring" | "running";

                    export type RuntimeState = {
                      phase: RuntimePhase;
                      threadIds: Record<string, string>;
                    };
                    """,
                ),
                _wf(
                    "apps/game-runtime/src/runtime/bootstrap.ts",
                    """
                    export class ThreadBootstrapper {
                      created: string[] = [];

                      ensureThread(agentId: string): string {
                        const threadId = `thread-${agentId}`;
                        this.created.push(threadId);
                        return threadId;
                      }
                    }
                    """,
                ),
                _wf(
                    "apps/game-runtime/src/runtime/restore.ts",
                    """
                    import type { RuntimeState } from "./types";
                    import { ThreadBootstrapper } from "./bootstrap";

                    export type Snapshot = {
                      agentIds: string[];
                      threadIds: Record<string, string>;
                    };

                    export function restoreRuntime(
                      snapshot: Snapshot,
                      state: RuntimeState,
                      bootstrapper: ThreadBootstrapper,
                    ): RuntimeState {
                      state.phase = "running";
                      state.threadIds = {};
                      for (const agentId of snapshot.agentIds) {
                        state.threadIds[agentId] = bootstrapper.ensureThread(agentId);
                      }
                      return state;
                    }
                    """,
                ),
                _wf(
                    "tests/test_restore_runtime.mjs",
                    """
                    import test from "node:test";
                    import assert from "node:assert/strict";
                    import { ThreadBootstrapper } from "../apps/game-runtime/src/runtime/bootstrap.ts";
                    import { restoreRuntime } from "../apps/game-runtime/src/runtime/restore.ts";

                    test("preserves existing thread ids and only creates missing ones", () => {
                      const state = { phase: "idle", threadIds: { a1: "thread-a1" } };
                      const bootstrapper = new ThreadBootstrapper();
                      const next = restoreRuntime(
                        {
                          agentIds: ["a1", "a2"],
                          threadIds: { a1: "thread-a1" },
                        },
                        state,
                        bootstrapper,
                      );
                      assert.equal(next.phase, "running");
                      assert.deepEqual(next.threadIds, { a1: "thread-a1", a2: "thread-a2" });
                      assert.deepEqual(bootstrapper.created, ["thread-a2"]);
                    });

                    test("does not expose running phase before thread ids exist", () => {
                      const state = { phase: "idle", threadIds: {} };
                      const bootstrapper = new ThreadBootstrapper();
                      const next = restoreRuntime({ agentIds: ["a1"], threadIds: {} }, state, bootstrapper);
                      assert.equal(next.phase, "running");
                      assert.deepEqual(next.threadIds, { a1: "thread-a1" });
                    });
                    """,
                ),
            ),
            validation_commands=("node --experimental-strip-types --test tests/test_restore_runtime.mjs",),
            hidden_checklist=(
                "Should preserve existing thread ids from snapshot instead of recreating them blindly.",
                "Must not expose running state before thread restoration is effectively complete.",
                "Requires multi-file coordination across restore/types/bootstrap.",
                "Passing tests confirm idempotent bootstrap behavior.",
            ),
        ),
        AgenticTask(
            task_id="agentic_bash_log_triage_gz",
            description="Produce a Bash triage script that handles .log and .log.gz together, normalizes volatile ids, ignores health checks, and sorts counts descending.",
            max_tokens=1800,
            workspace_files=(
                _wf(
                    "logs/app.log",
                    """
                    2026-03-08T10:00:01Z INFO healthcheck ok
                    2026-03-08T10:00:02Z ERROR OrderService failed to reserve inventory orderId=991 sku=abc code=INV-409
                    2026-03-08T10:00:03Z ERROR OrderService failed to reserve inventory orderId=992 sku=abc code=INV-409
                    2026-03-08T10:00:04Z ERROR PaymentGateway timeout providerTxnId=P-9001 traceId=T-1
                    """,
                ),
                _wf(
                    "logs/archive.log",
                    """
                    2026-03-08T10:00:05Z ERROR PaymentGateway timeout providerTxnId=P-9002 traceId=T-2
                    2026-03-08T10:00:06Z WARN healthcheck latency 81ms
                    2026-03-08T10:00:07Z ERROR ProfileService duplicate email email=alice@example.com requestId=R-9
                    """,
                ),
                _wf(
                    "scripts/triage.sh",
                    """
                    #!/usr/bin/env bash
                    set -euo pipefail
                    echo "TODO"
                    """,
                ),
                _wf(
                    "tests/test_triage_gz.py",
                    """
                    import gzip
                    import subprocess
                    import unittest
                    from pathlib import Path


                    class TriageScriptGzTests(unittest.TestCase):
                        def test_triage_groups_signatures_with_gz(self) -> None:
                            repo_root = Path(__file__).resolve().parents[1]
                            archive = repo_root / "logs" / "archive.log.gz"
                            archive.write_bytes(gzip.compress((repo_root / "logs" / "archive.log").read_bytes()))
                            script = repo_root / "scripts" / "triage.sh"
                            result = subprocess.run(
                                ["bash", str(script), str(repo_root / "logs" / "app.log"), str(archive)],
                                check=True,
                                capture_output=True,
                                text=True,
                            )
                            output = result.stdout.strip().splitlines()
                            self.assertTrue(any("OrderService failed to reserve inventory" in line and line.startswith("2 ") for line in output))
                            self.assertTrue(any("PaymentGateway timeout" in line and line.startswith("2 ") for line in output))
                            self.assertTrue(any("ProfileService duplicate email" in line and line.startswith("1 ") for line in output))
                            self.assertFalse(any("healthcheck" in line.lower() for line in output))


                    if __name__ == "__main__":
                        unittest.main()
                    """,
                ),
            ),
            validation_commands=("python3 -m unittest -q",),
            hidden_checklist=(
                "Must actually process .gz files, not just mention them.",
                "Should normalize volatile ids such as orderId/providerTxnId/traceId/email/requestId.",
                "Must suppress health check noise and sort counts descending.",
                "Passing tests are the success criterion.",
            ),
        ),
        AgenticTask(
            task_id="agentic_python_replay_analyzer_patch",
            description="Produce a working Python replay analyzer that streams JSONL, counts malformed lines, and aggregates per-session turns and invalid outputs.",
            max_tokens=1900,
            workspace_files=(
                _wf(
                    "data/replay.jsonl",
                    """
                    {"sessionId":"s1","type":"agent.turn"}
                    {"sessionId":"s1","type":"error","code":"invalid_output"}
                    {"sessionId":"s2","type":"agent.turn"}
                    not-json
                    {"sessionId":"s1","type":"agent.turn"}
                    {"sessionId":"s2","type":"agent.turn"}
                    {"sessionId":"s2","type":"error","code":"invalid_output"}
                    """,
                ),
                _wf(
                    "scripts/replay_analyzer.py",
                    """
                    import json


                    def analyze(path: str) -> dict:
                        return {"malformed_lines": 0, "sessions": {}}
                    """,
                ),
                _wf(
                    "tests/test_replay_analyzer.py",
                    """
                    import unittest
                    from pathlib import Path

                    from scripts.replay_analyzer import analyze


                    class ReplayAnalyzerTests(unittest.TestCase):
                        def test_streaming_analysis(self) -> None:
                            repo_root = Path(__file__).resolve().parents[1]
                            result = analyze(str(repo_root / "data" / "replay.jsonl"))
                            self.assertEqual(result["malformed_lines"], 1)
                            self.assertEqual(result["sessions"]["s1"]["turns"], 2)
                            self.assertEqual(result["sessions"]["s1"]["invalid_output"], 1)
                            self.assertEqual(result["sessions"]["s2"]["turns"], 2)
                            self.assertEqual(result["sessions"]["s2"]["invalid_output"], 1)


                    if __name__ == "__main__":
                        unittest.main()
                    """,
                ),
            ),
            validation_commands=("python3 -m unittest -q",),
            hidden_checklist=(
                "Must stream line-by-line rather than assume tiny files.",
                "Must count malformed lines explicitly.",
                "Must aggregate per-session turns and invalid_output counts.",
                "Passing tests are the success criterion.",
            ),
        ),
    ]
