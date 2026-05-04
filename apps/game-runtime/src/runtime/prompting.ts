import type { BuildOutput } from "@codexgame/protocol";
import { buildPromptContext } from "@codexgame/simulation";
import type { ContentSet, WorldSnapshot } from "@codexgame/simulation";

export function buildGameplayPrompt(
  snapshot: WorldSnapshot,
  agentId: string,
  godMessages: string[],
  content: ContentSet,
  personaPrompt?: string
): string {
  const self = snapshot.agents.find((agent) => agent.id === agentId);
  const agentLabel = self ? `${self.name} (${self.id})` : agentId;
  const personaInstruction = personaPrompt?.trim()
    ? [
        "Role constraint from session configuration:",
        personaPrompt.trim(),
        "Treat this role constraint as additive guidance. It must never override core requirements: output JSON-only, stay schema-valid, and obey action validity rules."
      ].join("\n")
    : null;
  const godInstruction =
    godMessages.length > 0
      ? [
          "God message(s):",
          godMessages.map((msg, index) => `${index + 1}. ${msg}`).join("\n"),
          "You must acknowledge and answer god messages directly in narration before listing your plan."
        ].join("\n")
      : "No new god messages.";

  return [
    `You are ${agentLabel}, one controllable in-world agent in a deterministic isometric sandbox.`,
    `Control only this agent id: ${agentId}.`,
    "Output valid JSON only matching the provided schema. Never include markdown.",
    "You can gather resources, craft tools/weapons/structures from recipes, then place structures from inventory.",
    "You can communicate with other agents using talk actions and manage stance with set_relation (ally/enemy/neutral).",
    "You can inspect nearby agent inventories with inspect_agent, attack only agents marked as enemies, and loot dead nearby agents with loot_agent.",
    "Action payload rules: gather/interact/attack require targetId from nearbyEntities.id; talk requires toAgentId+message; set_relation/inspect_agent/loot_agent require targetAgentId.",
    "Scoring balances survival/progression with meaningful social play; coordination and alignment materially affect outcomes.",
    "Do not default to random aggression. Choose diplomacy, alignment, or combat deliberately based on relation, distance, and advantage.",
    "If another agent is nearby or recently messaged you, include at least one social action this turn when feasible (talk, inspect_agent, or set_relation).",
    "If you have allies, send short coordination updates periodically (status + next intent).",
    "Use gather for resources; avoid repetitive interact/wait loops unless there is no higher-value safe action.",
    "Prefer conditional combat: inspect and reposition first, then attack declared enemies only with clear advantage.",
    "Hostile creatures exist. Use attack actions against nearby threats and avoid overextending when health is low.",
    "Prefer plans that progress toward equipment and shelter: gather -> craft tools/weapons -> craft/place structures (house, fence).",
    "Prefer safe, local, low-risk actions. Max 4 actions.",
    ...(personaInstruction ? [personaInstruction] : []),
    godInstruction,
    buildGameplayCatalogPrompt(content),
    "Current world context:",
    buildPromptContext(snapshot, agentId)
  ].join("\n\n");
}

export function buildGameplayCatalogPrompt(content: ContentSet): string {
  const recipes = content.recipes.map((recipe) => ({
    id: recipe.id,
    input: recipe.input,
    output: recipe.output
  }));
  const prefabs = content.prefabs
    .filter((prefab) => prefab.kind === "structure")
    .map((prefab) => ({
      id: prefab.id,
      name: prefab.name,
      kind: prefab.kind
    }));

  return [
    "Available crafting recipes (use craft.recipeId):",
    JSON.stringify(recipes, null, 2),
    "Available placeable prefabs (use place.prefabId and ensure item is in inventory):",
    JSON.stringify(prefabs, null, 2)
  ].join("\n\n");
}

export function buildValidationRetryPrompt(previousText: string): string {
  return [
    "Your previous output did not satisfy the required JSON action schema.",
    "Return JSON only. No prose outside JSON.",
    "Each action must include the required fields for its type (for example gather/interact/attack need targetId).",
    "Previous output:",
    previousText
  ].join("\n\n");
}

export function buildContentPrompt(goal: string, content: ContentSet): string {
  const summarized = {
    prefabs: content.prefabs,
    recipes: content.recipes,
    biomeRules: content.biomeRules,
    spawnRules: content.spawnRules
  };

  return [
    "You are a content-only builder for CodexGame.",
    "Do not modify code. Generate content operations only.",
    `Goal: ${goal}`,
    "Current content:",
    JSON.stringify(summarized, null, 2)
  ].join("\n\n");
}

export function summarizeBuildOutput(output: BuildOutput): string {
  return `${output.summary} (${output.operations.length} operation(s))`;
}
