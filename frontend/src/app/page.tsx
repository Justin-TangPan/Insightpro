"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, Radar } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { API } from "@/lib/api";
import { eventImage } from "@/lib/vendor-image";
import { selectRecentFocus } from "@/lib/home-focus";
import { businessNames, displayTitle, usefulSummary } from "@/lib/home-content";
import { DailyAiBrief } from "@/components/daily-ai-brief";

type Source = { name: string; url: string };
type Event = { image_url?: string; id: string; title: string; vendor: string; happened_at: string; date_basis: string; type: string; summary: string; why: string; importance: number; sources: Source[]; board: string };
type HomeData = { as_of: string; event_count: number; priority_count: number; vendor_count: number; source_count: number; events: Event[] };

const boardLinks: Record<string, string> = { github: "/insights/hotspots", apps: "/insights/app-launches", solutions: "/insights/solutions", community: "/insights/community", competitors: "/insights/competitors" };
const categories = ["全部", ...Object.values(businessNames)];

function eventHref(event: Event) {
  return event.sources.find(source => /^https?:\/\//i.test(source.url))?.url || (event.id.startsWith("event:") ? `/events/${event.id.slice(6)}` : boardLinks[event.board] || "/insights/hotspots");
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

export default function HomePage() {
  const [data, setData] = useState<HomeData | null>(null);
  const [failed, setFailed] = useState(false);
  const [filter, setFilter] = useState("全部");
  const [failedFocusImage, setFailedFocusImage] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API}/api/radar/intelligence`, { signal: controller.signal })
      .then(response => response.ok ? response.json() : Promise.reject(new Error(String(response.status))))
      .then((result: HomeData) => setData(result))
      .catch(error => { if (error.name !== "AbortError") setFailed(true); });
    return () => controller.abort();
  }, []);

  const events = useMemo(() => data?.events ?? [], [data]);
  const keypoints = useMemo(() => selectRecentFocus(events, data?.as_of || "", 5), [data?.as_of, events]);
  const focusItem = keypoints[0];
  const focus = focusItem?.event;
  const secondary = keypoints.slice(1);
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
        <div className="intel-dateline"><time>近 7 天优先 · 不足时扩展至 30 天</time><span>数据更新 {updateTime || "读取中"}</span><span className="intel-live"><i />{failed ? "读取失败" : data ? "数据已就绪" : "读取中"}</span></div>
        <p className="intel-kicker">INSIGHTPRO · AI 商业情报</p>
        <div className="intel-focus-heading"><div><h1 id="intel-headline">近期焦点</h1>{focus && <h2>{displayTitle(focus)}</h2>}</div>{focus && <Link className="intel-focus-image" href={eventHref(focus)} target="_blank" rel="noopener noreferrer" aria-label={`查看${displayTitle(focus)}`}><Radar className="intel-focus-fallback" size={35} />{eventImage(focus.image_url, focus.vendor) && failedFocusImage !== focus.id && <Image src={eventImage(focus.image_url, focus.vendor)} alt={focus.vendor || "发布方"} width={80} height={80} unoptimized onError={() => setFailedFocusImage(focus.id)} />}</Link>}</div>
        {focus ? <><div className="intel-focus-meta"><span className="intel-focus-type">{focusItem.type}</span><span>{focus.vendor || "行业动态"}</span><span>{businessOf(focus)}</span><time>{focusItem.dateBasis === "version" ? "版本日期" : focusItem.dateBasis === "source" ? "来源日期" : focus.board === "github" || focusItem.dateBasis === "observed" ? "发现" : "发布"} · {dateLabel(focusItem.date)}</time></div><div className="intel-focus-brief"><p><strong>发布了什么</strong>{usefulSummary(focus) || "来源暂未提供发布摘要，请查看原始来源。"}</p><p><strong>为何值得关注</strong>{focus.why || "可从来源内容核实其影响与后续采用情况。"}</p></div><div className="intel-focus-actions"><span>{focus.sources.length} 个来源{focus.sources[0]?.name ? ` · ${focus.sources[0].name}` : ""}</span><Link href={eventHref(focus)} target="_blank" rel="noopener noreferrer">{focus.sources.some(source => /^https?:\/\//i.test(source.url)) ? "查看原文" : "查看详情"} <ArrowUpRight size={14} /></Link></div></> : <p className="intel-hero-summary">{failed ? "请稍后刷新页面重试。" : data ? "近 30 天暂无可核实的新发布或重要能力变化。" : "正在从技术生态、AI 应用、解决方案、社区和友商动态汇总近期变化。"}</p>}
        <div className="intel-metrics" aria-label="情报统计">
          {[[data?.event_count, "近 30 天情报"], [data?.priority_count, "重点情报"], [data?.vendor_count, "重点厂商"], [data?.source_count, "覆盖来源"]].map(([value, label]) => <div key={label}><strong>{value ?? "—"}</strong><span>{label}</span></div>)}
        </div>
      </div>
      <aside className="intel-keypoints" aria-labelledby="intel-keypoints-title">
        <div className="intel-section-head"><h2 id="intel-keypoints-title">次重点</h2><a href="#intel-latest">浏览近期动态 <ArrowRight size={14} /></a></div>
        {secondary.length ? <ol>{secondary.map((item, index) => { const event = item.event; return <li key={event.id}><span className="intel-number">{String(index + 2).padStart(2, "0")}</span><div><Link href={eventHref(event)} target="_blank" rel="noopener noreferrer">{displayTitle(event)}</Link><p>{usefulSummary(event) || event.why}</p><span className="intel-point-meta"><b>{item.type}</b><span>{event.vendor || "行业动态"}</span><time>{item.dateBasis === "version" ? "版本日期" : item.dateBasis === "source" ? "来源日期" : event.board === "github" || item.dateBasis === "observed" ? "发现" : "发布"} · {dateLabel(item.date)}</time></span></div></li>; })}</ol> : <p className="intel-empty">{failed ? "情报加载失败。" : data ? "近期暂无其他高价值焦点。" : "正在加载…"}</p>}
      </aside>
    </section>

    <DailyAiBrief />

    <section className="intel-latest" id="intel-latest" aria-labelledby="intel-latest-title">
      <div className="intel-section-head"><h2 id="intel-latest-title">最新情报</h2><span>近 7 天</span></div>
      <div className="intel-filters" role="group" aria-label="筛选业务分类">{categories.map(category => <button key={category} type="button" className={category === filter ? "is-active" : ""} onClick={() => setFilter(category)} aria-pressed={category === filter}>{category}</button>)}</div>
      {filtered.length ? <ol className="intel-feed">{filtered.slice(0, 12).map(event => <li key={event.id}><time>{dateLabel(event.happened_at)}</time><span>{businessOf(event)}</span><div><Link href={eventHref(event)} target="_blank" rel="noopener noreferrer">{event.title}</Link><p>{usefulSummary(event) || event.why}</p></div><small>{eventTypeOf(event)} · {event.vendor || "行业情报"} · {event.sources.length} 个来源</small><ArrowUpRight size={15}/></li>)}</ol> : <p className="intel-empty">{failed ? "情报加载失败，请稍后重试。" : data ? "该分类近 7 天暂无情报。" : "正在加载最新情报…"}</p>}
    </section>
  </div>;
}
