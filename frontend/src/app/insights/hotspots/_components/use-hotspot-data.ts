"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { API } from "@/lib/api";
import { cachedJson, peekJson } from "@/lib/client-data-cache";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { Solution, workbenchFetch } from "@/lib/workbench";
import { useAuth } from "@/components/auth-provider";
import { usePreferences } from "@/lib/preferences";
import type {
  TrendingItem,
  TrendingResponse,
  HistoryEntry,
  EvalItem,
  EvalResponse,
} from "./hotspot-types";

export interface HotspotDataState {
  period: string;
  data: TrendingItem[];
  source: string;
  date: string;
  loading: boolean;
  error: boolean;
  refreshing: boolean;
  history: HistoryEntry[];
  showHistory: boolean;
  historyLoading: boolean;
  historyDate: string;
  evaluations: EvalItem[];
  evalSummary: EvalResponse["summary"] | null;
  evalLoading: boolean;
  evalRefreshing: boolean;
  evalError: string;
  savingRepo: string;
  savedRepos: Set<string>;
  saveError: string;
  displayData: TrendingItem[];
  displayEvaluations: EvalItem[];
  displayEvalSummary: EvalResponse["summary"] | null;
}

export interface HotspotDataActions {
  setPeriod: (p: string) => void;
  setHistoryDate: (d: string) => void;
  setShowHistory: (show: boolean) => void;
  handleRefresh: () => Promise<void>;
  handleReload: () => Promise<void>;
  handleEvalRefresh: () => Promise<void>;
  savePractice: (item: TrendingItem) => Promise<void>;
}

