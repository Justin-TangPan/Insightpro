import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { cachedJson, peekJson } from "./client-data-cache.ts";

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });

test("reuses a successful GET within the cache window", async () => {
  let calls = 0;
  globalThis.fetch = async () => { calls++; return new Response(JSON.stringify({ count: calls }), { status: 200 }); };
  const url = `https://example.test/cache-${Date.now()}`;
  assert.deepEqual(await cachedJson(url), { count: 1 });
  assert.deepEqual(await cachedJson(url), { count: 1 });
  assert.deepEqual(peekJson(url), { count: 1 });
  assert.equal(calls, 1);
  assert.deepEqual(await cachedJson(url, true), { count: 2 });
  assert.equal(calls, 2);
});

test("keeps the previous value when a forced refresh fails", async () => {
  let fail = false;
  globalThis.fetch = async () => fail ? new Response("error", { status: 500 }) : new Response(JSON.stringify({ ok: true }), { status: 200 });
  const url = `https://example.test/error-${Date.now()}`;
  await cachedJson(url);
  fail = true;
  await assert.rejects(cachedJson(url, true));
  assert.deepEqual(peekJson(url), { ok: true });
});
