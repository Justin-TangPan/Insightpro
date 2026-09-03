import assert from "node:assert/strict";
import test from "node:test";
import { emitAgentRoute, subscribeAgentRoute, type AgentRoute } from "./agent-events.ts";

test("agent route events preserve typed detail and unsubscribe", () => {
  const target = new EventTarget();
  const received: AgentRoute[] = [];
  const stop = subscribeAgentRoute((detail) => received.push(detail), target);
  const route = { contextType: "solution", contextId: "7", actionKey: "architecture" } as const;
  emitAgentRoute(route, target);
  stop();
  emitAgentRoute(route, target);
  assert.deepEqual(received, [route]);
});
