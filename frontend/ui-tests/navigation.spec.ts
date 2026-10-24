import { expect, test } from "@playwright/test";

test("洞察区顶部导航保留检索和主题切换", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("navigation", { name: "洞察导航" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "洞察导航" }).getByRole("link", { name: "工作区" })).toHaveCount(0);
  await expect(page.locator("#sidebar")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "InsightPro 首页" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("button", { name: "切换深色主题" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  if (testInfo.project.name === "mobile") {
    await page.getByRole("link", { name: "打开全局搜索" }).click();
    await page.getByRole("search").locator("input").fill("Agent");
    await page.getByRole("search").locator("input").press("Enter");
  } else {
    await page.getByRole("search").locator("input").fill("Agent");
    await page.getByRole("search").locator("input").press("Enter");
  }
  await expect(page).toHaveURL(/\/search\?q=Agent/);
});

test("工作区仅允许管理员登录后进入", async ({ page }) => {
  await page.goto("/workbench");
  await expect(page).toHaveURL(/\/auth\/login\?next=%2Fworkbench/);
});
