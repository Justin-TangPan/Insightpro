export type Period = "today" | "week" | "month" | "7days";
export type Solution = {
  id: number; event_id?: number | null; is_active?: boolean; image_url?: string; detail_text?: string; title: string; url: string; category: string; vendor: string;
  source_description: string; summary: string; change_summary: string; first_seen_date: string;
  last_seen_date: string; last_changed_date: string; is_baseline: boolean; updated_at?: string;
};
export type SolutionEvent = {
  id: number; entity_key: string; title: string; summary: string | null; vendor: string;
  event_type: string; first_seen_at: string; last_seen_at: string; published_at?: string | null;
  source_names?: string[]; scores?: Record<string, number>;
};
export const periods: { key: Period; label: string }[] = [
  { key: "today", label: "今日" }, { key: "week", label: "本周" },
  { key: "month", label: "本月" }, { key: "7days", label: "近 7 天" },
];
const scenarioRules: [string, RegExp][] = [
  ["AI / Agent", /agent|智能体|mcp|智能代理/i], ["RAG / 知识库", /\brag\b|知识库|向量检索/i],
  ["数字人", /数字人|虚拟人|avatar/i], ["大模型部署", /deepseek|大模型|模型推理|模型训练|llm|gpu|vllm/i],
  ["数据分析", /数据分析|数据管理|搜索分析|elasticsearch|数据湖|数据仓库|data analytics|data management/i],
  ["云迁移", /云迁移|迁移上云|数据上云|cloud migration/i], ["容灾备份", /容灾|备份|灾备/i],
  ["安全合规", /安全|合规|等保|零信任|security|compliance/i], ["数据库", /数据库|mysql|postgresql|redis/i],
  ["网络", /网络|cdn|专线|负载均衡|networking/i], ["运维", /运维|监控|可观测|monitoring|ops/i],
  ["开发平台", /开发平台|devops|低代码/i],
];
const abilityRules: [string, RegExp][] = [
  ["Agent", /\bagent\b|智能体/i], ["MCP", /\bmcp\b/i], ["RAG", /\brag\b|检索增强/i],
  ["LLM", /\bllm\b|大模型/i], ["GPU 推理", /gpu|vllm|推理加速/i],
  ["向量数据库", /向量数据库|向量检索/i], ["多模态", /多模态|文生图|图生视频/i],
  ["OCR", /\bocr\b|文字识别/i], ["云原生", /云原生|kubernetes|\bk8s\b/i],
  ["数据分析", /数据分析|搜索分析/i], ["容灾备份", /容灾|备份/i],
];
export function cleanCategory(category: string): string {
  return category.replace(/(?:\s*\/\s*)?(?:Solution Practice|解决方案实践|Category Entry)$/i, "").replace(/\s*\/\s*$/, "").trim();
}
export function scenario(item: Solution): string {
  const category = cleanCategory(item.category);
  const text = `${item.title} ${category} ${item.source_description}`;
  return scenarioRules.find(([, rule]) => rule.test(text))?.[0] || category || "其他";
}
export function abilities(item: Solution): string[] {
  const text = `${item.title} ${item.source_description} ${item.summary}`;
  return abilityRules.filter(([, rule]) => rule.test(text)).map(([label]) => label);
}
export function eventType(item: Solution): string {
  const text = item.change_summary || "";
  if (/下线|removed/i.test(text)) return "方案下线";
  if (item.first_seen_date === item.last_changed_date && !item.is_baseline) return "新方案";
  if (/架构|architecture/i.test(text)) return "架构调整";
  if (/产品替换|产品调整/i.test(text)) return "产品调整";
  if (/模型升级/i.test(text)) return "模型升级";
  if (/新增能力|能力新增/i.test(text)) return "能力新增";
  if (/新增场景|场景扩展/i.test(text)) return "场景扩展";
  return "方案更新";
}
export function categoryNoise(value: string): boolean {
  const match = /^Category:\s*(.*?)\s*→\s*(.*?)(?:;|$)/i.exec(value.trim());
  return !!match && cleanCategory(match[1]) === cleanCategory(match[2]) && !value.includes(";");
}
export function meaningfulChange(value: string): boolean {
  const text = value.trim();
  return !!text && !/^(?:Solution (?:page )?content updated|Content updated)$/i.test(text) && !categoryNoise(text);
}
export function dateInPeriod(value: string | null | undefined, period: Period, now = new Date()): boolean {
  if (!value) return false;
  const date = value.slice(0, 10);
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
  if (period === "today") return date === today;
  if (period === "month") return date.slice(0, 7) === today.slice(0, 7);
  const current = new Date(`${today}T00:00:00Z`);
  const days = period === "week" ? (new Date(`${today}T12:00:00Z`).getUTCDay() + 6) % 7 : 6;
  current.setUTCDate(current.getUTCDate() - days);
  return date >= current.toISOString().slice(0, 10) && date <= today;
}
export function solutionValue(item: Solution): string {
  const text = item.source_description || item.summary.replace(/^Solution value:\s*/i, "").split("; Open-source projects:")[0];
  return text && !/^Solution (?:page )?content updated$/i.test(text) ? text : "官方方案已收录，详细价值以来源页面为准。";
}
export function priority(item: Solution): number {
  const text = `${item.title} ${item.source_description} ${item.change_summary}`;
  return (meaningfulChange(item.change_summary) ? 4 : 0) + (eventType(item) === "新方案" ? 3 : 0) +
    (abilities(item).length > 0 ? 2 : 0) + (/新增|new|升级|替换|部署/i.test(text) ? 2 : 0) +
    (item.vendor === "Huawei Cloud" || item.vendor === "Alibaba Cloud" ? 1 : 0);
}

export function industry(item: Solution): string {
  const text = `${item.title} ${item.source_description}`;
  return ([
    ["金融", /金融|银行|保险|证券|finance|banking/i], ["医疗", /医疗|医院|医药|healthcare/i],
    ["制造", /制造|工厂|工业|manufactur/i], ["零售", /零售|电商|retail/i],
    ["政务", /政务|政府|公共服务/i], ["教育", /教育|高校|校园|education/i],
  ] as [string, RegExp][]).find(([, pattern]) => pattern.test(text))?.[0] || "未标注";
}
export function products(item: Solution): string {
  const value = (item.summary || "").split(`${item.vendor} resources:`)[1]?.trim() || "";
  return value && !/not confirmed in official materials/i.test(value) ? value : "未明确列出";
}
