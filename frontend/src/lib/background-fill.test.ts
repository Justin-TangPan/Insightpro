import assert from "node:assert/strict";
import test from "node:test";
import { hasReadableGithubSource } from "./background-fill.ts";

test("only labels safe GitHub repository links as readable", () => {
  assert.equal(hasReadableGithubSource("https://github.com/NousResearch/hermes-agent"), true);
  assert.equal(hasReadableGithubSource("https://github.com/NousResearch/hermes-agent.git"), true);
  assert.equal(hasReadableGithubSource("http://github.com/NousResearch/hermes-agent"), false);
  assert.equal(hasReadableGithubSource("https://github.com.evil.test/NousResearch/hermes-agent"), false);
  assert.equal(hasReadableGithubSource("https://github.com/NousResearch/hermes-agent/tree/main"), false);
});
