"use client";

import { ArrowUpRight } from "lucide-react";
import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import { usePreferences } from "@/lib/preferences";

type EventItem = { id: number; entity_key?: string; entity_type?: string; title: string; summary?: string | null; last_seen_at: string; source_url?: string; source_names?: string[]; source_count: number; scores?: { hot_score?: number }; vendor?: string; categories?: string[] };

export function EventStream({ scope, title, limit = 8 }: { scope: string; title: string; limit?: number }) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [items, setItems] = useState<EventItem[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API}/api/v2/events?business_scope=${encodeURIComponent(scope)}&limit=${limit}`, { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error("Events unavailable"); return response.json(); })
      .then(result => { setItems(result.items || []); setError(false); })
      .catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [scope, limit]);

  if (!items.length && !error) return null;
  return <section className="ui-card" aria-label={title}>
    <div className="flex items-center justify-between gap-3"><h2 className="type-h3 text-ink">{title}</h2>{!!items.length && <span className="font-mono text-xs text-ink-muted">{items.length}</span>}</div>
    {error && !items.length ? <p role="status" className="mt-3 text-sm text-warning">{en ? "Events are temporarily unavailable." : "事件暂时无法加载。"}</p> : <div className="mt-3 divide-y divide-grid">{items.map(item => { const external = /^https?:\/\//i.test(item.source_url || ""); const href = external ? item.source_url! : item.entity_type === "repository" && item.entity_key ? `/repositories/${encodeURIComponent(item.entity_key)}` : `/events/${item.id}`; return <a key={item.id} href={href} target="_blank" rel="noopener noreferrer" className="group grid gap-2 py-4 first:pt-1 sm:grid-cols-[1fr_auto]">
      <div><div className="flex flex-wrap items-center gap-2">{item.vendor && <span className="ui-tag">{item.vendor}</span>}{item.categories?.map(category => <span key={category} className="ui-tag">{category}</span>)}{item.source_names?.map(source => <span key={source} className="ui-tag">{source}</span>)}<h3 className="font-semibold text-ink group-hover:text-primary">{item.title}</h3></div>{item.summary && <p className="mt-2 line-clamp-2 text-sm leading-6 text-ink-secondary">{item.summary}</p>}<p className="mt-2 text-xs text-ink-muted">{en ? "Seen" : "最近发现"} {item.last_seen_at?.slice(0, 10)} · {item.source_count} {en ? "sources" : "个来源"}{item.scores?.hot_score != null ? ` · ${en ? "Score" : "热度分"} ${Math.round(item.scores.hot_score)}` : ""}</p></div><ArrowUpRight className="mt-1 h-4 w-4 text-ink-muted group-hover:text-primary" />
    </a>; })}</div>}
  </section>;
}
