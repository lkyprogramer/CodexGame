"""Local tests only: fake benchmark children never contact the inference server."""
import datetime as dt
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import guardian


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 10, 20, tzinfo=dt.timezone.utc)

    def status(self, age=0, **values):
        return {"state": "CALIBRATING",
                "heartbeat_utc": (self.now - dt.timedelta(seconds=age)).isoformat(), **values}

    def test_startup_waits_for_current_pid_status(self):
        self.assertIsNone(guardian.status_failure(None, self.now, 119))
        self.assertEqual(guardian.status_failure(None, self.now, 121), "STATUS_UNAVAILABLE")
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "status.json"
            p.write_text(json.dumps({"pid": 4, "state": guardian.COMPLETED}))
            self.assertIsNone(guardian.read_status(p, 5)[0])
            p.write_text("{")
            self.assertIsNone(guardian.read_status(p, 5)[0])

    def test_fresh_heartbeat_allows_long_hash_or_calibration(self):
        self.assertIsNone(guardian.status_failure(self.status(), self.now, 900))
        self.assertEqual(guardian.status_failure(self.status(age=121), self.now, 900),
                         "HEARTBEAT_STALE")

    def test_deadline_catches_stuck_running_with_fresh_heartbeat(self):
        s = self.status(state="RUNNING", request_deadline_utc=(
            self.now - dt.timedelta(seconds=121)).isoformat())
        self.assertEqual(guardian.status_failure(s, self.now, 900), "REQUEST_DEADLINE_EXCEEDED")
        s["state"] = "CALIBRATING"
        self.assertIsNone(guardian.status_failure(s, self.now, 900))

    def test_invalid_timestamps_fail_closed(self):
        for s in ({"heartbeat_utc": "bad"}, {"heartbeat_utc": "2026-10-20T00:00:00"},
                  self.status(state="RUNNING")):
            with self.subTest(status=s):
                self.assertEqual(guardian.status_failure(s, self.now, 5),
                                 "INVALID_STATUS_TIMESTAMPS")

    def test_termination_addresses_child_group_and_escalates(self):
        child = mock.Mock(pid=1234)
        child.wait.side_effect = [subprocess.TimeoutExpired("fake", 1), -9]
        with mock.patch.object(guardian.os, "killpg") as kill:
            self.assertEqual(guardian.terminate_group(child, 1), ["SIGTERM", "SIGKILL"])
            self.assertEqual(kill.call_args_list,
                             [mock.call(1234, signal.SIGTERM), mock.call(1234, signal.SIGKILL)])


@unittest.skipUnless(os.name == "posix", "requires POSIX process groups")
class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "evidence"
        self.runner = self.base / "fake_runner.py"

    def fake(self, body):
        self.runner.write_text('''import datetime as dt, json, os, pathlib, signal, sys, time
root = pathlib.Path(sys.argv[sys.argv.index("--root") + 1])
def status(state, heartbeat=None):
    value = {"pid":os.getpid(), "state":state,
             "heartbeat_utc": heartbeat or dt.datetime.now(dt.timezone.utc).isoformat()}
    p=root/"status.tmp"
    p.write_text(json.dumps(value))
    p.replace(root/"status.json")
print("raw fake benchmark output", flush=True)
''' + body)

    def run_supervisor(self, **values):
        return guardian.supervise(self.root, self.runner, "all", poll_seconds=.02,
                                  terminate_grace=.05, **values)

    def watchdog(self):
        return json.loads((self.root / "watchdog.json").read_text())

    def test_success_requires_completed_state_and_keeps_raw_log(self):
        self.fake('status("MEASUREMENT_STAGES_FINISHED")\n')
        self.assertEqual(self.run_supervisor(), 0)
        record = self.watchdog()
        self.assertEqual(record["state"], guardian.COMPLETED)
        self.assertEqual(record["qualification"], "NOT_A_PASS")
        self.assertEqual(record["child_returncode"], 0)
        self.assertEqual(record["supervisor_pid"], os.getpid())
        self.assertEqual(record["child_pid"], record["child_process_group"])
        self.assertEqual(len(record["runner_sha256"]), 64)
        self.assertIn("raw fake benchmark output", Path(record["child_log"]).read_text())

    def test_clean_exit_without_completed_status_is_failure(self):
        self.fake('status("RUNNING")\n')
        self.assertEqual(self.run_supervisor(), 1)
        self.assertEqual(self.watchdog()["state"], "NEEDS_ATTENTION")

    def test_nonzero_exit_does_not_retry_or_overwrite_raw(self):
        self.fake('status("NEEDS_ATTENTION")\nsys.exit(7)\n')
        self.assertEqual(self.run_supervisor(), 1)
        self.assertEqual(self.watchdog()["child_returncode"], 7)
        self.assertFalse(self.watchdog()["automatic_retry"])
        self.assertEqual(len(list(self.root.glob("guardian-child-*.log"))), 1)

    def test_stale_child_is_killed_even_if_it_ignores_term(self):
        self.fake('signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
                  'status("CALIBRATING", "2000-01-01T00:00:00+00:00")\n'
                  'while True: time.sleep(1)\n')
        self.assertEqual(self.run_supervisor(), 1)
        record = self.watchdog()
        self.assertEqual(record["stop_reason"], "HEARTBEAT_STALE")
        self.assertEqual(record["child_returncode"], -signal.SIGKILL)
        self.assertIn("SIGKILL", record["termination_actions"])

    def test_missing_status_times_out_without_retry(self):
        self.fake('while True: time.sleep(1)\n')
        self.assertEqual(self.run_supervisor(heartbeat_timeout=.12), 1)
        self.assertEqual(self.watchdog()["stop_reason"], "STATUS_UNAVAILABLE")

    def test_parent_sigterm_stops_child_group(self):
        self.fake('status("CALIBRATING")\nwhile True: time.sleep(1)\n')
        parent = subprocess.Popen([sys.executable, str(Path(guardian.__file__)),
                                   "--root", str(self.root), "--runner", str(self.runner),
                                   "--stage", "bridge"], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: parent.kill() if parent.poll() is None else None)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if (self.root / "status.json").exists():
                break
            time.sleep(.02)
        self.assertTrue((self.root / "status.json").exists())
        parent.terminate()
        stdout, stderr = parent.communicate(timeout=5)
        self.assertEqual(parent.returncode, 143, stdout + stderr)
        record = self.watchdog()
        self.assertEqual(record["state"], "STOPPED")
        with self.assertRaises(ProcessLookupError):
            os.killpg(record["child_process_group"], 0)


if __name__ == "__main__":
    unittest.main()
