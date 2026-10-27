"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import { ArrowRight, ArrowUpRight, Boxes, ExternalLink, Sparkles, X } from "lucide-react";
import { API } from "@/lib/api";
import { cachedJson, peekJson } from "@/lib/client-data-cache";
import { eventImage, vendorLogo } from "@/lib/vendor-image";
import { usePreferences } from "@/lib/preferences";
import { InsightPageShell } from "@/components/insight-page-shell";
import { DailyAiBrief } from "@/components/daily-ai-brief";
import { buildEvents, CATEGORIES, EVENT_TYPES, inPeriod, vendorActivity, categoryOf } from "@/lib/ai-app-intelligence";
import type { AppEvent, Period, Product, RawUpdate, Source, EventType } from "@/lib/ai-app-intelligence";

type Response = { items: RawUpdate[]; products: Product[]; sources: Source[]; vendors: string[]; refreshing: boolean };
const vendorZh: Record<string, string> = { "Tencent Cloud": "腾讯", "Alibaba Cloud": "阿里巴巴", Volcengine: "字节跳动 / 火山引擎", "Microsoft Azure": "Microsoft / GitHub", Google: "Google", AWS: "AWS", GLM: "智谱", Kimi: "月之暗面", MiniMax: "稀宇科技", DeepSeek: "深度求索" };
const periodNames: Record<Period, string> = { today: "今日", week: "本周", month: "本月", "7days": "近 7 天", all: "全部" };
const label = (vendor: string, en: boolean) => en ? vendor : vendorZh[vendor] || vendor;
const match = (value: string, query: string) => value.toLowerCase().includes(query.toLowerCase());
const sourceType = (url: string) => /github\.com/i.test(url) ? "GitHub" : /changelog/i.test(url) ? "Changelog" : /release.notes|releases/i.test(url) ? "Release Notes" : /blog/i.test(url) ? "官方博客" : /news/i.test(url) ? "官方新闻" : /docs|document|help/i.test(url) ? "官方文档" : "官方页面";

function Detail({ event, product, history, sources, close, en }: { event: AppEvent | null; product: Product | null; history: AppEvent[]; sources: Source[]; close: () => void; en: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const dialog = ref.current; if (dialog && !dialog.open) dialog.showModal(); }, []);
  const related = product ? history.filter(item => item.vendor === product.vendor && item.product === product.name) : [];
  const official = product ? sources.filter(item => item.vendor === product.vendor && (!item.product || match(product.name, item.product))) : [];
  return <dialog ref={ref} onClose={close} onClick={e => { if (e.target === ref.current) close(); }} className="ai-app-dialog">
    <div className="ai-app-dialog-body">
      <div className="ai-app-dialog-top"><span className="ai-app-eyebrow">{product ? (en ? "Product intelligence" : "产品情报档案") : (en ? "Official update" : "官方应用动态")}</span><button type="button" aria-label={en ? "Close" : "关闭详情"} onClick={close}><X size={20} /></button></div>
      {product ? <>
        <h2>{product.name}</h2><p className="ai-app-muted">{label(product.vendor, en)} · {categoryOf(product.name)} · {en ? "Tracked" : "已跟踪"}</p>
        <p className="ai-app-intro">{related[0]?.summary || (en ? "Official product page is tracked. No attributable update is available yet." : "已收录官方产品页，暂无可明确归属的更新。")}</p>
        <a className="ai-app-text-link" href={product.url} target="_blank" rel="noopener noreferrer">{en ? "Official product page" : "官方产品页"}<ExternalLink size={14} /></a>
        <h3>{en ? "Recent updates and timeline" : "最近更新与历史时间线"}</h3>
        {related.length ? related.map(item => <div key={item.event_id} className="ai-app-timeline"><time>{item.published_at || "日期待核实"}</time><strong>{item.title}</strong><p>{item.summary}</p><a href={item.source_url} target="_blank" rel="noopener noreferrer">{en ? "Evidence" : "官方来源"}<ArrowUpRight size={13} /></a></div>) : <p className="ai-app-muted">{en ? "No dated update linked to this product yet." : "暂无可核实的产品历史动态。"}</p>}
        {related.some(item => item.why_it_matters) && <><h3>{en ? "Change summary" : "产品变化总结"}</h3><p className="ai-app-intro">{related.slice(0, 3).filter(item => item.why_it_matters).map(item => item.why_it_matters).join("；")}</p></>}
        <h3>{en ? "Official sources" : "官方来源"}</h3>{official.length ? official.map(item => <a key={item.url} className="ai-app-source" href={item.url} target="_blank" rel="noopener noreferrer">{item.product || label(item.vendor, en)} · {sourceType(item.url)} · {new URL(item.url).hostname}<ArrowUpRight size={14} /></a>) : <p className="ai-app-muted">{en ? "Product page above is the verified official entry." : "以上产品页为已收录的官方入口。"}</p>}
      </> : event && <>
        <h2>{event.title}</h2><p className="ai-app-muted">{label(event.vendor, en)} · {event.product || (en ? "Vendor update" : "厂商动态")} · {event.published_at || "日期待核实"} · {event.event_type}</p>
        {event.summary && <p className="ai-app-intro">{event.summary}</p>}
        {event.what_changed && <><h3>{en ? "What changed" : "更新了什么"}</h3><p>{event.what_changed}</p></>}
        {event.why_it_matters && <><h3>{en ? "Why it matters" : "为何值得关注"}</h3><p>{event.why_it_matters}</p></>}
        {event.business_impact && event.business_impact !== event.why_it_matters && <><h3>{en ? "Business impact" : "业务影响"}</h3><p>{event.business_impact}</p></>}
        <h3>{en ? "Official evidence" : "官方来源"}</h3><a className="ai-app-source" href={event.source_url} target="_blank" rel="noopener noreferrer">{event.source_name}<ArrowUpRight size={14} /></a>
      </>}
    </div>
  </dialog>;
}

