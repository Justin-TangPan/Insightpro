"use client";

import { Bot, CheckCircle2, Clock3, Play, RefreshCw, Search, XCircle } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

type Run = { id: number; task_key: string; trigger: string; status: string; started_at: string; finished_at: string | null; result: Record<string, unknown> | null; error: string | null };
type Task = { key: string; name: string; schedule: string; uses_ai: boolean; next_run_at: string; last_run: Run | null };

const time = (value?: string | null) => value ? new Date(value).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }) : "—";
const statusLabel = (status?: string) => status === "success" ? "成功" : status === "failed" ? "失败" : status === "running" ? "运行中" : status === "skipped" ? "已跳过" : "尚未运行";
const statusClass = (status?: string) => status === "success" ? "ui-tag-success" : status === "failed" ? "ui-tag-danger" : status === "running" ? "ui-tag-warning" : "";

export default function AdminTasksPage() {
  const { user, loading } = useAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [running, setRunning] = useState("");
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [updatedAt, setUpdatedAt] = useState("");

  const load = useCallback(async () => {
    try {
      const response = await authenticatedFetch(`${API}/api/admin/tasks?limit=200`);
      if (!response.ok) throw new Error("任务数据加载失败");
      const data = await response.json();
      setTasks(data.tasks || []); setRuns(data.runs || []); setUpdatedAt(new Date().toLocaleTimeString("zh-CN")); setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "任务数据加载失败"); }
  }, []);

  useEffect(() => {
    if (user?.app_metadata?.role !== "admin") return;
    void Promise.resolve().then(load);
    const timer = window.setInterval(() => { if (document.visibilityState === "visible") void load(); }, 5000);
    return () => window.clearInterval(timer);
  }, [load, user]);

  const run = async (key: string) => {
    setRunning(key);
    try {
      const response = await authenticatedFetch(`${API}/api/admin/tasks/${key}/run`, { method: "POST" });
      if (!response.ok) throw new Error("任务启动失败");
      window.setTimeout(() => void load(), 800);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "任务启动失败"); }
    finally { setRunning(""); }
  };

  const active = tasks.filter(item => item.last_run?.status === "running").length;
  const failed = tasks.filter(item => item.last_run?.status === "failed").length;
  const succeeded = tasks.filter(item => item.last_run?.status === "success").length;
  const filteredRuns = useMemo(() => runs.filter(item =>
    (filter === "all" || item.status === filter) &&
    (!query.trim() || `${item.task_key} ${tasks.find(task => task.key === item.task_key)?.name || ""} ${item.error || ""}`.toLowerCase().includes(query.trim().toLowerCase()))
  ), [runs, tasks, filter, query]);
  const selectedRun = runs.find(item => item.id === selected);

  if (loading) return <div className="ui-card py-12 text-center text-sm text-ink-muted">正在验证权限…</div>;
  if (user?.app_metadata?.role !== "admin") return <div className="ui-card py-12 text-center text-sm text-ink-muted">需要管理员权限。</div>;

  return <div className="page-stack">
    <SectionHeader badge="Admin / Tasks" title="任务中心" subtitle="追踪采集、分析、知识同步与邮件发送的每次执行" action={<button type="button" onClick={() => void load()} className="ui-button-secondary"><RefreshCw className="h-4 w-4" />刷新</button>} />
    <div className="grid gap-3 sm:grid-cols-3" aria-label="任务状态概览">
      {[{ label: "运行中", count: active, icon: Clock3 }, { label: "最近成功", count: succeeded, icon: CheckCircle2 }, { label: "需要处理", count: failed, icon: XCircle }].map(item => <div key={item.label} className="ui-card flex items-center justify-between"><div><p className="text-sm text-ink-muted">{item.label}</p><p className="mt-1 text-3xl font-semibold tabular-nums text-ink">{item.count}</p></div><item.icon className="h-5 w-5 text-ink-muted" /></div>)}
    </div>
    <p className="text-xs text-ink-muted">按 5 秒自动更新 · 上次更新 {updatedAt || "—"}</p>
    {error && <div role="alert" className="rounded-xl border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">{error}</div>}
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" aria-label="平台任务">
      {tasks.map(task => <article key={task.key} className="ui-card">
        <div className="flex items-start justify-between gap-3"><div><div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold text-ink">{task.name}</h2>{task.uses_ai && <span className="ui-tag"><Bot className="h-3 w-3" /> AI</span>}</div><p className="mt-1 font-mono text-[11px] text-ink-muted">{task.key}</p></div><button type="button" aria-label={`立即运行${task.name}`} disabled={running === task.key || task.last_run?.status === "running"} onClick={() => void run(task.key)} className="ui-button-secondary min-h-11 px-3 disabled:opacity-50"><Play className="h-4 w-4" />运行</button></div>
        <dl className="mt-6 grid grid-cols-2 gap-3 text-xs"><div><dt className="text-ink-muted">计划</dt><dd className="mt-1 font-medium text-ink">{task.schedule}</dd></div><div><dt className="text-ink-muted">下次运行</dt><dd className="mt-1 font-medium text-ink">{time(task.next_run_at)}</dd></div><div><dt className="text-ink-muted">最近状态</dt><dd className="mt-1"><span className={`ui-tag ${statusClass(task.last_run?.status)}`}>{statusLabel(task.last_run?.status)}</span></dd></div><div><dt className="text-ink-muted">最近开始</dt><dd className="mt-1 font-medium text-ink">{time(task.last_run?.started_at)}</dd></div></dl>
        {task.last_run?.status === "failed" && task.last_run.error && <p className="mt-4 line-clamp-2 rounded-lg bg-danger/5 p-3 text-xs text-danger">{task.last_run.error}</p>}
      </article>)}
    </section>
    <section className="ui-card"><div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><h2 className="type-h3 text-ink">执行记录</h2><div className="flex flex-wrap gap-2"><label className="relative"><span className="sr-only">搜索任务记录</span><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="搜索任务或错误" className="ui-input min-h-11 pl-9" /></label><label className="sr-only" htmlFor="task-status">筛选状态</label><select id="task-status" value={filter} onChange={event => setFilter(event.target.value)} className="ui-input min-h-11"><option value="all">全部状态</option><option value="running">运行中</option><option value="success">成功</option><option value="failed">失败</option></select></div></div>
      <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm"><thead><tr className="border-b border-grid text-xs text-ink-muted"><th className="px-3 py-3 font-medium">开始时间</th><th className="px-3 py-3 font-medium">任务</th><th className="px-3 py-3 font-medium">触发</th><th className="px-3 py-3 font-medium">状态</th><th className="px-3 py-3 font-medium">耗时 / 结果</th></tr></thead><tbody className="divide-y divide-grid/70">{filteredRuns.map(item => <tr key={item.id}><td className="whitespace-nowrap px-3 py-3 text-xs text-ink-muted">{time(item.started_at)}</td><td className="px-3 py-3 font-medium text-ink">{tasks.find(task => task.key === item.task_key)?.name || item.task_key}</td><td className="px-3 py-3 text-ink-secondary">{item.trigger === "manual" ? "手动" : item.trigger === "startup" ? "启动补偿" : "定时"}</td><td className="px-3 py-3"><span className={`ui-tag ${statusClass(item.status)}`}>{statusLabel(item.status)}</span></td><td className="px-3 py-3"><button type="button" onClick={() => setSelected(selected === item.id ? null : item.id)} className="min-h-10 text-left text-xs text-primary underline-offset-4 hover:underline focus-visible:underline">{item.error ? "查看错误" : item.finished_at ? `${Math.max(0, Math.round((new Date(item.finished_at).getTime() - new Date(item.started_at).getTime()) / 1000))} 秒 · 查看结果` : "正在执行 · 查看详情"}</button></td></tr>)}</tbody></table>{!filteredRuns.length && <p className="py-12 text-center text-sm text-ink-muted">没有匹配的执行记录</p>}</div>
      {selectedRun && <div className="mt-5 rounded-xl border border-grid bg-white p-4" role="region" aria-label="执行详情"><div className="flex items-center justify-between"><h3 className="font-semibold text-ink">执行详情 #{selectedRun.id}</h3><button type="button" className="ui-button-secondary" onClick={() => setSelected(null)}>关闭</button></div><p className="mt-2 text-xs text-ink-muted">{time(selectedRun.started_at)} → {time(selectedRun.finished_at)}</p><pre className="mt-3 overflow-auto whitespace-pre-wrap break-words text-sm text-ink-secondary">{selectedRun.error || JSON.stringify(selectedRun.result || { status: selectedRun.status }, null, 2)}</pre></div>}
    </section>
  </div>;
}
