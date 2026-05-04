import type { AgentAction, Direction } from "@codexgame/protocol";
import type { WorldSnapshot } from "@codexgame/simulation";

const directionVector: Record<Direction, { dx: number; dy: number }> = {
  N: { dx: 0, dy: -1 },
  NE: { dx: 1, dy: -1 },
  E: { dx: 1, dy: 0 },
  SE: { dx: 1, dy: 1 },
  S: { dx: 0, dy: 1 },
  SW: { dx: -1, dy: 1 },
  W: { dx: -1, dy: 0 },
  NW: { dx: -1, dy: -1 }
};

type ActionType = AgentAction["type"];

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function asNonEmptyString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function asInteger(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.trunc(value);
  }
  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return Math.trunc(parsed);
    }
  }
  return null;
}

function asDirection(value: unknown): Direction | null {
  if (value === "N" || value === "NE" || value === "E" || value === "SE" || value === "S" || value === "SW" || value === "W" || value === "NW") {
    return value;
  }
  return null;
}

function asRelation(value: unknown): "ally" | "enemy" | "neutral" | null {
  if (value === "ally" || value === "enemy" || value === "neutral") {
    return value;
  }
  return null;
}

function manhattanDistance(ax: number, ay: number, bx: number, by: number): number {
  return Math.abs(ax - bx) + Math.abs(ay - by);
}

function inferDirectionalTargetId(
  snapshot: WorldSnapshot,
  agentId: string,
  actionType: "interact" | "gather" | "attack",
  direction: Direction
): string | null {
  const self = snapshot.agents.find((agent) => agent.id === agentId);
  if (!self) {
    return null;
  }
  const vector = directionVector[direction];
  const targetX = self.x + vector.dx;
  const targetY = self.y + vector.dy;

  if (actionType === "gather") {
    const resource = snapshot.world.entities.find(
      (entity) => entity.type === "resource" && entity.x === targetX && entity.y === targetY
    );
    return resource?.id ?? null;
  }

  if (actionType === "interact") {
    const resource = snapshot.world.entities.find(
      (entity) => entity.type !== "creature" && entity.x === targetX && entity.y === targetY
    );
    return resource?.id ?? null;
  }

  const creature = snapshot.world.entities.find(
    (entity) => entity.type === "creature" && entity.x === targetX && entity.y === targetY
  );
  if (creature) {
    return creature.id;
  }
  const agent = snapshot.agents.find((item) => item.id !== agentId && item.alive && item.x === targetX && item.y === targetY);
  return agent?.id ?? null;
}

function inferAdjacentTargetId(
  snapshot: WorldSnapshot,
  agentId: string,
  actionType: "interact" | "gather" | "attack"
): string | null {
  const self = snapshot.agents.find((agent) => agent.id === agentId);
  if (!self) {
    return null;
  }

  if (actionType === "attack") {
    const creature = snapshot.world.entities
      .filter((entity) => entity.type === "creature")
      .map((entity) => ({ id: entity.id, distance: manhattanDistance(self.x, self.y, entity.x, entity.y) }))
      .filter((item) => item.distance <= 1)
      .sort((a, b) => a.distance - b.distance || a.id.localeCompare(b.id))[0];
    if (creature) {
      return creature.id;
    }

    const enemyAgent = snapshot.agents
      .filter((item) => item.id !== agentId && item.alive)
      .map((item) => ({ id: item.id, distance: manhattanDistance(self.x, self.y, item.x, item.y) }))
      .filter((item) => item.distance <= 1)
      .sort((a, b) => a.distance - b.distance || a.id.localeCompare(b.id))[0];
    return enemyAgent?.id ?? null;
  }

  const candidates = snapshot.world.entities
    .filter((entity) => (actionType === "gather" ? entity.type === "resource" : entity.type !== "creature"))
    .map((entity) => ({ id: entity.id, distance: manhattanDistance(self.x, self.y, entity.x, entity.y) }))
    .filter((item) => item.distance <= 1)
    .sort((a, b) => a.distance - b.distance || a.id.localeCompare(b.id));

  return candidates[0]?.id ?? null;
}

