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
