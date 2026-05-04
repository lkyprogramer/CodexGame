export type RuntimePhase = "idle" | "restoring" | "running";

export type RuntimeState = {
  phase: RuntimePhase;
  threadIds: Record<string, string>;
};
