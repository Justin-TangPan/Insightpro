"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, Radar } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { API } from "@/lib/api";

type Source = { name: string; url: string };
type Event = { id: string; title: string; vendor: string; happened_at: string; date_basis: string; type: string; summary: string; why: string; importance: number; sources: Source[]; board: string };
type HomeData = { as_of: string; today_count: number; event_count: number; priority_count: number; vendor_count: number; source_count: number; events: Event[]; highlights: Event[]; highlights_scope: "today" | "recent" };

const boardLinks: Record<string, string> = { github: "/insights/hotspots", apps: "/insights/app-launches", solutions: "/insights/solutions", community: "/insights/community", competitors: "/insights/competitors" };
const businessNames: Record<string, string> = { github: "技术生态", apps: "AI 应用", solutions: "解决方案", community: "社区洞察", competitors: "友商动态" };
const vendorNames = ["OpenAI", "Anthropic", "Google", "DeepSeek", "Meta", "华为", "阿里云"];
const categories = ["全部", ...Object.values(businessNames)];
const insightKinds = [
  { label: "厂商动态", href: "/insights/competitors", match: (event: Event) => event.board === "competitors" },
  { label: "技术趋势", href: "/insights/hotspots", match: (event: Event) => event.board === "github" || event.type === "模型" },
  { label: "市场机会", href: "/insights/app-launches", match: (event: Event) => /机会|增长|需求|落地|市场/.test(`${event.why} ${event.summary}`) },
  { label: "潜在风险", href: "/insights/solutions", match: (event: Event) => /风险|压力|成本|监管|安全|漏洞|价格上涨/.test(`${event.title} ${event.summary}`) },
];

function eventHref(event: Event) {
  return event.id.startsWith("event:") ? `/events/${event.id.slice(6)}` : boardLinks[event.board] || "/insights/hotspots";
}

function usefulSummary(event?: Event) {
  const summary = event?.summary?.trim();
  return summary && !/^(来源暂未提供摘要|暂无摘要|摘要待补充|solution content updated|content updated)[。…！!]*$/i.test(summary) ? summary : "";
}

function displayTitle(event: Event) {
  return event.title.replace(/^(?:Alibaba Cloud|Huawei Cloud|阿里云|华为云)方案更新[：:]\s*/i, "").replace(/[_\s]*(?:部署教程|deployment guide)$/i, "");
}

function dateLabel(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("zh-CN", { month: "long", day: "numeric", timeZone: "Asia/Shanghai" }).format(date);
}

function businessOf(event: Event) {
  return businessNames[event.board] || "友商动态";
}

function eventTypeOf(event: Event) {
  // shortcut: 接口未单独提供动作字段，暂从现有标题归纳；有标准事件动作字段时改用该字段。
  const text = `${event.type} ${event.title}`;
  if (/融资|并购|收购/.test(text)) return "融资并购";
  if (/政策|监管|合规/.test(text)) return "政策监管";
  if (/合作|联合|伙伴/.test(text)) return "合作";
  if (event.board === "community") return "社区热点";
  if (event.board === "github") return /发布|release|开源/i.test(text) ? "开源发布" : "开源动态";
  if (event.board === "solutions") return "方案更新";
  if (/版本|升级|更新|update/i.test(text)) return "版本更新";
  if (/发布|推出|上线|launch|release/i.test(text)) return "产品发布";
  return event.board === "competitors" ? "厂商动作" : event.board === "apps" ? "产品动态" : "技术进展";
}

function vendorGroup(vendor: string) {
  if (!vendor || vendor === "行业动态") return "";
  if (/华为|huawei/i.test(vendor)) return "华为";
  if (/阿里云|alibaba/i.test(vendor)) return "阿里云";
  return vendorNames.find(name => vendor.toLowerCase().includes(name.toLowerCase())) || "其他厂商";
}

function vendorLogo(vendor: string) {
  if (/阿里|Alibaba/i.test(vendor)) return "/brand-logos/alibabacloud.svg";
  if (/华为|Huawei/i.test(vendor)) return "/brand-logos/huawei.svg";
  if (/OpenAI/i.test(vendor)) return "/brand-logos/openai.svg";
  if (/Anthropic/i.test(vendor)) return "/brand-logos/anthropic.svg";
  if (/Google/i.test(vendor)) return "/brand-logos/google.svg";
  if (/Meta/i.test(vendor)) return "/brand-logos/meta.svg";
  return "";
}

