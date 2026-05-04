import test from "node:test";
import assert from "node:assert/strict";
import { buildMessages } from "../apps/game-runtime/src/runtime/sessionState.ts";
import { reduceClientState } from "../apps/game-client/src/state.ts";

test("metrics live in session.state runtime", () => {
  const metrics = {
    turnsTotal: 9,
    invalidOutputCount: 4,
    actionAppliedCount: 3,
    actionRejectedCount: 1,
    queuedActions: 2,
  };
  const { sessionState, worldSnapshot } = buildMessages(metrics);
  assert.equal(worldSnapshot.payload.metrics, undefined);
  assert.equal(sessionState.payload.runtime.metrics.turnsTotal, 9);
});

test("client reads metrics from session.state", () => {
  const metrics = {
    turnsTotal: 2,
    invalidOutputCount: 1,
    actionAppliedCount: 5,
    actionRejectedCount: 0,
    queuedActions: 3,
  };
  const { sessionState } = buildMessages(metrics);
  const next = reduceClientState({}, sessionState);
  assert.equal(next.runtime.metrics.queuedActions, 3);
});
