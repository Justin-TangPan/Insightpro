"use client";

import { SectionHeader } from "@/components/section-header";
import { useEffect, useState } from "react";
import {
  CalendarDays, FileText, TrendingUp, Activity, Search, ArrowLeft,
  ExternalLink, Star, GitFork, RefreshCw
} from "lucide-react";
import Link from "next/link";

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
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [category, setCategory] = useState<"daily" | "weekly" | "monthly">("daily");

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/github-trending/history?days=30&category=${category}`);
      const data = await res.json();
      setHistory(data.history || []);
    } catch (err) {
      console.error("历史记录加载失败:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [category]);

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
    <div className="space-y-8">
      <SectionHeader
        badge="Archive"
        title="历史日报存档"
        subtitle="按日期查阅 GitHub Trending 历史快照，追溯技术趋势变化轨迹"
        action={
          <div className="flex items-center gap-2 text-xs text-ink-muted">
            <FileText className="h-4 w-4" />
            <span>已收录 {history.length} 天数据</span>
          </div>
        }
      />

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex items-center gap-2 bg-white border border-slate-200/80 px-3.5 py-2 rounded-lg flex-1">
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
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                category === c
                  ? "bg-slate-900 text-white"
                  : "bg-white border border-slate-200 text-ink-secondary hover:border-slate-300"
              }`}
            >
              {c === "daily" ? "日榜" : c === "weekly" ? "周榜" : "月榜"}
            </button>
          ))}
        </div>
        <button
          onClick={fetchHistory}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-white border border-slate-200 text-ink-secondary hover:border-slate-300 transition-all"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          刷新
        </button>
      </div>

      {/* Timeline */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-lg bg-white border border-slate-200/80 p-5 animate-shimmer">
              <div className="h-5 w-32 bg-slate-100 rounded mb-3" />
              <div className="h-4 w-full bg-slate-100 rounded mb-2" />
              <div className="h-4 w-3/4 bg-slate-100 rounded" />
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
            <div key={entry.date} className="rounded-lg bg-white border border-slate-200/80 overflow-hidden shadow-sm">
              {/* Date Header */}
              <div className="flex items-center justify-between px-5 py-3 bg-slate-50 border-b border-slate-100">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-lg bg-slate-900 flex items-center justify-center text-white text-xs font-bold">
                    {entry.date.slice(8)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <CalendarDays className="h-3.5 w-3.5 text-ink-muted" />
                      <span className="text-sm font-semibold text-ink">{entry.date}</span>
                    </div>
                    <p className="text-[11px] text-ink-muted">
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
                      className="group flex items-start gap-3 p-3 rounded-lg border border-slate-100 hover:border-slate-200 hover:bg-slate-50/50 transition-all"
                    >
                      <span className="flex h-5 w-5 items-center justify-center rounded bg-slate-100 text-[9px] font-bold text-ink-muted shrink-0 mt-0.5">
                        {j + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-ink group-hover:text-primary transition-colors truncate">
                          {item.repo_name}
                        </p>
                        <p className="text-[11px] text-ink-muted line-clamp-1 mt-0.5">
                          {item.description || "暂无描述"}
                        </p>
                        <div className="flex items-center gap-3 mt-1.5">
                          {item.language && item.language !== "N/A" && (
                            <span className="text-[10px] text-ink-muted">{item.language}</span>
                          )}
                          <span className="flex items-center gap-0.5 text-[10px] text-ink-muted">
                            <Star className="h-2.5 w-2.5" /> {item.stars}
                          </span>
                          {item.today_stars && (
                            <span className="text-[10px] font-semibold text-emerald-600">{item.today_stars}</span>
                          )}
                        </div>
                      </div>
                      <ExternalLink className="h-3.5 w-3.5 text-ink-muted shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </a>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
