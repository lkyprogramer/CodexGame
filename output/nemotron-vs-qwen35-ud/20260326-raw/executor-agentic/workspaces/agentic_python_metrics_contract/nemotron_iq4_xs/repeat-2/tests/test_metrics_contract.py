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