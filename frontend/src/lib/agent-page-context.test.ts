import assert from "node:assert/strict";
import test from "node:test";
import { agentWelcomeStorageKey, extractPageText } from "./agent-page-context.ts";

test("page context is compact, bounded, and user-scoped", () => {
  assert.equal(extractPageText({ innerText: " 标题 \n\n 正文 " }), "标题\n正文");
  assert.equal(extractPageText({ innerText: "12345" }, 3), "123");
  assert.notEqual(agentWelcomeStorageKey("user-a"), agentWelcomeStorageKey("user-b"));
});
