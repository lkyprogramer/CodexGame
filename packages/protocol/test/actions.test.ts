import { describe, expect, it } from "vitest";
import { agentTurnOutputJsonSchema, agentTurnOutputSchema } from "../src/actions";

describe("agentTurnOutputSchema", () => {
  it("accepts valid actions", () => {
    const parsed = agentTurnOutputSchema.parse({
      narration: "Moving and waiting.",
      actions: [
        { type: "move", direction: "NE", steps: 2 },
        { type: "attack", targetId: "npc-1" },
        { type: "wait", ticks: 2 },
        { type: "inspect_agent", targetAgentId: "agent-2" }
      ]
    });
    expect(parsed.actions).toHaveLength(4);
  });

  it("rejects invalid direction", () => {
    expect(() =>
      agentTurnOutputSchema.parse({
        narration: "bad",
        actions: [{ type: "move", direction: "NORTH", steps: 1 }]
      })
    ).toThrow();
  });

  it("rejects invalid relation", () => {
    expect(() =>
      agentTurnOutputSchema.parse({
        narration: "bad",
        actions: [{ type: "set_relation", targetAgentId: "agent-2", relation: "friend" }]
      })
    ).toThrow();
  });

  it("uses per-action required fields in JSON schema", () => {
    const itemSchema = agentTurnOutputJsonSchema.properties.actions.items as {
      required: ReadonlyArray<string>;
      properties: {
        type?: { enum?: ReadonlyArray<string> };
        direction?: { enum?: ReadonlyArray<string | null> };
        targetId?: { type?: ReadonlyArray<string> };
      };
    };

    expect(itemSchema.required).toContain("type");
    expect(itemSchema.required).toContain("direction");
    expect(itemSchema.required).toContain("targetId");
    expect(itemSchema.properties.type?.enum).toContain("gather");
    expect(itemSchema.properties.direction?.enum).toContain(null);
    expect(itemSchema.properties.targetId?.type).toEqual(["string", "null"]);
  });
});
