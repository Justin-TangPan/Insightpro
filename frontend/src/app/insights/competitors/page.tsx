"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Binoculars, CheckCircle2, RefreshCw, Search, ShieldAlert } from "lucide-react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { SectionHeader } from "@/components/section-header";
import { usePreferences } from "@/lib/preferences";
import { useAuth } from "@/components/auth-provider";
import type { Intelligence } from "@/lib/intelligence";
import { plainIntelligenceText } from "@/lib/intelligence";
import { DailyBoardInsight } from "@/components/daily-board-insight";

type News = { id: number; title: string; summary: string; link: string; category: string; date: string; intelligence?: Intelligence };
type Vendor = { name: string; region: string; marketShare: string; products: string[]; strengths: string[]; weaknesses: string[]; vs_huawei: string; recent_news_count: number };
type FeedItem = News & { vendor: string; eventId?: number };
type EventRow = { id: number; title: string; summary?: string | null; published_at?: string | null; vendor?: string; categories?: string[] };

const alias: Record<string, string> = { Azure: "Microsoft Azure", 火山云: "Volcengine", 火山引擎: "Volcengine" };
const code = (name: string) => ({ AWS: "AWS", "Microsoft Azure": "AZ", "Alibaba Cloud": "AL", "Tencent Cloud": "TC", Volcengine: "VC" }[name] || name.slice(0, 2).toUpperCase());
const vendorLabel = (name: string, en: boolean) => en ? name : ({ "Alibaba Cloud": "阿里云", "Tencent Cloud": "腾讯云", Volcengine: "火山引擎", "Microsoft Azure": "微软 Azure" }[name] || name);
const categoryLabel = (name: string, en: boolean) => en ? name : ({ "Solution New": "解决方案上新", "Product Launch": "产品发布", "Price Change": "价格调整", "Region New": "地域新增", "Feature Update": "功能更新", "Case Study": "客户案例", "Product Update": "产品更新" }[name] || name);
const aliyunProfile = {
  strengths: ["国内云市场份额领先", "经过双十一高并发场景验证", "钉钉提供企业服务入口"],
  weaknesses: ["政企行业纵深仍需持续加强", "海外市场覆盖相对有限", "大模型商业化落地仍在加速"],
  vs_huawei: "阿里云在互联网行业与开发者生态方面领先；华为云则在政务、金融、制造等行业纵深以及云边端协同方面更具优势。",
};
const tencentProfile = {
  strengths: ["微信生态与企业微信提供业务入口", "游戏、音视频和实时互动场景积累深", "混元模型、知识引擎与数据库产品形成组合"],
  weaknesses: ["企业级场景覆盖与交付能力仍需逐项验证", "大模型应用的规模化效果需要持续观察", "跨行业解决方案的完整度有待对比"],
  vs_huawei: "腾讯云在社交、游戏和实时音视频场景有积累；可重点比较双方在企业 Agent、行业应用和云上部署方案中的能力与落地案例。",
};
const awsProfile = {
  strengths: ["全球云基础设施与服务覆盖广", "Bedrock、SageMaker 等 AI 服务形成产品组合", "开发者与企业生态成熟"],
  weaknesses: ["中国市场可用服务与全球区域存在差异", "跨区域部署与合规要求需要逐项评估", "产品与计费体系复杂，方案成本需要核算"],
  vs_huawei: "重点比较 AWS 与华为云在模型平台、全球部署、国内行业交付及成本上的适用场景。",
};
const volcengineProfile = {
  strengths: ["豆包模型与火山方舟形成 AI 服务入口", "视频、互动与数据产品有场景积累", "Coding Plan 等开发者产品更新活跃"],
  weaknesses: ["跨行业交付能力需要结合案例验证", "产品覆盖与区域可用性需要逐项比较", "模型及套餐变化需要持续跟踪"],
  vs_huawei: "重点比较火山引擎与华为云在模型服务、Agent 开发、数据基础设施和行业方案中的能力与落地案例。",
};
const chineseVendors = ["Alibaba Cloud", "Tencent Cloud", "AWS", "Volcengine"];

