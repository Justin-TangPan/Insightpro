"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight, Bot, CircleDollarSign, Cpu, Network, Server, Sparkles, TrendingUp } from "lucide-react";
import { API } from "@/lib/api";
import { cachedJson, peekJson } from "@/lib/client-data-cache";

type Judgment = { icon: string; title: string; detail: string };
type BriefItem = {
  title: string;
  category: string;
  summary: string;
  commentary: string;
  source_name: string;
  source_url: string;
  published_at: string;
  vendor: string;
  original_event_id: string | null;
};
type Brief = {
  date: string;
  status: string;
  version?: number;
  generated_at?: string;
  fallback_for?: string;
  generation_warning?: string;
  note?: string;
  recent_judgments: Judgment[];
  headline: BriefItem | null;
  quick_reads: BriefItem[];
};

const url = `${API}/api/daily-ai-brief`;
const viewAllHref = "/insights/hotspots";

const judgmentIcon = (icon: string) => {
  switch (icon) {
    case "trend": return TrendingUp;
    case "model": return Cpu;
    case "agent": return Bot;
    case "infra": return Server;
    case "commercial": return CircleDollarSign;
    case "eco": return Network;
    default: return Sparkles;
  }
};

function dateLabel(value: string) {
  const date = new Date(`${value.slice(0, 10)}T00:00:00+08:00`);
  return Number.isNaN(date.getTime())
    ? value.slice(0, 10)
    : new Intl.DateTimeFormat("zh-CN", { month: "long", day: "numeric", timeZone: "Asia/Shanghai" }).format(date);
}

function displayTitle(item: BriefItem) {
  const chinese = (item.title.match(/[\u3400-\u9fff]/g) || []).length;
  if ((chinese >= 3 && item.title.length < 29) || !/[\u3400-\u9fff]/.test(item.summary)) return item.title;
  return item.summary.split(/[，。；：]/, 1)[0].trim() || item.title;
}

export function DailyAiBrief() {
  const [data, setData] = useState<Brief | null>(() => peekJson<Brief>(url) || null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    const load = (force = false) => void cachedJson<Brief>(url, force)
      .then(value => { if (active) { setData(value); setError(false); } })
      .catch(() => { if (active) setError(true); });
    load();
    const timer = setInterval(() => load(true), 60_000);
    return () => { active = false; clearInterval(timer); };
  }, []);

  const stale = data?.fallback_for && data.fallback_for !== data.date;

  return <section className="intel-summary intel-brief" aria-labelledby="daily-ai-brief-title">
    <header className="intel-brief__header">
      <div className="intel-brief__title">
        <h2 id="daily-ai-brief-title">每日 AI 洞察简讯</h2>
        <span className="intel-brief__eyebrow">由 Agent 每日精选近期高价值 AI 情报，并生成近日判断、头条摘要与快速点评</span>
      </div>
      <div className="intel-brief__actions">
        {data && <time>{data.date}{stale ? ` · 上一成功版本` : ""}</time>}
        <a className="intel-brief__all" href={viewAllHref}>查看全部 <ArrowUpRight size={14} /></a>
      </div>
    </header>
    {(stale || data?.generation_warning) && <p className="intel-brief__fallback" role="status">{data?.generation_warning || `今日简讯尚未更新，当前展示 ${data?.date} 的上一成功版本。`}</p>}

    {error ? <p className="intel-brief__empty" role="alert">简讯暂时无法读取，请稍后重试。</p> :
      !data ? <div role="status" aria-label="正在加载简讯" className="intel-summary__skeleton"><i /><i /><i /></div> :
        !data.recent_judgments.length && !data.headline && !data.quick_reads.length ? <p className="intel-brief__empty">{data.note || "今日简讯正在生成，暂无可核实内容。"}</p> :
          <div className="intel-brief__grid">
            <article className="intel-brief__col intel-brief__headline" aria-labelledby="daily-brief-headline">
              <h3 id="daily-brief-headline">头条详解</h3>
              {data.headline ? <>
                <div className="intel-brief__headline-meta"><span className="intel-brief__category" data-category={data.headline.category}>{data.headline.category}</span><div className="intel-brief__meta"><span>{data.headline.source_name}</span><time>{dateLabel(data.headline.published_at)}</time></div></div>
                <h4 className="intel-brief__headline-title">{displayTitle(data.headline)}</h4>
                <p className="intel-brief__body intel-brief__abstract"><strong>摘要</strong>{data.headline.summary}</p>
                <p className="intel-brief__body intel-brief__opinion"><strong>Agent 点评</strong>{data.headline.commentary}</p>
                <a className="intel-brief__source intel-brief__source--primary" href={data.headline.source_url} target="_blank" rel="noopener noreferrer">查看原文 <ArrowUpRight size={14} /></a>
              </> : <p className="intel-brief__empty">{data.note || "近 7 天暂无可核实的重要头条。"}</p>}
            </article>

            <aside className="intel-brief__col intel-brief__judgments" aria-labelledby="daily-brief-judgments">
              <h3 id="daily-brief-judgments">近日判断</h3>
              {data.recent_judgments.length ? <ol>{data.recent_judgments.map((judgment, index) => {
                const Icon = judgmentIcon(judgment.icon);
                return <li key={judgment.title}><span className="intel-brief__judgment-icon"><Icon size={15} /><small>{String(index + 1).padStart(2, "0")}</small></span><div><h4>{judgment.title}</h4><p>{judgment.detail}</p></div></li>;
              })}</ol> : <p className="intel-brief__empty">近期暂未形成明显趋势。</p>}
            </aside>

            <aside className="intel-brief__col intel-brief__quick" aria-labelledby="daily-brief-quick">
              <h3 id="daily-brief-quick">今日快读</h3>
              {data.quick_reads.length ? <ol>{data.quick_reads.map((item, index) => <li key={`${item.source_url}:${item.title}`}>
                <span className="intel-brief__number">{String(index + 2).padStart(2, "0")}</span>
                <div className="intel-brief__quick-body">
                  <span className="intel-brief__category" data-category={item.category}>{item.category}</span>
                  <h4 title={item.title}>{displayTitle(item)}</h4>
                  <p className="intel-brief__quick-summary">{item.summary}</p>
                  <p className="intel-brief__quick-opinion"><strong>点评 · </strong>{item.commentary}</p>
                  <div className="intel-brief__quick-footer"><div className="intel-brief__meta"><span>{item.source_name}</span><time>{dateLabel(item.published_at)}</time></div><a className="intel-brief__source" href={item.source_url} target="_blank" rel="noopener noreferrer">查看原文 <ArrowUpRight size={13} /></a></div>
                </div>
              </li>)}</ol> : <p className="intel-brief__empty">今日暂无其他高价值快读。</p>}
            </aside>
          </div>}
  </section>;
}
