"use client";

import { SectionHeader } from "@/components/section-header";
import { useAuth } from "@/components/auth-provider";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { Solution, workbenchFetch } from "@/lib/workbench";
import { AgentAction } from "@/components/agent-action";
import {
  Star, GitFork, TrendingUp, CalendarDays, RefreshCw,
  ExternalLink, Activity, Zap, Clock, ArrowUpRight, BookmarkPlus, Bot, Check
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
  evaluations: EvalItem[];
}

interface EvalItem {
  repo_name: string;
  repo_url: string | null;
  language: string | null;
  stars: string | null;
  summary: string | null;
  d1: number; d2: number; d3: number; d4: number;
  total: number;
  level: string;
  recommendation: string;
  reasoning: string;
  eval_time: string | null;
}

interface EvalResponse {
  date: string;
  items: EvalItem[];
  count: number;
  summary: { strong: number; worth: number; marginal: number; not_recommended: number };
}

const evalDimensions = [
  { key: "d1", label: "服务端" },
  { key: "d2", label: "营销" },
  { key: "d3", label: "场景" },
  { key: "d4", label: "云上" },
] as const;

const levelStyles: Record<string, string> = {
  "强烈推荐": "bg-primary-soft text-primary border-primary/20",
  "值得做": "bg-warning-soft text-warning border-warning/20",
  "勉强": "bg-warning-soft text-warning border-warning/20",
  "不建议": "bg-warning-soft text-warning border-warning/20",
};

function levelClass(level: string) {
  if (level.includes("强烈推荐")) return levelStyles["强烈推荐"];
  if (level.includes("值得做")) return levelStyles["值得做"];
  if (level.includes("勉强")) return levelStyles["勉强"];
  return levelStyles["不建议"];
}

const periods = [
  { key: "daily", label: "今日", icon: Zap },
  { key: "weekly", label: "本周", icon: Activity },
  { key: "monthly", label: "本月", icon: TrendingUp },
];

const langColors: Record<string, string> = {
  Python: "bg-primary", TypeScript: "bg-primary-dark", JavaScript: "bg-primary-light",
  Rust: "bg-ink-secondary", Go: "bg-primary", Java: "bg-primary-dark",
  "C++": "bg-primary-light", C: "bg-ink-muted", Ruby: "bg-primary",
  PHP: "bg-primary-dark", Shell: "bg-primary-light", Kotlin: "bg-primary",
  Swift: "bg-ink-secondary", Dart: "bg-primary-light", Vue: "bg-primary",
  Svelte: "bg-primary-dark", Jupyter: "bg-ink-muted",
};

