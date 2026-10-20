"use client";

import Link from "next/link";
import { ArrowUpRight, Radar } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { API } from "@/lib/api";

type Source = { name: string; url: string };
type Event = { id: string; title: string; short_title: string; vendor: string; happened_at: string; type: string; summary: string; why: string; importance: number; sources: Source[]; related: { id: string; title: string }[]; is_multi_source: boolean };
type Board = { key: string; name: string; href: string; count: number; change: string; unit: string };
type RadarData = { as_of: string; today_count: number; priority_count: number; vendor_count: number; source_count: number; vendors: string[]; events: Event[]; highlights: Event[]; highlights_scope: "today" | "week"; boards: Board[] };

const TYPE_COLORS: Record<string, string> = {
  "产品发布": "#8fb3ff", "AI 应用": "#67d7c1", "模型": "#c1a3ff", "解决方案": "#f1bd6b",
  "GitHub 技术": "#a7b3c2", "社区动态": "#e99bb5", "商业动作": "#ff896f",
};
const RINGS = [{ radius: 62, label: "24 小时内" }, { radius: 151, label: "1–3 天" }, { radius: 242, label: "3–7 天" }];
const cx = 450, cy = 350;

function eventRadius(day: string, today: string) {
  const age = Math.max(0, Math.floor((Date.parse(`${today}T12:00:00`) - Date.parse(`${day}T12:00:00`)) / 86_400_000));
  return age < 1 ? 62 : age <= 3 ? 151 : 242;
}

