import { expect, test } from "@playwright/test";

const sections = [
  { name: "首页情报总览", path: "/", heading: "从技术信号" },
  { name: "技术生态", path: "/insights/hotspots", heading: "技术生态" },
  { name: "AI 应用", path: "/insights/app-launches", heading: "AI 应用" },
  { name: "解决方案", path: "/insights/solutions", heading: "解决方案" },
  { name: "友商洞察", path: "/insights/competitors", heading: "友商" },
  { name: "社区洞察", path: "/insights/community", heading: "社区" },
  { name: "方案实践", path: "/workbench/solutions" },
  { name: "工作台总览", path: "/workbench" },
  { name: "需求工作区", path: "/workbench/requirements" },
  { name: "新建需求", path: "/workbench/requirements/new" },
  { name: "新建方案", path: "/workbench/solutions/new" },
  { name: "AI 工作区", path: "/workbench/ai" },
  { name: "Insight Agent", path: "/insight-agent" },
  { name: "仪表盘", path: "/dashboard", loginRequired: true },
  { name: "报告", path: "/reports" },
  { name: "知识库", path: "/knowledge" },
  { name: "历史记录", path: "/history" },
  { name: "系统设置", path: "/settings" },
  { name: "搜索", path: "/search" },
  { name: "平台管理", path: "/admin" },
  { name: "管理仪表盘", path: "/admin/dashboard" },
  { name: "任务管理", path: "/admin/tasks" },
  { name: "数据源管理", path: "/admin/sources" },
  { name: "事件管理", path: "/admin/events" },
  { name: "覆盖审计", path: "/admin/coverage" },
  { name: "邮件投递", path: "/admin/emails" },
  { name: "运行配置", path: "/admin/runtime" },
  { name: "知识管理", path: "/admin/knowledge" },
  { name: "访问管理", path: "/admin/access" },
  { name: "登录", path: "/auth/login", loginRequired: true },
  { name: "注册", path: "/auth/register" },
  { name: "忘记密码", path: "/auth/forgot-password" },
  { name: "重置密码", path: "/auth/reset-password" },
];

for (const section of sections) {
  test(`${section.name} 页面可用且布局完整`, async ({ page }, testInfo) => {
    const pageErrors: string[] = [];
    page.on("pageerror", error => pageErrors.push(error.message));

    const response = await page.goto(section.path, { waitUntil: "domcontentloaded" });
    expect(response, "页面应返回 HTTP 响应").not.toBeNull();
    expect(response!.status(), "页面不应返回服务端错误").toBeLessThan(500);
    await expect(page.locator("body")).toBeVisible();
    await expect(page.locator("main h1, main h2").first(), "页面应显示主标题").toBeVisible({ timeout: 15_000 });
    const loginHeading = page.getByRole("heading", { name: "登录" });
    const gatedByLogin = section.loginRequired === true || new URL(page.url()).pathname === "/auth/login" || await loginHeading.count() > 0;
    if (gatedByLogin) {
      await expect(loginHeading).toBeVisible();
    }

    if (section.heading && !gatedByLogin) {
      await expect(page.getByRole("heading", { level: 1 }).first()).toContainText(section.heading, { timeout: 15_000 });
    }

    const layout = await page.evaluate(() => ({
      viewportWidth: document.documentElement.clientWidth,
      documentWidth: document.documentElement.scrollWidth,
      mainTextLength: document.querySelector("main")?.innerText.trim().length ?? 0,
    }));
    expect(layout.mainTextLength, "主内容区不应是空白页面").toBeGreaterThan(10);
    expect(layout.documentWidth, "页面主体不应产生横向溢出").toBeLessThanOrEqual(layout.viewportWidth + 2);
    expect(pageErrors, `页面运行时错误：${pageErrors.join(" | ")}`).toEqual([]);

    await page.screenshot({ path: testInfo.outputPath("screen.png"), fullPage: true, animations: "disabled" });
    await testInfo.attach("layout.json", { body: JSON.stringify({ ...layout, finalUrl: page.url(), access: gatedByLogin ? "login_required" : "public" }, null, 2), contentType: "application/json" });
  });
}

