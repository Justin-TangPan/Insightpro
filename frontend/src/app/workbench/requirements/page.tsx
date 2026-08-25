"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowRight, ClipboardList, Link2, Plus, Trash2 } from "lucide-react";
import { SectionHeader } from "@/components/section-header";
import { useAuth } from "@/components/auth-provider";
import {
  formatWorkbenchDate, priorityLabels, Requirement, RequirementStatus,
  requirementStatusLabels, workbenchFetch,
} from "@/lib/workbench";

const filters: { value: "" | RequirementStatus; label: string }[] = [
  { value: "", label: "全部状态" },
  ...Object.entries(requirementStatusLabels).map(([value, label]) => ({ value: value as RequirementStatus, label })),
];

export default function RequirementsPage() {
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState<Requirement[]>([]);
  const [status, setStatus] = useState<"" | RequirementStatus>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError("");
    try {
      setItems(await workbenchFetch<Requirement[]>(`/requirements${status ? `?status=${status}` : ""}`));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Requirement 加载失败");
    } finally {
      setLoading(false);
    }
  }, [status, user]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  const remove = async (item: Requirement) => {
    if (!window.confirm(`删除 Requirement“${item.title}”？`)) return;
    try {
      await workbenchFetch(`/requirements/${item.id}`, { method: "DELETE" });
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "删除失败");
    }
  };

  if (!authLoading && !user) {
    return <LoginRequired title="Requirements 工作台需要登录" />;
  }

  return (
    <div className="page-stack">
      <SectionHeader
        badge="Workbench / Requirements"
        title="Requirements"
        subtitle="把洞察收敛为可跟踪、可关联方案的技术需求。"
        action={<Link href="/workbench/requirements/new" className="ui-button-primary"><Plus className="h-4 w-4" />创建 Requirement</Link>}
      />

      <div className="flex flex-col gap-4 rounded-xl bg-surface-subtle p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3 text-sm text-ink-secondary">
          <ClipboardList className="h-4 w-4 text-primary" />
          <span>共 {items.length} 条需求</span>
        </div>
        <label className="flex items-center gap-2 text-sm text-ink-muted">
          状态
          <select value={status} onChange={(event) => setStatus(event.target.value as "" | RequirementStatus)} className="ui-input min-w-36 px-3 py-2 text-sm">
            {filters.map((filter) => <option key={filter.value} value={filter.value}>{filter.label}</option>)}
          </select>
        </label>
      </div>

      {error && <div role="alert" className="rounded-xl bg-warning-soft px-5 py-4 text-sm text-warning">{error}</div>}

      {loading || authLoading ? (
        <div className="grid gap-3 lg:grid-cols-2">{Array.from({ length: 4 }).map((_, index) => <div key={index} className="h-52 animate-shimmer rounded-xl bg-white" />)}</div>
      ) : items.length ? (
        <div className="grid gap-3 lg:grid-cols-2">
          {items.map((item) => (
            <article key={item.id} className="ui-card ui-card-interactive group flex min-h-52 flex-col">
              <div className="flex items-start justify-between gap-4">
                <div className="flex flex-wrap gap-2">
                  <span className="ui-tag">{requirementStatusLabels[item.status]}</span>
                  <span className={item.priority === "critical" || item.priority === "high" ? "ui-tag ui-tag-warning" : "ui-tag"}>{priorityLabels[item.priority]}优先级</span>
                </div>
                <button onClick={() => void remove(item)} aria-label={`删除 ${item.title}`} className="rounded-lg p-2 text-ink-muted transition-colors hover:bg-warning-soft hover:text-warning">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              <h2 className="mt-5 type-h3 text-ink">{item.title}</h2>
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-ink-muted">{item.description || "尚未补充需求描述"}</p>
              <div className="mt-auto flex items-end justify-between gap-4 pt-6">
                <div className="text-xs leading-5 text-ink-muted">
                  <p className="flex items-center gap-1.5"><Link2 className="h-3.5 w-3.5" />{item.solution_count || 0} 个关联 Solution</p>
                  <p>更新于 {formatWorkbenchDate(item.updated_at)}</p>
                </div>
                <Link href={`/workbench/requirements/${item.id}`} className="ui-link flex items-center gap-1.5 text-sm">查看详情<ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" /></Link>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="ui-card flex min-h-72 flex-col items-center justify-center text-center">
          <ClipboardList className="h-8 w-8 text-primary" />
          <h2 className="mt-4 type-h3 text-ink">还没有 Requirement</h2>
          <p className="mt-2 text-sm text-ink-muted">从解决方案洞察创建，或直接记录一条技术需求。</p>
          <Link href="/workbench/requirements/new" className="ui-button-primary mt-5">创建 Requirement</Link>
        </div>
      )}
    </div>
  );
}

function LoginRequired({ title }: { title: string }) {
  return (
    <div className="ui-card mx-auto mt-20 flex max-w-lg flex-col items-center py-12 text-center">
      <ClipboardList className="h-8 w-8 text-primary" />
      <h1 className="mt-4 type-h2 text-ink">{title}</h1>
      <p className="mt-2 text-sm text-ink-muted">登录后可查看和管理仅属于你的工作台数据。</p>
      <Link href="/auth/login" className="ui-button-primary mt-5">前往登录</Link>
    </div>
  );
}
