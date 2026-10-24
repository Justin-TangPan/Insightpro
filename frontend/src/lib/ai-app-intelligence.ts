export type RawUpdate = { vendor: string; title: string; published: string; url: string; kind: "launch" | "update" | "product"; summary?: string; capability?: string; opportunity?: string; limitation?: string; source_text?: string; image_url?: string; analyzed_at?: string; source_updated_at?: string; intelligence?: { brief?: string }; analysis_id?: number };
export type Product = { vendor: string; name: string; url: string };
export type Source = { vendor: string; product: string; url: string; status: "matched" | "empty" | "error" | "pending" };
export type EventType = "产品发布" | "版本更新" | "新能力" | "模型升级" | "平台更新" | "API 更新" | "合作集成" | "商业化变化" | "其他";
export type Category = "智能助手" | "AI 编程" | "办公工具" | "多模态应用" | "AI 搜索" | "Agent 平台" | "企业 AI" | "内容创作" | "开发者平台" | "其他";
export type AppEvent = { event_id: string; vendor: string; product: string; title: string; summary: string; source_url: string; source_name: string; published_at: string; collected_at: string; event_type: EventType; product_category: Category; importance_level: "重点" | "常规"; what_changed: string; why_it_matters: string; business_impact: string; tags: string[]; source_count: number; image_url?: string };
export const EVENT_TYPES: EventType[] = ["产品发布", "版本更新", "新能力", "模型升级", "平台更新", "API 更新", "合作集成", "商业化变化", "其他"];
export const CATEGORIES: Category[] = ["智能助手", "AI 编程", "办公工具", "多模态应用", "AI 搜索", "Agent 平台", "企业 AI", "内容创作", "开发者平台", "其他"];

export function categoryOf(name: string): Category {
  if (/code|codex|github copilot|qoder|jules|kiro|编程|开发|antigravity/i.test(name)) return "AI 编程";
  if (/studio|开放平台|bedrock|foundry|ai studio|api/i.test(name)) return "开发者平台";
  if (/agent|智能体|扣子|coze|cowork/i.test(name)) return "Agent 平台";
  if (/workspace|钉钉|workbuddy|q business|企业/i.test(name)) return "企业 AI";
  if (/office|365|notebook|work|文档/i.test(name)) return "办公工具";
  if (/search|夸克/i.test(name)) return "AI 搜索";
  if (/flow|海螺|vibes|video/i.test(name)) return "多模态应用";
  if (/design|stitch|创作/i.test(name)) return "内容创作";
  if (/chatgpt|claude|gemini|kimi|千问|元宝|豆包|deepseek|清言|z\.ai|meta ai|星野|q apps|copilot/i.test(name)) return "智能助手";
  return "其他";
}

export function typeOf(item: RawUpdate): EventType {
  const text = `${item.title} ${item.summary || ""}`;
  if (/案例|实践|指南|教程|how to|case study/i.test(text) && !/新产品|新功能|新版本|推出|上线|发布.*(模型|产品|功能|平台|应用)/i.test(text)) return "其他";
  if (/价格|定价|订阅|付费|收费|pricing|subscription/i.test(text)) return "商业化变化";
  if (/合作|集成|接入|整合|integration|partnership/i.test(text)) return "合作集成";
  if (/\bapi\b|sdk|接口更新/i.test(text)) return "API 更新";
  if (/模型|model|推理|reasoning/i.test(text) && /升级|更新|发布|推出|上线|release|launch/i.test(text)) return "模型升级";
  if (/平台|platform|studio|console/i.test(text) && /升级|更新|发布|推出|上线|release|launch/i.test(text)) return "平台更新";
  if (/新能力|新功能|功能上线|新增|支持|能力升级|feature|now supports/i.test(text)) return "新能力";
  if (/版本|release notes|changelog|更新日志|\bv\d|\d+\.\d+/i.test(text) || item.kind === "update") return "版本更新";
  if (/发布|推出|上线|launch|introduc|release/i.test(text)) return "产品发布";
  return "其他";
}

function productFor(item: RawUpdate, products: Product[], sources: Source[]): Product | undefined {
  const candidates = products.filter(product => product.vendor === item.vendor);
  const haystack = `${item.title} ${item.summary || ""} ${item.url}`.toLowerCase();
  const explicit = candidates.filter(product => product.name.length > 2 && haystack.includes(product.name.toLowerCase()))
    .sort((a, b) => b.name.length - a.name.length)[0];
  if (explicit) return explicit;
  const source = sources.find(source => source.vendor === item.vendor && source.product && item.url.startsWith(source.url.split("#")[0]));
  if (source) return candidates.find(product => product.name === source.product);
  return undefined;
}

export function buildEvents(items: RawUpdate[], products: Product[], sources: Source[]): AppEvent[] {
  return items.filter(item => item.kind !== "product").map(item => {
    const product = productFor(item, products, sources);
    const event_type = typeOf(item);
    const summary = item.summary || item.intelligence?.brief || item.source_text || "";
    const why = item.opportunity || item.capability || "";
    return {
      event_id: String(item.analysis_id || item.url), vendor: item.vendor, product: product?.name || "", title: item.title,
      summary, source_url: item.url, source_name: (() => { try { return new URL(item.url).hostname.replace(/^www\./, ""); } catch { return "官方来源"; } })(),
      published_at: item.published || "", collected_at: item.source_updated_at || item.analyzed_at || "",
      event_type, product_category: product ? categoryOf(product.name) : "其他",
      importance_level: (item.opportunity && !/未提及|无明显|尚不明确|缺乏|暂无/.test(item.opportunity) && ["产品发布", "新能力", "模型升级", "平台更新"].includes(event_type) ? "重点" : "常规") as "重点" | "常规",
      what_changed: item.capability || summary, why_it_matters: why, business_impact: item.opportunity || "",
      tags: [event_type, ...(product ? [categoryOf(product.name)] : [])], source_count: 1, image_url: item.image_url,
    };
  }).sort((a, b) => b.published_at.localeCompare(a.published_at));
}

