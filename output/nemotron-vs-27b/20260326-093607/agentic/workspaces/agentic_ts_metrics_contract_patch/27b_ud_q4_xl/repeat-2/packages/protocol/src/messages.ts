export type RuntimeMetrics = {
  turnsTotal: number;
  invalidOutputCount: number;
  actionAppliedCount: number;
  actionRejectedCount: number;
  queuedActions: number;
};

export type RuntimeState = {
  model: string | null;
  tickMs: number;
  metrics: RuntimeMetrics;
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