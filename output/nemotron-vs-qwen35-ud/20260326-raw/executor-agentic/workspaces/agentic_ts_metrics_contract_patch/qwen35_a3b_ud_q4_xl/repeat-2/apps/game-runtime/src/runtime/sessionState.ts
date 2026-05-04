import type { SessionStateMessage, WorldSnapshotMessage } from "@codexgame/protocol";
import type { RuntimeMetrics } from "./metrics";

export function buildMessages(metrics: RuntimeMetrics): {
  sessionState: SessionStateMessage;
  worldSnapshot: WorldSnapshotMessage;
} {
  return {
    sessionState: {
      type: "session.state",
      payload: {
        phase: "running",
        runtime: {
          model: "local-qwen",
          tickMs: 200,
          metrics,
        },
      },
    },
    worldSnapshot: {
      type: "world.snapshot",
      payload: {
        tick: 42,
        world: {},
      },
    } as unknown as WorldSnapshotMessage,
  };
}