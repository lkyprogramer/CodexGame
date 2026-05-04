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