export function useHotspotData(): HotspotDataState & HotspotDataActions {
  const router = useRouter();
  const { user } = useAuth();
  const { preferences } = usePreferences();
  const locale = preferences.language;

  const [period, setPeriod] = useState("daily");
  const [data, setData] = useState<TrendingItem[]>(() => peekJson<TrendingResponse>(`${API}/api/v2/repositories/trending?period=daily`)?.items || peekJson<TrendingResponse>(`${API}/api/github-trending?since=daily`)?.items || []);
  const [source, setSource] = useState(() => (peekJson<TrendingResponse>(`${API}/api/v2/repositories/trending?period=daily`) || peekJson<TrendingResponse>(`${API}/api/github-trending?since=daily`))?.source || "");
  const [date, setDate] = useState(() => (peekJson<TrendingResponse>(`${API}/api/v2/repositories/trending?period=daily`) || peekJson<TrendingResponse>(`${API}/api/github-trending?since=daily`))?.date || "");
  const [loading, setLoading] = useState(() => !peekJson(`${API}/api/v2/repositories/trending?period=daily`) && !peekJson(`${API}/api/github-trending?since=daily`));
  const [error, setError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyDate, setHistoryDate] = useState("");
  const [evaluations, setEvaluations] = useState<EvalItem[]>([]);
  const [evalSummary, setEvalSummary] = useState<EvalResponse["summary"] | null>(null);
  const [evalLoading, setEvalLoading] = useState(false);
  const [evalRefreshing, setEvalRefreshing] = useState(false);
  const [evalError, setEvalError] = useState("");
  const [savingRepo, setSavingRepo] = useState("");
  const [savedRepos, setSavedRepos] = useState<Set<string>>(new Set());
  const [saveError, setSaveError] = useState("");
  const evalRequest = useRef(0);
  const historyRequest = useRef(0);

  // ── Save practice ────────────────────────────────────────
  const savePractice = async (item: TrendingItem) => {
    if (!user) return router.push("/admin/login?next=/insights/hotspots");
    setSavingRepo(item.repo_url);
    setSaveError("");
    try {
      await workbenchFetch<Solution>("/solutions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: locale === "en" ? `Evaluate GitHub project: ${item.repo_name}` : `评估 GitHub 项目：${item.repo_name}`,
          description:
            item.description ||
            (locale === "en" ? "Evaluate this project's technical capabilities, use cases, and practical value." : "评估该项目的技术能力、适用场景与落地价值。"),
          status: "draft",
          category: item.category || (locale === "en" ? "GitHub project" : "GitHub 项目"),
          version: "v0.1.0",
          reference_url: item.repo_url,
        }),
      });
      setSavedRepos((current) => new Set(current).add(item.repo_url));
    } catch (reason) {
      setSaveError(
        reason instanceof Error ? reason.message : (locale === "en" ? "Could not save the practice" : "收纳方案实践失败"),
      );
    } finally {
      setSavingRepo("");
    }
  };

  // ── Fetch trending ───────────────────────────────────────
  const fetchTrending = useCallback(async (p: string, force = false) => {
    if (!peekJson(`${API}/api/v2/repositories/trending?period=${p}`) && !peekJson(`${API}/api/github-trending?since=${p}`) && p !== "all") setLoading(true);
    try {
      const periods = p === "all" ? ["daily", "weekly", "monthly"] : [p];
      const responses = await Promise.all(periods.map(async (period) => {
        try { return await cachedJson<TrendingResponse>(`${API}/api/v2/repositories/trending?period=${period}`, force); }
        catch (error) {
          if (!String(error).includes("(404)")) throw error;
          return cachedJson<TrendingResponse>(`${API}/api/github-trending?since=${period}`, force);
        }
      }));
      const seen = new Set<string>();
      setData(responses.flatMap(response => response.items).filter(item => {
        const key = item.repo_url || item.repo_name;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      }));
      setSource(responses[0].source);
      setDate(responses[0].date);
      setError(false);
    } catch (err) {
      console.error("GitHub Trending 加载失败:", err);
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Handle refresh ───────────────────────────────────────
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await authenticatedFetch(`${API}/api/github-trending/refresh`, {
        method: "POST",
      });
      await fetchTrending(period, true);
    } catch (err) {
      console.error("刷新失败:", err);
    } finally {
      setRefreshing(false);
    }
  };

  const handleReload = async () => fetchTrending(period, true);

  // ── Fetch history ────────────────────────────────────────
  const fetchHistory = useCallback(async () => {
    const request = ++historyRequest.current;
    setHistoryLoading(true);
    try {
      const json = await cachedJson<{ history: HistoryEntry[] }>(`${API}/api/github-trending/history?days=14&category=${period === "all" ? "daily" : period}&locale=${locale}`);
      if (request === historyRequest.current) setHistory(json.history);
    } catch (err) {
      console.error("历史记录加载失败:", err);
    } finally {
      if (request === historyRequest.current) setHistoryLoading(false);
    }
  }, [period, locale]);

  // ── Fetch evaluation ─────────────────────────────────────
  const fetchEvaluation = useCallback(async (force = false) => {
    const request = ++evalRequest.current;
    setEvalLoading(true);
    try {
      const json = await cachedJson<EvalResponse>(`${API}/api/github-trending/business-eval?locale=${locale}`, force);
      if (request === evalRequest.current) {
        setEvaluations(json.items);
        setEvalSummary(json.summary);
        setEvalError("");
      }
    } catch (err) {
      console.error("业务价值评估加载失败:", err);
      if (request === evalRequest.current) setEvalError(locale === "en" ? "Evaluation refresh failed" : "评估更新失败");
    } finally {
      if (request === evalRequest.current) setEvalLoading(false);
    }
  }, [locale]);

  // ── Handle eval refresh ──────────────────────────────────
  const handleEvalRefresh = async () => {
    setEvalRefreshing(true);
    setEvalError("");
    try {
      const res = await authenticatedFetch(
        `${API}/api/github-trending/business-eval/refresh?limit=5&locale=${locale}`,
        { method: "POST" },
      );
      if (!res.ok) throw new Error(`AI evaluation unavailable (${res.status})`);
      const json: EvalResponse & { status?: string } = await res.json();
      await fetchEvaluation(true);
      if (json.status === "partial_success") {
        setEvalError(locale === "en" ? "Some projects remain estimates because the AI provider limited requests." : "部分项目因 AI 服务限流仍显示规则估算。");
      }
    } catch (err) {
      console.error("评估刷新失败:", err);
      setEvalError(locale === "en" ? "AI evaluation is unavailable. Existing estimates are still shown." : "AI 评估暂不可用，已保留现有估算结果。");
    } finally {
      setEvalRefreshing(false);
    }
  };

  // ── Effects ──────────────────────────────────────────────
  useEffect(() => {
    void Promise.resolve().then(() => fetchTrending(period));
  }, [fetchTrending, period]);

  useEffect(() => {
    void Promise.resolve().then(fetchHistory);
  }, [fetchHistory]);

  useEffect(() => {
    if (!historyDate) {
      void Promise.resolve().then(() => fetchEvaluation());
    }
  }, [period, historyDate, fetchEvaluation]);

  // ── Derived display data ─────────────────────────────────
  const displayData = historyDate
    ? history.find((h) => h.date === historyDate)?.items || data
    : data;

  const displayEvaluations = historyDate
    ? history.find((h) => h.date === historyDate)?.evaluations || []
    : evaluations;

  const displayEvalSummary = historyDate
    ? {
        strong: displayEvaluations.filter((item) =>
          item.level.includes("强烈推荐") || item.level.includes("Strongly Recommended"),
        ).length,
        worth: displayEvaluations.filter((item) =>
          item.level.includes("值得做") || item.level.includes("Worth Doing"),
        ).length,
        marginal: displayEvaluations.filter((item) =>
          item.level.includes("勉强") || item.level.includes("Marginal"),
        ).length,
        not_recommended: displayEvaluations.filter((item) =>
          item.level.includes("不建议") || item.level.includes("Not Recommended"),
        ).length,
      }
    : evalSummary;

  return {
    period,
    data,
    source,
    date,
    loading,
    error,
    refreshing,
    history,
    showHistory,
    historyLoading,
    historyDate,
    evaluations,
    evalSummary,
    evalLoading,
    evalRefreshing,
    evalError,
    savingRepo,
    savedRepos,
    saveError,
    displayData,
    displayEvaluations,
    displayEvalSummary,
    setPeriod,
    setHistoryDate,
    setShowHistory,
    handleRefresh,
    handleReload,
    handleEvalRefresh,
    savePractice,
  };
}
