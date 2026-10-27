import assert from "node:assert/strict";
import test from "node:test";
import { focusType, selectRecentFocus, type FocusEvent } from "./home-focus.ts";

const event = (patch: Partial<FocusEvent>): FocusEvent => ({
  id: "1", vendor: "OpenAI", happened_at: "2026-10-25", date_basis: "published", type: "AI 应用", board: "apps",
  title: "OpenAI launches a new coding app", summary: "A new AI product is now available.", why: "", importance: 5,
  sources: [{ name: "Official", url: "https://example.com" }], ...patch,
});

test("focus labels favor launches and filter routine coverage", () => {
  assert.equal(focusType(event({ title: "Google introduces a new Agent", summary: "Agent launch", board: "competitors" })), "新 Agent");
  assert.equal(focusType(event({ title: "OpenAI launches a new coding app" })), "新应用");
  assert.equal(focusType(event({ title: "Qwen model v4 released", type: "模型", board: "competitors" })), "新模型");
  assert.equal(focusType(event({ title: "DeepSeek-V4.1-Flash-1017 全新模型发布", board: "community", date_basis: "observed" })), "新模型");
  assert.equal(focusType(event({ title: "KimiK3.1 发布", board: "competitors" })), "新模型");
  assert.equal(focusType(event({ title: "Kimi Code · K3.1 Pro Series is live October 23, 2026", summary: "Kimi官方于2026年10月23日发布K3.1 Pro系列模型，用于Kimi Code。" })), "新模型");
  assert.equal(focusType(event({ title: "Introducing memory in Kiro IDE and CLI", summary: "A new memory feature." })), "新平台能力");
  assert.equal(focusType(event({ title: "New AI solution launched", board: "solutions" })), null);
  assert.equal(focusType(event({ title: "BrowserAgent", board: "github", type: "GitHub 技术" })), null);
  assert.equal(focusType(event({ title: "BrowserAgent open-source project launched", board: "github", type: "GitHub 技术" })), "新项目");
  assert.equal(focusType(event({ title: "Copilot release notes and changelog" })), null);
  assert.equal(focusType(event({ title: "AI Agent case study", board: "community", date_basis: "observed" })), null);
});

test("recent launches lead and older high-value events only fill the remaining slots", () => {
  const items = selectRecentFocus([
    event({ id: "old-agent", board: "competitors", title: "Announcing a new Agent", happened_at: "2026-10-05" }),
    event({ id: "app", title: "Launching a new AI desktop app", happened_at: "2026-10-25" }),
    event({ id: "model", board: "competitors", type: "模型", title: "New model released", happened_at: "2026-10-19" }),
    event({ id: "old-app", title: "New AI product launched", board: "competitors", happened_at: "2026-10-18" }),
    event({ id: "today-model", board: "competitors", type: "模型", title: "New GPT-6 model released", happened_at: "2026-10-25" }),
    event({ id: "community", board: "community", date_basis: "observed", title: "New Agent discussion" }),
    event({ id: "future", title: "Launching a new AI app", happened_at: "2026-10-26" }),
  ], "2026-10-25T12:00:00+08:00", 5);
  assert.deepEqual(items.map(item => item.event.id), ["app", "today-model", "model", "old-app", "old-agent"]);
  assert.deepEqual(items.map(item => item.type), ["新应用", "新模型", "新模型", "新产品", "新 Agent"]);
});

test("newer model announcements outrank older ones regardless of type priority", () => {
  const items = selectRecentFocus([
    event({ id: "deepseek", board: "community", title: "DeepSeek 全新模型发布", summary: "本次版本为 DeepSeek-V4.1-Flash-1017。", date_basis: "observed", happened_at: "2026-10-25" }),
    event({ id: "kimi", board: "competitors", title: "KimiK3.1 发布", happened_at: "2026-10-23" }),
    event({ id: "agent", board: "competitors", title: "Google introduces a new Agent", happened_at: "2026-10-23" }),
  ], "2026-10-25T12:00:00+08:00", 3);
  assert.deepEqual(items.map(item => item.event.id), ["agent", "kimi", "deepseek"]);
  assert.deepEqual(items.map(item => item.date), ["2026-10-23", "2026-10-23", "2026-10-17"]);
  assert.equal(items[2].dateBasis, "version");
});

test("dated headlines use their stated date instead of a later ingestion date", () => {
  const items = selectRecentFocus([
    event({ id: "old", title: "2026-10-08 Introducing memory in Kiro IDE", happened_at: "2026-10-23" }),
    event({ id: "new", board: "competitors", title: "Google introduces a new Agent", happened_at: "2026-10-20" }),
  ], "2026-10-25", 2);
  assert.deepEqual(items.map(item => item.event.id), ["new", "old"]);
  assert.equal(items[1].date, "2026-10-08");
});

test("an old dated source anchor cannot become a recent focus when collected late", () => {
  const items = selectRecentFocus([
    event({ id: "stale", title: "扣子 · 2025年10月", summary: "新增能力", happened_at: "2026-10-24", date_basis: "observed", sources: [{ name: "官方动态", url: "https://docs.example.com/updates#update-2025-10-3" }] }),
    event({ id: "fresh", board: "competitors", title: "Google introduces a new Agent", happened_at: "2026-10-23" }),
  ], "2026-10-25", 2);
  assert.deepEqual(items.map(item => item.event.id), ["fresh"]);
});
