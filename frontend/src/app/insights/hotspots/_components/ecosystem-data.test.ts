import assert from "node:assert/strict";
import { test } from "node:test";
import { historySeries, metric, projectCategory, sparkline } from "./ecosystem-data.ts";
import type { HistoryEntry, TrendingItem } from "./hotspot-types.ts";

const item = (name: string, growth: string): TrendingItem => ({ repo_name: name, repo_url: name, description: "", language: "", stars: "", forks: "", today_stars: growth, category: "daily" });
test("ecosystem metrics and history use observed values", () => {
  assert.equal(metric("1,234 stars today"), 1234);
  assert.equal(metric("1.2k"), 1200);
  assert.equal(projectCategory(item("secure-audit", "4")), "security");
  assert.equal(projectCategory({ ...item("OpenShell", "4"), description: "runtime for AI Agents" }), "framework");
  const history = [{ date: "2026-10-24", items: [item("secure-audit", "4")], evaluations: [] }, { date: "2026-10-23", items: [item("secure-audit", "2")], evaluations: [] }] satisfies HistoryEntry[];
  assert.deepEqual(historySeries(history, () => true), [2, 4]);
  assert.equal(sparkline([2, 4]), "0.0,30.0 100.0,4.0");
  assert.equal(sparkline([4]), "");
});
