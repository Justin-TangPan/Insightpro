"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowUpRight, ExternalLink } from "lucide-react";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";
import { usePreferences } from "@/lib/preferences";
import { AgentAction } from "@/components/agent-action";

type Repository = {
  entity: { entity_key: string; entity_type: string; canonical_name: string; canonical_url?: string; metadata: Record<string, unknown> };
  events: { id: number; title: string; summary?: string; event_type: string; scores: Record<string, unknown>; last_seen_at: string }[];
  evidence: { id: number; title: string; canonical_url?: string; source_name: string; authority: string; observed_at: string; published_at?: string }[];
  metrics: { metric_key: string; metric_value: number; observed_at: string; source_key: string }[];
  trends: { stale: boolean; windows: Record<string, Record<string, number | null>> };
};

const windows: Record<string, [string, string]> = { "1h": ["1 小时", "1 hour"], "6h": ["6 小时", "6 hours"], "24h": ["24 小时", "24 hours"], "7d": ["7 天", "7 days"], "30d": ["30 天", "30 days"] };

export default function RepositoryDetailPage() {
  const { entity_key } = useParams<{ entity_key: string }>();
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [data, setData] = useState<Repository | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    fetch(`${API}/api/v2/entities/${encodeURIComponent(entity_key)}`)
      .then(response => response.ok ? response.json() : Promise.reject(new Error(String(response.status))))
      .then(value => { if (active) setData(value); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [entity_key]);

  const repository = data?.entity;
  const trends = data?.trends;
  const evaluation = data?.events.map(event => event.scores.business_evaluation as {
    total?: number; level?: string; summary?: string; reasoning?: string; recommendation?: string;
    d1?: number; d2?: number; d3?: number; d4?: number;
    technical_assessment?: Partial<Record<"engineering_maturity" | "innovation" | "deployability", {
      score: number | null; reasoning: string; evidence_keys: string[];
    }>>;
  } | undefined).find(Boolean);
  return <div className="page-stack">
    <SectionHeader compact badge={en ? "Repository" : "技术项目"} title={repository?.canonical_name || (en ? "Loading repository" : "正在读取技术项目")} />
    <Link href="/insights/hotspots" className="ui-link inline-flex w-fit items-center gap-2 text-sm"><ArrowLeft size={15} />{en ? "Back to Technology Ecosystem" : "返回技术生态"}</Link>
    {failed ? <div role="alert" className="ui-card text-sm text-ink-muted">{en ? "Repository unavailable." : "项目不存在或暂时无法读取。"}</div> : !data ? <div className="ui-card h-32 animate-pulse" /> : repository?.entity_type !== "repository" ? <div role="alert" className="ui-card text-sm text-ink-muted">{en ? "This entity is not a repository." : "该实体不是代码仓库。"}</div> : <>
      <section className="ui-card">
        <div className="flex flex-wrap items-center gap-2"><span className="ui-tag">{String(repository.metadata.language || (en ? "Language not reported" : "未标注语言"))}</span>{repository.canonical_url && <a href={repository.canonical_url} target="_blank" rel="noreferrer" className="ui-link inline-flex items-center gap-1">{en ? "Open repository" : "打开代码仓库"}<ExternalLink size={13} /></a>}<AgentAction contextType="github_project" contextId={repository.canonical_name} actionKey="deep_research" className="ui-link">{en ? "Deep research" : "深入研究"}</AgentAction></div>
        <p className="mt-4 font-mono text-xs text-ink-muted">{repository.entity_key}</p>
        {data.events[0]?.summary && <p className="mt-4 max-w-4xl text-sm leading-6 text-ink-secondary">{data.events[0].summary}</p>}
      </section>

      {trends?.windows && <section className="ui-card">
        <div className="flex items-center justify-between gap-3"><h2 className="type-h3">{en ? "Observed growth" : "观测变化"}</h2>{trends.stale && <span className="ui-tag ui-tag-warning">{en ? "Stale metrics" : "指标已过期"}</span>}</div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{Object.entries(trends.windows).map(([window, values]) => <div key={window} className="rounded-xl bg-surface-subtle p-3"><h3 className="text-xs text-ink-muted">{windows[window]?.[en ? 1 : 0] || window}</h3><dl className="mt-2 space-y-1 text-sm">{Object.entries(values).filter(([, value]) => value != null && typeof value === "number").map(([name, value]) => <div key={name} className="flex justify-between gap-2"><dt className="text-ink-muted">{name}</dt><dd className="font-mono text-ink">{Number(value).toLocaleString()}</dd></div>)}</dl></div>)}</div>
      </section>}

      {evaluation && <section className="ui-card">
        <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="type-h3">{en ? "Business assessment" : "业务价值评估"}</h2><span className="ui-tag">{evaluation.level} · {evaluation.total?.toFixed(1) ?? "—"}</span></div>
        {evaluation.summary && <p className="mt-3 text-sm leading-6 text-ink-secondary">{evaluation.summary}</p>}
        <dl className="mt-4 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">{(["d1", "d2", "d3", "d4"] as const).map((key, index) => <div key={key} className="rounded-lg bg-surface-subtle p-3"><dt className="text-ink-muted">{(en ? ["Customer pain", "Scenario fit", "Business value", "Delivery"] : ["客户痛点", "场景适配", "业务价值", "交付复制"])[index]}</dt><dd className="mt-1 font-mono font-semibold text-ink">{evaluation[key]?.toFixed(1) ?? "—"}</dd></div>)}</dl>
        {evaluation.technical_assessment && <div className="mt-3 grid gap-2 sm:grid-cols-3">{(["engineering_maturity", "innovation", "deployability"] as const).map((key, index) => {
          const dimension = evaluation.technical_assessment?.[key];
          if (!dimension) return null;
          return <div key={key} className="rounded-lg bg-surface-subtle p-3"><h3 className="text-xs text-ink-muted">{(en ? ["Engineering maturity", "Innovation", "Deployability"] : ["工程成熟度", "创新性", "可部署性"])[index]} · AI</h3><p className="mt-1 font-mono font-semibold text-ink">{dimension.score == null ? (en ? "Insufficient evidence" : "证据不足") : `${dimension.score}/10`}</p>{dimension.evidence_keys.length > 0 && <p className="mt-1 text-[11px] text-ink-muted">{en ? "Evidence:" : "依据："}{dimension.evidence_keys.join(", ")}</p>}<p className="mt-1 text-xs leading-5 text-ink-secondary">{dimension.reasoning}</p></div>;
        })}</div>}
        {(evaluation.reasoning || evaluation.recommendation) && <details className="mt-4 border-t border-grid pt-3"><summary className="cursor-pointer text-sm font-medium text-primary">{en ? "Evidence-based reasoning and next step" : "依据与下一步"}</summary><div className="mt-3 space-y-2 text-sm leading-6 text-ink-secondary">{evaluation.reasoning && <p>{evaluation.reasoning}</p>}{evaluation.recommendation && <p>{en ? "Next:" : "建议："}{evaluation.recommendation}</p>}</div></details>}
      </section>}

      {data.events.length > 0 && <section className="ui-card"><h2 className="type-h3">{en ? "Project signals" : "项目情报事件"}</h2><div className="mt-3 divide-y divide-grid">{data.events.map(event => <Link key={event.id} href={`/events/${event.id}`} className="group flex items-start justify-between gap-4 py-3"><span><span className="ui-tag">{event.event_type}</span><strong className="mt-2 block text-sm text-ink group-hover:text-primary">{event.title}</strong>{event.summary && <span className="mt-1 block text-sm text-ink-secondary">{event.summary}</span>}<time className="mt-1 block text-xs text-ink-muted">{new Date(event.last_seen_at).toLocaleDateString(en ? "en" : "zh-CN")}</time></span><ArrowUpRight size={14} className="mt-1 shrink-0 text-ink-muted" /></Link>)}</div></section>}

      {data.metrics.length > 0 && <section className="ui-card"><h2 className="type-h3">{en ? "Metric history" : "指标历史"}</h2><div className="mt-3 divide-y divide-grid">{data.metrics.slice(0, 30).map((metric, index) => <div key={`${metric.metric_key}-${metric.observed_at}-${index}`} className="grid grid-cols-[1fr_auto_auto] gap-3 py-2 text-sm"><span className="text-ink-secondary">{metric.metric_key}</span><strong className="font-mono text-ink">{Number(metric.metric_value).toLocaleString()}</strong><time className="text-xs text-ink-muted">{new Date(metric.observed_at).toLocaleDateString(en ? "en" : "zh-CN")}</time></div>)}</div></section>}

      <section className="ui-card"><div className="flex items-center justify-between"><h2 className="type-h3">{en ? "Source evidence" : "来源证据"}</h2><span className="text-xs text-ink-muted">{data.evidence.length}</span></div><div className="mt-3 divide-y divide-grid">{data.evidence.map(item => <a key={item.id} href={item.canonical_url || "#"} target={item.canonical_url ? "_blank" : undefined} rel="noreferrer" className="flex items-start justify-between gap-4 py-3"><span><span className="text-xs text-ink-muted">{item.source_name} · {item.authority}</span><strong className="mt-1 block text-sm text-ink">{item.title}</strong><time className="mt-1 block text-xs text-ink-muted">{new Date(item.published_at || item.observed_at).toLocaleString(en ? "en" : "zh-CN")}</time></span><ExternalLink size={14} className="mt-1 shrink-0 text-ink-muted" /></a>)}</div></section>
    </>}
  </div>;
}
