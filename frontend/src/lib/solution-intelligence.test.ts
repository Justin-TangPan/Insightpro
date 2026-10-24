import assert from "node:assert/strict";
import test from "node:test";
import { abilities, categoryNoise, cleanCategory, dateInPeriod, scenario } from "./solution-intelligence.ts";

const item = { id: 1, title: "GPU 服务器部署 DeepSeek-R1", url: "https://example.com", category: "AI / Solution Practice", vendor: "Alibaba Cloud", source_description: "基于 GPU 与 vLLM 推理框架部署大模型", summary: "", change_summary: "Solution content updated", first_seen_date: "2026-10-01", last_seen_date: "2026-10-24", last_changed_date: "2026-10-24", is_baseline: false };
test("normalizes source type out of scene and derives evidenced capabilities", () => {
  assert.equal(cleanCategory("安全与合规 / Solution Practice"), "安全与合规");
  assert.equal(scenario(item), "大模型部署");
  assert.deepEqual(abilities(item), ["LLM", "GPU 推理"]);
});
test("suppresses bilingual category-only noise and respects Shanghai period boundaries", () => {
  assert.ok(categoryNoise("Category: 安全与合规 / 解决方案实践 → 安全与合规 / Solution Practice"));
  assert.equal(dateInPeriod("2026-10-19", "week", new Date("2026-10-24T04:00:00Z")), true);
  assert.equal(dateInPeriod("2026-10-18", "week", new Date("2026-10-24T04:00:00Z")), false);
});
