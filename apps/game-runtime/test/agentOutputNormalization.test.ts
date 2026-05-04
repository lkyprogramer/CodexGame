import { describe, expect, it } from "vitest";
import { agentTurnOutputSchema } from "@codexgame/protocol";
import type { WorldSnapshot } from "@codexgame/simulation";
import { normalizeAgentTurnOutput } from "../src/runtime/agentOutput";

function createSnapshot(withNorthResource: boolean): WorldSnapshot {
  return {
    tick: 10,
    world: {
      width: 12,
      height: 12,
      seed: 7,
      tiles: Array.from({ length: 12 }, () => Array.from({ length: 12 }, () => "plains")),
      entities: withNorthResource
        ? [
            {
              id: "res-north",
              type: "resource",
              subtype: "wood",
              x: 5,
              y: 4,
              quantity: 2
            }
          ]
        : [],
      placements: []
    },
    agents: [
      {
        id: "agent-1",
        name: "Agent 1",
        x: 5,
        y: 5,
        facing: "N",
        stamina: 100,
        hp: 40,
        maxHp: 40,
        attack: 5,
        defense: 3,
        attackRange: 1,
        cooldownTicks: 0,
        alive: true,
        inventory: {},
        score: {
          survival: 60,
          progression: 0,
          social: 0,
          total: 30
        },
        scoreTrack: {
          creatureKills: 0,
          enemyAgentKills: 0,
          successfulLoots: 0,
          crafts: 0,
          structuresPlaced: 0,
          cooperativeTalks: 0,
          tacticalInspects: 0,
          idleStreak: 0
        },
        knownPeerInventories: {},
        nearbyEntities: [],
        relations: {
          allies: [],
          enemies: [],
          neutral: ["agent-2"]
        },
        inbox: []
      },
      {
        id: "agent-2",
        name: "Agent 2",
        x: 6,
        y: 5,
        facing: "W",
        stamina: 100,
        hp: 40,
        maxHp: 40,
        attack: 5,
        defense: 3,
        attackRange: 1,
        cooldownTicks: 0,
        alive: true,
        inventory: {},
        score: {
          survival: 60,
          progression: 0,
          social: 0,
          total: 30
        },
        scoreTrack: {
          creatureKills: 0,
          enemyAgentKills: 0,
          successfulLoots: 0,
          crafts: 0,
          structuresPlaced: 0,
          cooperativeTalks: 0,
          tacticalInspects: 0,
          idleStreak: 0
        },
        knownPeerInventories: {},
        nearbyEntities: [],
        relations: {
          allies: [],
          enemies: [],
          neutral: ["agent-1"]
        },
        inbox: []
      }
    ]
  };
}

describe("normalizeAgentTurnOutput", () => {
  it("converts nullable expanded action payload into strict action payload", () => {
    const snapshot = createSnapshot(true);
    const raw = {
      narration: "Collect resource then coordinate.",
      actions: [
        {
          type: "gather",
          direction: "N",
          steps: null,
          targetId: null,
          recipeId: null,
          prefabId: null,
          x: null,
          y: null,
          ticks: null,
          toAgentId: null,
          message: null,
          targetAgentId: null,
          relation: null
        },
        {
          type: "talk",
          direction: null,
          steps: null,
          targetId: null,
          recipeId: null,
          prefabId: null,
          x: null,
          y: null,
          ticks: null,
          toAgentId: "agent-2",
          message: "Collecting wood north tile first.",
          targetAgentId: null,
          relation: null
        }
      ]
    };

    const normalized = normalizeAgentTurnOutput(raw, snapshot, "agent-1");
    const parsed = agentTurnOutputSchema.parse(normalized);

    expect(parsed.actions[0]).toEqual({ type: "gather", targetId: "res-north" });
    expect(parsed.actions[1]).toEqual({
      type: "talk",
      toAgentId: "agent-2",
      message: "Collecting wood north tile first."
    });
  });

  it("falls back to wait when no action can be normalized", () => {
    const snapshot = createSnapshot(false);
    const raw = {
      narration: "Do something.",
      actions: [
        {
          type: "gather",
          direction: null,
          steps: null,
          targetId: null,
          recipeId: null,
          prefabId: null,
          x: null,
          y: null,
          ticks: null,
          toAgentId: null,
          message: null,
          targetAgentId: null,
          relation: null
        }
      ]
    };

    const normalized = normalizeAgentTurnOutput(raw, snapshot, "agent-1");
    const parsed = agentTurnOutputSchema.parse(normalized);

    expect(parsed.actions).toEqual([{ type: "wait", ticks: 1 }]);
  });
});
