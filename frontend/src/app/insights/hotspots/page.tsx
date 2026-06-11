"use client";

import { SectionHeader } from "@/components/section-header";
import { useEffect, useState } from "react";
import {
  Star, GitFork, TrendingUp, CalendarDays, RefreshCw,
  ExternalLink, Activity, Zap, Clock, ArrowUpRight
} from "lucide-react";

interface TrendingItem {
  repo_name: string;
  repo_url: string;
  description: string;
  language: string;
  stars: string;
  forks: string;
  today_stars: string;
  category: string;
}

interface TrendingResponse {
  items: TrendingItem[];
  source: string;
  count: number;
  date: string;
}

interface HistoryEntry {
  date: string;
  items: TrendingItem[];
}

const periods = [
  { key: "daily", label: "今日", icon: Zap },
  { key: "weekly", label: "本周", icon: Activity },
  { key: "monthly", label: "本月", icon: TrendingUp },
];

const langColors: Record<string, string> = {
  Python: "bg-blue-500", TypeScript: "bg-blue-600", JavaScript: "bg-yellow-400",
  Rust: "bg-orange-700", Go: "bg-cyan-500", Java: "bg-red-600",
  "C++": "bg-pink-500", C: "bg-gray-500", Ruby: "bg-red-500",
  PHP: "bg-purple-500", Shell: "bg-green-500", Kotlin: "bg-purple-600",
  Swift: "bg-orange-500", Dart: "bg-blue-400", Vue: "bg-green-400",
  Svelte: "bg-orange-600", Jupyter: "bg-orange-400",
};

