"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, CalendarDays, Search } from "lucide-react";
import { API } from "@/lib/api";
import { usePreferences } from "@/lib/preferences";
import type { Intelligence } from "@/lib/intelligence";
import { plainIntelligenceText } from "@/lib/intelligence";
import { ExpandableText } from "@/components/expandable-text";
import { metricLabel } from "@/lib/data-display";

type Launch = { vendor: string; title: string; published: string; url: string; kind: "launch" | "update" | "product"; summary?: string; opportunity?: string; limitation?: string; intelligence?: Intelligence; eventId?: number };
type IntelligenceEvent = { id: number; title: string; summary?: string | null; published_at?: string | null; vendor?: string; kinds?: string[] };
type Product = { vendor: string; name: string; url: string };
type Source = { vendor: string; product: string; url: string; status: "matched" | "empty" | "error" | "pending" };
type Response = { items: Launch[]; products: Product[]; sources: Source[]; vendors: string[]; refreshing: boolean };
const vendorZh: Record<string, string> = { "Tencent Cloud": "腾讯", "Alibaba Cloud": "阿里巴巴", Volcengine: "字节跳动 / 火山引擎", "Microsoft Azure": "微软 / GitHub", Google: "谷歌", AWS: "亚马逊", GLM: "智谱", Kimi: "月之暗面", MiniMax: "稀宇科技", DeepSeek: "深度求索" };
const label = (vendor: string, en: boolean) => en ? vendor : vendorZh[vendor] || vendor;
const today = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());