export default function CompetitorsPage() {
  const { preferences } = usePreferences();
  const { user } = useAuth();
  const en = preferences.language === "en";
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [summary, setSummary] = useState<Record<string, News[]>>({});
  const [v2Events, setV2Events] = useState<EventRow[]>([]);
  const [vendor, setVendor] = useState("Alibaba Cloud");
  const [category, setCategory] = useState("全部");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [profiles, updates, events] = await Promise.all([
      fetch(`${API}/api/competitors`), fetch(`${API}/api/competitors/summary`),
      fetch(`${API}/api/v2/events?business_scope=competitor_dynamics&limit=100`).catch(() => null),
    ]);
    if (!profiles.ok || !updates.ok) throw new Error(en ? "Could not load competitor updates" : "友商动态加载失败，请重试");
    const [profileData, updateData] = await Promise.all([profiles.json(), updates.json()]);
    const eventData = events?.ok ? await events.json() : { items: [] };
    setVendors(profileData.vendors || []);
    setSummary(updateData.vendors || {});
    setV2Events(eventData.items || []);
  }, [en]);

  useEffect(() => { void Promise.resolve().then(load).catch(reason => setError(reason.message)).finally(() => setLoading(false)); }, [load]);
  const v2News: FeedItem[] = v2Events.map(item => ({
    id: item.id, title: item.title, summary: item.summary || "", link: "",
    category: item.categories?.[0] || "Product Update", date: item.published_at?.slice(0, 10) || "",
    vendor: item.vendor || "", eventId: item.id,
  }));
  const allNews: FeedItem[] = useMemo(() => v2Events.length ? v2News : Object.entries(summary).flatMap(([name, items]) => items.map(item => ({ ...item, vendor: alias[name] || name }))), [summary, v2Events, v2News]);
  const visibleVendors = en ? vendors : vendors.filter(item => chineseVendors.includes(item.name));
  const categories = ["全部", ...new Set(allNews.filter(item => vendor === "全部" || item.vendor === vendor).map(item => item.category))];
  const news = useMemo(() => allNews.filter(item => en || chineseVendors.includes(item.vendor)).filter(item => vendor === "全部" || item.vendor === vendor).filter(item => category === "全部" || item.category === category).filter(item => !query.trim() || `${item.title} ${item.summary}`.toLowerCase().includes(query.trim().toLowerCase())).sort((a, b) => (b.date || "").localeCompare(a.date || "")), [allNews, vendor, category, query, en]);
  const selected = vendors.find(item => item.name === vendor);
  const selectedProfile = !en && selected ? ({ "Alibaba Cloud": aliyunProfile, "Tencent Cloud": tencentProfile, AWS: awsProfile, Volcengine: volcengineProfile } as Record<string, typeof aliyunProfile>)[selected.name] : undefined;
  const vendorCount = (name: string) => allNews.filter(item => item.vendor === name).length;

  async function retryLoad() {
    setLoading(true); setError("");
    try { await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : (en ? "Could not load competitor updates" : "友商动态加载失败")); }
    finally { setLoading(false); }
  }

  async function refresh() {
    setRefreshing(true); setError("");
    try { const response = await authenticatedFetch(`${API}/api/competitors/refresh`, { method: "POST" }); if (!response.ok) throw new Error(en ? "Refresh failed; check your sign-in" : "刷新失败，请检查登录状态"); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : (en ? "Refresh failed" : "刷新失败")); }
    finally { setRefreshing(false); }
  }

  return <div className="page-stack intel-subpage">
    <SectionHeader compact icon={<Binoculars className="h-5 w-5" />} title={en ? "Competitor Insights" : "友商洞察"} action={user ? <button type="button" onClick={refresh} disabled={refreshing} className="ui-button-secondary"><RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />{refreshing ? (en ? "Refreshing..." : "刷新中") : (en ? "Refresh updates" : "刷新动态")}</button> : undefined} />
    <DailyBoardInsight board="competitors" />
    {error && <div role="alert" className="ui-card flex items-center justify-between gap-3 text-sm text-warning"><span>{error}</span><button type="button" className="ui-button-secondary" onClick={() => void retryLoad()}>{en ? "Retry" : "重试"}</button></div>}
    <section className="ui-card"><div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"><div><h2 className="mt-1 type-h2 text-ink"> {en ? "Choose a vendor" : "选择观察厂商"}</h2></div><div className="flex flex-wrap gap-2">{en && <VendorButton active={vendor === "全部"} label="All" code="ALL" onClick={() => setVendor("全部")} />}{visibleVendors.map(item => <VendorButton key={item.name} active={vendor === item.name} label={vendorLabel(item.name, en)} code={code(item.name)} count={vendorCount(item.name)} onClick={() => { setVendor(item.name); setCategory("全部"); }} />)}</div></div>
      {selected && <div className="mt-6 grid gap-5 border-t border-grid pt-6 lg:grid-cols-[1fr_1fr_1.4fr]"><Insight title={en ? "Strengths" : "主要优势"} icon={CheckCircle2} items={selectedProfile?.strengths || selected.strengths} /><Insight title={en ? "Weaknesses" : "关注短板"} icon={ShieldAlert} items={selectedProfile?.weaknesses || selected.weaknesses} /><div className="rounded-xl bg-primary-soft p-5"><p className="swiss-kicker text-primary"> {en ? "Compared with Huawei Cloud" : "与华为云对照"}</p><p className="mt-3 text-sm leading-6 text-ink-secondary">{selectedProfile?.vs_huawei || selected.vs_huawei}</p><div className="mt-4 flex flex-wrap gap-2">{selected.products.map(item => <span key={item} className="ui-tag">{item}</span>)}</div></div></div>}
  </section>
    <section className="grid gap-5 xl:grid-cols-[260px_1fr]"><aside className="ui-card self-start xl:sticky xl:top-20"><h2 className="mt-1 type-h3 text-ink"> {en ? "Filter updates" : "筛选情报"}</h2><label htmlFor="competitor-query" className="mt-5 block text-xs font-semibold text-ink-secondary"> {en ? "Search titles and summaries" : "搜索标题与摘要"}</label><div className="relative mt-2"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" /><input id="competitor-query" value={query} onChange={event => setQuery(event.target.value)} spellCheck={false} autoComplete="off" className="ui-input min-h-11 w-full pl-10 pr-3 text-sm" placeholder={en ? "Model, database, agent..." : "模型、数据库、Agent…"} /></div><p className="mt-6 text-xs font-semibold text-ink-secondary"> {en ? "Update type" : "动态类型"}</p><div className="mt-2 flex flex-wrap gap-2 xl:flex-col">{categories.map(item => <button key={item} type="button" onClick={() => setCategory(item)} className={`min-h-10 rounded-lg px-3 text-left text-sm ${category === item ? "bg-primary text-white" : "bg-surface-subtle text-ink-secondary hover:bg-primary-soft"}`}>{item === "全部" && en ? "All" : categoryLabel(item, en)}</button>)}</div></aside>
      <div className="ui-card min-w-0"><div className="flex items-end justify-between gap-4"><div><h2 className="mt-1 type-h2 text-ink">{vendor === "全部" ? (en ? "All vendor updates" : "全部厂商动态") : (en ? `${vendor} updates` : `${vendorLabel(vendor, false)}动态`)}</h2></div><span className="font-mono text-sm text-ink-muted"> {news.length} {en ? "items" : "条"}</span></div><div className="mt-5 divide-y divide-grid">{loading ? <div className="h-72 animate-shimmer rounded-xl" /> : news.length ? news.map(item => <Link key={item.eventId || item.intelligence?.key || `${item.vendor}-${item.id}`} href={item.eventId ? `/events/${item.eventId}` : item.intelligence?.source || item.link} target={item.eventId ? undefined : "_blank"} rel={item.eventId ? undefined : "noopener noreferrer"} className="group grid gap-3 py-5 sm:grid-cols-[88px_1fr_auto]"><div><span className="ui-tag">{categoryLabel(item.category, en)}</span><p className="mt-2 font-mono text-[10px] text-ink-muted">{item.date || (en ? "Date pending" : "日期待确认")}</p></div><div><div className="flex flex-wrap items-center gap-2"><span className="font-mono text-[11px] font-semibold text-primary"> {vendorLabel(item.vendor, en)}</span><h3 className="font-semibold text-ink group-hover:text-primary">{item.intelligence?.title || item.title}</h3></div><p className="mt-2 text-sm leading-6 text-ink-secondary">{(item.intelligence?.brief || item.summary || "").replace(/^Use:\s*/, en ? "Use: " : "用途：")}</p>{item.intelligence?.analysis && <p className="mt-2 line-clamp-2 text-sm leading-6 text-ink-secondary">{plainIntelligenceText(item.intelligence.analysis)}</p>}</div><ArrowUpRight className="mt-1 h-4 w-4 text-ink-muted group-hover:text-primary" /></Link>) : <div className="py-16 text-center"><Binoculars className="mx-auto h-7 w-7 text-ink-muted" /><p className="mt-3 text-sm text-ink-secondary"> {en ? "No updates match these filters" : "当前筛选下没有动态"}</p><button type="button" onClick={() => { setCategory("全部"); setQuery(""); }} className="ui-button-secondary mt-4"> {en ? "Clear filters" : "清除筛选"}</button></div>}</div></div>
    </section>
  </div>;
}

function VendorButton({ active, label, code: vendorCode, count, onClick }: { active: boolean; label: string; code: string; count?: number; onClick: () => void }) { return <button type="button" onClick={onClick} aria-pressed={active} className={`flex min-h-11 items-center gap-2 rounded-xl px-3 text-sm font-semibold ${active ? "bg-primary text-white" : "bg-surface-subtle text-ink-secondary hover:bg-primary-soft"}`}><span className="font-mono text-[10px] opacity-65">{vendorCode}</span>{label}{typeof count === "number" && <span className="rounded-full bg-white/15 px-1.5 font-mono text-[10px]">{count}</span>}</button>; }
function Insight({ title, icon: Icon, items }: { title: string; icon: typeof CheckCircle2; items: string[] }) { return <div><div className="flex items-center gap-2"><Icon className="h-4 w-4 text-primary" /><h3 className="text-sm font-semibold text-ink">{title}</h3></div><ul className="mt-3 space-y-2">{items.map(item => <li key={item} className="flex gap-2 text-sm leading-5 text-ink-secondary"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-primary" />{item}</li>)}</ul></div>; }
