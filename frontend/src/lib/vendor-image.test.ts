import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import test from "node:test";
import { eventImage, vendorLogo } from "./vendor-image.ts";

test("tracked vendor and community marks resolve to local files", () => {
  for (const name of [
    "AWS", "Alibaba Cloud", "Anthropic", "DeepSeek", "GLM", "Google", "Kimi", "Meta",
    "Microsoft Azure", "MiniMax", "OpenAI", "Tencent Cloud", "Volcengine", "Huawei Cloud",
    "CSDN 热榜", "百度热搜", "知乎热榜", "腾讯云开发者社区",
  ]) {
    const path = vendorLogo(name);
    assert.match(path, /^\/brand-logos\//, name);
    assert.ok(existsSync(`public${path}`), `${name}: ${path}`);
  }
  assert.equal(vendorLogo("unknown source"), "");
  assert.equal(eventImage("https://example.com/cover.png", "Kimi"), "https://example.com/cover.png");
});
