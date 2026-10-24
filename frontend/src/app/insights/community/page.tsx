"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, MessagesSquare, RefreshCw } from "lucide-react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { SectionHeader } from "@/components/section-header";
import { DailyBoardInsight } from "@/components/daily-board-insight";

type Insight = { source: string; title: string; summary: string; url: string; topic_category?: string; relevance?: string; published_at?: string | null; observed_at?: string };
type Event = { id: number; title: string; summary?: string | null; last_seen_at: string; source_names: string[]; source_count: number; scores: Record<string, number> };
type LegacyResponse = { items: Insight[]; count: number; sources: { name: string; count: number }[] };

export default function CommunityInsightsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [legacy, setLegacy] = useState<LegacyResponse>({ items: [], count: 0, sources: [] });
  const [source, setSource] = useState("全部");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(false);
  const load = useCallback(async () => {
    try {
      const response = await fetch(`${API}/api/v2/events?business_scope=community_insights&limit=100`);
      if (!response.ok) throw new Error("V2 events unavailable");
      const result = await response.json();
      const items: Event[] = result.items || [];
      setEvents(items);
      if (items.length) { setLegacy({ items: [], count: 0, sources: [] }); return; }
    } catch { setEvents([]); }
    const response = await fetch(`${API}/api/community/insights`);
    if (!response.ok) throw new Error("社区热点加载失败");
    setLegacy(await response.json());
  }, []);
  useEffect(() => { void Promise.resolve().then(load).catch(() => setError(true)).finally(() => setLoading(false)); }, [load]);
  const sources = useMemo(() => events.length
    ? Array.from(new Set(events.flatMap(item => item.source_names || []))).map(name => ({ name, count: events.filter(item => item.source_names?.includes(name)).length }))
    : legacy.sources, [events, legacy.sources]);
  const items = useMemo(() => events.length
    ? events.filter(item => source === "全部" || item.source_names?.includes(source))
    : legacy.items.filter(item => source === "全部" || item.source === source), [events, legacy.items, source]);
  const refresh = async () => {
    setRefreshing(true);
    try {
      const response = await authenticatedFetch(`${API}/api/community/insights/refresh`, { method: "POST" });
      if (!response.ok) throw new Error("刷新失败");
      await response.json();
      await load();
      setError(false);
    } catch { setError(true); } finally { setRefreshing(false); }
  };

  return <div className="page-stack intel-subpage">
    <SectionHeader compact icon={<MessagesSquare className="h-5 w-5" />} title="AI 社区热点" action={<button type="button" onClick={refresh} disabled={refreshing} className="ui-button-secondary"><RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />{refreshing ? "刷新中" : "刷新热点"}</button>} />
    <DailyBoardInsight board="community" />
    {error && <div role="alert" className="ui-card flex items-center justify-between gap-3 text-sm text-warning"><span>社区热点加载失败。</span><button type="button" className="ui-button-secondary" onClick={() => { setError(false); setLoading(true); void load().catch(() => setError(true)).finally(() => setLoading(false)); }}>重试</button></div>}
    <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="社区来源">{sources.map(item => <button key={item.name} type="button" onClick={() => setSource(item.name)} aria-pressed={source === item.name} className={`ui-card min-h-28 text-left ${source === item.name ? "border-primary bg-primary-soft/40" : ""}`}><p className="text-sm font-semibold text-ink">{item.name}</p><p className="mt-3 font-mono text-2xl font-semibold text-primary">{item.count}</p></button>)}</section>
    <div className="flex items-center justify-between"><h2 className="type-h3 text-ink">{source === "全部" ? "全部 AI 热点" : source}</h2>{source !== "全部" && <button type="button" onClick={() => setSource("全部")} className="ui-link">查看全部</button>}</div>
    <section className="ui-card divide-y divide-grid">{loading ? <div className="h-72 animate-shimmer rounded-xl" /> : items.length ? items.map((item, index) => {
      const isEvent = "id" in item;
      const title = item.title;
      const summary = item.summary;
      const labels = isEvent ? item.source_names : [item.source];
      const date = isEvent ? item.last_seen_at?.slice(0, 10) : item.published_at?.slice(0, 10) || item.observed_at?.slice(0, 10);
      const content = <><span className="font-mono text-xs text-ink-muted">{String(index + 1).padStart(2, "0")}</span><div><div className="flex flex-wrap items-center gap-2">{labels?.map(name => <span key={name} className="ui-tag">{name}</span>)}<h3 className="font-semibold text-ink group-hover:text-primary">{title}</h3></div>{summary && <p className="mt-2 line-clamp-2 text-sm leading-6 text-ink-secondary">{summary}</p>}<p className="mt-2 text-xs text-ink-muted">{date ? `${isEvent ? "最近发现" : "热榜采集于"} ${date}` : "当前热榜话题"}{isEvent && item.source_count > 1 ? ` · ${item.source_count} 个来源` : ""}</p></div><ArrowUpRight className="mt-1 h-4 w-4 text-ink-muted group-hover:text-primary" /></>;
      return isEvent ? <Link key={item.id} href={`/events/${item.id}`} className="group grid gap-3 py-5 first:pt-0 last:pb-0 sm:grid-cols-[52px_1fr_auto]">{content}</Link> : <a key={`${item.source}-${item.url}-${index}`} href={item.url} target="_blank" rel="noopener noreferrer" className="group grid gap-3 py-5 first:pt-0 last:pb-0 sm:grid-cols-[52px_1fr_auto]">{content}</a>;
    }) : <div className="py-16 text-center"><MessagesSquare className="mx-auto h-7 w-7 text-ink-muted" /><p className="mt-3 text-sm text-ink-secondary">当前来源暂未获取到 AI 相关热点</p></div>}</section>
  </div>;
}
