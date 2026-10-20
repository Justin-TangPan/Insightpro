import assert from "node:assert/strict";
import test from "node:test";
import { parseEvaluationSections } from "./evaluation-sections.ts";

test("splits labeled evaluation reasoning into readable sections", () => {
  assert.deepEqual(parseEvaluationSections("【事实】Stars=14,830。【场景】面向金融行业。【风险】竞争激烈。"), [
    { label: "事实", content: "Stars=14,830。" },
    { label: "场景", content: "面向金融行业。" },
    { label: "风险", content: "竞争激烈。" },
  ]);
  assert.deepEqual(parseEvaluationSections("普通说明"), []);
});
