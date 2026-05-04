#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Callable

from model_compare_tasks import ContextFile, _repo_file, get_tasks


COMMON_SYSTEM = dedent(
    """\
    You are a senior software engineer.

    Use only the provided project snapshot.
    Focus on correctness, sequencing, smallest safe changes, and concrete file-level guidance.
    Do not invent files or APIs that are not present in the snapshot.
    """
).strip()


@dataclass(frozen=True)
class SpecializedTask:
    task_id: str
    family: str
    description: str
    system_message: str
    max_tokens: int
    context_files: tuple[ContextFile, ...]
    round_prompts: tuple[str, ...]
    hidden_focus: tuple[str, ...]

    @property
    def multi_round(self) -> bool:
        return len(self.round_prompts) > 1

    def render_context(self, repo_root: Path) -> str:
        parts: list[str] = []
        for file in self.context_files:
            parts.append(f"=== File: {file.display_path} ===")
            parts.append(file.load_content(repo_root).rstrip())
            parts.append("")
        return "\n".join(parts).strip() + "\n"

    def manifest(self) -> dict:
        return {
            "task_id": self.task_id,
            "family": self.family,
            "description": self.description,
            "max_tokens": self.max_tokens,
            "multi_round": self.multi_round,
            "context_files": [file.display_path for file in self.context_files],
            "round_prompts": list(self.round_prompts),
            "hidden_focus": list(self.hidden_focus),
        }


def _inline(path: str, content: str) -> ContextFile:
    return ContextFile(display_path=path, inline_content=dedent(content).strip())


def _repeat_block(title: str, block: str, repeat: int) -> str:
    section = dedent(block).strip()
    parts: list[str] = []
    for index in range(1, repeat + 1):
        parts.append(f"# {title} {index}")
        parts.append(section)
    return "\n\n".join(parts)


def _longctx_restore(repo_root: Path) -> str:
    files = [
        "apps/game-runtime/src/runtime/GameRuntimeServer.ts",
        "apps/game-runtime/src/runtime/stateStore.ts",
        "apps/game-runtime/src/runtime/replay.ts",
        "apps/game-runtime/src/runtime/types.ts",
        "apps/game-runtime/src/runtime/contentStore.ts",
        "packages/protocol/src/messages.ts",
        "apps/game-runtime/test/ui-contract.integration.test.ts",
    ]
    chunks = [
        f"=== File: {path} ===\n{(repo_root / path).read_text(encoding='utf-8').rstrip()}"
        for path in files
    ]
    synthetic_log = _repeat_block(
        "restore-incident-log",
        """
        2026-03-08T09:00:01Z INFO restoreSession loaded simulation tick=1245 agents=3
        2026-03-08T09:00:01Z INFO phase=running preparedSeed=null connected=false threadIds={}
        2026-03-08T09:00:01Z WARN scheduler skipped agent turn because gameplay thread missing
        2026-03-08T09:00:02Z INFO model catalog refresh started
        2026-03-08T09:00:02Z INFO thread bootstrap requested for agent-1
        2026-03-08T09:00:02Z INFO thread bootstrap requested for agent-2
        2026-03-08T09:00:02Z INFO thread bootstrap requested for agent-3
        2026-03-08T09:00:03Z WARN client observed session.state phase=running while no thread ids were present
        """,
        320,
    )
    return "\n\n".join(chunks + ["=== File: logs/restore-incident.log ===", synthetic_log]).rstrip() + "\n"


def _longctx_metrics(repo_root: Path) -> str:
    files = [
        "apps/game-runtime/src/runtime/metrics.ts",
        "apps/game-runtime/src/runtime/GameRuntimeServer.ts",
        "packages/protocol/src/messages.ts",
        "apps/game-client/src/App.tsx",
        "apps/game-client/src/components/GodConsoleSidebar.tsx",
        "apps/game-runtime/test/ui-contract.integration.test.ts",
    ]
    chunks = [
        f"=== File: {path} ===\n{(repo_root / path).read_text(encoding='utf-8').rstrip()}"
        for path in files
    ]
    synthetic_log = _repeat_block(
        "runtime-metrics-snapshots",
        """
        {"tick": 1201, "queuedActions": 3, "invalidOutputCount": 5, "actionAppliedCount": 410, "actionRejectedCount": 29, "turnsTotal": 88}
        {"tick": 1202, "queuedActions": 1, "invalidOutputCount": 5, "actionAppliedCount": 411, "actionRejectedCount": 29, "turnsTotal": 89}
        {"tick": 1203, "queuedActions": 0, "invalidOutputCount": 6, "actionAppliedCount": 412, "actionRejectedCount": 29, "turnsTotal": 90}
        {"tick": 1204, "queuedActions": 4, "invalidOutputCount": 6, "actionAppliedCount": 412, "actionRejectedCount": 30, "turnsTotal": 90}
        """,
        360,
    )
    return "\n\n".join(chunks + ["=== File: logs/runtime-metrics.jsonl ===", synthetic_log]).rstrip() + "\n"


