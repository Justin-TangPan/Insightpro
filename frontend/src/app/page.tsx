"use client";

import Link from "next/link";
import { ArrowUpRight, Radar, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import { radarMarkerPositions } from "@/lib/radar-markers";
import { usePreferences } from "@/lib/preferences";
import { useAuth } from "@/components/auth-provider";
import { ExpandableText } from "@/components/expandable-text";
import type { Intelligence } from "@/lib/intelligence";

type Signal = { title: string; summary: string; tagline?: string; why?: string; category: string; source: string; url: string; day: string; intelligence?: Intelligence };
type Category = { name: string; current: number; previous: number; direction: string };
type Snapshot = { as_of: string; today_count: number; recent_count: number; categories: Category[]; top_signals: Signal[]; apps: Signal[] };

export default function HomePage() {
  const { preferences } = usePreferences();
  const { user } = useAuth();
  const en = preferences.language === "en";
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    void fetch(`${API}/api/radar/snapshot`)
      .then(response => response.ok ? response.json() : Promise.reject())
      .then(setSnapshot)
      .catch(() => setError(true));
  }, []);

  const categories = snapshot?.categories || [];
  const rising = categories.filter(item => item.direction === "↑");
  const lead = snapshot?.apps[0];
  const radarItems = [
    ...(snapshot?.apps ?? []).map((signal, index) => ({ signal, code: `A${index + 1}`, target: `radar-app-${index + 1}`, kind: "app" as const })),
    ...(snapshot?.top_signals ?? []).map((signal, index) => ({ signal, code: `V${index + 1}`, target: `radar-vendor-${index + 1}`, kind: "vendor" as const })),
  ];
  const markerPositions = radarMarkerPositions(radarItems.map(item => item.signal), categories.map(item => item.name));

  return <div className="radar-home page-stack">
    <section className="radar-board" aria-labelledby="radar-heading">
      <div className="radar-board__head">
        <div>
          <p className="radar-kicker">INSIGHTPRO / AI RADAR</p>
          <h1 id="radar-heading" className="mt-3 text-[clamp(2rem,3.8vw,3.6rem)] font-semibold leading-[1.08] tracking-[-.055em] text-ink">{en ? "What's worth watching in AI?" : "最近 AI 有什么值得关注？"}</h1>
        </div>
        <p className="radar-board__date">{snapshot ? `${snapshot.as_of} · ${en ? "Last 7 days" : "近 7 天"}` : error ? (en ? "Radar data is temporarily unavailable" : "雷达数据暂不可用") : (en ? "Loading today's brief…" : "正在整理今日简报…")}</p>
      </div>

      <div className="radar-board__metrics">{[
        [snapshot?.today_count, en ? "Signals today" : "今日采集"],
        [snapshot?.recent_count, en ? "Signals this week" : "近 7 天信号"],
        [snapshot?.apps.length, en ? "AI apps" : "AI 应用"],
        [rising.length, en ? "Rising directions" : "升温方向"],
      ].map(([value, label]) => <div key={label} className="radar-board__metric"><strong className="tabular-nums">{snapshot ? value : "—"}</strong><span>{label}</span></div>)}</div>

      <div className="radar-board__main">
        <div className="radar-board__plot">
          <div className="radar-board__plot-head"><div className="flex items-center gap-2"><Radar className="h-4 w-4 text-primary" aria-hidden="true" /><h2 className="text-sm font-semibold text-ink">{en ? "AI Radar · featured signals" : "AI 雷达 · 代表情报"}</h2></div><span className="text-xs text-ink-muted">{en ? "Signal volume" : "信号量"}</span></div>
          <div className="radar-board__chart">
            <svg className="radar-board__map" viewBox="-190 -190 380 380" role="group" aria-label={en ? "AI intelligence radar: five directions and linked signals" : "AI 情报雷达：五个方向及可点击的情报点"}>
              {[46, 88, 130].map(radius => <circle key={radius} r={radius} className="radar-board__ring" />)}
              {categories.map((category, index) => {
                const angle = -Math.PI / 2 + index * 2 * Math.PI / categories.length;
                const x = Math.cos(angle), y = Math.sin(angle);
                return <g key={category.name}>
                  <line x1="0" y1="0" x2={x * 132} y2={y * 132} className="radar-board__spoke" />
                  <text x={x * 158} y={y * 158} textAnchor={x > 0.2 ? "start" : x < -0.2 ? "end" : "middle"} dominantBaseline="central" className="radar-board__category">{category.name === "商业化与产业" ? "商业化" : category.name}</text>
                  <text x={x * 158} y={y * 158 + 15} textAnchor={x > 0.2 ? "start" : x < -0.2 ? "end" : "middle"} dominantBaseline="central" className="radar-board__count">{category.current} {en ? "signals" : "条情报"}</text>
                </g>;
              })}
              <circle r="20" className="radar-board__hub" />
              <text y="1" textAnchor="middle" dominantBaseline="central" className="radar-board__hub-text">AI</text>
              {radarItems.map((item, index) => { const position = markerPositions[index]; return position && <a key={item.code} href={`#${item.target}`} aria-label={`${item.code} ${item.signal.title}`}><title>{item.signal.title}</title><g className={`radar-board__marker radar-board__marker--${item.kind}`} transform={`translate(${position.x} ${position.y})`}><rect x="-15" y="-13" width="30" height="26" rx="13" /><text textAnchor="middle" dominantBaseline="central">{item.code}</text></g></a>; })}
            </svg>
          </div>
          <div className="radar-board__legend"><span><i className="radar-board__legend-current" />{en ? "Signal" : "情报点"}</span><span><i className="radar-board__legend-app" />{en ? "AI app" : "AI 应用"}</span></div>
          <p className="mt-3 text-center text-[11px] leading-4 text-ink-muted">{en ? "Each spoke is a topic. Select a numbered point to read the signal below." : "每个方向代表一类主题；点击编号查看对应情报。"}</p>
        </div>
        <div className="radar-board__side">
          <div className="flex items-center justify-between gap-3"><h2 className="text-sm font-semibold text-ink">{en ? "On the radar" : "雷达情报"}</h2><span className="text-xs text-ink-muted">{en ? "Select to view" : "点击查看"}</span></div>
          {radarItems.length ? <div className="mt-3">{radarItems.map(item => <a key={item.code} href={`#${item.target}`} className="radar-board__signal"><span className={`radar-board__signal-code radar-board__signal-code--${item.kind}`}>{item.code}</span><span className="min-w-0 flex-1"><span className="block truncate text-xs font-medium text-ink" title={item.signal.title}>{item.signal.title}</span><span className="block text-[11px] text-ink-muted">{item.signal.source} · {item.signal.category}</span></span><ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-ink-muted" aria-hidden="true" /></a>)}</div> : <p className="mt-4 text-xs text-ink-muted">{en ? "No featured signals yet." : "暂无代表情报。"}</p>}
          <p className="mt-auto pt-4 text-[11px] leading-4 text-ink-muted">{en ? "Outline compares signal volume with the prior seven days; volume is not a trend score." : "轮廓对比前 7 天信号量；信号量不等于趋势强度。"}</p>
        </div>
      </div>
    </section>

    <section aria-labelledby="apps-heading"><div className="mb-4 flex flex-wrap items-end justify-between gap-3"><div><p className="radar-kicker">DISCOVER / OFFICIAL AI APPS</p><h2 id="apps-heading" className="mt-1 text-2xl font-semibold tracking-tight text-ink">{en ? "AI apps" : "AI 应用"}</h2></div><Link href="/insights/app-launches" className="text-xs font-semibold text-primary hover:underline">{en ? "View all" : "查看全部"} <ArrowUpRight className="inline h-3.5 w-3.5" aria-hidden="true" /></Link></div>
      {snapshot?.apps.length ? <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{snapshot.apps.map((app, index) => <article key={app.intelligence?.key || app.url} id={`radar-app-${index + 1}`} className="radar-home-card flex scroll-mt-24 flex-col"><div className="flex items-center justify-between gap-2"><span className="radar-tag">A{index + 1} · {app.source}</span><span className="text-xs text-ink-muted">{app.day ? app.day.slice(5) : ""}</span></div><h3 className="mt-4 text-lg font-semibold text-ink">{app.intelligence?.title || app.title}</h3><ExpandableText lines={3} en={en} className="mt-2 flex-1 text-sm leading-6 text-ink-secondary">{app.intelligence?.analysis || app.summary}</ExpandableText>{app.url && <a href={app.intelligence?.source || app.url} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline">{en ? "Official source" : "查看官方原文"}<ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" /></a>}</article>)}</div> : <div className="radar-home-card text-sm text-ink-muted">{error ? (en ? "Official app feed is unavailable." : "官方应用信息暂不可用。") : snapshot ? (en ? "No official AI app matched the current sources." : "当前来源暂无符合条件的官方 AI 应用。") : (en ? "Finding official apps…" : "正在发现官方应用…")}</div>}
    </section>

    <section aria-labelledby="signals-heading"><div className="mb-4 flex flex-wrap items-end justify-between gap-3"><div><p className="radar-kicker">INDUSTRY / SIGNALS</p><h2 id="signals-heading" className="mt-1 text-2xl font-semibold tracking-tight text-ink">{en ? "Vendor launch signals" : "厂商产品发布信号"}</h2></div><span className="text-xs text-ink-muted">{en ? "Existing competitor feed" : "现有友商动态采集"}</span></div>
      {snapshot?.top_signals.length ? <div className="grid gap-3 lg:grid-cols-3">{snapshot.top_signals.map((item, index) => <article key={item.intelligence?.key || `${item.title}-${index}`} id={`radar-vendor-${index + 1}`} className="radar-home-card scroll-mt-24"><div className="flex items-center justify-between gap-2"><span className="radar-tag">V{index + 1} · {item.category}</span><span className="text-xs text-ink-muted">{item.day.slice(5)}</span></div><h3 className="mt-4 text-base font-semibold leading-6 text-ink">{item.intelligence?.title || item.title}</h3><ExpandableText lines={3} en={en} className="mt-2 text-sm leading-6 text-ink-secondary">{item.intelligence?.brief || item.summary || (en ? "Brief pending" : "来源摘要待补充")}</ExpandableText>{item.intelligence?.analysis && <div className="mt-3 border-t border-grid pt-3"><span className="text-xs font-semibold text-primary">{en ? "AI analysis" : "AI 分析"}</span><ExpandableText lines={3} en={en} className="mt-1 text-xs leading-5 text-ink-secondary">{item.intelligence.analysis}</ExpandableText></div>}<p className="mt-3 text-xs text-ink-muted">{item.source}</p>{item.url && <a href={item.intelligence?.source || item.url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline">{en ? "Verify source" : "核实来源"}<ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" /></a>}</article>)}</div> : <div className="radar-home-card text-sm text-ink-muted">{en ? "No clear official launch signal in the current sample." : "当前样本中暂无明确的官方发布信号。"}</div>}
    </section>

    {user && <section className="radar-home-card flex flex-wrap items-center justify-between gap-5"><div><div className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-primary" aria-hidden="true" /><h2 className="text-base font-semibold text-ink">{en ? "Suggested next step" : "建议下一步"}</h2></div><p className="mt-2 max-w-3xl text-sm leading-6 text-ink-secondary">{lead ? (en ? `Review "${lead.title}" with its official analysis.` : `查看「${lead.title}」的官方应用与分析。`) : (en ? "Review original sources before choosing a research topic." : "先核实原始来源，再决定需要深入研究的对象。")}</p></div><Link href="/workbench/ai" className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-primary-dark px-5 text-sm font-semibold text-white hover:opacity-90">{en ? "Research in AI workspace" : "进入 AI 工作区研究"}<ArrowUpRight className="h-4 w-4" aria-hidden="true" /></Link></section>}
  </div>;
}
