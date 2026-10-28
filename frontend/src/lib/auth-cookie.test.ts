import assert from "node:assert/strict";
import test from "node:test";
import { createBrowserClient, createServerClient } from "@supabase/ssr";
import { authCookieOptions } from "../utils/supabase/auth-cookie.ts";

test("browser and internal Supabase URLs share one session cookie", () => {
  const cookies = { getAll: () => [], setAll: () => undefined };
  const browser = createBrowserClient("https://public.example.test/supabase", "anon", {
    cookieOptions: authCookieOptions, cookies, isSingleton: false,
  });
  const server = createServerClient("http://supabase-envoy:8000", "anon", {
    cookieOptions: authCookieOptions, cookies,
  });
  assert.equal(Reflect.get(browser.auth, "storageKey"), authCookieOptions.name);
  assert.equal(Reflect.get(server.auth, "storageKey"), authCookieOptions.name);
});
