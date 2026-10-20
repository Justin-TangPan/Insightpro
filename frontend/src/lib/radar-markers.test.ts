import assert from "node:assert/strict";
import test from "node:test";
import { radarMarkerPositions } from "./radar-markers.ts";

test("radar markers stay on their category spoke and separate repeated signals", () => {
  const positions = radarMarkerPositions(
    [{ category: "AI 应用" }, { category: "AI 应用" }, { category: "Agent" }, { category: "未知" }],
    ["AI 应用", "Agent", "模型与技术", "AI Infra", "商业化与产业"],
  );
  assert.ok(positions[0] && positions[0].y < 0);
  assert.ok(positions[1] && positions[1].y < 0);
  assert.notDeepEqual(positions[0], positions[1]);
  assert.ok(positions[2] && positions[2].x > 0);
  assert.equal(positions[3], null);
});
