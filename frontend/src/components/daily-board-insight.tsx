"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight, RotateCw } from "lucide-react";
import { API } from "@/lib/api";
import { usePreferences } from "@/lib/preferences";

type Board = "github" | "apps" | "solutions" | "competitors" | "community";
type Summary = {
  judgment: string;
  analysis_mode?: "source_only";
  focus: { title: string; url: string; meta: string; why: string; analysis: string; impact: string; caveat?: string } | null;
};
type Insight = { date: string; count: number; metrics: { label: string; value: number }[]; summary: Summary; sources: { title: string; url: string }[] };

export function DailyBoardInsight({ board, compact = false }: { board: Board; compact?: boolean }) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [data, setData] = useState<Insight | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const load = () => fetch(`${API}/api/boards/${board}/daily-insight`, { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error("Insight unavailable"); return response.json(); })
      .then(value => { setData(value); setError(false); setLoading(false); })
      .catch(() => { if (!controller.signal.aborted) { setError(true); setLoading(false); } });
    void load();
    const timer = setInterval(() => { void load(); }, 60_000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [board, retry]);

  const summary = data?.summary;
  const focus = summary?.focus;
  if (compact) return <div className="ecosystem-ai-judgment" role="status"><span>{en ? "AI perspective" : "AI 趋势判断"}</span><p>{loading ? (en ? "Analyzing recent signals…" : "正在分析近期信号…") : error ? (en ? "Recent assessment unavailable" : "近期判断暂不可用") : summary?.judgment || (en ? "No assessment yet" : "暂无趋势判断")}</p>{focus?.url && <a href={focus.url} target="_blank" rel="noopener noreferrer">{en ? "Key signal" : "重点信号"}<ArrowUpRight size={13} /></a>}</div>;
  return <section aria-labelledby={`${board}-daily-insight`} className="intel-summary">
    <header className="intel-summary__header"><h2 id={`${board}-daily-insight`}>{board === "community" ? (en ? "Current community snapshot" : "当前社区热榜") : (en ? "Recent intelligence · 7 days" : "近期情报 · 近 7 天")}</h2><div>{loading ? <span>{en ? "Loading" : "正在加载"}</span> : error ? <span>{en ? "Temporarily unavailable" : "暂不可用"}</span> : data && <span>{data.date || (en ? "Date unavailable" : "日期待补充")} · {data.count ? `${data.count} ${en ? "sources" : "条依据"}` : (en ? "No source items" : "暂无来源条目")}</span>}{!!data?.metrics?.length && <div className="intel-summary__metrics">{data.metrics.map(metric => <span key={metric.label}><b>{metric.value}</b>{metric.label}</span>)}</div>}</div></header>
    {loading && <div role="status" aria-label={en ? "Loading analysis" : "正在加载分析"} className="intel-summary__skeleton"><i /><i /><i /></div>}
    {error && !loading && <div role="alert" className="intel-summary__error"><span>{en ? "Could not load recent intelligence." : "近期情报加载失败。"}</span><button type="button" onClick={() => { setLoading(true); setRetry(value => value + 1); }} className="ui-button-secondary"><RotateCw className="h-3.5 w-3.5" />{en ? "Retry" : "重试"}</button></div>}
    {!loading && !error && summary && <>
      <div className="intel-summary__judgment"><span>{en ? "Overall assessment" : "总体判断"}</span><p>{summary.judgment}</p></div>
      {summary.analysis_mode === "source_only" && <p role="status" className="intel-summary__note">{en ? "Source summary only; deeper analysis is pending." : "目前仅依据来源归纳，深入分析待更新。"}</p>}
      {focus && <article className="intel-summary__focus">
        <div className="intel-summary__focus-head"><span>{en ? "Focus to examine" : "本期重点分析"}</span><a href={focus.url} target="_blank" rel="noopener noreferrer">{focus.title}<ArrowUpRight className="h-3.5 w-3.5 shrink-0" /></a>{focus.meta && <small>{focus.meta}</small>}</div>
        <div className="intel-summary__focus-body"><p><strong>{en ? "Why it matters" : "为何值得关注"}</strong>{focus.why}</p><p><strong>{en ? "What changed" : "事件解读"}</strong>{focus.analysis}</p><p><strong>{en ? "Business impact" : "业务影响"}</strong>{focus.impact}</p></div>
        {focus.caveat && <p className="intel-summary__focus-caveat">{en ? "Evidence boundary" : "证据边界"}：{focus.caveat}</p>}
      </article>}
    </>}
    {board === "community" && data && <p className="intel-summary__note">{en ? "Current trend snapshot; topic publication dates are unverified." : "社区数据为当前热榜快照，话题发布日期未逐条核实。"}</p>}
    {!!data?.sources.length && <details className="intel-summary__sources"><summary>{en ? "Analysis sources" : "分析依据"} · {data.sources.length}</summary><ol>{data.sources.map(item => <li key={item.url}><a href={item.url} target="_blank" rel="noopener noreferrer">{item.title}<ArrowUpRight className="h-3 w-3" /></a></li>)}</ol></details>}
  </section>;
}
