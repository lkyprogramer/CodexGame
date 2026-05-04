import test from "node:test";
import assert from "node:assert/strict";
import { ThreadBootstrapper } from "../apps/game-runtime/src/runtime/bootstrap.ts";
import { restoreRuntime } from "../apps/game-runtime/src/runtime/restore.ts";

test("preserves existing thread ids and only creates missing ones", () => {
  const state = { phase: "idle", threadIds: { a1: "thread-a1" } };
  const bootstrapper = new ThreadBootstrapper();
  const next = restoreRuntime(
    {
      agentIds: ["a1", "a2"],
      threadIds: { a1: "thread-a1" },
    },
    state,
    bootstrapper,
  );
  assert.equal(next.phase, "running");
  assert.deepEqual(next.threadIds, { a1: "thread-a1", a2: "thread-a2" });
  assert.deepEqual(bootstrapper.created, ["thread-a2"]);
});

test("does not expose running phase before thread ids exist", () => {
  const state = { phase: "idle", threadIds: {} };
  const bootstrapper = new ThreadBootstrapper();
  const next = restoreRuntime({ agentIds: ["a1"], threadIds: {} }, state, bootstrapper);
  assert.equal(next.phase, "running");
  assert.deepEqual(next.threadIds, { a1: "thread-a1" });
});
