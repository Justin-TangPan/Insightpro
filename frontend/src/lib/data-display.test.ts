import assert from "node:assert/strict";
import test from "node:test";
import { metricLabel } from "./data-display.ts";

test("metrics distinguish loading, unavailable, and a real empty result", () => {
  assert.equal(metricLabel(0, true, false, false, "暂无"), "加载中");
  assert.equal(metricLabel(0, false, true, false, "暂无"), "暂不可用");
  assert.equal(metricLabel(0, false, false, false, "暂无"), "暂无");
  assert.equal(metricLabel(8, false, false, true, "None"), "8");
});
