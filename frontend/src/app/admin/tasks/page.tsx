"use client";

import { Bot, CheckCircle2, Clock3, Play, RefreshCw, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

type Run = { id: number; task_key: string; trigger: string; status: string; started_at: string; finished_at: string | null; error: string | null };
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

  const load = useCallback(async () => {
    try {
      const response = await authenticatedFetch(`${API}/api/admin/tasks`);
      if (!response.ok) throw new Error("任务数据加载失败");
      const data = await response.json();
      setTasks(data.tasks || []); setRuns(data.runs || []); setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "任务数据加载失败"); }
  }, []);

  useEffect(() => {
    if (user?.app_metadata?.role !== "admin") return;
    // Loading remote state is the synchronization this effect owns.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
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

  if (loading) return <div className="ui-card py-12 text-center text-sm text-ink-muted">正在验证权限…</div>;
  if (user?.app_metadata?.role !== "admin") return <div className="ui-card py-12 text-center text-sm text-ink-muted">需要管理员权限。</div>;

  return <div className="page-stack">
    <SectionHeader badge="Admin / Tasks" title="任务中心" subtitle="集中查看采集、AI 分析、知识同步和邮件发送" action={<button type="button" onClick={() => void load()} className="ui-button-secondary"><RefreshCw className="h-4 w-4" />刷新</button>} />
    {error && <div role="alert" className="rounded-xl border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">{error}</div>}
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" aria-label="平台任务">
      {tasks.map((task) => <article key={task.key} className="ui-card">
        <div className="flex items-start justify-between gap-3"><div><div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold text-ink">{task.name}</h2>{task.uses_ai && <span className="ui-tag"><Bot className="h-3 w-3" /> AI</span>}</div><p className="mt-1 font-mono text-[11px] text-ink-muted">{task.key}</p></div><button type="button" aria-label={`立即运行${task.name}`} disabled={running === task.key || task.last_run?.status === "running"} onClick={() => void run(task.key)} className="ui-button-secondary min-h-11 px-3 disabled:opacity-50"><Play className="h-4 w-4" />运行</button></div>
        <dl className="mt-6 grid grid-cols-2 gap-3 text-xs"><div><dt className="text-ink-muted">计划</dt><dd className="mt-1 font-medium text-ink">{task.schedule}</dd></div><div><dt className="text-ink-muted">下次运行</dt><dd className="mt-1 font-medium text-ink">{time(task.next_run_at)}</dd></div><div><dt className="text-ink-muted">最近状态</dt><dd className="mt-1"><span className={`ui-tag ${statusClass(task.last_run?.status)}`}>{task.last_run?.status === "success" ? <CheckCircle2 className="h-3 w-3" /> : task.last_run?.status === "failed" ? <XCircle className="h-3 w-3" /> : <Clock3 className="h-3 w-3" />}{statusLabel(task.last_run?.status)}</span></dd></div><div><dt className="text-ink-muted">最近开始</dt><dd className="mt-1 font-medium text-ink">{time(task.last_run?.started_at)}</dd></div></dl>
      </article>)}
    </section>
    <section className="ui-card"><h2 className="type-h3 text-ink">最近执行记录</h2><div className="mt-5 overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead><tr className="border-b border-grid text-xs text-ink-muted"><th className="px-3 py-3 font-medium">开始时间</th><th className="px-3 py-3 font-medium">任务</th><th className="px-3 py-3 font-medium">触发方式</th><th className="px-3 py-3 font-medium">状态</th><th className="px-3 py-3 font-medium">结束时间 / 错误</th></tr></thead><tbody className="divide-y divide-grid/70">{runs.map((item) => <tr key={item.id}><td className="whitespace-nowrap px-3 py-3 text-xs text-ink-muted">{time(item.started_at)}</td><td className="px-3 py-3 font-medium text-ink">{tasks.find((task) => task.key === item.task_key)?.name || item.task_key}</td><td className="px-3 py-3 text-ink-secondary">{item.trigger === "manual" ? "手动" : item.trigger === "startup" ? "启动补偿" : "定时"}</td><td className="px-3 py-3"><span className={`ui-tag ${statusClass(item.status)}`}>{statusLabel(item.status)}</span></td><td className="max-w-sm px-3 py-3 text-xs text-ink-muted">{item.error || time(item.finished_at)}</td></tr>)}</tbody></table>{!runs.length && <p className="py-12 text-center text-sm text-ink-muted">暂无执行记录</p>}</div></section>
  </div>;
}
