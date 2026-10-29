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
  const [error, setError] = useState("");
  const [updated, setUpdated] = useState("");
  const load = useCallback(async () => {
    try {
      const paths = ["/api/admin/overview", "/api/admin/tasks?limit=100"];
      const responses = await Promise.all(paths.map(path => authenticatedFetch(API + path)));
      if (responses.some(response => !response.ok)) throw new Error("总览数据加载失败");
      const [overviewData, taskData] = await Promise.all(responses.map(response => response.json()));
      setOverview(overviewData); setTasks(taskData.tasks || []);
      setRuns(taskData.runs || []); setUpdated(new Date().toLocaleTimeString("zh-CN")); setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "总览数据加载失败"); }
  }, []);
  useEffect(() => { if (user?.app_metadata?.role === "admin") void Promise.resolve().then(load); }, [user, load]);
  if (loading) return <div className="ui-card">正在验证权限…</div>;
  if (user?.app_metadata?.role !== "admin") return <div className="ui-card">需要管理员权限。</div>;
  const metrics = [
    ["今日采集数据", overview?.raw_today ?? "—", "原始数据表今日入库"],
    ["今日生成事件", overview?.events_today ?? "—", "今日首次生成的事件"],
    ["今日发布情报", overview?.published_today ?? "—", "今日自动发布的情报"],
    ["失败任务", overview?.failed_tasks ?? "—", "每个任务的最近一次运行"],
  ] as const;
  return <div className="page-stack">
    <header className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-semibold tracking-widest text-primary">PLATFORM HEALTH</p><h1 className="mt-1 text-3xl font-semibold text-ink">任务健康</h1><p className="mt-2 text-sm text-ink-muted">五大业务的采集、任务与发布健康状态 · 更新于 {updated || "—"}</p></div><button className="ui-button-secondary" type="button" onClick={() => void load()}><RefreshCw size={16} />刷新</button></header>
    {error && <p role="alert" className="ui-card text-danger">{error}</p>}
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="关键指标">{metrics.map(([label, value, description]) => <div key={label} className="ui-card"><p className="text-sm text-ink-muted">{label}</p><p className="mt-3 text-3xl font-semibold tabular-nums text-ink">{value}</p><p className="mt-2 text-xs text-ink-muted">{description}</p></div>)}</section>
    <section className="ui-card"><h2 className="mb-3 text-lg font-semibold text-ink">业务状态</h2><div className="divide-y divide-grid">{domains.map(([key, name, front]) => { const state = overview?.domains.find(item => item.key === key); const unhealthy = Boolean(state?.source_errors || state?.failed_tasks); return <article key={key} className="flex flex-wrap items-center gap-x-5 gap-y-2 py-3 text-sm"><h3 className="min-w-32 flex-1 font-semibold text-ink">{name}</h3><span className="tabular-nums text-ink-secondary">{state?.events_today ?? "—"} 条事件</span><span className={unhealthy ? "text-danger" : "text-ink-muted"}>{unhealthy ? `${state?.source_errors ?? 0} 个异常来源 · ${state?.failed_tasks ?? 0} 个失败任务` : "运行正常"}</span><span className="text-ink-muted">{state?.source_count ?? "—"} 个来源</span><div className="flex gap-3 text-xs text-primary"><Link href={`/admin/sources?domain=${key}`}>来源</Link><Link href={`/admin/tasks?domain=${key}`}>任务</Link><Link href={front}>前台</Link></div></article>; })}</div></section>
    <section className="ui-card"><h2 className="mb-4 text-lg font-semibold text-ink">最近运行动态</h2><div className="divide-y divide-grid">{runs.slice(0, 8).map(run => <Link key={run.id} href={`/admin/tasks?run=${run.id}`} className="flex min-h-12 items-center justify-between gap-3 py-2 text-sm hover:text-primary"><span><time className="mr-3 text-ink-muted">{time(run.started_at)}</time>{tasks.find(item => item.key === run.task_key)?.name || run.task_key}</span><span className={run.status === "failed" ? "text-danger" : "text-ink-muted"}>{run.status === "failed" ? "失败" : run.status === "running" ? "运行中" : "完成"}</span></Link>)}{!runs.length && <p className="text-sm text-ink-muted">暂无运行记录</p>}</div></section>
  </div>;
}