function normalizeTargetAction(
  action: Record<string, unknown>,
  snapshot: WorldSnapshot,
  agentId: string,
  actionType: "interact" | "gather" | "attack"
): AgentAction | null {
  const explicitTarget =
    asNonEmptyString(action.targetId) ??
    (actionType === "attack" ? asNonEmptyString(action.targetAgentId) : null) ??
    null;

  const directionalTarget = explicitTarget
    ? null
    : (() => {
        const direction = asDirection(action.direction);
        if (!direction) {
          return null;
        }
        return inferDirectionalTargetId(snapshot, agentId, actionType, direction);
      })();

  const fallbackTarget = explicitTarget || directionalTarget || inferAdjacentTargetId(snapshot, agentId, actionType);

  if (!fallbackTarget) {
    return null;
  }

  if (actionType === "interact") {
    return { type: "interact", targetId: fallbackTarget };
  }
  if (actionType === "gather") {
    return { type: "gather", targetId: fallbackTarget };
  }
  return { type: "attack", targetId: fallbackTarget };
}

function normalizeAction(action: Record<string, unknown>, snapshot: WorldSnapshot, agentId: string): AgentAction | null {
  const type = asNonEmptyString(action.type) as ActionType | null;
  if (!type) {
    return null;
  }

  switch (type) {
    case "move": {
      const direction = asDirection(action.direction);
      if (!direction) {
        return null;
      }
      const stepsRaw = asInteger(action.steps);
      const steps = stepsRaw === 2 || stepsRaw === 3 ? stepsRaw : 1;
      return { type: "move", direction, steps };
    }
    case "interact":
      return normalizeTargetAction(action, snapshot, agentId, "interact");
    case "gather":
      return normalizeTargetAction(action, snapshot, agentId, "gather");
    case "attack":
      return normalizeTargetAction(action, snapshot, agentId, "attack");
    case "craft": {
      const recipeId = asNonEmptyString(action.recipeId);
      if (!recipeId) {
        return null;
      }
      return { type: "craft", recipeId };
    }
    case "place": {
      const prefabId = asNonEmptyString(action.prefabId);
      const x = asInteger(action.x);
      const y = asInteger(action.y);
      if (!prefabId || x === null || y === null) {
        return null;
      }
      return { type: "place", prefabId, x, y };
    }
    case "wait": {
      const ticksRaw = asInteger(action.ticks);
      const ticks = Math.max(1, Math.min(20, ticksRaw ?? 1));
      return { type: "wait", ticks };
    }
    case "talk": {
      const toAgentId = asNonEmptyString(action.toAgentId) ?? asNonEmptyString(action.targetAgentId);
      const message = asNonEmptyString(action.message);
      if (!toAgentId || !message) {
        return null;
      }
      return { type: "talk", toAgentId, message: message.slice(0, 240) };
    }
    case "set_relation": {
      const targetAgentId = asNonEmptyString(action.targetAgentId) ?? asNonEmptyString(action.toAgentId);
      const relation = asRelation(action.relation);
      if (!targetAgentId || !relation) {
        return null;
      }
      return { type: "set_relation", targetAgentId, relation };
    }
    case "inspect_agent": {
      const targetAgentId = asNonEmptyString(action.targetAgentId) ?? asNonEmptyString(action.toAgentId);
      if (!targetAgentId) {
        return null;
      }
      return { type: "inspect_agent", targetAgentId };
    }
    case "loot_agent": {
      const targetAgentId = asNonEmptyString(action.targetAgentId) ?? asNonEmptyString(action.toAgentId);
      if (!targetAgentId) {
        return null;
      }
      return { type: "loot_agent", targetAgentId };
    }
    default:
      return null;
  }
}

export function normalizeAgentTurnOutput(raw: unknown, snapshot: WorldSnapshot, agentId: string): unknown {
  const value = asRecord(raw) ?? {};
  const narration = asNonEmptyString(value.narration) ?? "Continuing with the best available move.";
  const rawActions = Array.isArray(value.actions) ? value.actions : [];

  const actions: AgentAction[] = [];
  for (const rawAction of rawActions) {
    const normalized = asRecord(rawAction) ? normalizeAction(rawAction as Record<string, unknown>, snapshot, agentId) : null;
    if (!normalized) {
      continue;
    }
    actions.push(normalized);
    if (actions.length >= 4) {
      break;
    }
  }

  if (actions.length === 0) {
    actions.push({ type: "wait", ticks: 1 });
  }

  return {
    narration,
    actions
  };
}