export function AgentLaunches() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [data, setData] = useState<Response>(() => peekJson<Response>(`${API}/api/agent-launches`) || { items: [], products: [], sources: [], vendors: [], refreshing: false });
  const [period, setPeriod] = useState<Period>("7days");
  const [vendor, setVendor] = useState("");
  const [category, setCategory] = useState("");
  const [eventType, setEventType] = useState<EventType | "">("");
  const [tab, setTab] = useState<"updates" | "products" | "sources">("updates");
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [limit, setLimit] = useState(20);
  const [loading, setLoading] = useState(() => !peekJson<Response>(`${API}/api/agent-launches`));
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    async function load(force = false) {
      try {
        const result = await cachedJson<Response>(`${API}/api/agent-launches`, force || retry > 0);
        if (active) { setData(result); setLoading(false); setError(false); }
      } catch { if (active) { setError(true); setLoading(false); } }
    }
    void load(); const timer = setInterval(() => void load(true), 60_000);
    return () => { active = false; clearInterval(timer); };
  }, [retry]);

  const allEvents = useMemo(() => buildEvents(data.items, data.products, data.sources), [data]);
  const searched = allEvents;
  const scoped = searched.filter(item => !vendor || item.vendor === vendor);
  const current = scoped.filter(item => inPeriod(item.published_at, period));
  const sevenDays = scoped.filter(item => inPeriod(item.published_at, "7days"));
  const dated = searched.filter(item => inPeriod(item.published_at, period) && /^\d{4}-\d{2}(?:-\d{2})?$/.test(item.published_at));
  const activity = vendorActivity(dated);
  const filteredProducts = data.products.filter(item => (!vendor || item.vendor === vendor) && (!category || categoryOf(item.name) === category));
  const filteredSources = data.sources.filter(item => !vendor || item.vendor === vendor);
  const visibleUpdates = current.filter(item => !eventType || item.event_type === eventType);
  const latest = allEvents.map(item => item.collected_at).filter(Boolean).sort().at(-1);
  const updated = latest ? new Date(latest).toLocaleString(en ? "en-US" : "zh-CN", { timeZone: "Asia/Shanghai" }) : allEvents[0]?.published_at || "—";
  const vendorCount = new Set([...data.products.map(item => item.vendor), ...data.sources.map(item => item.vendor)]).size;
  const metric = (n: number) => loading ? "—" : error ? "—" : n.toLocaleString();
  const productUpdates = (name: string, owner: string) => allEvents.filter(item => item.vendor === owner && item.product === name);
  const selectVendor = (name: string) => { setVendor(name); setLimit(20); };

  return <InsightPageShell artwork="/illustrations/ai-apps.png" title={en ? "AI Applications" : "AI 应用"} description={en ? "Track global AI products, platforms and applications to spot new capabilities, versions and vendor moves." : "跟踪全球 AI 产品、平台与应用动态，识别新能力、新版本与重点厂商动作。"} icon={<Boxes size={21} />} range={en ? ({ today: "Today", week: "This week", month: "This month", "7days": "Last 7 days", all: "All history" })[period] : periodNames[period]} updated={updated} status={error ? (en ? "Unavailable" : "读取失败") : data.refreshing ? (en ? "Updating" : "更新中") : (en ? "Data ready" : "数据已就绪")} metrics={[{ label: en ? "Updates in range" : "周期内应用动态", value: metric(current.length), note: `${periodNames[period]} · ${en ? "verified dates" : "已核实日期"}` }, { label: en ? "Tracked products & platforms" : "已纳入产品与平台", value: metric(data.products.length), note: en ? "Official product entries" : "官方产品入口" }, { label: en ? "Vendors / official sources" : "厂商 / 官方来源", value: loading || error ? "—" : `${vendorCount} / ${data.sources.length}`, note: en ? "Tracked directory" : "已登记清单" }, { label: en ? "Key updates · 7 days" : "近 7 天重点更新", value: metric(sevenDays.filter(item => item.importance_level === "重点").length), note: en ? "Source backed events" : "有来源依据的事件" }]}>
    <div className="ai-app-page">
        {error && <div className="ai-app-alert" role="alert">{en ? "Official application data is unavailable." : "官方应用数据暂时无法读取。"}<button type="button" onClick={() => setRetry(n => n + 1)}>{en ? "Retry" : "重试"}</button></div>}
    {loading && <div className="ai-app-loading" role="status">{en ? "Loading official application intelligence…" : "正在读取官方应用情报…"}</div>}
    <DailyAiBrief />
    {!loading && (data.items.length > 0 || data.products.length > 0 || !error) && <>
      <section className="ai-app-section"><div className="ai-app-section-head"><div><span className="ai-app-eyebrow">VENDOR WATCH</span><h2>{en ? "Vendor activity" : "厂商动态"}</h2><p>{en ? "Official events and attributable products in the current range" : `${periodNames[period]}官方更新、涉及产品与重点事件`}</p><div className="ai-app-periods" role="group" aria-label={en ? "Time range" : "时间筛选"}>{(Object.keys(periodNames) as Period[]).map(key => <button key={key} type="button" aria-pressed={period === key} onClick={() => setPeriod(key)}>{en ? ({ today: "Today", week: "This week", month: "This month", "7days": "Last 7 days", all: "All history" })[key] : periodNames[key]}</button>)}</div><button type="button" aria-pressed={!vendor} onClick={() => selectVendor("")}>{en ? "All vendors" : "全部"}</button></div></div>{activity.length ? <div className="ai-app-activity">{activity.map(item => <button type="button" key={item.vendor} aria-pressed={vendor === item.vendor} onClick={() => selectVendor(item.vendor)}><div className="ai-app-activity-head"><span className="ai-app-activity-logo">{vendorLogo(item.vendor) ? <Image src={vendorLogo(item.vendor)} alt="" width={28} height={28} unoptimized /> : <Boxes size={20} />}</span><strong>{label(item.vendor, en)}</strong></div><span><b>{item.count}</b>{en ? "updates" : "次更新"}</span><small>{item.products} {en ? "products" : "个产品"} · {item.important} {en ? "key events" : "个重点事件"}</small><time>{item.latest}</time></button>)}</div> : <p className="ai-app-empty">{en ? "No vendor activity in this range." : "当前周期暂无厂商动态。"}</p>}</section>

      <section className="ai-app-section" id="ai-app-catalog"><div className="ai-app-section-head"><div><span className="ai-app-eyebrow">TRACKED PRODUCTS</span><h2>{en ? "AI application catalog" : "AI 应用目录"}</h2><p>{en ? "Tracked products and platforms; the directory remains available across time ranges" : "查看已收录产品与平台；目录不随时间范围隐藏"}</p></div><span>{filteredProducts.length} {en ? "products" : "项产品"}</span></div><div className="ai-app-categories" role="group" aria-label={en ? "Product category" : "产品类型"}><button type="button" aria-pressed={!category} onClick={() => setCategory("")}>{en ? "All types" : "全部类型"}</button>{CATEGORIES.map(item => <button key={item} type="button" aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>)}</div><div className="ai-app-products">{filteredProducts.slice(0, 12).map(item => { const history = productUpdates(item.name, item.vendor); const currentCount = history.filter(event => inPeriod(event.published_at, period)).length; return <article key={`${item.vendor}:${item.name}`}><div className="ai-app-product-icon">{vendorLogo(item.vendor).startsWith("/") ? <Image src={vendorLogo(item.vendor)} alt="" width={25} height={25} unoptimized /> : <Boxes size={21} />}</div><h3>{item.name}</h3><span>{label(item.vendor, en)} · {categoryOf(item.name)}</span><p>{en ? `A tracked ${categoryOf(item.name)} product from ${label(item.vendor, en)}.` : `${label(item.vendor, en)}的${categoryOf(item.name)}产品，持续跟踪官方动态。`}</p><p className="ai-app-product-latest">{history[0]?.summary || (en ? "No attributable update yet." : "暂无可归属的最近动态。")}</p><div className="ai-app-tags"><span>{categoryOf(item.name)}</span><span>{history.length ? (en ? "Updated" : "有更新") : (en ? "Tracked" : "已跟踪")}</span></div><footer><small>{history[0]?.published_at || (en ? "No dated update" : "暂无更新日期")} · {periodNames[period]} {currentCount} {en ? "updates" : "次更新"}</small><button type="button" onClick={() => setSelectedProduct(item)}>{en ? "Details" : "查看详情"}<ArrowRight size={13} /></button></footer></article>; })}</div>{filteredProducts.length > 12 && <button type="button" className="ai-app-more" onClick={() => { setTab("products"); document.getElementById("ai-app-records")?.scrollIntoView({ behavior: "smooth" }); }}>{en ? `View all ${filteredProducts.length} products` : `查看全部 ${filteredProducts.length} 项产品`}<ArrowRight size={15} /></button>}{!filteredProducts.length && <p className="ai-app-empty">{en ? "No product matches these filters." : "没有符合条件的产品。"}</p>}</section>

      <section className="ai-app-section" id="ai-app-records"><div className="ai-app-section-head"><div><span className="ai-app-eyebrow">SOURCE RECORDS</span><h2 id="ai-app-latest">{tab === "updates" ? (en ? "Latest application updates" : "最新应用动态") : tab === "products" ? (en ? "Product directory" : "产品目录") : (en ? "Official source list" : "来源清单")}</h2><p>{en ? "Trace every record to its official source" : "每条记录都可回溯至官方来源"}</p></div></div><div className="ai-app-tabs" role="group" aria-label={en ? "Record views" : "记录视图"}>{(["updates", "products", "sources"] as const).map(item => <button type="button" key={item} aria-pressed={tab === item} onClick={() => { setTab(item); setLimit(20); }}>{item === "updates" ? (en ? "Official updates" : "官方动态") : item === "products" ? (en ? "Products" : "产品目录") : (en ? "Sources" : "来源清单")}</button>)}</div>
      {tab === "updates" && <><div className="ai-app-types" role="group" aria-label={en ? "Event type" : "事件类型"}><button type="button" aria-pressed={!eventType} onClick={() => setEventType("")}>{en ? "All" : "全部"}</button>{EVENT_TYPES.map(type => <button key={type} type="button" aria-pressed={eventType === type} onClick={() => setEventType(type)}>{type}</button>)}</div><div className="ai-app-table-wrap"><table className="ai-app-table"><thead><tr><th>时间</th><th>厂商</th><th>产品</th><th>事件标题</th><th>事件类型</th><th>来源</th><th>操作</th></tr></thead><tbody>{visibleUpdates.slice(0, limit).map(item => <tr key={item.event_id}><td>{item.published_at || (en ? "Date unverified" : "日期待核实")}</td><td>{label(item.vendor, en)}</td><td>{item.product || "—"}</td><td><a href={item.source_url} target="_blank" rel="noopener noreferrer">{item.title}</a>{item.summary && <small>{item.summary}</small>}</td><td><span className="ai-app-chip">{item.event_type}</span></td><td><a href={item.source_url} target="_blank" rel="noopener noreferrer">{item.source_name}<ArrowUpRight size={12} /></a></td><td><a href={item.source_url} target="_blank" rel="noopener noreferrer">{en ? "Open source" : "查看原文"}<ArrowUpRight size={13} /></a></td></tr>)}</tbody></table></div>{!visibleUpdates.length && <p className="ai-app-empty">{en ? "No dated update matches this range and filter." : "当前时间与筛选条件下暂无动态。"}</p>}{visibleUpdates.length > limit && <button type="button" className="ai-app-more" onClick={() => setLimit(limit + 20)}>{en ? "Load more" : "加载更多"}</button>}</>}
      {tab === "products" && <div className="ai-app-record-list">{filteredProducts.map(item => <button key={`${item.vendor}:${item.name}`} type="button" onClick={() => setSelectedProduct(item)}><strong>{item.name}</strong><span>{label(item.vendor, en)} · {categoryOf(item.name)}</span><small>{productUpdates(item.name, item.vendor)[0]?.published_at || "暂无更新日期"}</small><ArrowRight size={14} /></button>)}{!filteredProducts.length && <p className="ai-app-empty">没有符合条件的产品。</p>}</div>}
      {tab === "sources" && <div className="ai-app-record-list">{filteredSources.map(item => <a key={`${item.vendor}:${item.url}`} href={item.url} target="_blank" rel="noopener noreferrer"><strong>{item.product || `${label(item.vendor, en)}官方栏目`}</strong><span>{label(item.vendor, en)} · {sourceType(item.url)} · {new URL(item.url).hostname}</span><small>{{ matched: "有匹配动态", empty: "可读取", error: "暂不可读取", pending: "待检查" }[item.status || "pending"]}</small><ArrowUpRight size={14} /></a>)}{!filteredSources.length && <p className="ai-app-empty">没有符合条件的来源。</p>}</div>}
      </section>
    </>}
    {selectedProduct && <Detail product={selectedProduct} event={null} history={allEvents} sources={data.sources} en={en} close={() => setSelectedProduct(null)} />}
    </div>
  </InsightPageShell>;
}
