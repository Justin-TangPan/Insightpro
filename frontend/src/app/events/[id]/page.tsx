"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";
import { usePreferences } from "@/lib/preferences";

type Evidence = { id: number; source_name: string; authority: string; title: string; canonical_url: string; published_at?: string; observed_at: string };
type Metric = { metric_key: string; metric_value: number; observed_at: string; source_key: string };
type Trend = { stars_delta?: number; stars_velocity?: number; ranking_change?: number; mention_growth?: number; comment_growth?: number; download_growth?: number };
type EventRecord = { id: number; title: string; summary?: string; event_type: string; business_scopes: string[]; tags: string[]; scores: Record<string, unknown>; status: string; first_seen_at: string; last_seen_at: string; evidence: Evidence[]; metrics: Metric[]; trends?: { stale: boolean; windows: Record<string, Trend> } };

const windows: Record<string, [string, string]> = { "1h": ["1 小时", "1 hour"], "6h": ["6 小时", "6 hours"], "24h": ["24 小时", "24 hours"], "7d": ["7 天", "7 days"], "30d": ["30 天", "30 days"] };
const trendMetrics = [["stars_delta", "Stars"], ["stars_velocity", "Stars / hour"], ["ranking_change", "Rank change"], ["mention_growth", "Mention growth"], ["comment_growth", "Comment growth"], ["download_growth", "Download growth"]] as const;
const chineseMetric: Record<string, string> = { "Stars / hour": "Stars / 小时", "Rank change": "排名变化", "Mention growth": "提及变化", "Comment growth": "评论变化", "Download growth": "下载变化" };

export default function EventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [event, setEvent] = useState<EventRecord | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    fetch(API + "/api/v2/events/" + encodeURIComponent(id))
      .then(response => response.ok ? response.json() : Promise.reject(new Error(String(response.status))))
      .then(data => { if (active) setEvent(data); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [id]);

  return <div className="page-stack">
    <SectionHeader compact badge={en ? "Event" : "事件详情"} title={event?.title || (en ? "Loading event" : "正在读取事件")} />
    <Link href="/" className="ui-link inline-flex w-fit items-center gap-2 text-sm"><ArrowLeft size={15} />{en ? "Back to radar" : "返回情报雷达"}</Link>
    {failed ? <div role="alert" className="ui-card text-sm text-ink-muted">{en ? "Event unavailable." : "事件不存在或暂时无法读取。"}</div> : !event ? <div className="ui-card h-32 animate-pulse" /> : <>
      <section className="ui-card">
        <div className="flex flex-wrap gap-2">{[event.event_type, ...event.business_scopes, ...event.tags].map(tag => <span key={tag} className="ui-tag">{tag}</span>)}</div>
        {event.summary && <p className="mt-5 max-w-4xl text-base leading-7 text-ink-secondary">{event.summary}</p>}
        <p className="mt-4 text-xs text-ink-muted">{en ? "First seen" : "首次观察"} {new Date(event.first_seen_at).toLocaleString(en ? "en" : "zh-CN")} · {en ? "Last seen" : "最近观察"} {new Date(event.last_seen_at).toLocaleString(en ? "en" : "zh-CN")}</p>
      </section>
      {event.trends?.windows && <section className="ui-card">
        <div className="flex items-center justify-between gap-3"><h2 className="type-h3">{en ? "Change over time" : "变化趋势"}</h2>{event.trends.stale && <span className="ui-tag ui-tag-warning">{en ? "Data is stale" : "数据已过期"}</span>}</div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{Object.entries(event.trends.windows).map(([window, values]) => <div key={window} className="rounded-xl bg-surface-subtle p-3"><p className="text-xs text-ink-muted">{windows[window]?.[en ? 1 : 0] || window}</p><dl className="mt-2 space-y-1 text-sm">{trendMetrics.filter(([key]) => values[key] != null).map(([key, label]) => <div key={key} className="flex justify-between gap-2"><dt className="text-ink-muted">{en ? label : (chineseMetric[label] || label)}</dt><dd className="font-mono text-ink">{Number(values[key]).toLocaleString()}</dd></div>)}</dl></div>)}</div>
      </section>}
      {event.metrics.length > 0 && <section className="ui-card"><h2 className="type-h3">{en ? "Observed metrics" : "观测指标"}</h2><div className="mt-4 divide-y divide-grid">{event.metrics.slice(0, 12).map((metric, index) => <div key={metric.metric_key + metric.observed_at + index} className="grid grid-cols-[1fr_auto_auto] gap-4 py-2.5 text-sm"><span className="text-ink-secondary">{metric.metric_key}</span><strong className="font-mono text-ink">{Number(metric.metric_value).toLocaleString()}</strong><time className="text-xs text-ink-muted">{new Date(metric.observed_at).toLocaleString(en ? "en" : "zh-CN")}</time></div>)}</div></section>}
      <section className="ui-card"><div className="flex items-center justify-between"><h2 className="type-h3">{en ? "Evidence" : "来源证据"}</h2><span className="text-xs text-ink-muted">{event.evidence.length}</span></div><div className="mt-3 divide-y divide-grid">{event.evidence.map(item => <a key={item.id} href={item.canonical_url} target="_blank" rel="noreferrer" className="flex items-start justify-between gap-4 py-3"><span><span className="text-xs text-ink-muted">{item.source_name} · {item.authority}</span><strong className="mt-1 block text-sm text-ink">{item.title}</strong><time className="mt-1 block text-xs text-ink-muted">{item.published_at ? new Date(item.published_at).toLocaleString(en ? "en" : "zh-CN") : (en ? "Observed " : "采集于 ") + new Date(item.observed_at).toLocaleString(en ? "en" : "zh-CN")}</time></span><ExternalLink size={14} className="mt-1 shrink-0 text-ink-muted" /></a>)}</div></section>
    </>}
  </div>;
}
