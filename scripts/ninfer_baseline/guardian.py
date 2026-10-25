#!/usr/bin/env python3
"""Supervise one benchmark process group without touching the inference engine."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time


COMPLETED = "MEASUREMENT_STAGES_FINISHED"


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def timestamp(value):
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp lacks timezone")
    return parsed


def atomic_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_status(path, child_pid):
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict) or value.get("pid") != child_pid:
            return None, "status missing or belongs to another runner PID"
        return value, None
    except (OSError, ValueError, TypeError) as exc:
        return None, "status unreadable: " + type(exc).__name__


def status_failure(status, now, elapsed, heartbeat_timeout=120, deadline_grace=120):
    """Return a stop reason; startup gets the same heartbeat grace as a live runner."""
    if status is None:
        return "STATUS_UNAVAILABLE" if elapsed > heartbeat_timeout else None
    try:
        heartbeat = timestamp(status["heartbeat_utc"])
        if (now - heartbeat).total_seconds() > heartbeat_timeout:
            return "HEARTBEAT_STALE"
        if status.get("state") == "RUNNING":
            deadline = timestamp(status["request_deadline_utc"])
            if (now - deadline).total_seconds() > deadline_grace:
                return "REQUEST_DEADLINE_EXCEEDED"
    except (KeyError, ValueError, TypeError, AttributeError):
        return "INVALID_STATUS_TIMESTAMPS"
    return None


def terminate_group(child, grace):
    """The group is the new session created for this child, never an engine process."""
    actions = []
    try:
        os.killpg(child.pid, signal.SIGTERM)
        actions.append("SIGTERM")
    except ProcessLookupError:
        child.wait()
        return actions
    try:
        child.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        pass
    # Descendants can outlive the direct child; terminate the whole remaining group.
    try:
        os.killpg(child.pid, signal.SIGKILL)
        actions.append("SIGKILL")
    except ProcessLookupError:
        pass
    child.wait()
    return actions


def supervise(root, runner, stage, poll_seconds=15, heartbeat_timeout=120,
              deadline_grace=120, terminate_grace=15):
    root, runner = Path(root).resolve(), Path(runner).resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    started = utc_now()
    startup_monotonic = time.monotonic()
    stop = threading.Event()
    received_signal = []
    previous_handlers = {}

    def requested(signum, _frame):
        received_signal.append(signum)
        stop.set()

    record = {
        "schema": "ninfer.baseline.watchdog.v1", "state": "STARTING",
        "qualification": "NOT_A_PASS", "supervisor_pid": os.getpid(),
        "supervisor_started_utc": started.isoformat(), "stage": stage,
        "runner": str(runner), "runner_sha256": hashlib.sha256(runner.read_bytes()).hexdigest(),
        "guardian_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python_executable": sys.executable, "python_version": sys.version,
        "poll_seconds": poll_seconds, "heartbeat_timeout_seconds": heartbeat_timeout,
        "deadline_grace_seconds": deadline_grace, "automatic_retry": False,
    }
    watchdog = root / "watchdog.json"

    def publish(**values):
        record.update(values)
        record["heartbeat_utc"] = utc_now().isoformat()
        atomic_json(watchdog, record)

    child = None
    try:
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[signum] = signal.signal(signum, requested)
        logfile = root / ("guardian-child-" + str(time.time_ns()) + ".log")
        argv = [sys.executable, "-u", str(runner), "--root", str(root), "--stage", stage]
        publish(argv=argv, child_log=str(logfile))
        with logfile.open("xb", buffering=0) as output:
            child = subprocess.Popen(argv, stdout=output, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, start_new_session=True)
            publish(state="MONITORING", child_pid=child.pid, child_process_group=child.pid,
                    child_started_utc=utc_now().isoformat())
            while True:
                status, status_error = read_status(root / "status.json", child.pid)
                code = child.poll()
                if stop.is_set():
                    publish(state="STOPPING", stop_reason="SUPERVISOR_SIGNAL",
                            received_signal=received_signal[-1] if received_signal else None)
                    actions = terminate_group(child, terminate_grace)
                    publish(state="STOPPED", child_returncode=child.returncode,
                            termination_actions=actions, finished_utc=utc_now().isoformat())
                    return 128 + (received_signal[-1] if received_signal else signal.SIGTERM)
                if code is not None:
                    # The status writer finishes before process exit; read it again after poll.
                    status, status_error = read_status(root / "status.json", child.pid)
                    complete = code == 0 and status is not None and status.get("state") == COMPLETED
                    actions = terminate_group(child, terminate_grace)
                    publish(state=COMPLETED if complete else "NEEDS_ATTENTION",
                            stop_reason="CHILD_EXITED", child_returncode=code,
                            termination_actions=actions, runner_state=status.get("state") if status else None,
                            status_error=status_error, finished_utc=utc_now().isoformat())
                    return 0 if complete else 1
                reason = status_failure(status, utc_now(), time.monotonic() - startup_monotonic,
                                        heartbeat_timeout, deadline_grace)
                publish(runner_state=status.get("state") if status else None,
                        runner_heartbeat_utc=status.get("heartbeat_utc") if status else None,
                        runner_current_case=status.get("current_case") if status else None,
                        status_error=status_error)
                if reason:
                    publish(state="STOPPING", stop_reason=reason)
                    actions = terminate_group(child, terminate_grace)
                    publish(state="NEEDS_ATTENTION", child_returncode=child.returncode,
                            termination_actions=actions, finished_utc=utc_now().isoformat())
                    return 1
                stop.wait(poll_seconds)
    except BaseException as exc:
        actions = terminate_group(child, terminate_grace) if child is not None else []
        publish(state="NEEDS_ATTENTION", stop_reason="SUPERVISOR_ERROR",
                error=type(exc).__name__ + ": " + str(exc), termination_actions=actions,
                finished_utc=utc_now().isoformat())
        raise
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--runner", type=Path, default=Path(__file__).with_name("runner.py"))
    parser.add_argument("--stage", choices=["all", "bridge", "priority", "remaining"], default="all")
    args = parser.parse_args()
    os.umask(0o077)
    return supervise(args.root, args.runner, args.stage)


if __name__ == "__main__":
    raise SystemExit(main())
