export type DashboardItem = {
  id: string; title: string; summary: string; href: string; detailHref?: string;
  owner: string; owners?: string[]; category: string; topic: string; date: string; dateLabel: string;
  heat?: number; heatLabel?: string; reads?: number; priority: boolean;
  analysis?: string; scores?: Record<string, number>;
};
export type History = { metric: string; points: { date: string; count: number }[]; groups: { name: string; points: { date: string; count: number }[] }[] };
export type BoardInsight = { date: string; count: number; summary?: { judgment?: string; analysis_mode?: string; focus?: { title: string; url: string; why: string; analysis: string; impact: string; caveat?: string } }; sources?: { title: string; url: string }[] };
export type CommunityEvent = { id: number; title: string; summary?: string | null; published_at?: string | null; first_seen_at?: string; last_seen_at?: string; source_names?: string[]; source_url?: string; source_count?: number; categories?: string[]; relevance?: string; scores?: Record<string, number>; tags?: string[] };
export type CommunityLegacy = { source: string; title: string; summary?: string; url: string; topic_category?: string; relevance?: string; published_at?: string | null; observed_at?: string };
export type CompetitorNews = { id: number; vendor?: string; title: string; summary?: string; link?: string; category?: string; date?: string; analysis?: string | null; intelligence?: { brief?: string; analysis?: string | null; source?: string | null } };

export function localDate(value: string): string {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value.slice(0, 10) : new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit" }).format(date);
}
export function parseHeat(text: string): { value?: number; label?: string; reads?: number } {
  const heat = text.match(/(?:热度|热搜指数)\s*([\d,.]+)\s*(亿|万|w|k)?/i) || text.match(/([\d,.]+)\s*(亿|万|w|k)?\s*(?:热度|热搜指数)/i);
  const reads = text.match(/阅读\s*([\d,.]+)\s*(亿|万|w|k)?/i);
  const number = (match: RegExpMatchArray) => Number(match[1].replaceAll(",", "")) * ({ 亿: 1e8, 万: 1e4, w: 1e4, k: 1e3 }[match[2]?.toLowerCase() as "亿" | "万" | "w" | "k"] || 1);
  return { value: heat ? number(heat) : undefined, label: heat ? `${heat[1]}${heat[2] || ""}` : undefined, reads: reads ? number(reads) : undefined };
}
export function communityItems(events: CommunityEvent[], legacy: CommunityLegacy[]): DashboardItem[] {
  if (events.length) return events.map(item => {
    const source = item.source_names?.[0] || "来源待核实";
    const heat = parseHeat(item.summary || "");
    return { id: String(item.id), title: item.title, summary: item.summary || "", href: item.source_url || `/events/${item.id}`,
      detailHref: `/events/${item.id}`, owner: source, owners: item.source_names || [source], category: item.categories?.[0] || "未分类", topic: item.categories?.[0] || "未分类",
      date: item.published_at ? localDate(item.published_at) : localDate(item.first_seen_at || item.last_seen_at || ""),
      dateLabel: item.published_at ? "发布" : "发现", heat: heat.value, heatLabel: heat.label, reads: heat.reads,
      priority: item.relevance === "high" || Object.values(item.scores || {}).some(value => value >= 80), scores: item.scores };
  });
  return legacy.map((item, index) => { const heat = parseHeat(item.summary || ""); return {
    id: `${item.source}-${index}`, title: item.title, summary: item.summary || "", href: item.url,
    owner: item.source, owners: [item.source], category: item.topic_category || "未分类", topic: item.topic_category || "未分类",
    date: localDate(item.published_at || item.observed_at || ""), dateLabel: item.published_at ? "发布" : "发现",
    heat: heat.value, heatLabel: heat.label, reads: heat.reads, priority: item.relevance === "high",
  }; });
}
export function competitorTopic(text: string): string {
  if (/安全|合规|治理|防护|firewall|security/i.test(text)) return "安全治理";
  if (/数据库|存储|向量|database|db\b|milvus|polar/i.test(text)) return "数据库与数据";
  if (/agent|智能体|copilot|工作流/i.test(text)) return "Agent";
  if (/模型|推理|训练|qwen|trainium|pytorch|llm|bedrock|ai foundry/i.test(text)) return "模型与算力";
  if (/开发|api|sdk|平台|dev|code/i.test(text)) return "开发平台";
  if (/合作|生态|伙伴|集成|partner/i.test(text)) return "生态合作";
  if (/行业|方案|金融|制造|政府|医疗/i.test(text)) return "行业方案";
  return "其他";
}
export function competitorItems(rows: CompetitorNews[]): DashboardItem[] {
  return rows.map(item => {
    const summary = (item.intelligence?.brief || item.summary || "").replace(/^Use:\s*/, "").trim();
    const topic = competitorTopic(`${item.title} ${summary} ${item.analysis || ""}`);
    return { id: `${item.vendor}-${item.id}`, title: item.title, summary, href: item.intelligence?.source || item.link || "",
      owner: item.vendor || "厂商待核实", category: item.category || "其他", topic, date: (item.date || "").slice(0, 10), dateLabel: "发布",
      priority: /product launch|price change|产品发布|价格调整/i.test(item.category || ""), analysis: item.analysis || item.intelligence?.analysis || undefined };
  }).sort((a, b) => b.date.localeCompare(a.date));
}
export function distribution(items: DashboardItem[]) {
  const counts = new Map<string, number>();
  items.forEach(item => counts.set(item.topic, (counts.get(item.topic) || 0) + 1));
  return [...counts].map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);
}
const STOP_WORDS = new Set(["AI", "一个", "一种", "什么", "如何", "支持", "更新", "发布", "使用", "可以", "进行", "以及", "相关", "当前", "这个", "技术", "产品", "能力", "服务", "正式", "提供", "新增", "通过", "最新", "今天"]);
export function keywords(items: DashboardItem[]) {
  const counts = new Map<string, number>();
  const segmenter = new Intl.Segmenter("zh-CN", { granularity: "word" });
  for (const item of items) {
    const words = new Set([...segmenter.segment(item.title)].filter(piece => piece.isWordLike).map(piece => piece.segment.trim()).filter(word => word.length >= 2 && !STOP_WORDS.has(word) && !/^\d/.test(word)));
    words.forEach(word => counts.set(word, (counts.get(word) || 0) + 1));
  }
  return [...counts].filter(([, count]) => count >= 2).sort((a, b) => b[1] - a[1]).slice(0, 12).map(([name, count]) => ({ name, count }));
}
export function withinLastDays(value: string | undefined | null, days: number): boolean {
  if (!value) return false;
  const at = new Date(value).getTime();
  return !Number.isNaN(at) && at >= Date.now() - days * 86400000;
}
export function daysAgo(date: string, days: number, now = new Date()): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
  const today = localDate(now.toISOString());
  const start = new Date(`${today}T00:00:00+08:00`);
  start.setUTCDate(start.getUTCDate() - days + 1);
  return date >= localDate(start.toISOString()) && date <= today;
}
export function groupChange(points: { date: string; count: number }[], days: number, now = new Date()) {
  const current = points.filter(point => daysAgo(point.date, days, now)).reduce((n, point) => n + point.count, 0);
  const prior = points.filter(point => daysAgo(point.date, days * 2, now) && !daysAgo(point.date, days, now)).reduce((n, point) => n + point.count, 0);
  const earliest = points[0]?.date;
  return earliest && daysAgo(earliest, days * 2, now) && !daysAgo(earliest, days, now) && prior > 0 ? Math.round((current - prior) * 100 / prior) : null;
}