def _longctx_java(_: Path) -> str:
    repeated_service = _repeat_block(
        "src/main/java/com/example/order/OrderApprovalService.java",
        """
        package com.example.order;

        import java.time.Instant;

        public class OrderApprovalService {
            private final OrderRepository orderRepository;
            private final AuditRepository auditRepository;
            private final NotificationGateway notificationGateway;

            public OrderApprovalService(
                    OrderRepository orderRepository,
                    AuditRepository auditRepository,
                    NotificationGateway notificationGateway) {
                this.orderRepository = orderRepository;
                this.auditRepository = auditRepository;
                this.notificationGateway = notificationGateway;
            }

            public void approve(long orderId, String operator) {
                Order order = orderRepository.require(orderId);
                order.setStatus("APPROVED");
                orderRepository.save(order);
                notificationGateway.sendApproval(orderId, operator);
                auditRepository.record("ORDER_APPROVED", orderId, Instant.now());
            }
        }
        """,
        300,
    )
    repeated_log = _repeat_block(
        "logs/order-approval-failures.log",
        """
        2026-03-08T10:00:01Z INFO approving order=991 operator=alice
        2026-03-08T10:00:01Z WARN notification timeout order=991 operator=alice
        2026-03-08T10:00:01Z INFO retry attempt=2 order=991
        2026-03-08T10:00:02Z INFO duplicate approval email observed order=991 operator=alice
        """,
        360,
    )
    return "\n\n".join([repeated_service, repeated_log]).rstrip() + "\n"


def _generated(path: str, factory: Callable[[Path], str]) -> ContextFile:
    return ContextFile(display_path=path, generated_content=factory)


def _task_map() -> dict[str, object]:
    return {task.task_id: task for task in get_tasks()}


