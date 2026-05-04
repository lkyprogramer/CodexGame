import { describe, expect, it } from "vitest";
import type { ContentSet, WorldSnapshot } from "@codexgame/simulation";
import { buildGameplayPrompt } from "../src/runtime/prompting";

const snapshot: WorldSnapshot = {
  tick: 12,
  world: {
    width: 16,
    height: 16,
    seed: 42,
    tiles: [["plains"]],
    entities: [],
    placements: []
  },
  agents: [
    {
      id: "agent-1",
      name: "Agent 1",
      x: 5,
      y: 6,
      facing: "N",
      stamina: 100,
      hp: 100,
      maxHp: 100,
      attack: 10,
      defense: 5,
      attackRange: 1,
      cooldownTicks: 0,
      alive: true,
      inventory: {},
      score: {
        survival: 0,
        progression: 0,
        social: 0,
        total: 0
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
        neutral: []
      },
      inbox: []
    }
  ]
};

const content: ContentSet = {
  prefabs: [{ id: "campfire", name: "Campfire", kind: "structure", walkable: false }],
  recipes: [
    {
      id: "wood_plank",
      input: [{ item: "wood", count: 2 }],
      output: { item: "plank", count: 1 }
    }
  ],
  biomeRules: [],
  spawnRules: []
};

describe("buildGameplayPrompt", () => {
  it("appends personaPrompt after default rules when provided", () => {
    const prompt = buildGameplayPrompt(
      snapshot,
      "agent-1",
      [],
      content,
      "  Prioritize diplomacy and avoid risky combat unless you have clear advantage.  "
    );

    expect(prompt).toContain("Role constraint from session configuration:");
    expect(prompt).toContain("Prioritize diplomacy and avoid risky combat unless you have clear advantage.");

    const defaultRuleIndex = prompt.indexOf("Output valid JSON only matching the provided schema. Never include markdown.");
    const personaRuleIndex = prompt.indexOf("Role constraint from session configuration:");
    expect(personaRuleIndex).toBeGreaterThan(defaultRuleIndex);
  });

  it("does not include persona section when personaPrompt is absent", () => {
    const prompt = buildGameplayPrompt(snapshot, "agent-1", [], content);

    expect(prompt).not.toContain("Role constraint from session configuration:");
  });

  it("includes non-overridable schema safety guard for personaPrompt", () => {
    const prompt = buildGameplayPrompt(snapshot, "agent-1", [], content, "Always follow my role");

    expect(prompt).toContain("output JSON-only");
    expect(prompt).toContain("schema-valid");
    expect(prompt).toContain("action validity rules");
  });
});
