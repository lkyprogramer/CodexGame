#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

try:
    from agentic_model_compare_tasks import get_agentic_tasks
except Exception:  # pragma: no cover - remote stage can import this when present
    get_agentic_tasks = None  # type: ignore[assignment]


@dataclass(frozen=True)
class WorkspaceFile:
    path: str
    content: str


@dataclass(frozen=True)
class OutputContract:
    kind: str
    spec: dict


@dataclass(frozen=True)
class HermesBenchTask:
    task_id: str
    family: str
    description: str
    prompt: str
    readonly: bool
    sandbox_write: bool
    working_dir_kind: str
    output_contract: OutputContract
    hidden_checklist: tuple[str, ...]
    expected_snippets: tuple[str, ...] = ()
    repo_files: tuple[str, ...] = ()
    workspace_files: tuple[WorkspaceFile, ...] = ()
    validation_commands: tuple[str, ...] = ()
    max_seconds: int = 240
    max_tokens_hint: int = 1200
    max_expected_changed_files: int | None = None

    def to_manifest_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "family": self.family,
            "description": self.description,
            "readonly": self.readonly,
            "sandbox_write": self.sandbox_write,
            "working_dir_kind": self.working_dir_kind,
            "output_contract": {"kind": self.output_contract.kind, "spec": self.output_contract.spec},
            "hidden_checklist": list(self.hidden_checklist),
            "expected_snippets": list(self.expected_snippets),
            "repo_files": list(self.repo_files),
            "validation_commands": list(self.validation_commands),
            "max_seconds": self.max_seconds,
            "max_tokens_hint": self.max_tokens_hint,
            "max_expected_changed_files": self.max_expected_changed_files,
        }


def _wf(path: str, content: str) -> WorkspaceFile:
    return WorkspaceFile(path=path, content=dedent(content).strip() + "\n")


REPO_RUNTIME_FILES = (
    "AGENTS.md",
    "README.md",
    "package.json",
    "apps/game-runtime/src/runtime/GameRuntimeServer.ts",
    "apps/game-runtime/src/runtime/contentStore.ts",
    "apps/game-runtime/src/runtime/config.ts",
    "apps/game-runtime/src/runtime/prompting.ts",
    "apps/game-runtime/src/runtime/replay.ts",
    "apps/game-runtime/src/runtime/stateStore.ts",
    "apps/game-runtime/src/codex/CodexAppServerClient.ts",
    "apps/game-client/src/App.tsx",
    "packages/protocol/src/messages.ts",
    "packages/protocol/src/actions.ts",
    "packages/protocol/src/build.ts",
    "packages/simulation/src/simulation.ts",
    "packages/simulation/src/world.ts",
    "packages/simulation/src/snapshot.ts",
)


def _basic_tasks() -> list[HermesBenchTask]:
    return [
        HermesBenchTask(
            task_id="basic_ready_only",
            family="basic",
            description="Minimal single-token query should return exact READY output.",
            prompt="Reply READY only.",
            readonly=True,
            sandbox_write=False,
            working_dir_kind="hermes",
            output_contract=OutputContract("exact_text", {"text": "READY"}),
            hidden_checklist=(
                "Must return exactly READY.",
                "Must not add explanation or markdown.",
            ),
            expected_snippets=("READY",),
            max_seconds=60,
            max_tokens_hint=16,
        ),
        HermesBenchTask(
            task_id="basic_status_line",
            family="basic",
            description="Single-line fixed-prefix output should remain stable.",
            prompt="Return exactly one line: STATUS: READY",
            readonly=True,
            sandbox_write=False,
            working_dir_kind="hermes",
            output_contract=OutputContract(
                "line_prefixes",
                {"lines": ["STATUS: READY"], "exact_count": 1},
            ),
            hidden_checklist=(
                "Must keep a single line.",
                "Must preserve exact STATUS prefix.",
            ),
            expected_snippets=("STATUS: READY",),
            max_seconds=60,
            max_tokens_hint=32,
        ),
        HermesBenchTask(
            task_id="basic_json_only",
            family="basic",
            description="Strict JSON-only response must be parseable without cleanup.",
            prompt=dedent(
                """\
                Return strict JSON only.

                Schema:
                {"status":"ready","endpoint":"local","mode":"custom"}
                """
            ).strip(),
            readonly=True,
            sandbox_write=False,
            working_dir_kind="hermes",
            output_contract=OutputContract(
                "json_keys",
                {"required_keys": ["status", "endpoint", "mode"], "exact_values": {"status": "ready"}},
            ),
            hidden_checklist=(
                "Must be valid JSON.",
                "Must not include markdown fences.",
                "Must include status, endpoint, mode.",
            ),
            expected_snippets=("ready", "local", "custom"),
            max_seconds=60,
            max_tokens_hint=64,
        ),
        HermesBenchTask(
            task_id="basic_three_bullets",
            family="basic",
            description="Longer plain-text response should remain contract-compliant.",
            prompt=dedent(
                """\
                Explain when this local endpoint should prefer system+user over developer role.

                Output requirements:
                - exactly 3 bullet lines
                - each bullet under 12 words
                - no markdown fences
                """
            ).strip(),
            readonly=True,
            sandbox_write=False,
            working_dir_kind="hermes",
            output_contract=OutputContract("bullet_count", {"count": 3}),
            hidden_checklist=(
                "Must return exactly 3 bullets.",
                "Should mention role compatibility or stability.",
            ),
            expected_snippets=("system", "user", "developer"),
            max_seconds=90,
            max_tokens_hint=160,
        ),
    ]


