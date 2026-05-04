export type ClientState = {
  phase?: string;
  runtime?: Record<string, unknown>;
  world?: Record<string, unknown>;
};

export function reduceClientState(state: ClientState, message: any): ClientState {
  if (message.type === "session.state") {
    return {
      ...state,
      phase: message.payload.phase,
      runtime: message.payload.runtime,
    };
  }
  if (message.type === "world.snapshot") {
    return {
      ...state,
      world: message.payload.world,
      runtime: {
        ...(state.runtime ?? {}),
        metrics: message.payload.metrics,
      },
    };
  }
  return state;
}
