"use client";

import Link from "next/link";
import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

const domains = [
  ["technology_ecosystem", "技术生态", "/insights/hotspots"],
  ["ai_applications", "AI 应用", "/insights/app-launches"],
  ["solutions", "解决方案", "/insights/solutions"],
  ["community_insights", "社区洞察", "/insights/community"],
  ["competitor_dynamics", "友商动态", "/insights/competitors"],
] as const;
type DomainStatus = { key: string; raw_today: number; events_today: number; published_today: number; pending_review: number; source_count: number; source_errors: number; failed_tasks: number; last_source_update?: string; publication_status: string; last_published_id?: number };
type Overview = { domains: DomainStatus[]; raw_today: number; events_today: number; published_today: number; pending_review: number; failed_tasks: number };
type Run = { id: number; task_key: string; status: string; started_at: string; error?: string };
type Task = { key: string; name: string; business_scopes: string[]; last_run?: Run | null };
const time = (value?: string) => value ? new Date(value).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";

export default function AdminOverview() {
  const { user, loading } = useAuth();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [sync, setSync] = useState<Record<string, boolean | null>>({});
  const [candidates, setCandidates] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [updated, setUpdated] = useState("");
  const load = useCallback(async () => {
    try {
      const paths = ["/api/admin/overview", "/api/admin/tasks?limit=100", "/api/v2/admin/candidates?status=pending&limit=100"];
      const responses = await Promise.all(paths.map(path => authenticatedFetch(API + path)));
      if (responses.some(response => !response.ok)) throw new Error("总览数据加载失败");
      const [overviewData, taskData, candidateData] = await Promise.all(responses.map(response => response.json()));
      setOverview(overviewData); setTasks(taskData.tasks || []);
      const checks = await Promise.all(domains.map(async ([key]) => {
        const state = (overviewData as Overview).domains.find(item => item.key === key);
        if (!state?.last_published_id) return [key, null] as const;
        try {
          const response = await fetch(`${API}/api/v2/events?business_scope=${key}&limit=100`, { cache: "no-store" });
          if (!response.ok) return [key, false] as const;
          const data = await response.json();
          return [key, (data.items || []).some((item: {id: number}) => item.id === state.last_published_id)] as const;
        } catch { return [key, false] as const; }
      }));
      setSync(Object.fromEntries(checks)); setRuns(taskData.runs || []); setCandidates((candidateData.items || []).length); setUpdated(new Date().toLocaleTimeString("zh-CN")); setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "总览数据加载失败"); }
  }, []);
  useEffect(() => { if (user?.app_metadata?.role === "admin") void Promise.resolve().then(load); }, [user, load]);
  if (loading) return <div className="ui-card">正在验证权限…</div>;
  if (user?.app_metadata?.role !== "admin") return <div className="ui-card">需要管理员权限。</div>;
  const metrics = [
    ["今日采集数据", overview?.raw_today ?? "—", "原始数据表今日入库"],
    ["今日生成事件", overview?.events_today ?? "—", "今日首次生成的事件"],
    ["今日发布情报", overview?.published_today ?? "—", "今日审核发布的事件"],
    ["待核验候选", candidates ?? "—", "当前候选队列"],
    ["失败任务", overview?.failed_tasks ?? "—", "每个任务的最近一次运行"],
  ] as const;
  return <div className="page-stack">
    <header className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-semibold tracking-widest text-primary">OPERATIONS OVERVIEW</p><h1 className="mt-1 text-3xl font-semibold text-ink">系统总览</h1><p className="mt-2 text-sm text-ink-muted">五大业务的来源、任务与事件状态 · 更新于 {updated || "—"}</p></div><button className="ui-button-secondary" type="button" onClick={() => void load()}><RefreshCw size={16} />刷新</button></header>
    {error && <p role="alert" className="ui-card text-danger">{error}</p>}
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-label="关键指标">{metrics.map(([label, value, description]) => <div key={label} className="ui-card"><p className="text-sm text-ink-muted">{label}</p><p className="mt-3 text-3xl font-semibold tabular-nums text-ink">{value}</p><p className="mt-2 text-xs text-ink-muted">{description}</p></div>)}</section>
    <section className="ui-card"><h2 className="text-lg font-semibold text-ink">前台五大业务</h2><p className="mb-5 mt-1 text-xs text-ink-muted">每个业务可进入对应来源、任务、事件和前台页面</p><div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">{domains.map(([key, name, front]) => { const state = overview?.domains.find(item => item.key === key); return <article key={key} className="rounded-xl border border-grid bg-surface p-4"><h3 className="font-semibold text-ink">{name}</h3><p className="mt-2 text-2xl font-semibold text-primary">{state?.events_today ?? "—"}</p><p className="text-xs text-ink-muted">今日事件 · {state?.raw_today ?? "—"} 条原始数据 · {state?.source_count ?? "—"} 个来源</p><dl className="mt-4 space-y-2 text-xs"><div className="flex justify-between"><dt>最近采集</dt><dd>{time(state?.last_source_update)}</dd></div><div className="flex justify-between"><dt>当前状态</dt><dd>{state?.source_errors || state?.failed_tasks ? "异常" : "正常"}</dd></div><div className="flex justify-between"><dt>异常来源</dt><dd className={state?.source_errors ? "text-danger" : "text-ink"}>{state?.source_errors ?? "—"}</dd></div><div className="flex justify-between"><dt>前台事件流</dt><dd>{sync[key] === true ? "已同步" : sync[key] === false ? "同步异常" : "今日待更新"}</dd></div></dl><p className="mt-2 text-xs text-ink-muted">{state?.pending_review ?? "—"} 条待审 · {state?.failed_tasks ?? "—"} 个失败任务</p><div className="mt-4 flex flex-wrap gap-x-3 gap-y-2 border-t border-grid pt-3 text-xs text-primary"><Link href={`/admin/sources?domain=${key}`}>来源</Link><Link href={`/admin/tasks?domain=${key}`}>任务</Link><Link href={`/admin/operations?tab=1&domain=${key}`}>事件</Link><Link href={front}>前台</Link></div></article>; })}</div></section>
    <section className="ui-card"><h2 className="mb-4 text-lg font-semibold text-ink">最近运行动态</h2><div className="divide-y divide-grid">{runs.slice(0, 8).map(run => <Link key={run.id} href={`/admin/tasks?run=${run.id}`} className="flex min-h-12 items-center justify-between gap-3 py-2 text-sm hover:text-primary"><span><time className="mr-3 text-ink-muted">{time(run.started_at)}</time>{tasks.find(item => item.key === run.task_key)?.name || run.task_key}</span><span className={run.status === "failed" ? "text-danger" : "text-ink-muted"}>{run.status === "failed" ? "失败" : run.status === "running" ? "运行中" : "完成"}</span></Link>)}{!runs.length && <p className="text-sm text-ink-muted">暂无运行记录</p>}</div></section>
  </div>;
}