def _repo_readonly_tasks() -> list[HermesBenchTask]:
    return [
        HermesBenchTask(
            task_id="repo_entrypoints_json",
            family="repo_readonly",
            description="Identify the core authority and main entrypoints in CodexGame.",
            prompt=dedent(
                """\
                Use terminal tools to inspect the current repository first.
                Do not modify files.

                Return strict JSON only with this schema:
                {
                  "runtime_authority": "string",
                  "runtime_entrypoint": "string",
                  "client_entrypoint": "string",
                  "protocol_source": "string"
                }
                """
            ).strip(),
            readonly=True,
            sandbox_write=False,
            working_dir_kind="repo",
            output_contract=OutputContract(
                "json_keys",
                {"required_keys": ["runtime_authority", "runtime_entrypoint", "client_entrypoint", "protocol_source"]},
            ),
            hidden_checklist=(
                "Must identify runtime authority as apps/game-runtime.",
                "Must point to GameRuntimeServer.ts or equivalent runtime entrypoint.",
                "Must point to apps/game-client/src/App.tsx for client entrypoint.",
                "Must identify packages/protocol/src/messages.ts as protocol source.",
            ),
            expected_snippets=(
                "apps/game-runtime",
                "GameRuntimeServer.ts",
                "apps/game-client/src/App.tsx",
                "packages/protocol/src/messages.ts",
            ),
            repo_files=REPO_RUNTIME_FILES,
            max_seconds=180,
            max_tokens_hint=500,
        ),
        HermesBenchTask(
            task_id="repo_restore_root_cause",
            family="repo_readonly",
            description="Analyze the boot-time restore inconsistency risk and propose the smallest safe fix.",
            prompt=dedent(
                """\
                Use terminal tools to inspect the current repository first.
                Do not modify files.

                Task:
                Find the most likely root cause of the boot-time restore inconsistency around running state and thread restoration.

                Output format:
                1. Root cause
                2. Evidence
                3. Smallest safe fix
                4. Risks
                """
            ).strip(),
            readonly=True,
            sandbox_write=False,
            working_dir_kind="repo",
            output_contract=OutputContract("sections", {"required_prefixes": ["1.", "2.", "3.", "4."]}),
            hidden_checklist=(
                "Must mention running state exposed before threads are restored or rebuilt.",
                "Must reference session persistence / stateStore / runtime restore path.",
                "Must prefer a minimal ordering fix over broad refactor.",
            ),
            expected_snippets=("running", "thread", "stateStore", "restore"),
            repo_files=REPO_RUNTIME_FILES,
            max_seconds=240,
            max_tokens_hint=900,
        ),
        HermesBenchTask(
            task_id="repo_metrics_protocol_json",
            family="repo_readonly",
            description="Explain the protocol-first gap for exposing runtime metrics to the client.",
            prompt=dedent(
                """\
                Use terminal tools to inspect the current repository first.
                Do not modify files.

                Return strict JSON only with this schema:
                {
                  "root_cause": "string",
                  "protocol_files": ["string"],
                  "runtime_files": ["string"],
                  "client_files": ["string"],
                  "smallest_safe_fix": "string"
                }
                """
            ).strip(),
            readonly=True,
            sandbox_write=False,
            working_dir_kind="repo",
            output_contract=OutputContract(
                "json_keys",
                {"required_keys": ["root_cause", "protocol_files", "runtime_files", "client_files", "smallest_safe_fix"]},
            ),
            hidden_checklist=(
                "Must route metrics through protocol first, not ad-hoc client state.",
                "Must mention packages/protocol/src/messages.ts.",
                "Must include runtime and client touch points.",
            ),
            expected_snippets=(
                "packages/protocol/src/messages.ts",
                "apps/game-runtime",
                "apps/game-client",
                "metrics",
            ),
            repo_files=REPO_RUNTIME_FILES,
            max_seconds=240,
            max_tokens_hint=900,
        ),
        HermesBenchTask(
            task_id="repo_reconnect_circuit_breaker",
            family="repo_readonly",
            description="Trace the reconnect circuit breaker risk and propose the minimum safe guardrail-preserving fix.",
            prompt=dedent(
                """\
                Use terminal tools to inspect the current repository first.
                Do not modify files.

                Task:
                Explain how reconnect handling could bypass or weaken the circuit breaker, and give the smallest safe fix.

                Output format:
                1. Root cause
                2. Evidence
                3. Smallest safe fix
                4. Regression risks
                """
            ).strip(),
            readonly=True,
            sandbox_write=False,
            working_dir_kind="repo",
            output_contract=OutputContract("sections", {"required_prefixes": ["1.", "2.", "3.", "4."]}),
            hidden_checklist=(
                "Must mention maxReconnectAttempts or reconnect guardrail.",
                "Must preserve safety semantics instead of widening retries.",
                "Should reference runtime config or reconnect loop implementation.",
            ),
            expected_snippets=("maxReconnectAttempts", "reconnect", "circuit breaker", "config"),
            repo_files=REPO_RUNTIME_FILES,
            max_seconds=240,
            max_tokens_hint=900,
        ),
        HermesBenchTask(
            task_id="repo_atomic_build_write_guard",
            family="repo_readonly",
            description="Explain the atomic build write requirement and the smallest safe way to preserve it.",
            prompt=dedent(
                """\
                Use terminal tools to inspect the current repository first.
                Do not modify files.

                Return strict JSON only with this schema:
                {
                  "root_cause": "string",
                  "key_file": "string",
                  "required_invariant": "string",
                  "smallest_safe_fix": "string",
                  "risks": ["string"]
                }
                """
            ).strip(),
            readonly=True,
            sandbox_write=False,
            working_dir_kind="repo",
            output_contract=OutputContract(
                "json_keys",
                {"required_keys": ["root_cause", "key_file", "required_invariant", "smallest_safe_fix", "risks"]},
            ),
            hidden_checklist=(
                "Must mention tmp + rename or equivalent atomic write pattern.",
                "Must identify contentStore.ts as key file.",
                "Must not recommend non-atomic overwrite.",
            ),
            expected_snippets=("contentStore.ts", "tmp", "rename", "atomic"),
            repo_files=REPO_RUNTIME_FILES,
            max_seconds=180,
            max_tokens_hint=700,
        ),
        HermesBenchTask(
            task_id="repo_top_gaps_json",
            family="repo_readonly",
            description="Summarize the top 3 engineering gaps already implied by the repository and AGENTS guidance.",
            prompt=dedent(
                """\
                Use terminal tools to inspect the current repository first.
                Do not modify files.

                Return strict JSON only with this schema:
                {
                  "gaps": [
                    {"title":"string","files":["string"],"reason":"string"}
                  ]
                }

                Return exactly 3 gaps.
                """
            ).strip(),
            readonly=True,
            sandbox_write=False,
            working_dir_kind="repo",
            output_contract=OutputContract(
                "json_array_length",
                {"root_key": "gaps", "length": 3},
            ),
            hidden_checklist=(
                "Should surface boot-time restore gap.",
                "Should surface reconnect fault-injection or circuit-breaker test gap.",
                "Should surface runtime metrics exposure gap.",
            ),
            expected_snippets=("restore", "reconnect", "metrics"),
            repo_files=REPO_RUNTIME_FILES,
            max_seconds=240,
            max_tokens_hint=900,
        ),
    ]


