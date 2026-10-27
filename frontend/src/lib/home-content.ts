import type { FocusEvent } from "./home-focus";

export const businessNames: Record<string, string> = { apps: "AI 应用", github: "技术生态", solutions: "解决方案", community: "社区洞察", competitors: "友商动态" };
export const insightKinds = [
  { label: "厂商动态", href: "/insights/competitors", match: (event: FocusEvent) => event.board === "competitors" },
  { label: "技术趋势", href: "/insights/hotspots", match: (event: FocusEvent) => event.board === "github" },
  { label: "市场机会", href: "/insights/app-launches", match: (event: FocusEvent) => /机会|增长|需求|落地|市场/.test(`${event.why} ${event.summary}`) },
  { label: "潜在风险", href: "/insights/solutions", match: (event: FocusEvent) => /风险|压力|成本|监管|安全|漏洞|价格上涨/.test(`${event.title} ${event.summary}`) },
];

export function usefulSummary(event?: FocusEvent) {
  const summary = event?.summary?.trim();
  return summary && !/^(来源暂未提供摘要|暂无摘要|摘要待补充|solution content updated|content updated)[。…！!]*$/i.test(summary) ? summary : "";
}

export function displayTitle(event: FocusEvent) {
  return event.title.replace(/^(?:Alibaba Cloud|Huawei Cloud|阿里云|华为云)方案更新[：:]\s*/i, "").replace(/[_\s]*(?:部署教程|deployment guide)$/i, "");
}
