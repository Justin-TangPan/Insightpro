import type { HistoryEntry, TrendingItem } from "./hotspot-types";

export function metric(value: string | null | undefined): number {
  const match = String(value || "").replaceAll(",", "").match(/[\d.]+/);
  if (!match) return 0;
  const amount = Number(match[0]);
  return Number.isFinite(amount) ? amount * (/k/i.test(value || "") ? 1000 : /m/i.test(value || "") ? 1000000 : 1) : 0;
}

const groups = [
  { key: "language", label: "编程语言", en: "Languages", pattern: /language|compiler|programming|语言|编译|php|python|golang|node\.js/i },
  { key: "multimodal", label: "多模态", en: "Multimodal", pattern: /multimodal|vision|image|video|audio|speech|多模态|视觉|图像|视频|语音/i },
  { key: "security", label: "安全", en: "Security", pattern: /security|audit|safety|guard|安全|审计|评测|eval/i },
  { key: "framework", label: "AI 框架", en: "AI frameworks", pattern: /agent|llm|model|inference|ai framework|模型|推理|智能体|框架/i },
  { key: "tool", label: "开发工具", en: "Developer tools", pattern: /tool|developer|devops|plugin|sdk|cli|工具|插件|开发|部署/i },
] as const;

export const projectCategories = [{ key: "all", label: "全部", en: "All" }, ...groups, { key: "other", label: "其他", en: "Other" }];

// shortcut: category is inferred from repository text; use curated topic taxonomy when it becomes available.
export function projectCategory(item: TrendingItem): string {
  const content = `${item.repo_name} ${item.description} ${item.category} ${(item.topics || []).join(" ")}`;
  return groups.find(group => group.pattern.test(content))?.key || "other";
}

export function projectTags(item: TrendingItem, en: boolean): string[] {
  const category = projectCategories.find(group => group.key === projectCategory(item));
  return [...new Set([item.language && item.language !== "N/A" ? item.language : "", category ? (en ? category.en : category.label) : "", ...(item.topics || []).slice(0, 2)].filter(Boolean))].slice(0, 3);
}

export function historySeries(history: HistoryEntry[], match: (item: TrendingItem) => boolean): number[] {
  return history.slice().reverse().map(day => day.items.filter(match).reduce((sum, item) => sum + metric(item.today_stars), 0));
}

export function sparkline(values: number[]): string {
  if (values.length < 2) return "";
  const max = Math.max(...values);
  const min = Math.min(...values);
  return values.map((value, index) => `${(index / (values.length - 1) * 100).toFixed(1)},${(30 - (max === min ? 15 : (value - min) / (max - min) * 26)).toFixed(1)}`).join(" ");
}
