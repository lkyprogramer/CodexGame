import type { RuntimeState } from "./types";
import { ThreadBootstrapper } from "./bootstrap";

export type Snapshot = {
  agentIds: string[];
  threadIds: Record<string, string>;
};

export function restoreRuntime(
  snapshot: Snapshot,
  state: RuntimeState,
  bootstrapper: ThreadBootstrapper,
): RuntimeState {
  state.phase = "restoring";
  state.threadIds = { ...snapshot.threadIds };
  for (const agentId of snapshot.agentIds) {
    if (!(agentId in state.threadIds)) {
      state.threadIds[agentId] = bootstrapper.ensureThread(agentId);
    }
  }
  state.phase = "running";
  return state;
}
