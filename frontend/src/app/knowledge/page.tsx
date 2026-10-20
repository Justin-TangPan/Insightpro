"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { BookOpenText, Bot, Database, ExternalLink, FileText, LockKeyhole, RefreshCw, Search, Server, Users } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { usePreferences } from "@/lib/preferences";

type Source = { source_type: string; visibility: "team" | "private"; chunks: number; documents: number };
type KnowledgeItem = { source_type: string; source_id: string; title: string; content?: string; source_url?: string; visibility?: "team" | "private"; score?: number; updated_at?: string };
type Overview = { documents: number; chunks: number; sources: Source[]; recent: KnowledgeItem[]; embedding_model: string; reranker_model: string };

const sourceMeta: Record<string, { label: string; en: string; icon: typeof Database; color: string }> = {
  github_project: { label: "开源项目", en: "Open-source project", icon: Server, color: "bg-primary" },
  cloud_solution: { label: "云方案", en: "Cloud solution", icon: Database, color: "bg-info" },
  agent_artifact: { label: "AI 成果", en: "AI artifact", icon: Bot, color: "bg-warning" },
  user_answer: { label: "我的回答", en: "My answer", icon: LockKeyhole, color: "bg-ink-secondary" },
};

const metaFor = (type: string, en: boolean) => {
  const meta = sourceMeta[type];
  return meta ? { ...meta, label: en ? meta.en : meta.label } : { label: type, icon: FileText, color: "bg-ink-muted" };
};

export default function KnowledgePage() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const { user, loading: authLoading } = useAuth();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<KnowledgeItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) return;
    authenticatedFetch("/api/agent/knowledge/overview")
      .then(async response => { if (!response.ok) throw new Error(en ? "Could not load knowledge overview" : "知识库概览加载失败"); return response.json(); })
      .then(setOverview).catch(error => setError(error.message)).finally(() => setLoading(false));
  }, [user]);

  useEffect(() => {
    const initial = new URLSearchParams(window.location.search).get("q")?.trim();
    if (user && initial) void Promise.resolve().then(() => { setQuery(initial); return runSearch(initial); });
  }, [user]);

  async function runSearch(value: string) {
    setSearching(true); setError("");
    try {
      const response = await authenticatedFetch(`/api/agent/knowledge/search?q=${encodeURIComponent(value)}`);
      if (!response.ok) throw new Error(en ? "Semantic search failed; please retry" : "语义检索失败，请重试");
      setResults((await response.json()).items || []);
    } catch (reason) { setError(reason instanceof Error ? reason.message : (en ? "Semantic search failed" : "语义检索失败")); }
    finally { setSearching(false); }
  }

  async function searchKnowledge(event: FormEvent) {
    event.preventDefault();
    const value = query.trim();
    if (!value) return;
    await runSearch(value);
  }

  if (!authLoading && !user) return <div className="ui-card mx-auto mt-20 max-w-lg py-12 text-center"><BookOpenText className="mx-auto h-8 w-8 text-primary" /><h1 className="mt-4 type-h2 text-ink"> {en ? "Sign in to view the knowledge base" : "登录后查看知识库"}</h1><p className="mt-2 text-sm text-ink-muted"> {en ? "Team knowledge and personal answers follow their access permissions." : "团队知识和个人回答会按权限分别展示。"}</p><Link href="/auth/login?next=/knowledge" className="ui-button-primary mt-5"> {en ? "Sign in" : "前往登录"}</Link></div>;

  const sources = overview?.sources || [];
  const totalDocuments = Math.max(overview?.documents || 0, 1);
  const displayed = results ?? overview?.recent ?? [];

  return <div className="page-stack">
    <section className="overflow-hidden rounded-2xl border border-grid/80 bg-primary-dark text-white shadow-[var(--shadow-elevated)]">
      <div className="grid gap-8 px-6 py-8 lg:grid-cols-[1fr_auto] lg:items-end lg:px-9">
        <div><p className="font-mono text-[11px] font-semibold uppercase tracking-[.16em] text-white/55">Knowledge Map</p><h1 className="mt-3 text-3xl font-semibold tracking-[-.035em] sm:text-4xl"> {en ? "Search what the platform knows" : "平台知道什么，一搜便知"}</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-white/70"> {en ? "Find project analysis, cloud solutions, approved artifacts, and your answers. Team materials are shared; your answers stay private." : "汇聚项目分析、云方案、已审核成果和你的回答。团队资料共同可见，个人回答仅你可见。"}</p></div>
        <div className="flex gap-6 font-mono"><div><p className="text-3xl font-semibold tabular-nums">{overview?.documents ?? "—"}</p><p className="mt-1 text-[11px] text-white/55"> {en ? "Documents" : "知识对象"}</p></div><div><p className="text-3xl font-semibold tabular-nums">{overview?.chunks ?? "—"}</p><p className="mt-1 text-[11px] text-white/55"> {en ? "Search chunks" : "检索片段"}</p></div></div>
      </div>
      <div className="border-t border-white/15 px-6 py-5 lg:px-9">
        <div className="flex h-3 w-full overflow-hidden rounded-full bg-white/10" aria-label={en ? "Knowledge source share" : "知识来源占比"}>
          {sources.map(source => <div key={`${source.source_type}-${source.visibility}`} className={`${metaFor(source.source_type, en).color} min-w-1`} style={{ width: `${source.documents / totalDocuments * 100}%` }} title={`${metaFor(source.source_type, en).label} ${source.documents}`} />)}
        </div>
        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2">{sources.map(source => { const meta = metaFor(source.source_type, en); return <span key={`${source.source_type}-${source.visibility}`} className="flex items-center gap-2 text-xs text-white/70"><span className={`h-2 w-2 rounded-full ${meta.color}`} /><span>{meta.label}</span><strong className="font-mono text-white">{source.documents}</strong>{source.visibility === "private" && <LockKeyhole className="h-3 w-3" aria-label={en ? "Only visible to me" : "仅自己可见"} />}</span>; })}</div>
      </div>
    </section>

    <form onSubmit={searchKnowledge} className="ui-card">
      <label htmlFor="knowledge-query" className="type-h3 text-ink"> {en ? "Semantic search" : "语义搜索"}</label>
      <p className="mt-1 text-sm text-ink-muted"> {en ? "Describe the problem you want to solve; exact keywords are unnecessary." : "不必记住原文关键词，直接描述你要解决的问题。"}</p>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row"><div className="relative flex-1"><Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" /><input id="knowledge-query" value={query} onChange={event => setQuery(event.target.value)} spellCheck={false} autoComplete="off" className="ui-input min-h-12 w-full pl-11 pr-4 text-base" placeholder={en ? "Which projects suit private enterprise deployment?" : "例如：哪些项目适合企业私有化部署？"} /></div><button type="submit" disabled={searching || !query.trim()} className="ui-button-primary min-h-12 px-6">{searching ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}{searching ? (en ? "Searching" : "检索中") : (en ? "Search knowledge" : "搜索知识")}</button></div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-ink-muted"><span className="ui-tag"><Bot className="h-3 w-3" />{overview?.embedding_model || "Embedding"}</span><span className="ui-tag"><RefreshCw className="h-3 w-3" />{overview?.reranker_model || "Reranker"}</span></div>
    </form>

    {error && <div role="alert" className="rounded-xl bg-warning-soft px-5 py-4 text-sm text-warning">{error}</div>}

    <section className="ui-card">
      <div className="flex items-end justify-between gap-4"><div><p className="swiss-kicker text-ink-muted">{results ? "Semantic Results" : "Recently Indexed"}</p><h2 className="mt-1 type-h2 text-ink">{results ? (en ? `Results for “${query.trim()}”` : `“${query.trim()}”的相关知识`) : (en ? "Recently indexed" : "最近进入知识库")}</h2></div>{results && <button type="button" onClick={() => setResults(null)} className="ui-button-secondary"> {en ? "View recent" : "查看最近更新"}</button>}</div>
      <div className="mt-6 divide-y divide-grid">{loading ? <div className="h-48 animate-shimmer rounded-xl" /> : displayed.length ? displayed.map((item, index) => <KnowledgeRow key={`${item.source_type}-${item.source_id}-${index}`} item={item} />) : <div className="py-14 text-center"><Search className="mx-auto h-6 w-6 text-ink-muted" /><p className="mt-3 text-sm font-medium text-ink-secondary"> {en ? "No matching knowledge" : "没有找到相关知识"}</p><p className="mt-1 text-xs text-ink-muted"> {en ? "Try a different question or wait for the next sync." : "换一种问题描述，或等待下一次知识同步。"}</p></div>}</div>
    </section>
  </div>;
}

