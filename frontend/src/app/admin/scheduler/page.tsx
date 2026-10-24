"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { SectionHeader } from "@/components/section-header";
import { useAuth } from "@/components/auth-provider";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

type Task = { key: string; name: string; schedule: string; next_run_at: string; last_run?: { status: string; started_at: string } | null };

export default function AdminSchedulerPage() {
  const { user, loading } = useAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try {
      const response = await authenticatedFetch(`${API}/api/admin/tasks?limit=100`);
      if (!response.ok) throw new Error("调度信息加载失败。");
      setTasks((await response.json()).tasks || []);
      setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "调度信息加载失败。"); }
  }, []);
  useEffect(() => { if (user?.app_metadata?.role === "admin") void Promise.resolve().then(load); }, [load, user]);
  if (loading) return <div className="ui-card py-12 text-center text-sm text-ink-muted">正在验证权限…</div>;
  if (user?.app_metadata?.role !== "admin") return <div className="ui-card py-12 text-center text-sm text-ink-muted">需要管理员权限。</div>;
  return <div className="page-stack">
    <SectionHeader badge="Admin / Scheduler" title="调度配置" subtitle="查看定时任务与下次执行时间；采集计划在来源管理中修改。" action={<Link href="/admin/sources" className="ui-button-primary">管理采集计划</Link>} />
    {error && <div role="alert" className="ui-card text-sm text-danger">{error}</div>}
    <section className="ui-card overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead className="text-xs text-ink-muted"><tr><th className="py-2">任务</th><th>执行计划</th><th>下次执行</th><th>最近状态</th></tr></thead><tbody>{tasks.map(task => <tr key={task.key} className="border-t border-grid"><td className="py-3"><span className="block font-medium text-ink">{task.name}</span><span className="font-mono text-xs text-ink-muted">{task.key}</span></td><td className="font-mono text-xs">{task.schedule || "—"}</td><td>{task.next_run_at ? new Date(task.next_run_at).toLocaleString("zh-CN") : "—"}</td><td>{task.last_run?.status || "尚未运行"}</td></tr>)}</tbody></table>{!tasks.length && !error && <p className="py-8 text-center text-sm text-ink-muted">暂无已注册的定时任务。</p>}</section>
  </div>;
}