export default function HotspotsPage() {
  const [period, setPeriod] = useState("daily");
  const [data, setData] = useState<TrendingItem[]>([]);
  const [source, setSource] = useState("");
  const [date, setDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyDate, setHistoryDate] = useState("");

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchTrending = async (p: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/github-trending?since=${p}`);
      const json: TrendingResponse = await res.json();
      setData(json.items);
      setSource(json.source);
      setDate(json.date);
    } catch (err) {
      console.error("GitHub Trending 加载失败:", err);
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await fetch(`${API}/api/github-trending/refresh`, { method: "POST" });
      await fetchTrending(period);
    } catch (err) {
      console.error("刷新失败:", err);
    } finally {
      setRefreshing(false);
    }
  };

  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API}/api/github-trending/history?days=14&category=${period}`);
      const json = await res.json();
      setHistory(json.history);
    } catch (err) {
      console.error("历史记录加载失败:", err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => { fetchTrending(period); }, [period]);
  useEffect(() => { if (showHistory) fetchHistory(); }, [showHistory, period]);

  const displayData = historyDate
    ? history.find((h) => h.date === historyDate)?.items || data
    : data;

  return (
    <div className="space-y-6">
      <SectionHeader
        badge="Tech Trends"
        title="技术热点追踪"
        subtitle="实时 GitHub Trending 项目监控 · 按日/周/月维度追踪增长最快的技术项目"
        image="https://images.unsplash.com/photo-1618401471353-b98afee0b2eb?w=1200&q=80"
        action={
          <div className="flex items-center gap-2 text-xs text-ink-muted">
            <Clock className="h-3.5 w-3.5" />
            <span>自动更新：每天 09:00</span>
            <span className="mx-1">·</span>
            <span>{source === "live" ? "实时抓取" : source === "database" ? "本地存储" : "暂无数据"}</span>
          </div>
        }
      />

      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex gap-1.5">
          {periods.map((p) => (
            <button
              key={p.key}
              onClick={() => { setPeriod(p.key); setHistoryDate(""); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                period === p.key
                  ? "gradient-primary text-white shadow-md shadow-indigo-500/20"
                  : "bg-white border border-slate-200/60 text-ink-secondary hover:border-primary/30 hover:text-primary"
              }`}
            >
              <p.icon className="h-3.5 w-3.5" />
              {p.label}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              showHistory
                ? "gradient-primary text-white shadow-md shadow-indigo-500/20"
                : "bg-white border border-slate-200/60 text-ink-secondary hover:border-primary/30"
            }`}
          >
            <CalendarDays className="h-3.5 w-3.5" />
            历史记录
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-white border border-slate-200/60 text-ink-secondary hover:border-primary/30 hover:text-primary transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
            {refreshing ? "刷新中..." : "手动刷新"}
          </button>
        </div>
      </div>

      {/* History Panel */}
      {showHistory && (
        <div className="rounded-xl bg-white border border-slate-200/60 p-5 shadow-[var(--shadow-card)]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-sm text-ink">历史抓取记录（近 14 天）</h3>
            {historyDate && (
              <button onClick={() => setHistoryDate("")} className="text-xs font-semibold text-primary hover:underline">
                ← 返回今日数据
              </button>
            )}
          </div>
          {historyLoading ? (
            <div className="grid grid-cols-7 gap-2">
              {[...Array(7)].map((_, i) => <div key={i} className="h-14 bg-slate-100 animate-shimmer rounded-xl" />)}
            </div>
          ) : history.length === 0 ? (
            <p className="text-sm text-ink-muted text-center py-6">暂无历史记录，明早 09:00 首次抓取</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {history.map((h) => (
                <button
                  key={h.date}
                  onClick={() => setHistoryDate(h.date === historyDate ? "" : h.date)}
                  className={`flex flex-col items-center px-3.5 py-2.5 rounded-xl transition-all ${
                    historyDate === h.date
                      ? "gradient-primary text-white shadow-md shadow-indigo-500/20"
                      : "bg-slate-50 border border-slate-200/60 hover:border-primary/30"
                  }`}
                >
                  <span className="text-[10px] font-semibold uppercase tracking-wider">
                    {new Date(h.date).toLocaleDateString("zh-CN", { weekday: "short" })}
                  </span>
                  <span className="text-base font-bold">{h.date.slice(8)}</span>
                  <span className={`text-[10px] ${historyDate === h.date ? "text-white/70" : "text-ink-muted"}`}>{h.items.length} 项</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Date indicator */}
      {historyDate && (
        <div className="flex items-center gap-2 text-sm font-semibold text-primary bg-indigo-50 border border-indigo-200/60 rounded-xl px-4 py-2 w-fit">
          <CalendarDays className="h-4 w-4" />
          正在查看 {historyDate} 的历史数据
        </div>
      )}

      {/* Trending Projects Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="rounded-xl bg-white border border-slate-200/60 p-5 animate-shimmer">
              <div className="h-5 w-2/3 bg-slate-100 rounded mb-3" />
              <div className="h-4 w-full bg-slate-100 rounded mb-2" />
              <div className="h-4 w-3/4 bg-slate-100 rounded mb-4" />
              <div className="flex gap-3">
                <div className="h-5 w-14 bg-slate-100 rounded-full" />
                <div className="h-5 w-14 bg-slate-100 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      ) : displayData.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-lg font-serif font-bold text-ink-muted">暂无数据</p>
          <p className="text-sm text-ink-muted mt-1">点击上方"手动刷新"获取最新数据</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {displayData.map((item, i) => (
            <a
              key={item.repo_url || i}
              href={item.repo_url}
              target="_blank"
              rel="noopener noreferrer"
              className="group rounded-xl bg-white border border-slate-200/60 p-5 shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-card-hover)] hover:-translate-y-0.5 transition-all duration-300"
            >
              <div className="flex items-start justify-between mb-2.5">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="flex h-6 w-6 items-center justify-center rounded-md gradient-primary text-white text-[10px] font-bold shrink-0">
                      {i + 1}
                    </span>
                    <h4 className="font-semibold text-sm text-ink group-hover:text-primary transition-colors truncate">
                      {item.repo_name}
                    </h4>
                  </div>
                  <p className="text-xs text-ink-secondary leading-relaxed line-clamp-2 ml-8 min-h-[2rem]">
                    {item.description || "暂无描述"}
                  </p>
                </div>
                <ExternalLink className="h-4 w-4 text-ink-muted group-hover:text-primary shrink-0 ml-3 transition-colors" />
              </div>
              <div className="flex flex-wrap items-center gap-3 ml-8 mt-2.5">
                {item.language && item.language !== "N/A" && (
                  <span className="flex items-center gap-1.5 text-xs font-medium text-ink-secondary">
                    <span className={`h-2.5 w-2.5 rounded-full ${langColors[item.language] || "bg-gray-400"}`} />
                    {item.language}
                  </span>
                )}
                <span className="flex items-center gap-1 text-xs text-ink-muted">
                  <Star className="h-3 w-3" /> {item.stars}
                </span>
                <span className="flex items-center gap-1 text-xs text-ink-muted">
                  <GitFork className="h-3 w-3" /> {item.forks}
                </span>
                {item.today_stars && (
                  <span className="flex items-center gap-1 text-[10px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                    <TrendingUp className="h-3 w-3" /> {item.today_stars}
                  </span>
                )}
              </div>
            </a>
          ))}
        </div>
      )}

      {/* Stats Footer */}
      <div className="flex items-center justify-between rounded-xl bg-white border border-slate-200/60 px-5 py-3.5 text-xs text-ink-muted">
        <span>当前显示 {displayData.length} 个项目</span>
        <div className="flex items-center gap-4">
          <span>数据更新时间：{date || "—"}</span>
          <a href="https://github.com/trending" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-primary hover:underline font-medium">
            GitHub 官方 Trending <ArrowUpRight className="h-3 w-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