function KnowledgeRow({ item }: { item: KnowledgeItem }) {
  const { preferences } = usePreferences(); const en = preferences.language === "en";
  const meta = metaFor(item.source_type, en); const Icon = meta.icon;
  return <article className="group grid gap-3 py-5 sm:grid-cols-[auto_1fr_auto] sm:items-start">
    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-surface-subtle text-primary"><Icon className="h-4 w-4" /></span>
    <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold text-ink">{item.title}</h3><span className="ui-tag">{meta.label}</span>{item.visibility === "private" ? <span className="ui-tag"><LockKeyhole className="h-3 w-3" /> {en ? "Only me" : "仅自己"}</span> : <span className="ui-tag"><Users className="h-3 w-3" /> {en ? "Team" : "团队"}</span>}</div>{item.content && <p className="mt-2 line-clamp-3 max-w-4xl text-sm leading-6 text-ink-secondary">{item.content}</p>}<p className="mt-2 font-mono text-[11px] text-ink-muted">{item.updated_at ? new Date(item.updated_at).toLocaleString(en ? "en-US" : "zh-CN") : item.source_id}</p></div>
    <div className="flex items-center gap-3 sm:justify-end">{typeof item.score === "number" && <span className="font-mono text-xs font-semibold text-primary">{en ? "Relevance" : "相关度"} {(item.score * 100).toFixed(1)}%</span>}{item.source_url?.startsWith("http") && <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="ui-button-secondary min-h-10" aria-label={en ? `Open source for ${item.title}` : `打开 ${item.title} 来源`}><ExternalLink className="h-4 w-4" /></a>}</div>
  </article>;
}