def _terminal_tasks() -> list[HermesBenchTask]:
    return [
        HermesBenchTask(
            task_id="terminal_pwd_git_status",
            family="terminal",
            description="Use terminal tools to report cwd and clean git status in fixed format.",
            prompt=dedent(
                """\
                Use terminal tools only.
                Do not modify files.

                Run:
                1. pwd
                2. git status --short

                Return exactly two lines:
                PWD: <absolute-path>
                GIT: <summary>
                """
            ).strip(),
            readonly=True,
            sandbox_write=False,
            working_dir_kind="repo",
            output_contract=OutputContract(
                "line_prefixes",
                {"required_prefixes": ["PWD:", "GIT:"], "exact_count": 2},
            ),
            hidden_checklist=(
                "Must call terminal tools, not guess the path.",
                "Must preserve fixed two-line format.",
            ),
            expected_snippets=("PWD:", "GIT:"),
            repo_files=REPO_RUNTIME_FILES,
            max_seconds=120,
            max_tokens_hint=128,
        ),
        HermesBenchTask(
            task_id="terminal_protocol_version_json",
            family="terminal",
            description="Use rg to locate the protocol version source and return fixed JSON.",
            prompt=dedent(
                """\
                Use terminal tools only.
                Do not modify files.

                Find where the runtime protocol version is defined.

                Return strict JSON only with this schema:
                {"path":"string","version":"string"}
                """
            ).strip(),
            readonly=True,
            sandbox_write=False,
            working_dir_kind="repo",
            output_contract=OutputContract(
                "json_keys",
                {"required_keys": ["path", "version"], "exact_values": {"version": "v1"}},
            ),
            hidden_checklist=(
                "Must locate packages/protocol/src/messages.ts.",
                "Must report v1.",
            ),
            expected_snippets=("packages/protocol/src/messages.ts", "v1"),
            repo_files=REPO_RUNTIME_FILES,
            max_seconds=120,
            max_tokens_hint=160,
        ),
        HermesBenchTask(
            task_id="terminal_log_summary_json",
            family="terminal",
            description="Summarize recurring errors from a prepared log fixture using shell tools only.",
            prompt=dedent(
                """\
                Use terminal tools only.
                Do not modify files.

                There is an application log in the current directory.
                Return strict JSON only with this schema:
                {
                  "error_count": 0,
                  "top_signature": "string",
                  "top_count": 0
                }
                """
            ).strip(),
            readonly=True,
            sandbox_write=False,
            working_dir_kind="fixture",
            output_contract=OutputContract(
                "json_keys",
                {"required_keys": ["error_count", "top_signature", "top_count"]},
            ),
            hidden_checklist=(
                "Must use the actual log fixture.",
                "Must identify the dominant recurring signature.",
            ),
            expected_snippets=("Database timeout", "7"),
            workspace_files=(
                _wf(
                    "app.log",
                    """
                    2026-03-15T10:00:01Z INFO startup complete
                    2026-03-15T10:01:00Z ERROR Database timeout while loading session
                    2026-03-15T10:01:03Z ERROR Database timeout while loading session
                    2026-03-15T10:01:07Z ERROR Database timeout while loading session
                    2026-03-15T10:02:00Z WARN retrying
                    2026-03-15T10:03:00Z ERROR Redis connection reset by peer
                    2026-03-15T10:03:05Z ERROR Database timeout while loading session
                    2026-03-15T10:04:00Z INFO heartbeat
                    2026-03-15T10:05:00Z ERROR Database timeout while loading session
                    2026-03-15T10:05:10Z ERROR Redis connection reset by peer
                    2026-03-15T10:06:00Z ERROR Database timeout while loading session
                    2026-03-15T10:06:15Z ERROR Database timeout while loading session
                    """,
                ),
            ),
            max_seconds=120,
            max_tokens_hint=220,
        ),
        HermesBenchTask(
            task_id="terminal_top_level_dirs_json",
            family="terminal",
            description="Report whether key top-level project directories exist.",
            prompt=dedent(
                """\
                Use terminal tools only.
                Do not modify files.

                Return strict JSON only with this schema:
                {
                  "repo_name": "string",
                  "apps": true,
                  "packages": true,
                  "scripts": true,
                  "data": true
                }
                """
            ).strip(),
            readonly=True,
            sandbox_write=False,
            working_dir_kind="repo",
            output_contract=OutputContract(
                "json_keys",
                {"required_keys": ["repo_name", "apps", "packages", "scripts", "data"]},
            ),
            hidden_checklist=(
                "Must inspect the actual directory structure.",
                "Must identify apps/packages/scripts/data.",
            ),
            expected_snippets=("CodexGame", "apps", "packages", "scripts", "data"),
            repo_files=REPO_RUNTIME_FILES,
            max_seconds=120,
            max_tokens_hint=180,
        ),
    ]


