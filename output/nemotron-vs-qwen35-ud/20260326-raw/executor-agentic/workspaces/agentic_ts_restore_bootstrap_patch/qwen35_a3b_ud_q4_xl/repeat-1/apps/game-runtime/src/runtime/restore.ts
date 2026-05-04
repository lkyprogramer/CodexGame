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
  state.threadIds = {};
  for (const agentId of snapshot.agentIds) {
    state.threadIds[agentId] = bootstrapper.ensureThread(agentId);
  }
  state.phase = "running";
  return state;
}
