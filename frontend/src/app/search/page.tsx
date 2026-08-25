"use client";

import { SectionHeader } from "@/components/section-header";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { API } from "@/lib/api";
import { Search, Radio, Layers3, ShieldCheck, Loader2 } from "lucide-react";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";

interface SearchResult {
  type: string;
  title: string;
  url?: string;
  source?: string;
}

const typeConfig: Record<string, { label: string; icon: LucideIcon; color: string }> = {
  technical: { label: "技术项目", icon: Radio, color: "text-lime" },
  solution: { label: "解决方案", icon: Layers3, color: "text-signal" },
  competitor: { label: "友商动态", icon: ShieldCheck, color: "text-ink" },
};

function SearchContent() {
  const searchParams = useSearchParams();
  const initialQ = searchParams.get("q") || "";
  const [query, setQuery] = useState(initialQ);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (q?: string) => {
    const searchQ = q || query;
    if (!searchQ.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await fetch(`${API}/api/search?q=${encodeURIComponent(searchQ.trim())}`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setResults(data.results || []);
    } catch (err) {
      console.error("Search failed:", err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  // Auto-search on mount if q param exists
  useState(() => {
    if (initialQ) handleSearch(initialQ);
  });

  return (
    <div className="page-stack">
      <SectionHeader badge="Search" title="全局搜索" subtitle="搜索技术项目、解决方案与友商动态" />

      {/* Search Input */}
      <div className="flex gap-3">
        <div className="ui-input flex flex-1 items-center gap-2 px-4 py-3">
          <Search className="h-4 w-4 text-ink-muted" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="输入关键词搜索..."
            className="flex-1 bg-transparent border-none text-sm text-ink focus:outline-none placeholder:text-ink-muted"
            autoFocus
          />
        </div>
        <button
          onClick={() => handleSearch()}
          disabled={loading || !query.trim()}
          className="ui-button-primary px-6"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
          搜索
        </button>
      </div>

      {/* Results */}
      {loading ? (
        <div className="text-center py-12">
          <Loader2 className="h-8 w-8 text-ink-muted mx-auto animate-spin" />
        </div>
      ) : searched && results.length === 0 ? (
        <div className="text-center py-12">
          <Search className="h-10 w-10 text-ink-muted mx-auto mb-3" />
          <p className="text-ink-secondary">未找到相关结果</p>
          <p className="text-xs text-ink-muted mt-1">尝试更换关键词</p>
        </div>
      ) : (
        <div className="space-y-2">
          {results.map((r, i) => {
            const config = typeConfig[r.type] || typeConfig.technical;
            const Icon = config.icon;
            return (
              <Link
                key={i}
                href={r.url || "#"}
                target={r.url ? "_blank" : undefined}
                className="ui-card ui-card-interactive flex items-start gap-3"
              >
                <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft ${config.color}`}>
                  <Icon className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-ink line-clamp-2">{r.title}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs font-medium text-ink-muted">{config.label}</span>
                    {r.source && <span className="text-xs text-ink-muted">· {r.source}</span>}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-ink-muted">加载中...</div>}>
      <SearchContent />
    </Suspense>
  );
}