def _extra_agentic_tasks() -> list[HermesBenchTask]:
    return [
        HermesBenchTask(
            task_id="sandbox_python_jsonl_replay_analyzer",
            family="sandbox",
            description="Implement a replay JSONL analyzer with malformed-line tolerance.",
            prompt=dedent(
                """\
                You are in a temporary workspace.
                Use terminal tools and file editing tools in the current directory.
                You may modify files only inside the current directory.

                Task:
                Complete the smallest safe implementation so the validation command passes.

                Output requirements:
                Return strict JSON only with:
                {"summary":"string","files_changed":["string"],"validation":"string"}
                """
            ).strip(),
            readonly=False,
            sandbox_write=True,
            working_dir_kind="sandbox",
            output_contract=OutputContract(
                "json_keys",
                {"required_keys": ["summary", "files_changed", "validation"]},
            ),
            hidden_checklist=(
                "Must tolerate malformed JSONL lines instead of crashing.",
                "Must return aggregated counts by event type.",
                "Must keep implementation small.",
            ),
            expected_snippets=("summary", "files_changed", "validation"),
            workspace_files=(
                _wf(
                    "analyzer.py",
                    """
                    from __future__ import annotations

                    import json
                    from collections import Counter
                    from pathlib import Path


                    def summarize(path: Path) -> dict[str, int]:
                        # TODO: tolerate malformed lines and count events by type.
                        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
                        counts = Counter(row["event"] for row in rows)
                        return dict(counts)
                    """,
                ),
                _wf(
                    "sample.jsonl",
                    """
                    {"event":"turn.start","ok":true}
                    {"event":"turn.end","ok":true}
                    {bad json line}
                    {"event":"turn.start","ok":true}
                    {"event":"build.result","ok":false}
                    """,
                ),
                _wf(
                    "tests/test_analyzer.py",
                    """
                    import unittest
                    from pathlib import Path

                    from analyzer import summarize


                    class AnalyzerTests(unittest.TestCase):
                        def test_tolerates_bad_lines_and_counts_events(self) -> None:
                            counts = summarize(Path("sample.jsonl"))
                            self.assertEqual(counts["turn.start"], 2)
                            self.assertEqual(counts["turn.end"], 1)
                            self.assertEqual(counts["build.result"], 1)


                    if __name__ == "__main__":
                        unittest.main()
                    """,
                ),
            ),
            validation_commands=("python3 -m unittest -q",),
            max_seconds=360,
            max_tokens_hint=1400,
            max_expected_changed_files=2,
        ),
        HermesBenchTask(
            task_id="sandbox_bash_atomic_swap",
            family="sandbox",
            description="Produce a working Bash deploy script that performs atomic symlink swap after health check.",
            prompt=dedent(
                """\
                You are in a temporary workspace.
                Use terminal tools and file editing tools in the current directory.
                You may modify files only inside the current directory.

                Task:
                Complete the deploy script so the validation command passes.

                Output requirements:
                Return strict JSON only with:
                {"summary":"string","files_changed":["string"],"validation":"string"}
                """
            ).strip(),
            readonly=False,
            sandbox_write=True,
            working_dir_kind="sandbox",
            output_contract=OutputContract(
                "json_keys",
                {"required_keys": ["summary", "files_changed", "validation"]},
            ),
            hidden_checklist=(
                "Must only flip current symlink after health check succeeds.",
                "Must keep previous symlink target on failed health check.",
                "Should avoid broad redesign.",
            ),
            expected_snippets=("summary", "files_changed", "validation"),
            workspace_files=(
                _wf(
                    "deploy.sh",
                    """
                    #!/usr/bin/env bash
                    set -euo pipefail

                    release_dir="$1"
                    current_link="./current"

                    # TODO: only switch symlink after a successful health check
                    ln -sfn "$release_dir" "$current_link"
                    "$release_dir/healthcheck.sh"
                    """,
                ),
                _wf(
                    "releases/good/healthcheck.sh",
                    """
                    #!/usr/bin/env bash
                    exit 0
                    """,
                ),
                _wf(
                    "releases/bad/healthcheck.sh",
                    """
                    #!/usr/bin/env bash
                    exit 1
                    """,
                ),
                _wf(
                    "test_deploy.sh",
                    """
                    #!/usr/bin/env bash
                    set -euo pipefail

                    chmod +x deploy.sh releases/good/healthcheck.sh releases/bad/healthcheck.sh
                    rm -f current
                    ln -s releases/good current

                    ./deploy.sh releases/good
                    test "$(readlink current)" = "releases/good"

                    ./deploy.sh releases/bad || true
                    test "$(readlink current)" = "releases/good"
                    """,
                ),
            ),
            validation_commands=("bash test_deploy.sh",),
            max_seconds=360,
            max_tokens_hint=1400,
            max_expected_changed_files=1,
        ),
    ]