test("首页单屏锚点和统一事件可进入详情", async ({ page }) => {
  const event = { id: 987, title: "New AI product", summary: "Official launch", event_type: "product_launch",
    business_scopes: ["ai_applications"], tags: [], scores: { hot_score: { value: 82 } }, status: "active",
    first_seen_at: "2026-10-23T08:00:00+08:00", last_seen_at: "2026-10-23T08:00:00+08:00", evidence: [], metrics: [] };
  await page.route("**/api/v2/events?limit=100", route => route.fulfill({
    status: 200, contentType: "application/json", body: JSON.stringify({ items: [{ ...event, source_count: 2, source_names: ["Official blog", "Hacker News"] }] }),
  }));
  await page.route("**/api/v2/events/987", route => route.fulfill({
    status: 200, contentType: "application/json", body: JSON.stringify(event),
  }));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "从技术信号，到可落地的方案实践。" })).toBeVisible();
  await expect(page.locator("#technology-ecosystem")).toBeVisible();
  await expect(page.locator("#community-insights")).toHaveCount(1);
  await expect(page.getByText("近期事件", { exact: true })).toHaveCount(0);
  await page.getByRole("navigation", { name: "洞察导航" }).getByRole("link", { name: "AI 应用" }).click();
  await expect(page).toHaveURL(/#ai-applications$/);
  await expect(page.locator("#ai-applications")).toBeInViewport();
  await page.getByRole("link", { name: /New AI product/ }).first().click();
  await expect(page).toHaveURL(/\/events\/987$/);
  await expect(page.getByRole("heading", { name: "New AI product" })).toBeVisible();
});

test("社区页优先展示统一事件并链接到 Event Detail", async ({ page }) => {
  await page.route("**/api/v2/events?business_scope=community_insights&limit=100", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ items: [{ id: 987, title: "社区发现的新 AI Agent", summary: "跨站信号摘要", last_seen_at: "2026-10-23T08:00:00+08:00", source_names: ["知乎", "CSDN"], source_count: 2, scores: {} }] }),
  }));
  await page.goto("/insights/community");
  const event = page.getByRole("link", { name: /社区发现的新 AI Agent/ });
  await expect(event).toHaveAttribute("href", "/events/987");
  await expect(event).toContainText("知乎");
  await expect(event).toContainText("CSDN");
});

test("AI 应用动态优先展示统一事件", async ({ page }) => {
  await page.route("**/api/agent-launches", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ items: [], products: [], sources: [], vendors: [], refreshing: false }),
  }));
  await page.route("**/api/v2/events?business_scope=ai_applications&limit=100", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ items: [{ id: 654, title: "OpenAI 发布新能力", summary: "官方发布摘要", published_at: "2026-10-23T00:00:00Z", vendor: "OpenAI", kinds: ["update"] }] }),
  }));
  await page.goto("/insights/app-launches");
  await expect(page.getByText("OpenAI 发布新能力")).toBeVisible();
  await expect(page.getByRole("link", { name: /查看事件与来源证据/ })).toHaveAttribute("href", "/events/654");
});

test("友商动态优先展示统一事件", async ({ page }) => {
  await page.route("**/api/competitors", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ vendors: [{ name: "Alibaba Cloud", region: "CN", marketShare: "", products: [], strengths: [], weaknesses: [], vs_huawei: "", recent_news_count: 1 }] }),
  }));
  await page.route("**/api/competitors/summary", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ vendors: {} }) }));
  await page.route("**/api/v2/events?business_scope=competitor_dynamics&limit=100", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ items: [{ id: 432, title: "阿里云发布新服务", summary: "发布摘要", published_at: "2026-10-23T00:00:00Z", vendor: "Alibaba Cloud", categories: ["Product Launch"] }] }),
  }));
  await page.goto("/insights/competitors");
  const event = page.getByRole("link", { name: /阿里云发布新服务/ });
  await expect(event).toHaveAttribute("href", "/events/432");
});

test("解决方案页展示统一事件并链接到详情", async ({ page }) => {
  await page.route("**/api/solutions/catalog", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ items: [], count: 0, recent_count: 0, baseline_count: 0, daily_insight: { date: "2026-10-23", new: 0, updated: 0, removed: 0 }, daily_insights: {}, last_checked: null, sources: {} }),
  }));
  await page.route("**/api/v2/events?business_scope=solutions&limit=8", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ items: [{ id: 321, title: "华为云方案能力更新", summary: "方案变更摘要", vendor: "Huawei Cloud", categories: ["AI"], last_seen_at: "2026-10-23T08:00:00+08:00", source_count: 1 }] }),
  }));
  await page.goto("/insights/solutions");
  await expect(page.getByText("官方方案", { exact: true })).toHaveCount(0);
  await expect(page.getByText("今日新增", { exact: true })).toHaveCount(0);
  await expect(page.getByText("今日更新", { exact: true })).toHaveCount(0);
  await expect(page.getByText("今日下线", { exact: true })).toHaveCount(0);
  const event = page.getByRole("link", { name: /华为云方案能力更新/ });
  await expect(event).toHaveAttribute("href", "/events/321");
});

