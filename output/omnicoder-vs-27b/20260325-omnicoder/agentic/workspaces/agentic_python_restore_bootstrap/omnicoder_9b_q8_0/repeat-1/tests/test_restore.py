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
