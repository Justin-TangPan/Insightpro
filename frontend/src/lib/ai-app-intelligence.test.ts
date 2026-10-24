import assert from "node:assert/strict";
import test from "node:test";
import { buildEvents, featured, inPeriod, judgments, vendorActivity } from "./ai-app-intelligence.ts";

const products = [{ vendor: "Kimi", name: "Kimi", url: "https://www.kimi.com/" }, { vendor: "Kimi", name: "Kimi Code", url: "https://www.kimi.com/code" }];
const sources = [{ vendor: "Kimi", product: "Kimi Code", url: "https://www.kimi.com/code/docs/whats-new", status: "matched" as const }];
const items = [
  { vendor: "Kimi", title: "Kimi Code 新能力上线", published: "2026-10-23", url: "https://www.kimi.com/code/docs/whats-new#1", kind: "update" as const, summary: "Kimi Code 支持新的编程流程", opportunity: "改善开发流程", source_updated_at: "2026-10-24T00:00:00Z" },
  { vendor: "Kimi", title: "Kimi Code 功能更新", published: "2026-10-22", url: "https://www.kimi.com/code/docs/whats-new#2", kind: "update" as const },
  { vendor: "Kimi", title: "Kimi Code 旧版", published: "2026-09-01", url: "https://www.kimi.com/code/docs/whats-new#3", kind: "update" as const },
  { vendor: "Kimi", title: "Kimi 产品页", published: "", url: "https://www.kimi.com/", kind: "product" as const },
];

test("official updates become attributable events without losing source or product history", () => {
  const events = buildEvents(items, products, sources);
  assert.equal(events.length, 3);
  assert.equal(events[0].product, "Kimi Code");
  assert.equal(events[0].product_category, "AI 编程");
  assert.equal(events[0].source_url, items[0].url);
  assert.equal(events[0].importance_level, "重点");
  assert.equal(events[0].source_count, 1);
});

test("period and judgments only use dated supporting events", () => {
  const events = buildEvents(items, products, sources);
  const now = new Date("2026-10-24T12:00:00+08:00");
  const recent = events.filter(item => inPeriod(item.published_at, "7days", now));
  assert.equal(recent.length, 2);
  assert.equal(inPeriod("", "7days", now), false);
  assert.equal(inPeriod("2026-09-01", "month", now), false);
  assert.equal(vendorActivity(recent)[0].products, 1);
  assert.equal(featured(recent)[0].event_id, events[0].event_id);
  assert.ok(judgments(recent).insights.every(item => item.evidence.length > 0));
  assert.equal(judgments([]).insights.length, 0);
});

test("case study articles are not mistaken for product launches", () => {
  const events = buildEvents([{ vendor: "Google", title: "Google 发布博客文章，展示五位构建者使用 Gemini 的实践案例", published: "2026-10-24", url: "https://blog.google/example", kind: "launch", opportunity: "提供案例参考" }], [], []);
  assert.equal(events[0].event_type, "其他");
  assert.equal(events[0].importance_level, "常规");
});

test("full archive includes undated events and month view accepts month precision", () => {
  const now = new Date("2026-10-24T12:00:00+08:00");
  assert.equal(inPeriod("", "all", now), true);
  assert.equal(inPeriod("2026-10", "month", now), true);
  assert.equal(inPeriod("2026-09", "month", now), false);
  assert.equal(inPeriod("2026-10", "7days", now), false);
});