def _sandbox_tasks() -> list[HermesBenchTask]:
    tasks: list[HermesBenchTask] = []
    if get_agentic_tasks is not None:
        imported = list(get_agentic_tasks())
        for task in imported:
            tasks.append(
                HermesBenchTask(
                    task_id=task.task_id,
                    family="sandbox",
                    description=task.description,
                    prompt=dedent(
                        """\
                        You are in a temporary workspace.
                        Use terminal tools and file editing tools in the current directory.
                        You may modify files only inside the current directory.

                        Task:
                        Complete the smallest safe fix so the validation command passes.

                        Output requirements:
                        Return strict JSON only with:
                        {"summary":"string","files_changed":["string"],"validation":"string"}
                        """
                    ).strip(),
                    readonly=False,
                    sandbox_write=True,
                    working_dir_kind="sandbox",
                    output_contract=OutputContract(
                        "json_keys",
                        {"required_keys": ["summary", "files_changed", "validation"]},
                    ),
                    hidden_checklist=task.hidden_checklist,
                    expected_snippets=("summary", "files_changed", "validation"),
                    workspace_files=tuple(WorkspaceFile(path=f.path, content=f.content) for f in task.workspace_files),
                    validation_commands=task.validation_commands,
                    max_seconds=420,
                    max_tokens_hint=task.max_tokens,
                    max_expected_changed_files=4,
                )
            )
    tasks.extend(_extra_agentic_tasks())
    return tasks


def get_tasks() -> list[HermesBenchTask]:
    tasks = _basic_tasks() + _repo_readonly_tasks() + _terminal_tasks() + _sandbox_tasks()
    if len(tasks) != 20:
        raise ValueError(f"Expected 20 tasks, got {len(tasks)}")
    return tasks


def get_required_repo_files() -> tuple[str, ...]:
    files: list[str] = []
    for task in get_tasks():
        for path in task.repo_files:
            if path not in files:
                files.append(path)
    return tuple(files)


def get_tasks_by_family() -> dict[str, list[HermesBenchTask]]:
    grouped: dict[str, list[HermesBenchTask]] = {}
    for task in get_tasks():
        grouped.setdefault(task.family, []).append(task)
    return grouped


def write_workspace(root: Path, files: tuple[WorkspaceFile, ...]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for file in files:
        path = root / file.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file.content, encoding="utf-8")


if __name__ == "__main__":
    import json

    print(json.dumps([task.to_manifest_dict() for task in get_tasks()], ensure_ascii=False, indent=2))