test("技术生态页保留项目榜单并移除近期信号区", async ({ page }) => {
  await page.route("**/api/v2/repositories/trending?period=daily", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ items: [{ repo_name: "team/agent-kit", repo_url: "https://github.com/team/agent-kit", description: "Agent framework", language: "Python", stars: "1.2k", forks: "80", today_stars: "300", category: "daily", entity_key: "github:team/agent-kit", event_id: 765 }], source: "event_store", count: 1, date: "2026-10-23" }),
  }));
  await page.route("**/api/github-trending/business-eval?locale=zh", route => route.fulfill({
    status: 200, contentType: "application/json", body: JSON.stringify({ items: [], count: 0, summary: {} }),
  }));
  await page.goto("/insights/hotspots");
  await expect(page.getByText("近期技术生态信号", { exact: true })).toHaveCount(0);
  await expect(page.getByText("team/agent-kit").first()).toBeVisible();
  await expect(page.getByRole("link", { name: "事件" })).toHaveAttribute("href", "/events/765");
  await expect(page.getByRole("link", { name: "情报" })).toHaveAttribute("href", "/repositories/github%3Ateam%2Fagent-kit");
});

test("V2 Trending 路由尚未部署时兼容读取 V1", async ({ page }) => {
  await page.route("**/api/v2/repositories/trending?period=daily", route => route.fulfill({ status: 404 }));
  await page.route("**/api/github-trending?since=daily", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ items: [{ repo_name: "legacy/project", repo_url: "https://github.com/legacy/project", description: "Existing V1 snapshot", language: "Go", stars: "900", forks: "40", today_stars: "80", category: "daily" }], source: "database", count: 1, date: "2026-10-23" }),
  }));
  await page.route("**/api/github-trending/business-eval?locale=zh", route => route.fulfill({
    status: 200, contentType: "application/json", body: JSON.stringify({ items: [], count: 0, summary: {} }),
  }));

  await page.goto("/insights/hotspots");

  await expect(page.getByText("legacy/project").first()).toBeVisible();
  await expect(page.getByText("热门项目加载失败。")).toHaveCount(0);
});

test("Repository Detail reads shared Entity metrics and evidence", async ({ page }) => {
  await page.route("**/api/v2/entities/**", route => {
    return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      entity: { entity_key: "github:team/agent-kit", entity_type: "repository", canonical_name: "team/agent-kit", canonical_url: "https://github.com/team/agent-kit", metadata: { language: "Python" } },
      events: [{ id: 765, title: "新型 Agent 开发框架", summary: "多源技术信号", event_type: "github_trending", scores: { business_evaluation: { total: 8.2, level: "Worth Doing", summary: "证据支持的项目判断", d1: 8, d2: 8, d3: 8, d4: 9, recommendation: "验证部署", reasoning: "基于观测证据", technical_assessment: {
        engineering_maturity: { score: 7, reasoning: "有发布与贡献者记录", evidence_keys: ["contributors_count", "latest_release_tag"] },
        innovation: { score: null, reasoning: "证据不足", evidence_keys: [] },
        deployability: { score: 6, reasoning: "开放许可证", evidence_keys: ["license"] },
      } } }, last_seen_at: "2026-10-23T08:00:00+08:00" }],
      evidence: [{ id: 12, title: "team/agent-kit", canonical_url: "https://github.com/team/agent-kit", source_name: "GitHub Trending", authority: "P1", observed_at: "2026-10-23T08:00:00+08:00" }],
      metrics: [{ metric_key: "stars", metric_value: 1200, observed_at: "2026-10-23T08:00:00+08:00", source_key: "github_trending" }],
      trends: { stale: false, windows: { "24h": { stars_delta: 300 } } },
    }),
    });
  });
  await page.goto("/repositories/github%3Ateam%2Fagent-kit");
  await expect(page.getByRole("heading", { name: "team/agent-kit" })).toBeVisible();
  await expect(page.getByText("stars_delta")).toBeVisible();
  await expect(page.getByRole("heading", { name: /来源证据|Source evidence/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /业务价值评估|Business assessment/ })).toBeVisible();
  await expect(page.getByText("证据支持的项目判断")).toBeVisible();
  await expect(page.getByText("工程成熟度")).toBeVisible();
  await expect(page.getByText("contributors_count, latest_release_tag")).toBeVisible();
});

test("全局搜索结果可进入 V2 Event Detail", async ({ page }) => {
  await page.route("**/api/search?*", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ results: [{ type: "community", title: "社区 Agent 信号", source: "知乎 · CSDN", url: "/events/876", snippet: "统一事件证据", date: "2026-10-23", date_basis: "observed" }], total: 1, query: "Agent", page: 1, pages: 1, facets: { community: 1 } }),
  }));
  await page.goto("/search");
  await page.getByRole("searchbox").fill("Agent");
  await page.getByRole("button", { name: "搜索", exact: true }).click();
  await expect(page.getByRole("tab", { name: /社区洞察/ })).toContainText("1");
  await expect(page.getByRole("link", { name: /社区 Agent 信号/ })).toHaveAttribute("href", "/events/876");
});
