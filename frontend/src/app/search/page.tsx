"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useCallback, useEffect, useState } from "react";
import {
  Blocks, ChevronLeft, ChevronRight, ClipboardList, ExternalLink,
  Layers3, Loader2, Radio, Search, ShieldCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";
import { optionalAuthenticatedFetch } from "@/lib/authenticated-fetch";

type SearchKind = "all" | "technical" | "solution" | "competitor" | "requirement" | "managed_solution";

interface SearchResult {
  type: Exclude<SearchKind, "all">;
  title: string;
  url: string;
  source: string;
  snippet: string;
}

interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
  page: number;
  pages: number;
  facets: Partial<Record<Exclude<SearchKind, "all">, number>>;
}

const typeConfig: Record<Exclude<SearchKind, "all">, { label: string; icon: LucideIcon }> = {
  technical: { label: "技术项目", icon: Radio },
  solution: { label: "方案洞察", icon: Layers3 },
  competitor: { label: "友商动态", icon: ShieldCheck },
  requirement: { label: "Requirement", icon: ClipboardList },
  managed_solution: { label: "Solution", icon: Blocks },
};

const filters: { value: SearchKind; label: string }[] = [
  { value: "all", label: "全部" },
  ...Object.entries(typeConfig).map(([value, config]) => ({ value: value as SearchKind, label: config.label })),
];

function SearchContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";
  const kindParam = searchParams.get("kind") || "all";
  const initialKind = (filters.some((filter) => filter.value === kindParam) ? kindParam : "all") as SearchKind;
  const initialPage = Math.max(1, Number(searchParams.get("page")) || 1);
  const [query, setQuery] = useState(initialQuery);
  const [activeKind, setActiveKind] = useState<SearchKind>(initialKind);
  const [data, setData] = useState<SearchResponse>({ results: [], total: 0, query: "", page: 1, pages: 0, facets: {} });
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");

  const runSearch = useCallback(async (searchQuery: string, page: number, kind: SearchKind) => {
    const normalized = searchQuery.trim();
    if (!normalized) return;
    setLoading(true);
    setSearched(true);
    setError("");
    try {
      const params = new URLSearchParams({ q: normalized, kind, page: String(page) });
      const response = await optionalAuthenticatedFetch(`${API}/api/search?${params}`);
      if (!response.ok) throw new Error(`搜索失败：${response.status}`);
      setData(await response.json());
      window.history.replaceState(null, "", `/search?${params}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "搜索服务暂时不可用");
      setData({ results: [], total: 0, query: normalized, page: 1, pages: 0, facets: {} });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (initialQuery) void Promise.resolve().then(() => runSearch(initialQuery, initialPage, initialKind));
  }, [initialKind, initialPage, initialQuery, runSearch]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void runSearch(query, 1, activeKind);
  };

  const changeKind = (kind: SearchKind) => {
    setActiveKind(kind);
    if ((data.query || query).trim()) void runSearch(data.query || query, 1, kind);
  };

  const allCount = Object.values(data.facets).reduce((total, count) => total + (count || 0), 0);

  return (
    <div className="page-stack">
      <SectionHeader badge="Search Engine" title="全局搜索" subtitle="按相关性检索技术项目、方案洞察、友商动态和你的 Workbench。" />

      <form onSubmit={submit} role="search" className="rounded-2xl bg-primary-dark p-4 sm:p-6">
        <label htmlFor="global-search" className="swiss-kicker text-white/60">输入名称、能力、场景或技术关键词</label>
        <div className="mt-3 flex flex-col gap-3 sm:flex-row">
          <div className="flex min-w-0 flex-1 items-center gap-3 rounded-xl bg-white px-4 py-3.5">
            <Search className="h-5 w-5 shrink-0 text-primary" />
            <input id="global-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="例如：RAG、数据迁移、可观测性、安全合规" className="min-w-0 flex-1 bg-transparent text-base text-ink outline-none placeholder:text-ink-muted" autoFocus />
          </div>
          <button disabled={loading || !query.trim()} className="ui-button-primary bg-white px-6 text-primary-dark hover:bg-primary-soft">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}搜索
          </button>
        </div>
        {!searched && <div className="mt-4 flex flex-wrap items-center gap-2"><span className="text-xs text-white/50">快速搜索</span>{["AI Agent", "数据迁移", "可观测性", "安全合规"].map((term) => <button key={term} type="button" onClick={() => { setQuery(term); setActiveKind("all"); void runSearch(term, 1, "all"); }} className="rounded-full bg-white/10 px-3 py-1.5 text-xs text-white/75 transition-colors hover:bg-white/20 hover:text-white">{term}</button>)}</div>}
      </form>

      {searched && (
        <div className="flex flex-col gap-3 rounded-xl bg-surface-subtle p-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="搜索结果类型">
            {filters.map((filter) => {
              const count = filter.value === "all" ? allCount : data.facets[filter.value as Exclude<SearchKind, "all">] || 0;
              return <button key={filter.value} type="button" role="tab" aria-selected={activeKind === filter.value} onClick={() => changeKind(filter.value)} className={`rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${activeKind === filter.value ? "bg-primary text-white" : "bg-white text-ink-muted hover:bg-primary-soft hover:text-primary"}`}>{filter.label}<span className="ml-1.5 opacity-65">{count}</span></button>;
            })}
          </div>
          <p className="text-xs text-ink-muted">找到 {data.total} 条结果 · 按相关性排序</p>
        </div>
      )}

      {error && <div role="alert" className="rounded-xl bg-warning-soft px-5 py-4 text-sm text-warning">{error}，请稍后重试。</div>}

      {loading ? (
        <div className="grid gap-3 md:grid-cols-2">{Array.from({ length: 6 }).map((_, index) => <div key={index} className="h-40 animate-shimmer rounded-xl bg-white" />)}</div>
      ) : searched && data.results.length === 0 ? (
        <div className="ui-card flex min-h-64 flex-col items-center justify-center text-center"><Search className="h-9 w-9 text-primary" /><h2 className="mt-4 type-h3 text-ink">没有找到匹配内容</h2><p className="mt-2 text-sm text-ink-muted">减少关键词数量，或切换到“全部”继续搜索。</p></div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {data.results.map((result) => {
            const config = typeConfig[result.type];
            const Icon = config.icon;
            const external = result.url.startsWith("http");
            return (
              <Link key={`${result.type}-${result.url}-${result.title}`} href={result.url} target={external ? "_blank" : undefined} rel={external ? "noreferrer" : undefined} className="ui-card ui-card-interactive group flex min-h-44 items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary"><Icon className="h-4 w-4" /></div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-3"><span className="ui-tag">{config.label}</span>{external && <ExternalLink className="h-3.5 w-3.5 text-ink-muted transition-colors group-hover:text-primary" />}</div>
                  <h2 className="mt-3 type-h3 text-ink"><Highlight text={result.title} query={data.query} /></h2>
                  {result.snippet && <p className="mt-2 line-clamp-2 text-sm leading-6 text-ink-muted"><Highlight text={result.snippet} query={data.query} /></p>}
                  <p className="mt-3 truncate text-xs font-medium text-ink-muted">{result.source}</p>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {!loading && data.pages > 1 && (
        <nav aria-label="搜索结果分页" className="flex items-center justify-center gap-3">
          <button type="button" disabled={data.page === 1} onClick={() => void runSearch(data.query, data.page - 1, activeKind)} className="ui-button-secondary"><ChevronLeft className="h-4 w-4" />上一页</button>
          <span className="font-mono text-xs font-semibold text-ink-muted">{data.page} / {data.pages}</span>
          <button type="button" disabled={data.page === data.pages} onClick={() => void runSearch(data.query, data.page + 1, activeKind)} className="ui-button-secondary">下一页<ChevronRight className="h-4 w-4" /></button>
        </nav>
      )}
    </div>
  );
}

function Highlight({ text, query }: { text: string; query: string }) {
  const tokens = query.trim().split(/\s+/).filter(Boolean);
  if (!tokens.length) return text;
  const pattern = new RegExp(`(${tokens.map((token) => token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
  return <>{text.split(pattern).map((part, index) => tokens.some((token) => token.toLowerCase() === part.toLowerCase()) ? <mark key={index} className="rounded bg-warning-soft px-0.5 text-ink">{part}</mark> : part)}</>;
}

export default function SearchPage() {
  return <Suspense fallback={<div className="h-80 animate-shimmer rounded-xl bg-white" />}><SearchContent /></Suspense>;
}