export default function HomePage() {
  const [data, setData] = useState<RadarData | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    fetch(`${API}/api/radar/intelligence`)
      .then(response => response.ok ? response.json() : Promise.reject())
      .then((result: RadarData) => { if (active) setData(result); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, []);

  const events = data?.events ?? [];
  const today = data?.as_of.slice(0, 10) ?? "";
  const selected = events.find(event => event.id === selectedId) ?? null;
  const placed = useMemo(() => {
    const counts = new Map<string, number>();
    const vendorCounts = new Map<string, number>();
    const visible = events.filter(event => {
      const count = vendorCounts.get(event.vendor) ?? 0;
      if (count >= 3) return false;
      vendorCounts.set(event.vendor, count + 1);
      return true;
    });
    return visible.map(event => {
      const vendorIndex = Math.max(0, data?.vendors.indexOf(event.vendor) ?? 0);
      const countKey = `${vendorIndex}:${eventRadius(event.happened_at, today)}`;
      const index = counts.get(countKey) ?? 0;
      counts.set(countKey, index + 1);
      const offset = ((index % 3) - 1) * 0.09;
      const angle = -Math.PI / 2 + vendorIndex * (2 * Math.PI / (data?.vendors.length || 10)) + offset;
      const base = eventRadius(event.happened_at, today);
      const radius = base === 62 ? 58 - index * 14 : base === 151 ? 144 - index * 28 : 239 - index * 32;
      return { event, x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius, angle };
    });
  }, [events, data?.vendors, today]);

  const choose = (id: string) => setSelectedId(current => current === id ? null : id);
  const focusEvent = selected ?? null;
  const defaultItems = data?.highlights ?? [];

  return <div className="page-stack intel-home">
    <header className="intel-topline">
      <div className="intel-title"><Radar size={19} aria-hidden="true" /><h1>商业情报雷达</h1><span>{data ? `更新至 ${data.as_of.replace("T", " ")}` : "近 7 天"}</span></div>
      <div className="intel-metrics" aria-label="情报概览">
        {[[data?.today_count, "今日新增"], [data?.priority_count, "重点情报"], [data?.vendor_count, "重点友商"], [data?.source_count, "覆盖来源"]].map(([value, label]) => <div className="intel-metric" key={label}><strong>{data ? value : "—"}</strong><span>{label}</span></div>)}
      </div>
    </header>

    <section className="intel-main" aria-label="商业情报雷达与重点情报">
      <div className="intel-radar-panel">
        <div className="intel-panel-head"><div><h2>重点友商动态</h2><p>方向代表友商 · 半径代表发生时间 · 点大小代表重要程度</p></div><span className="intel-event-count">{events.length} 条情报</span></div>
        <div className="intel-radar-wrap">
          <svg className="intel-radar" viewBox="0 0 900 700" role="group" aria-label="近七天重点友商商业情报雷达">
            {RINGS.map((ring, index) => <g key={ring.label}><circle cx={cx} cy={cy} r={ring.radius} className="intel-ring" /><text x={cx + 8} y={cy - ring.radius + 15} className="intel-ring-label">{ring.label}</text></g>)}
            {(data?.vendors ?? []).map((vendor, index) => {
              const angle = -Math.PI / 2 + index * (2 * Math.PI / (data?.vendors.length || 10));
              const x = cx + Math.cos(angle) * 254, y = cy + Math.sin(angle) * 254;
              const lx = cx + Math.cos(angle) * 292, ly = cy + Math.sin(angle) * 292;
              const anchor = Math.cos(angle) > .25 ? "start" : Math.cos(angle) < -.25 ? "end" : "middle";
              return <g key={vendor}><line x1={cx} y1={cy} x2={x} y2={y} className="intel-spoke" /><text x={lx} y={ly} textAnchor={anchor} dominantBaseline="middle" className="intel-vendor">{vendor}</text></g>;
            })}
            <circle cx={cx} cy={cy} r="4" className="intel-center" />
            {placed.map(({ event, x, y, angle }) => {
              const color = TYPE_COLORS[event.type] ?? TYPE_COLORS["商业动作"];
              const labelX = x + (Math.cos(angle) >= 0 ? 9 : -9);
              const anchor = Math.cos(angle) >= 0 ? "start" : "end";
              return <g key={event.id} role="button" tabIndex={0} aria-label={`${event.title}，${event.vendor}，${event.type}`} aria-pressed={selectedId === event.id} className={`intel-point ${selectedId === event.id ? "is-selected" : ""}`} onClick={() => choose(event.id)} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choose(event.id); } }}>
                <title>{`${event.title} · ${event.vendor} · ${event.happened_at} · ${event.type}`}</title>
                <circle cx={x} cy={y} r={selectedId === event.id ? 7 : event.importance >= 5 ? 6 : event.importance >= 4 ? 5 : 4} fill={color} />
                <text x={labelX} y={y + 3} textAnchor={anchor} className="intel-point-label" paintOrder="stroke" stroke="var(--color-surface-elevated)" strokeWidth="3">{event.short_title}</text>
              </g>;
            })}
          </svg>
        </div>
        <div className="intel-legend"><span className="intel-time-legend">由近及远：24 小时内 · 1–3 天 · 3–7 天</span><div>{Object.entries(TYPE_COLORS).map(([type, color]) => <span key={type}><i style={{ background: color }} />{type}</span>)}</div></div>
      </div>

      <aside className="intel-detail-panel" aria-live="polite">
        {focusEvent ? <>
          <div className="intel-detail-head"><span className="intel-eyebrow">情报详情</span><button type="button" onClick={() => setSelectedId(null)} className="intel-clear">返回今日重点</button></div>
          <h2 className="intel-detail-title">{focusEvent.title}</h2>
          <div className="intel-tags"><span>{focusEvent.vendor}</span><span style={{ color: TYPE_COLORS[focusEvent.type] }}>{focusEvent.type}</span><time>{focusEvent.happened_at}</time></div>
          <section className="intel-copy"><h3>情报摘要</h3><p>{focusEvent.summary}</p></section>
          <section className="intel-copy"><h3>为什么值得关注</h3><p>{focusEvent.why}</p></section>
          <section className="intel-copy"><h3>来源{focusEvent.is_multi_source ? " · 多个来源" : ""}</h3><div className="intel-sources">{focusEvent.sources.map(source => <a key={`${source.name}-${source.url}`} href={source.url} target="_blank" rel="noreferrer">{source.name}<ArrowUpRight size={13} /></a>)}</div></section>
          {focusEvent.related.length > 0 && <section className="intel-copy"><h3>关联情报</h3><div className="intel-related">{focusEvent.related.map(item => <button key={item.id} type="button" onClick={() => setSelectedId(item.id)}>{item.title}</button>)}</div></section>}
        </> : <>
          <div className="intel-detail-head"><span className="intel-eyebrow">{data?.highlights_scope === "week" ? "近 7 日重点情报" : "今日重点情报"}</span><span className="intel-muted">点击雷达点查看详情</span></div>
          <div className="intel-highlights">{defaultItems.length ? defaultItems.map((event, index) => <button type="button" className="intel-highlight" key={event.id} onClick={() => setSelectedId(event.id)}>
            <span className="intel-rank">{String(index + 1).padStart(2, "0")}</span><span className="intel-highlight-body"><strong>{event.title}</strong><span>{event.vendor} · {event.type} · {event.happened_at}</span><small>{event.why}</small></span><ArrowUpRight size={15} />
          </button>) : <p className="intel-empty">{failed ? "情报暂时无法加载，请稍后重试。" : "近 7 天暂无可展示情报。"}</p>}</div>
        </>}
      </aside>
    </section>

    <section className="intel-boards" aria-label="业务来源最新变化">{(data?.boards ?? []).map(board => <article key={board.key} className="intel-board"><div className="intel-board-number"><strong>{data ? board.count : "—"}</strong><span>{board.unit}</span></div><div className="intel-board-copy"><h2>{board.name}</h2><p>{board.change}</p></div><Link href={board.href} aria-label={`查看${board.name}`}><ArrowUpRight size={16} /></Link></article>)}</section>
  </div>;
}
