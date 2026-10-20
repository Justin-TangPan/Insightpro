"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowUpRight, MessagesSquare, RefreshCw } from "lucide-react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { SectionHeader } from "@/components/section-header";

type Insight = { source: string; title: string; summary: string; url: string };
type Response = { items: Insight[]; count: number; sources: { name: string; count: number }[] };

export default function CommunityInsightsPage() {
  const [data, setData] = useState<Response>({ items: [], count: 0, sources: [] });
  const [source, setSource] = useState("全部");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const load = useCallback(async () => {
    const response = await fetch(`${API}/api/community/insights`);
    if (!response.ok) throw new Error("社区热点加载失败");
    setData(await response.json());
  }, []);
  useEffect(() => { void Promise.resolve().then(load).finally(() => setLoading(false)); }, [load]);
  const items = useMemo(() => source === "全部" ? data.items : data.items.filter(item => item.source === source), [data.items, source]);
  const refresh = async () => {
    setRefreshing(true);
    try {
      const response = await authenticatedFetch(`${API}/api/community/insights/refresh`, { method: "POST" });
      if (!response.ok) throw new Error("刷新失败");
      setData(await response.json());
    } finally { setRefreshing(false); }
  };

  return <div className="page-stack">
    <SectionHeader badge="Community Signals" title="社区洞察" subtitle="聚合知乎、百度、腾讯云开发者社区与 CSDN 的中文技术热点，观察开发者正在讨论什么。" action={<button type="button" onClick={refresh} disabled={refreshing} className="ui-button-secondary"><RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />{refreshing ? "刷新中" : "刷新热点"}</button>} />
    <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="社区来源">{data.sources.map(item => <button key={item.name} type="button" onClick={() => setSource(item.name)} aria-pressed={source === item.name} className={`ui-card min-h-28 text-left ${source === item.name ? "border-primary bg-primary-soft/40" : ""}`}><p className="text-sm font-semibold text-ink">{item.name}</p><p className="mt-3 font-mono text-2xl font-semibold text-primary">{item.count}</p></button>)}</section>
    <div className="flex items-center justify-between"><div><p className="swiss-kicker text-primary">Developer Pulse</p><h2 className="mt-1 type-h2 text-ink">{source === "全部" ? "全部技术热点" : source}</h2></div>{source !== "全部" && <button type="button" onClick={() => setSource("全部")} className="ui-link">查看全部</button>}</div>
    <section className="ui-card divide-y divide-grid">{loading ? <div className="h-72 animate-shimmer rounded-xl" /> : items.length ? items.map((item, index) => <a key={`${item.source}-${item.url}-${index}`} href={item.url} target="_blank" rel="noopener noreferrer" className="group grid gap-3 py-5 first:pt-0 last:pb-0 sm:grid-cols-[52px_1fr_auto]"><span className="font-mono text-xs text-ink-muted">{String(index + 1).padStart(2, "0")}</span><div><div className="flex flex-wrap items-center gap-2"><span className="ui-tag">{item.source}</span><h3 className="font-semibold text-ink group-hover:text-primary">{item.title}</h3></div>{item.summary && <p className="mt-2 line-clamp-2 text-sm leading-6 text-ink-secondary">{item.summary}</p>}</div><ArrowUpRight className="mt-1 h-4 w-4 text-ink-muted group-hover:text-primary" /></a>) : <div className="py-16 text-center"><MessagesSquare className="mx-auto h-7 w-7 text-ink-muted" /><p className="mt-3 text-sm text-ink-secondary">当前来源暂未获取到技术热点</p></div>}</section>
  </div>;
}
