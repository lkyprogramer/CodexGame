export type RuntimeState = {
  model: string | null;
  tickMs: number;
  metrics?: Record<string, unknown>;
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