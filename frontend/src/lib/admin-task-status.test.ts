import assert from "node:assert/strict";
import test from "node:test";
import { taskStatus } from "./admin-task-status.ts";

test("task status uses the last recorded run and keeps unknown states pending", () => {
  assert.equal(taskStatus({ last_run: { status: "success" } }), "success");
  assert.equal(taskStatus({ last_run: { status: "running" } }), "running");
  assert.equal(taskStatus({ last_run: { status: "failed" } }), "error");
  assert.equal(taskStatus({ last_run: null }), "waiting");
  assert.equal(taskStatus({ last_run: { status: "skipped" } }), "waiting");
});