export function AgentLaunches() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [data, setData] = useState<Response>({ items: [], products: [], sources: [], vendors: [], refreshing: false });
  const [v2Events, setV2Events] = useState<IntelligenceEvent[]>([]);
  const [vendor, setVendor] = useState("");
  const [query, setQuery] = useState("");
  const [view, setView] = useState<"updates" | "products" | "sources">("updates");
  const [todayOnly, setTodayOnly] = useState(false);
  const [limit, setLimit] = useState(24);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const [response, eventsResponse] = await Promise.all([
          fetch(`${API}/api/agent-launches`, { signal: controller.signal }),
          fetch(`${API}/api/v2/events?business_scope=ai_applications&limit=100`, { signal: controller.signal }).catch(() => null),
        ]);
        if (!response.ok) throw new Error("AI application feed unavailable");
        const result: Response = await response.json();
        const eventResult = eventsResponse?.ok ? await eventsResponse.json() : { items: [] };
        setV2Events(eventResult.items || []);
        setData(result); setLoading(false); setError(false);
        if (result.refreshing) timer = setTimeout(load, 5000);
      } catch { if (!controller.signal.aborted) { setError(true); setLoading(false); } }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [retry]);

  const day = today();
  const v2Launches: Launch[] = v2Events.map(item => ({ vendor: item.vendor || "", title: item.title,
    published: item.published_at?.slice(0, 10) || "", url: "",
    kind: item.kinds?.includes("launch") ? "launch" : item.kinds?.includes("product") ? "product" : "update",
    summary: item.summary || "", eventId: item.id }));
  const launchItems = v2Events.length ? v2Launches : data.items;
  const vendorNames = Array.from(new Set([...data.vendors, ...v2Events.map(item => item.vendor).filter((name): name is string => Boolean(name))]));
  const updates = useMemo(() => launchItems.filter(item => item.kind !== "product")
    .filter(item => !vendor || item.vendor === vendor)
    .filter(item => !todayOnly || item.published === day)
    .filter(item => !query || `${item.title} ${item.vendor} ${item.summary || ""}`.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => (b.published || "").localeCompare(a.published || "")), [launchItems, vendor, todayOnly, day, query]);
  const products = data.products.filter(item => (!vendor || item.vendor === vendor) && (!query || `${item.name} ${item.vendor}`.toLowerCase().includes(query.toLowerCase())));
  const sources = data.sources.filter(item => (!vendor || item.vendor === vendor) && (!query || `${item.product} ${item.vendor} ${item.url}`.toLowerCase().includes(query.toLowerCase())));
  const todayCount = launchItems.filter(item => item.kind !== "product" && item.published === day).length;

  return <section aria-labelledby="agent-launches-heading" className="space-y-5">
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="ui-card"><p className="swiss-kicker text-ink-muted">{en ? "Today's updates" : "今日官方动态"}</p><p className="mt-3 font-mono text-3xl font-semibold text-primary">{metricLabel(todayCount, loading, error, en, en ? "None" : "暂无")}</p><p className="mt-2 text-xs text-ink-muted">{day}</p></div>
      <div className="ui-card"><p className="swiss-kicker text-ink-muted">{en ? "Tracked products and platforms" : "已纳入产品与平台"}</p><p className="mt-3 font-mono text-3xl font-semibold text-ink">{metricLabel(data.products.length, loading, error, en, en ? "None" : "暂无")}</p><p className="mt-2 text-xs text-ink-muted">{loading ? (en ? "Loading vendor list" : "正在读取厂商列表") : error ? (en ? "Vendor list unavailable" : "厂商列表暂不可用") : data.vendors.length ? (en ? `${data.vendors.length} vendors` : `${data.vendors.length} 家厂商`) : (en ? "No vendors registered" : "暂无已纳入厂商")}</p></div>
      <div className="ui-card"><p className="swiss-kicker text-ink-muted">{en ? "Tracked official columns" : "已登记官方栏目"}</p><p className="mt-3 font-mono text-3xl font-semibold text-ink">{metricLabel(data.sources.length, loading, error, en, en ? "None" : "暂无")}</p><p className="mt-2 text-xs text-ink-muted">{en ? "Check each source's fetch status below" : "可在来源清单核对抓取状态"}</p></div>
    </div>

    <div className="ui-card">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div><h2 id="agent-launches-heading" className="type-h3 text-ink">{en ? "Applications and official updates" : "应用与官方动态"}</h2><p className="mt-1 text-sm leading-6 text-ink-muted">{en ? "Browse dated updates, check the product list, and audit official sources." : "按日期查看官方发布，并核对产品覆盖与来源。"}</p></div>
        <div className="relative w-full lg:w-64"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" /><input aria-label={en ? "Search applications" : "搜索应用和动态"} value={query} onChange={event => { setQuery(event.target.value); setLimit(24); }} className="ui-input min-h-11 w-full pl-10 pr-3 text-sm" placeholder={en ? "Product or vendor" : "搜索产品、厂商或动态"} /></div>
      </div>
      <div className="mt-5 flex flex-wrap gap-2" aria-label={en ? "Filter vendors" : "按厂商筛选"}>
        {["", ...vendorNames].map(item => <button key={item} type="button" aria-pressed={vendor === item} onClick={() => { setVendor(item); setLimit(24); }} className={`min-h-11 rounded-lg px-3 text-sm font-medium ${vendor === item ? "bg-primary text-white" : "bg-surface-subtle text-ink-secondary hover:bg-primary-soft"}`}>{item ? label(item, en) : en ? "All vendors" : "全部厂商"}</button>)}
      </div>
      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-grid pt-5">
        <div className="flex flex-wrap gap-2" role="group" aria-label={en ? "Application views" : "应用视图"}>
          {(["updates", "products", "sources"] as const).map(item => <button key={item} type="button" aria-pressed={view === item} onClick={() => setView(item)} className={`min-h-11 rounded-lg px-4 text-sm font-semibold ${view === item ? "bg-primary-soft text-primary" : "text-ink-muted hover:bg-surface-subtle"}`}>{item === "updates" ? (en ? "Updates" : "官方动态") : item === "products" ? (en ? "Products" : "产品目录") : (en ? "Sources" : "来源清单")}</button>)}
        </div>
        {view === "updates" && <button type="button" aria-pressed={todayOnly} onClick={() => setTodayOnly(!todayOnly)} className={`min-h-11 rounded-lg px-3 text-sm ${todayOnly ? "bg-primary text-white" : "bg-surface-subtle text-ink-secondary"}`}>{en ? "Today only" : "只看今日"}</button>}
      </div>
    </div>

    {error && <div role="alert" className="ui-card flex flex-wrap items-center justify-between gap-3 text-sm text-warning"><span>{en ? "The update feed could not load." : "动态暂时无法加载。"}</span><button type="button" className="ui-button-secondary" onClick={() => { setError(false); setLoading(true); setRetry(value => value + 1); }}>{en ? "Retry" : "重试"}</button></div>}
    {loading && <div role="status" className="ui-card h-48 animate-shimmer" />}
    {!loading && !error && data.refreshing && <p role="status" className="rounded-lg bg-primary-soft px-4 py-3 text-xs text-primary">{en ? "Official sources and analyses are refreshing. New entries will appear here." : "正在更新官方来源与逐条分析，新内容会自动出现。"}</p>}
    {!loading && !error && view === "updates" && <div>
      <div className="mb-3 flex items-center justify-between"><h3 className="type-h3 text-ink">{todayOnly ? (en ? "Today's updates" : "今日动态") : (en ? "Official update archive" : "官方动态记录")}</h3><span className="text-xs text-ink-muted">{updates.length} {en ? "items" : "条"}</span></div>
      {updates.length ? <div className="space-y-3">{updates.slice(0, limit).map(item => <article key={item.eventId || item.url} className="ui-card grid gap-4 md:grid-cols-[120px_1fr]">
        <div><span className="ui-tag">{label(item.vendor, en)}</span><p className="mt-3 flex items-center gap-1 font-mono text-xs text-ink-muted"><CalendarDays className="h-3.5 w-3.5" />{item.published || (en ? "Date pending" : "日期待核实")}</p></div>
        <div className="min-w-0"><h4 className="text-base font-semibold leading-6 text-ink">{item.intelligence?.title || item.title}</h4>{(item.summary || item.intelligence?.brief) ? <ExpandableText lines={3} en={en} className="mt-2 text-sm leading-6 text-ink-secondary">{plainIntelligenceText(item.summary || item.intelligence?.brief || "")}</ExpandableText> : <p className="mt-2 text-sm text-ink-muted">{en ? "Analysis pending; read the official update." : "分析生成中，可先查看官方原文。"}</p>}
          {item.opportunity && <p className="mt-3 text-sm leading-6 text-ink-secondary"><span className="font-semibold text-primary">{en ? "Opportunity: " : "生态机会："}</span>{item.opportunity}</p>}
          {item.limitation && <p className="mt-1 text-sm leading-6 text-ink-muted"><span className="font-semibold">{en ? "To verify: " : "待验证："}</span>{item.limitation}</p>}
          {item.eventId ? <Link href={`/events/${item.eventId}`} className="ui-link mt-4 inline-flex min-h-10 items-center gap-1 text-sm">{en ? "View event and evidence" : "查看事件与来源证据"}<ArrowUpRight className="h-4 w-4" /></Link> : <a href={item.url} target="_blank" rel="noopener noreferrer" className="ui-link mt-4 inline-flex min-h-10 items-center gap-1 text-sm">{en ? "Official source" : "查看官方原文"}<ArrowUpRight className="h-4 w-4" /></a>}
        </div>
      </article>)}{updates.length > limit && <button type="button" onClick={() => setLimit(limit + 24)} className="ui-button-secondary mx-auto block">{en ? "Show more" : "加载更多"}</button>}</div> : <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "No dated official update matches these filters." : "当前筛选下暂无带日期的官方动态；可查看产品目录与来源清单。"}</div>}
    </div>}
    {!loading && !error && view === "products" && (products.length ? <div className="space-y-7">{data.vendors.filter(name => products.some(item => item.vendor === name)).map(name => <section key={name} aria-label={label(name, en)}><div className="mb-3 flex items-baseline gap-3"><h3 className="type-h3 text-ink">{label(name, en)}</h3><span className="text-xs text-ink-muted">{products.filter(item => item.vendor === name).length} {en ? "products" : "项"}</span></div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{products.filter(item => item.vendor === name).map(item => <a key={item.name} href={item.url} target="_blank" rel="noopener noreferrer" className="ui-card group flex min-h-24 items-center justify-between gap-3"><h4 className="font-semibold text-ink group-hover:text-primary">{item.name}</h4><ArrowUpRight className="h-4 w-4 shrink-0 text-ink-muted" /></a>)}</div></section>)}</div> : <p className="ui-card text-sm text-ink-muted">{en ? "No product matches this search." : "没有符合筛选条件的产品。"}</p>)}
    {!loading && !error && view === "sources" && (sources.length ? <div className="space-y-5">{data.vendors.filter(name => sources.some(item => item.vendor === name)).map(name => <section key={name} aria-label={label(name, en)} className="ui-card"><h3 className="type-h3 text-ink">{label(name, en)}</h3><div className="mt-3 divide-y divide-grid">{sources.filter(item => item.vendor === name).map(item => <a key={item.url} href={item.url} target="_blank" rel="noopener noreferrer" className="group flex min-h-16 items-center justify-between gap-3 py-3"><div className="min-w-0"><p className="text-sm font-semibold text-ink group-hover:text-primary">{item.product || (en ? "Official newsroom" : "官方发布栏目")}</p><p className="mt-1 truncate text-xs text-ink-muted">{item.url}</p><p className="mt-1 text-xs text-ink-muted">{{ matched: en ? "Updates found" : "本次有匹配动态", empty: en ? "Readable; no matching update" : "可读取，暂无匹配动态", error: en ? "Temporarily unavailable" : "暂不可读取", pending: en ? "Checking" : "待检查" }[item.status || "pending"]}</p></div><ArrowUpRight className="h-4 w-4 shrink-0 text-ink-muted" /></a>)}</div></section>)}</div> : <p className="ui-card text-sm text-ink-muted">{en ? "No source matches this search." : "没有符合筛选条件的来源。"}</p>)}
  </section>;
}
