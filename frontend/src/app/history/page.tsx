"use client";

import { SectionHeader } from "@/components/section-header";
import { useCallback, useEffect, useState } from "react";
import { API } from "@/lib/api";
import {
  CalendarDays, FileText, Activity, Search,
  ExternalLink, Star, RefreshCw
} from "lucide-react";

interface TrendingItem {
  repo_name: string;
  repo_url: string;
  description: string;
  language: string;
  stars: string;
  forks: string;
  today_stars: string;
  scrape_date: string;
}

interface HistoryEntry {
  date: string;
  items: TrendingItem[];
  evaluations: EvaluationItem[];
}

interface EvaluationItem {
  repo_name: string;
  total: number;
  level: string;
  recommendation: string;
  reasoning: string;
}

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [category, setCategory] = useState<"daily" | "weekly" | "monthly">("daily");

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/github-trending/history?days=30&category=${category}`);
      if (!res.ok) { throw new Error(`API error: ${res.status}`); }
      const data = await res.json();
      setHistory(data.history || []);
    } catch (err) {
      console.error("历史记录加载失败:", err);
    } finally {
      setLoading(false);
    }
  }, [category]);

  useEffect(() => {
    void Promise.resolve().then(fetchHistory);
  }, [fetchHistory]);

  const filtered = history.filter((entry) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      entry.date.includes(q) ||
      entry.items.some(
        (item) =>
          item.repo_name.toLowerCase().includes(q) ||
          (item.description && item.description.toLowerCase().includes(q))
      )
    );
  });

  return (
    <div className="page-stack">
      <SectionHeader
        badge="Archive"
        title="历史日报存档"
        subtitle="按日期查阅每天采集的技术热点与业务价值分析，追溯技术趋势变化轨迹"
        action={
          <div className="flex items-center gap-2 text-xs text-ink-muted">
            <FileText className="h-4 w-4" />
            <span>已收录 {history.length} 天数据</span>
          </div>
        }
      />

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="ui-input flex flex-1 items-center gap-2 px-3.5 py-2">
          <Search className="h-3.5 w-3.5 text-ink-muted" />
          <input
            type="text"
            placeholder="按日期或仓库名搜索..."
            className="bg-transparent border-none text-[13px] focus:outline-none w-full text-ink placeholder:text-ink-muted"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="flex gap-1.5">
          {(["daily", "weekly", "monthly"] as const).map((c) => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={`ui-button-secondary ${
                category === c
                  ? "!bg-primary !text-white"
                  : ""
              }`}
            >
              {c === "daily" ? "日榜" : c === "weekly" ? "周榜" : "月榜"}
            </button>
          ))}
        </div>
        <button
          onClick={fetchHistory}
          className="ui-button-secondary"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          刷新
        </button>
      </div>

      {/* Timeline */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="ui-card animate-shimmer">
              <div className="h-5 w-32 bg-surface-subtle rounded mb-3" />
              <div className="h-4 w-full bg-surface-subtle rounded mb-2" />
              <div className="h-4 w-3/4 bg-surface-subtle rounded" />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-lg font-serif font-bold text-ink-muted">暂无历史记录</p>
          <p className="text-sm text-ink-muted mt-1">
            {searchQuery ? "没有匹配的记录，试试其他关键词" : "每天 09:00 自动抓取，数据将逐步积累"}
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {filtered.map((entry) => (
            <div key={entry.date} className="overflow-hidden rounded-2xl bg-white shadow-[var(--shadow-card)]">
              {/* Date Header */}
              <div className="flex items-center justify-between px-5 py-3 bg-surface-subtle border-b border-grid/60">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-lg bg-primary flex items-center justify-center text-white text-xs font-bold">
                    {entry.date.slice(8)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <CalendarDays className="h-3.5 w-3.5 text-ink-muted" />
                      <span className="text-sm font-semibold text-ink">{entry.date}</span>
                    </div>
                    <p className="text-xs text-ink-muted">
                      {new Date(entry.date).toLocaleDateString("zh-CN", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-xs text-ink-muted">
                  <span className="flex items-center gap-1">
                    <Activity className="h-3 w-3" />
                    {entry.items.length} 个项目
                  </span>
                </div>
              </div>

              {/* Items */}
              <div className="p-5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {entry.items.slice(0, 10).map((item, j) => (
                    <a
                      key={item.repo_url || j}
                      href={item.repo_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group flex items-start gap-3 rounded-lg bg-surface-subtle/60 p-3 transition-colors hover:bg-primary-soft/70"
                    >
                      <span className="flex h-5 w-5 items-center justify-center rounded bg-surface-subtle text-[9px] font-bold text-ink-muted shrink-0 mt-0.5">
                        {j + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="serif-heading text-xs text-ink group-hover:text-primary transition-colors truncate">
                          {item.repo_name}
                        </p>
                        <p className="text-xs text-ink-muted line-clamp-1 mt-0.5">
                          {item.description || "暂无描述"}
                        </p>
                        <div className="flex items-center gap-3 mt-1.5">
                          {item.language && item.language !== "N/A" && (
                            <span className="text-xs text-ink-muted">{item.language}</span>
                          )}
                          <span className="flex items-center gap-0.5 text-[10px] text-ink-muted">
                            <Star className="h-2.5 w-2.5" /> {item.stars}
                          </span>
                          {item.today_stars && (
                            <span className="text-[10px] font-semibold text-primary">{item.today_stars}</span>
                          )}
                        </div>
                      </div>
                      <ExternalLink className="h-3.5 w-3.5 text-ink-muted shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </a>
                  ))}
                </div>
                {entry.evaluations?.length > 0 && (
                  <div className="mt-5 border-t border-grid/60 pt-5">
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="type-h3 text-ink">当日业务价值分析</h3>
                      <span className="text-xs text-ink-muted">{entry.evaluations.length} 个项目</span>
                    </div>
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                      {entry.evaluations.map((item) => (
                        <div key={item.repo_name} className="rounded-xl bg-surface-subtle p-4">
                          <div className="flex items-center justify-between gap-3">
                            <p className="truncate text-xs font-semibold text-ink">{item.repo_name}</p>
                            <span className="ui-tag shrink-0">
                              {item.total} · {item.level}
                            </span>
                          </div>
                          <p className="mt-2 text-xs leading-relaxed text-ink-secondary">{item.recommendation}</p>
                          <p className="mt-1 text-[11px] leading-relaxed text-ink-muted">{item.reasoning}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