export type Period = "today" | "week" | "month" | "7days" | "all";
export function inPeriod(date: string, period: Period, now = new Date()): boolean {
  if (period === "all") return true;
  if (period === "month" && /^\d{4}-\d{2}(?:-\d{2})?$/.test(date)) return date.slice(0, 7) === new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit" }).format(now).slice(0, 7);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
  const day = new Date(`${date}T00:00:00+08:00`);
  const local = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Shanghai" }));
  const today = new Date(`${local.getFullYear()}-${String(local.getMonth() + 1).padStart(2, "0")}-${String(local.getDate()).padStart(2, "0")}T00:00:00+08:00`);
  if (period === "today") return day.getTime() === today.getTime();
  if (period === "month") return date.slice(0, 7) === `${local.getFullYear()}-${String(local.getMonth() + 1).padStart(2, "0")}`;
  if (period === "week") {
    const monday = new Date(today); monday.setUTCDate(monday.getUTCDate() - ((local.getDay() + 6) % 7));
    return day >= monday && day <= today;
  }
  const start = new Date(today); start.setUTCDate(start.getUTCDate() - 6);
  return day >= start && day <= today;
}

export function featured(events: AppEvent[], limit = 5): AppEvent[] {
  return [...events].sort((a, b) => {
    const score = (event: AppEvent) => (event.importance_level === "重点" ? 4 : 0) +
      (["产品发布", "新能力", "模型升级"].includes(event.event_type) ? 2 : 0) + (event.product ? 1 : 0);
    return score(b) - score(a) || b.published_at.localeCompare(a.published_at);
  }).slice(0, limit);
}

export function vendorActivity(events: AppEvent[]) {
  const names = [...new Set(events.map(event => event.vendor))];
  return names.map(vendor => {
    const own = events.filter(event => event.vendor === vendor);
    return { vendor, count: own.length, products: new Set(own.map(event => event.product).filter(Boolean)).size,
      important: own.filter(event => event.importance_level === "重点").length, latest: own[0]?.published_at || "" };
  }).sort((a, b) => b.count - a.count || b.latest.localeCompare(a.latest));
}

export function judgments(events: AppEvent[]) {
  const categoryCounts = CATEGORIES.map(category => ({ category, count: events.filter(event => event.product_category === category).length }))
    .filter(item => item.count >= 2).sort((a, b) => b.count - a.count);
  const vendors = vendorActivity(events);
  const total = events.length;
  const overall = total ? `${total} 条有日期的官方动态涉及 ${vendors.length} 家厂商；${categoryCounts.length ? `${categoryCounts[0].category}是当前更新最密集的已归类方向` : "产品归属仍待更多可核实信息补充"}。` : "当前周期暂无可核实的官方应用动态。";
  const insights = [
    categoryCounts[0] && { label: "产品方向", text: `${categoryCounts[0].category}有 ${categoryCounts[0].count} 条更新`, evidence: events.filter(event => event.product_category === categoryCounts[0].category).slice(0, 3) },
    vendors[0] && { label: "厂商动作", text: `${vendors[0].vendor}发布 ${vendors[0].count} 条动态，涉及 ${vendors[0].products} 个已识别产品`, evidence: events.filter(event => event.vendor === vendors[0].vendor).slice(0, 3) },
    (() => { const types = EVENT_TYPES.map(type => ({ type, count: events.filter(event => event.event_type === type).length })).filter(item => item.count >= 2).sort((a, b) => b.count - a.count); return types[0] && { label: "更新形态", text: `${types[0].type}出现 ${types[0].count} 次`, evidence: events.filter(event => event.event_type === types[0].type).slice(0, 3) }; })(),
  ].filter((item): item is { label: string; text: string; evidence: AppEvent[] } => Boolean(item));
  return { overall, insights };
}

export function sevenDayTrend(events: AppEvent[], now = new Date()) {
  const local = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Shanghai" }));
  const today = new Date(`${local.getFullYear()}-${String(local.getMonth() + 1).padStart(2, "0")}-${String(local.getDate()).padStart(2, "0")}T00:00:00+08:00`);
  const start = new Date(today); start.setUTCDate(start.getUTCDate() - 13);
  const end = new Date(today); end.setUTCDate(end.getUTCDate() - 7);
  const current = events.filter(event => inPeriod(event.published_at, "7days", now));
  const previous = events.filter(event => /^\d{4}-\d{2}-\d{2}$/.test(event.published_at) && new Date(`${event.published_at}T00:00:00+08:00`) >= start && new Date(`${event.published_at}T00:00:00+08:00`) <= end);
  return CATEGORIES.map(category => {
    const count = current.filter(event => event.product_category === category).length;
    const prior = previous.filter(event => event.product_category === category).length;
    return { category, count, prior, direction: count > prior ? "升温" : count < prior ? "降温" : "持平" };
  }).filter(item => item.count + item.prior >= 2 && item.count > 0 && item.prior > 0);
}
