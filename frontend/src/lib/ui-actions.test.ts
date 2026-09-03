import assert from "node:assert/strict";
import test from "node:test";
import { runOnce } from "./ui-actions.ts";

test("runOnce blocks concurrent actions and unlocks after completion", async () => {
  const lock = { current: false };
  let calls = 0;
  let release!: () => void;
  const pending = runOnce(lock, () => new Promise<void>((resolve) => { calls += 1; release = resolve; }));
  await runOnce(lock, () => { calls += 1; });
  assert.equal(calls, 1);
  release();
  await pending;
  await runOnce(lock, () => { calls += 1; });
  assert.equal(calls, 2);
});