export default function HomePage() {
  const [data, setData] = useState<HomeData | null>(null);
  const [failed, setFailed] = useState(false);
  const [filter, setFilter] = useState("全部");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API}/api/radar/intelligence`, { signal: controller.signal })
      .then(response => response.ok ? response.json() : Promise.reject(new Error(String(response.status))))
      .then((result: HomeData) => setData(result))
      .catch(error => { if (error.name !== "AbortError") setFailed(true); });
    return () => controller.abort();
  }, []);

  const events = useMemo(() => data?.events ?? [], [data]);
  const keypoints = useMemo(() => {
    const seen = new Set<string>();
    const candidates = [...(data?.highlights ?? []), ...events].filter(event => usefulSummary(event) && !/[_\s]*(部署教程|deployment guide)$/i.test(event.title));
    const varied = candidates.filter(event => {
      const key = event.vendor || event.board;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
    return [...varied, ...candidates.filter(event => !varied.includes(event))].slice(0, 5);
  }, [data, events]);
  const focus = keypoints.find(event => usefulSummary(event)) ?? keypoints[0];
  const secondary = keypoints.filter(event => event.id !== focus?.id).slice(0, 4);
  const insights = insightKinds.map(kind => ({ ...kind, event: events.find(event => kind.match(event) && usefulSummary(event)) }));
  const radar = [...vendorNames, "其他厂商"].map(name => ({ name, count: events.filter(event => vendorGroup(event.vendor) === name).length }));
  const radarMax = Math.max(1, ...radar.map(item => item.count));
  const latest = events.filter(event => {
    const day = Date.parse(`${event.happened_at.slice(0, 10)}T00:00:00+08:00`);
    const asOf = Date.parse(data?.as_of ?? "");
    return Number.isFinite(day) && Number.isFinite(asOf) && asOf - day < 7 * 86400000 && asOf >= day;
  });
  const filtered = filter === "全部" ? latest : latest.filter(event => businessOf(event) === filter);
  const updateTime = data?.as_of ? new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Shanghai" }).format(new Date(data.as_of)) : "";

  return <div className="intel-home" id="top">
    <section className="intel-hero" aria-labelledby="intel-headline">
      <div className="intel-hero-main">
        <div className="intel-dateline"><time>{data?.as_of ? new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", day: "numeric", weekday: "long", timeZone: "Asia/Shanghai" }).format(new Date(data.as_of)) : "今日情报"}</time><span>最近更新 {updateTime || "读取中"}</span><span className="intel-live"><i />每日更新</span></div>
        <p className="intel-kicker">INSIGHTPRO · AI 商业情报</p>
        <h1 id="intel-headline">{focus ? <>今日关注：<em>{displayTitle(focus)}</em></> : failed ? "情报暂时无法读取" : data ? "今日情报正在整理" : "正在汇总今日情报"}</h1>
        <p className="intel-hero-summary">{focus ? usefulSummary(focus) || focus.why : failed ? "请稍后刷新页面重试。" : data ? "当前没有可核实的重点事件，继续关注最新情报。" : "正在从技术生态、AI 应用、解决方案、社区和友商动态汇总近期变化。"}</p>
        {data?.highlights_scope === "recent" && <p className="intel-scope-note">今日暂无新增重点事件，当前展示近期重点。</p>}
        <div className="intel-metrics" aria-label="情报统计">
          {[[data?.event_count, "近 30 天情报"], [data?.priority_count, "重点情报"], [data?.vendor_count, "重点厂商"], [data?.source_count, "覆盖来源"]].map(([value, label]) => <div key={label}><strong>{value ?? "—"}</strong><span>{label}</span></div>)}
        </div>
      </div>
      <aside className="intel-keypoints" aria-labelledby="intel-keypoints-title">
        <div className="intel-section-head"><h2 id="intel-keypoints-title">今日要点</h2><a href="#intel-latest">查看全部 <ArrowRight size={14} /></a></div>
        {data?.highlights_scope === "recent" && <p className="intel-muted">今日暂无新增，以下为近期重点。</p>}
        {keypoints.length ? <ol>{keypoints.map((event, index) => <li key={event.id}><span className="intel-number">{String(index + 1).padStart(2, "0")}</span><div><Link href={eventHref(event)}>{displayTitle(event)}</Link><p>{usefulSummary(event) || event.why}</p><span className="intel-point-meta"><b>{businessOf(event)}</b><span>{eventTypeOf(event)}</span><time>{dateLabel(event.happened_at)}</time></span></div></li>)}</ol> : <p className="intel-empty">{failed ? "情报加载失败。" : data ? "暂无可展示的要点。" : "正在加载…"}</p>}
      </aside>
    </section>

    <section className="intel-insights" aria-labelledby="intel-insights-title">
      <div className="intel-section-head"><h2 id="intel-insights-title">核心洞察</h2><span>来自近 30 天的情报信号</span></div>
      <div className="intel-insight-grid">{insights.map((item, index) => <Link key={item.label} href={item.event ? eventHref(item.event) : item.href} className="intel-insight"><span className={`intel-insight-icon icon-${index}`}>{["↗", "◇", "✦", "!"][index]}</span><div><span className="intel-insight-label">{item.label}</span><h3>{item.event?.why || "暂无可核实的新变化"}</h3><p>{item.event ? `${businessOf(item.event)} · ${item.event.title}` : "进入对应模块查看完整情报。"}</p></div><ArrowUpRight size={15} /></Link>)}</div>
    </section>

    <section className="intel-focus" aria-labelledby="intel-focus-title">
      <div className="intel-section-head"><h2 id="intel-focus-title">今日焦点</h2><span>{data?.highlights_scope === "recent" ? "近期重点事件" : "值得继续阅读的事件"}</span></div>
      {focus ? <div className="intel-focus-grid">
        <Link className="intel-focus-visual" href={eventHref(focus)} aria-label={`阅读${focus.title}`}><span className="intel-visual-grid"/><span className="intel-visual-orbit"/><span className="intel-visual-core">{vendorLogo(focus.vendor) ? <Image src={vendorLogo(focus.vendor)} alt="" width={150} height={90} unoptimized /> : <Radar size={80} strokeWidth={1.2} />}</span><span className="intel-visual-caption">INSIGHT / {focus.vendor || "AI INTELLIGENCE"}</span></Link>
        <article className="intel-focus-story"><div className="intel-focus-overline"><span>01</span><span>{businessOf(focus)} / {eventTypeOf(focus)}</span></div><h3><Link href={eventHref(focus)}>{displayTitle(focus)}</Link></h3><p>{usefulSummary(focus) || focus.why}</p><div className="intel-story-meta"><time>{dateLabel(focus.happened_at)}</time><span>{focus.sources.length} 个来源</span><span>{focus.vendor || "行业情报"}</span><span>{eventTypeOf(focus)}</span></div><Link className="intel-read-more" href={eventHref(focus)}>阅读详情 <ArrowRight size={15} /></Link></article>
        <div className="intel-secondary">{secondary.map((event, index) => <article key={event.id}><span className="intel-number">{String(index + 2).padStart(2, "0")}</span><div><Link href={eventHref(event)}>{displayTitle(event)}</Link><p>{usefulSummary(event) || event.why}</p><small>{businessOf(event)} · {eventTypeOf(event)} · {dateLabel(event.happened_at)} · {event.sources.length} 个来源</small></div><ArrowUpRight size={15}/></article>)}</div>
      </div> : <p className="intel-empty">{failed ? "焦点事件加载失败。" : "暂无可展示的焦点事件。"}</p>}
    </section>

    <section className="intel-radar" aria-labelledby="intel-radar-title">
      <div className="intel-section-head"><h2 id="intel-radar-title">情报雷达</h2><span>近 30 天 · 厂商提及量</span></div>
      <div className="intel-radar-body"><p>跟踪主要 AI 厂商的近期情报出现频次。点击厂商动态查看完整内容。</p><div className="intel-radar-bars">{radar.map(item => <div key={item.name}><span>{item.name}</span><i aria-hidden="true"><b style={{ width: `${item.count / radarMax * 100}%` }} /></i><strong>{item.count}</strong></div>)}</div></div>
      <Link href="/insights/competitors" className="intel-radar-link">查看友商动态 <ArrowRight size={14}/></Link>
    </section>

    <section className="intel-latest" id="intel-latest" aria-labelledby="intel-latest-title">
      <div className="intel-section-head"><h2 id="intel-latest-title">最新情报</h2><span>近 7 天</span></div>
      <div className="intel-filters" role="group" aria-label="筛选业务分类">{categories.map(category => <button key={category} type="button" className={category === filter ? "is-active" : ""} onClick={() => setFilter(category)} aria-pressed={category === filter}>{category}</button>)}</div>
      {filtered.length ? <ol className="intel-feed">{filtered.slice(0, 12).map(event => <li key={event.id}><time>{dateLabel(event.happened_at)}</time><span>{businessOf(event)}</span><div><Link href={eventHref(event)}>{event.title}</Link><p>{usefulSummary(event) || event.why}</p></div><small>{eventTypeOf(event)} · {event.vendor || "行业情报"} · {event.sources.length} 个来源</small><ArrowUpRight size={15}/></li>)}</ol> : <p className="intel-empty">{failed ? "情报加载失败，请稍后重试。" : data ? "该分类近 7 天暂无情报。" : "正在加载最新情报…"}</p>}
    </section>
  </div>;
}
