import assert from "node:assert/strict";
import test from "node:test";
import { communityItems, competitorItems, daysAgo, distribution, groupChange, keywords, parseHeat } from "./insight-dashboard.ts";

test("community adapter preserves observed date, source, evidence and disclosed heat", () => {
  const items = communityItems([{ id: 1, title: "DeepSeek Agent 发布", summary: "151 万热度 · 阅读 2.5w", first_seen_at: "2026-10-23T20:00:00Z", last_seen_at: "2026-10-24T02:00:00Z", source_names: ["知乎热榜"], source_url: "https://www.zhihu.com/question/1", categories: ["Agent 与框架"], relevance: "high" }], []);
  assert.equal(items[0].heat, 1510000);
  assert.equal(items[0].reads, 25000);
  assert.equal(items[0].date, "2026-10-24");
  assert.equal(items[0].href, "https://www.zhihu.com/question/1");
  assert.equal(items[0].topic, "Agent 与框架");
  assert.equal(items[0].priority, true);
  assert.equal(distribution(items)[0].value, 1);
  assert.equal(parseHeat("普通摘要").value, undefined);
});

test("competitor adapter uses existing categories and analysis without invented scores", () => {
  const items = competitorItems([{ id: 8, vendor: "AWS", title: "Trainium 发布 PyTorch 支持", summary: "Use: 原生支持", link: "https://aws.example/news", category: "Product Launch", date: "2026-10-20", analysis: "降低迁移门槛" }]);
  assert.equal(items[0].topic, "模型与算力");
  assert.equal(items[0].priority, true);
  assert.equal(items[0].analysis, "降低迁移门槛");
  assert.equal(items[0].summary, "原生支持");
  assert.ok(keywords([...items, ...items]).length > 0);
});

test("trend comparisons require a recorded previous period", () => {
  const now = new Date("2026-10-24T12:00:00+08:00");
  assert.equal(daysAgo("2026-10-18", 7, now), true);
  assert.equal(daysAgo("2026-10-17", 7, now), false);
  assert.equal(groupChange([{ date: "2026-10-24", count: 4 }], 7, now), null);
  assert.equal(groupChange([{ date: "2026-10-17", count: 2 }, { date: "2026-10-24", count: 4 }], 7, now), 100);
});