export default function HotspotsPage() {
  const router = useRouter();
  const { user } = useAuth();
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
  const [evaluations, setEvaluations] = useState<EvalItem[]>([]);
  const [evalSummary, setEvalSummary] = useState<EvalResponse["summary"] | null>(null);
  const [evalLoading, setEvalLoading] = useState(false);
  const [evalRefreshing, setEvalRefreshing] = useState(false);
  const [savingRepo, setSavingRepo] = useState("");
  const [savedRepos, setSavedRepos] = useState<Set<string>>(new Set());
  const [saveError, setSaveError] = useState("");

  const savePractice = async (item: TrendingItem) => {
    if (!user) return router.push("/auth/login?next=/insights/hotspots");
    setSavingRepo(item.repo_url);
    setSaveError("");
    try {
      await workbenchFetch<Solution>("/solutions", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: `评估 GitHub 项目：${item.repo_name}`,
          description: item.description || "评估该项目的技术能力、适用场景与落地价值。",
          status: "draft", category: item.category || "GitHub 项目", version: "v0.1.0",
          reference_url: item.repo_url,
        }),
      });
      setSavedRepos((current) => new Set(current).add(item.repo_url));
    } catch (reason) {
      setSaveError(reason instanceof Error ? reason.message : "收纳方案实践失败");
    } finally {
      setSavingRepo("");
    }
  };

  const fetchTrending = useCallback(async (p: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/github-trending?since=${p}`);
      if (!res.ok) { throw new Error(`API error: ${res.status}`); }
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
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await authenticatedFetch(`${API}/api/github-trending/refresh`, { method: "POST" });
      await fetchTrending(period);
    } catch (err) {
      console.error("刷新失败:", err);
    } finally {
      setRefreshing(false);
    }
  };

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API}/api/github-trending/history?days=14&category=${period}`);
      if (!res.ok) { throw new Error(`API error: ${res.status}`); }
      const json = await res.json();
      setHistory(json.history);
    } catch (err) {
      console.error("历史记录加载失败:", err);
    } finally {
      setHistoryLoading(false);
    }
  }, [period]);

  useEffect(() => {
    void Promise.resolve().then(() => fetchTrending(period));
  }, [fetchTrending, period]);
  useEffect(() => {
    if (showHistory) {
      void Promise.resolve().then(fetchHistory);
    }
  }, [fetchHistory, showHistory]);

  const fetchEvaluation = async () => {
    setEvalLoading(true);
    try {
      const res = await fetch(`${API}/api/github-trending/business-eval`);
      if (!res.ok) { throw new Error(`API error: ${res.status}`); }
      const json: EvalResponse = await res.json();
      setEvaluations(json.items);
      setEvalSummary(json.summary);
    } catch (err) {
      console.error("业务价值评估加载失败:", err);
      setEvaluations([]);
    } finally {
      setEvalLoading(false);
    }
  };

  const handleEvalRefresh = async () => {
    setEvalRefreshing(true);
    try {
      const res = await authenticatedFetch(`${API}/api/github-trending/business-eval/refresh?limit=25`, { method: "POST" });
      if (res.ok) {
        const json: EvalResponse = await res.json();
        if (json.items) {
          setEvaluations(json.items);
          setEvalSummary({ strong: 0, worth: 0, marginal: 0, not_recommended: 0 });
        }
      }
      await fetchEvaluation();
    } catch (err) {
      console.error("评估刷新失败:", err);
    } finally {
      setEvalRefreshing(false);
    }
  };

  useEffect(() => {
    if (period === "daily" && !historyDate) {
      void Promise.resolve().then(fetchEvaluation);
    }
  }, [period, historyDate]);

  const displayData = historyDate
    ? history.find((h) => h.date === historyDate)?.items || data
    : data;
  const displayEvaluations = historyDate
    ? history.find((h) => h.date === historyDate)?.evaluations || []
    : evaluations;
  const displayEvalSummary = historyDate ? {
    strong: displayEvaluations.filter((item) => item.level.includes("强烈推荐")).length,
    worth: displayEvaluations.filter((item) => item.level.includes("值得做")).length,
    marginal: displayEvaluations.filter((item) => item.level.includes("勉强")).length,
    not_recommended: displayEvaluations.filter((item) => item.level.includes("不建议")).length,
  } : evalSummary;

  return (
    <div className="page-stack">
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
              className={`ui-button-secondary ${
                period === p.key
                  ? "!bg-primary !text-white !shadow-[var(--shadow-brand)]"
                  : ""
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
            className={`ui-button-secondary ${
              showHistory
                ? "!bg-primary !text-white"
                : ""
            }`}
          >
            <CalendarDays className="h-3.5 w-3.5" />
            历史记录
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="ui-button-secondary"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
            {refreshing ? "刷新中..." : "手动刷新"}
          </button>
        </div>
      </div>

      {/* History Panel */}
      {showHistory && (
        <div className="ui-card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="type-h3 text-ink">历史抓取记录（近 14 天）</h3>
            {historyDate && (
              <button onClick={() => setHistoryDate("")} className="text-xs font-semibold text-primary hover:underline">
                ← 返回今日数据
              </button>
            )}
          </div>
          {historyLoading ? (
            <div className="grid grid-cols-7 gap-2">
              {[...Array(7)].map((_, i) => <div key={i} className="h-14 bg-surface-subtle animate-shimmer rounded-xl" />)}
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
                      ? "gradient-primary text-white shadow-md shadow-primary/20"
                      : "bg-surface-subtle border border-grid hover:border-primary/30"
                  }`}
                >
                  <span className="text-xs font-semibold uppercase tracking-wider">
                    {new Date(h.date).toLocaleDateString("zh-CN", { weekday: "short" })}
                  </span>
                  <span className="text-base font-bold">{h.date.slice(8)}</span>
                  <span className={`text-xs ${historyDate === h.date ? "text-white/70" : "text-ink-muted"}`}>{h.items.length} 项</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Date indicator */}
      {historyDate && (
        <div className="flex items-center gap-2 text-sm font-semibold text-primary bg-primary-soft border border-primary/20 rounded-xl px-4 py-2 w-fit">
          <CalendarDays className="h-4 w-4" />
          正在查看 {historyDate} 的历史数据
        </div>
      )}

      {/* Trending Projects Grid */}
      {saveError && <div role="alert" className="rounded-xl bg-warning-soft px-4 py-3 text-sm text-warning">{saveError}</div>}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="ui-card animate-shimmer">
              <div className="h-5 w-2/3 bg-surface-subtle rounded mb-3" />
              <div className="h-4 w-full bg-surface-subtle rounded mb-2" />
              <div className="h-4 w-3/4 bg-surface-subtle rounded mb-4" />
              <div className="flex gap-3">
                <div className="h-5 w-14 bg-surface-subtle rounded-full" />
                <div className="h-5 w-14 bg-surface-subtle rounded-full" />
              </div>
            </div>
          ))}
        </div>
      ) : displayData.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-lg font-serif font-bold text-ink-muted">暂无数据</p>
          <p className="text-sm text-ink-muted mt-1">点击上方&quot;手动刷新&quot;获取最新数据</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {displayData.map((item, i) => {
            const summary = displayEvaluations.find((ev) => ev.repo_name === item.repo_name)?.summary;
            return (
            <article
              key={item.repo_url || i}
              className="group ui-card hover:shadow-[var(--shadow-card-hover)] hover:-translate-y-0.5 transition-all duration-300"
            >
              <div className="flex items-start justify-between mb-2.5">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="flex h-6 w-6 items-center justify-center rounded-md gradient-primary text-white text-[10px] font-bold shrink-0">
                      {i + 1}
                    </span>
                    <a href={item.repo_url} target="_blank" rel="noopener noreferrer" className="serif-heading truncate text-sm text-ink transition-colors group-hover:text-primary">{item.repo_name}</a>
                  </div>
                  <p className="text-xs text-ink-secondary leading-relaxed line-clamp-2 ml-8 min-h-[2rem]">
                    {item.description || "暂无描述"}
                  </p>
                  {summary && (
                    <div className="ml-8 mt-3 border-l-2 border-primary/40 pl-3">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-primary">AI 项目速读</span>
                      <p className="mt-1 text-xs leading-relaxed text-ink">{summary}</p>
                    </div>
                  )}
                </div>
                <a href={item.repo_url} target="_blank" rel="noopener noreferrer" aria-label={`查看 ${item.repo_name}`}><ExternalLink className="h-4 w-4 text-ink-muted group-hover:text-primary shrink-0 ml-3 transition-colors" /></a>
              </div>
              <div className="flex flex-wrap items-center gap-3 ml-8 mt-2.5">
                {item.language && item.language !== "N/A" && (
                  <span className="flex items-center gap-1.5 text-xs font-medium text-ink-secondary">
                    <span className={`h-2.5 w-2.5 rounded-full ${langColors[item.language] || "bg-ink-muted"}`} />
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
                  <span className="flex items-center gap-1 text-xs font-semibold text-primary bg-primary-soft px-2 py-0.5 rounded-full">
                    <TrendingUp className="h-3 w-3" /> {item.today_stars}
                  </span>
                )}
                <button type="button" disabled={savingRepo === item.repo_url || savedRepos.has(item.repo_url)} onClick={() => savePractice(item)} className="ui-button-secondary ml-auto px-3 py-1.5 text-xs">
                  {savedRepos.has(item.repo_url) ? <Check className="h-3.5 w-3.5" /> : <BookmarkPlus className="h-3.5 w-3.5" />}
                  {savingRepo === item.repo_url ? "收纳中" : savedRepos.has(item.repo_url) ? "已收纳" : "收纳方案实践"}
                </button>
                <AgentAction contextType="github_project" contextId={item.repo_name} actionKey="deep_research" className="ui-button-secondary px-3 py-1.5 text-xs"><Bot className="h-3.5 w-3.5" />深入研究</AgentAction>
              </div>
            </article>
            );
          })}
        </div>
      )}

      {/* AI 业务价值评估面板 */}
      {period === "daily" && (
        <div className="ui-card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="type-h3 flex items-center gap-2 text-ink">
                <Zap className="h-4 w-4 text-primary" />
                AI 业务价值评估
              </h3>
              <p className="text-xs text-ink-muted mt-0.5">
                {historyDate ? ` ${historyDate} 历史评估` : "为当日项目生成用途速读，并评估解决方案实践价值"}
              </p>
            </div>
            {!historyDate && (
              <button
                onClick={handleEvalRefresh}
                disabled={evalRefreshing}
              className="ui-button-secondary"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${evalRefreshing ? "animate-spin" : ""}`} />
                {evalRefreshing ? "评估中..." : "重新评估"}
              </button>
            )}
          </div>

          {evalLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[...Array(4)].map((_, i) => <div key={i} className="h-28 bg-surface-subtle animate-shimmer rounded-xl" />)}
            </div>
          ) : displayEvaluations.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-sm text-ink-muted">暂无评估结果</p>
              <p className="text-xs text-ink-muted mt-1">点击右上角&quot;重新评估&quot;触发 AI 分析（每日 09:03 自动执行）</p>
            </div>
          ) : (
            <>
              {displayEvalSummary && (
                <div className="flex flex-wrap gap-2 mb-4 text-xs font-semibold">
                  <span className="ui-tag">强烈推荐 {displayEvalSummary.strong}</span>
                  <span className="ui-tag">值得做 {displayEvalSummary.worth}</span>
                  <span className="ui-tag ui-tag-warning">勉强可做 {displayEvalSummary.marginal}</span>
                  <span className="ui-tag ui-tag-warning">不建议 {displayEvalSummary.not_recommended}</span>
                </div>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {displayEvaluations.map((ev, i) => (
                  <div key={ev.repo_name || i} className="rounded-xl bg-surface-subtle p-4 transition-colors hover:bg-primary-soft/60">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="flex h-5 w-5 items-center justify-center rounded-md gradient-primary text-white text-[10px] font-bold shrink-0">{i + 1}</span>
                        {ev.repo_url ? (
                          <a href={ev.repo_url} target="_blank" rel="noopener noreferrer" className="text-sm font-semibold text-ink hover:text-primary truncate flex items-center gap-1">
                            {ev.repo_name} <ExternalLink className="h-3 w-3 shrink-0" />
                          </a>
                        ) : (
                          <span className="text-sm font-semibold text-ink truncate">{ev.repo_name}</span>
                        )}
                      </div>
                      <span className={`shrink-0 px-2 py-0.5 rounded-full text-[11px] font-semibold border ${levelClass(ev.level)}`}>
                        {ev.level}
                      </span>
                    </div>
                    <div className="grid grid-cols-4 gap-1.5 mb-2">
                      {evalDimensions.map((d) => {
                        const v = Number(ev[d.key]) || 0;
                        return (
                          <div key={d.key}>
                            <div className="flex items-center justify-between text-[10px] text-ink-muted mb-0.5">
                              <span>{d.label}</span><span className="font-semibold text-ink-secondary">{v.toFixed(1)}</span>
                            </div>
                            <div className="h-1.5 bg-surface-subtle rounded-full overflow-hidden">
                              <div className="h-full gradient-primary rounded-full" style={{ width: `${Math.min(100, v * 10)}%` }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-[11px] text-ink-muted">总分</span>
                      <span className="text-base font-bold text-primary">{Number(ev.total || 0).toFixed(1)}</span>
                      <span className="text-[11px] text-ink-muted">/ 10</span>
                    </div>
                    {ev.reasoning && <p className="text-xs text-ink-secondary leading-relaxed line-clamp-2">{ev.reasoning}</p>}
                    {ev.recommendation && <p className="text-xs text-ink-muted mt-1 line-clamp-1">建议：{ev.recommendation}</p>}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Stats Footer */}
      <div className="flex items-center justify-between rounded-xl bg-surface-subtle px-5 py-3.5 text-xs text-ink-muted">
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