def get_specialized_tasks() -> list[SpecializedTask]:
    compare_task_by_id = _task_map()
    return [
        SpecializedTask(
            task_id="longctx_restore_bootstrap",
            family="longctx",
            description="Long-context restore/bootstrap analysis with repeated incident logs and real runtime files.",
            system_message=COMMON_SYSTEM,
            max_tokens=1400,
            context_files=(
                _generated("generated/longctx_restore_context.txt", _longctx_restore),
            ),
            round_prompts=(
                "Read the oversized runtime snapshot and identify the highest-risk correctness bug. Explain the root cause, the smallest safe fix, and the exact files that should change. End with regression checks.",
            ),
            hidden_focus=(
                "Must identify running state exposed before thread restoration completes.",
                "Must mention ordering between thread bootstrap and visible session state.",
            ),
        ),
        SpecializedTask(
            task_id="longctx_metrics_contract",
            family="longctx",
            description="Long-context protocol/runtime/client metrics analysis under repeated snapshots.",
            system_message=COMMON_SYSTEM,
            max_tokens=1400,
            context_files=(
                _generated("generated/longctx_metrics_context.txt", _longctx_metrics),
            ),
            round_prompts=(
                "Analyze the long-context metrics snapshot and identify the single most important contract bug or architectural gap. Give a bounded patch plan with exact files and risk checks.",
            ),
            hidden_focus=(
                "Should mention metrics contract ownership between runtime, protocol, and client.",
                "Should stay concrete and not drift into generic observability advice.",
            ),
        ),
        SpecializedTask(
            task_id="longctx_java_change_impact",
            family="longctx",
            description="Long-context Java change-impact reasoning with repeated service implementations and failure logs.",
            system_message=COMMON_SYSTEM,
            max_tokens=1400,
            context_files=(
                _generated("generated/longctx_java_change_impact.txt", _longctx_java),
            ),
            round_prompts=(
                "Given the oversized Java snapshot, identify the most dangerous correctness risk and propose the smallest safe remediation plan. Explicitly call out rollback and regression checks.",
            ),
            hidden_focus=(
                "Should identify duplicate side effects / notification before durable commit risk.",
                "Should keep remediation bounded instead of redesigning the system.",
            ),
        ),
        SpecializedTask(
            task_id="multi_restore_self_repair",
            family="multi_round",
            description="Three-round repair refinement on restore consistency.",
            system_message=COMMON_SYSTEM,
            max_tokens=1000,
            context_files=tuple(compare_task_by_id["ts_boot_restore_consistency"].context_files),  # type: ignore[index]
            round_prompts=(
                "Round 1: identify the highest-risk bug and give the smallest safe patch plan.",
                "Round 2: keep the same root cause, but refine the patch plan under this extra constraint: public message contracts must not change in this patch.",
                "Round 3: produce the final file-level minimal patch plan, ordered implementation steps, and regression checks. Do not restate background.",
            ),
            hidden_focus=(
                "Should converge on restore/order-of-operations, not drift to unrelated refactors.",
                "Final round should be more concrete than round 1.",
            ),
        ),
        SpecializedTask(
            task_id="multi_outbox_self_repair",
            family="multi_round",
            description="Three-round repair refinement on publish-before-commit risk.",
            system_message=COMMON_SYSTEM,
            max_tokens=1000,
            context_files=tuple(compare_task_by_id["java_outbox_publish_before_commit"].context_files),  # type: ignore[index]
            round_prompts=(
                "Round 1: identify the highest-risk correctness bug and give the smallest safe patch plan.",
                "Round 2: refine the answer under this extra constraint: message shape and repository interfaces should stay stable if possible.",
                "Round 3: produce the final minimal patch plan with exact files, order of change, and rollback/regression checks.",
            ),
            hidden_focus=(
                "Should stay focused on publish-before-commit / outbox ordering.",
                "Final answer should remain minimal and implementation-oriented.",
            ),
        ),
        SpecializedTask(
            task_id="multi_reconnect_self_repair",
            family="multi_round",
            description="Three-round repair refinement on reconnect circuit breaker behavior.",
            system_message=COMMON_SYSTEM,
            max_tokens=1000,
            context_files=tuple(compare_task_by_id["ts_reconnect_circuit_breaker"].context_files),  # type: ignore[index]
            round_prompts=(
                "Round 1: identify the highest-risk reconnect correctness bug and give the smallest safe patch plan.",
                "Round 2: refine the answer under this extra constraint: do not relax the hard safety guard maxReconnectAttempts.",
                "Round 3: produce the final minimal patch plan and the exact regression checks needed.",
            ),
            hidden_focus=(
                "Must preserve reconnect safety guard.",
                "Should converge toward a bounded reconnect fix, not a broad retry redesign.",
            ),
        ),
        SpecializedTask(
            task_id="plan_boot_restore_gap",
            family="planning",
            description="Complex planning task for boot-time restore implementation.",
            system_message=COMMON_SYSTEM,
            max_tokens=1400,
            context_files=(
                _repo_file("apps/game-runtime/src/runtime/GameRuntimeServer.ts"),
                _repo_file("apps/game-runtime/src/runtime/stateStore.ts"),
                _repo_file("apps/game-runtime/src/runtime/replay.ts"),
                _repo_file("apps/game-runtime/src/runtime/types.ts"),
                _repo_file("apps/game-runtime/test/ui-contract.integration.test.ts"),
            ),
            round_prompts=(
                "Produce a decision-complete implementation plan for boot-time restore from persisted session state. The plan should be concrete enough for another engineer to implement directly, including failure handling and tests.",
            ),
            hidden_focus=(
                "Should break the work into restore sequencing, thread recreation, and tests.",
                "Should keep client protocol compatibility explicit.",
            ),
        ),
        SpecializedTask(
            task_id="plan_metrics_exposure",
            family="planning",
            description="Complex planning task for exposing runtime metrics to client cleanly.",
            system_message=COMMON_SYSTEM,
            max_tokens=1400,
            context_files=(
                _repo_file("apps/game-runtime/src/runtime/GameRuntimeServer.ts"),
                _repo_file("packages/protocol/src/messages.ts"),
                _repo_file("apps/game-client/src/App.tsx"),
                _repo_file("apps/game-runtime/test/ui-contract.integration.test.ts"),
            ),
            round_prompts=(
                "Produce a decision-complete implementation plan for exposing runtime metrics snapshots to the client without breaking current protocol guarantees. Include type/interface changes, runtime wiring, client wiring, and tests.",
            ),
            hidden_focus=(
                "Should start from protocol contract, then runtime emit, then client consume.",
                "Should mention tests, not only code changes.",
            ),
        ),
        SpecializedTask(
            task_id="plan_reconnect_fault_injection",
            family="planning",
            description="Complex planning task for reconnect fault-injection integration tests.",
            system_message=COMMON_SYSTEM,
            max_tokens=1400,
            context_files=(
                _repo_file("apps/game-runtime/src/runtime/GameRuntimeServer.ts"),
                _repo_file("apps/game-runtime/test/ui-contract.integration.test.ts"),
                _inline(
                    "docs/testing-goal.md",
                    """
                    Goal:
                    Add reconnect fault-injection integration coverage that proves the runtime recovers from transient disconnects,
                    respects maxReconnectAttempts, and does not duplicate visible side effects after reconnect.
                    """,
                ),
            ),
            round_prompts=(
                "Produce a decision-complete implementation plan for reconnect fault-injection integration tests. Include harness shape, failure injection points, assertions, and rollout of new tests into the existing suite.",
            ),
            hidden_focus=(
                "Should define explicit failure injection points and assertions.",
                "Should preserve current runtime safety semantics.",
            ),
        ),
    ]
