"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowRight, Blocks, ClipboardList, Plus, Trash2 } from "lucide-react";
import { SectionHeader } from "@/components/section-header";
import { useAuth } from "@/components/auth-provider";
import { formatWorkbenchDate, Solution, solutionStatusLabels, workbenchFetch } from "@/lib/workbench";

export default function SolutionsPage() {
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState<Solution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      setItems(await workbenchFetch<Solution[]>("/solutions"));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "方案实践加载失败");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  const remove = async (item: Solution) => {
    if (!window.confirm(`删除方案实践“${item.name}”？`)) return;
    try {
      await workbenchFetch(`/solutions/${item.id}`, { method: "DELETE" });
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "删除失败");
    }
  };

  if (!authLoading && !user) {
    return (
      <div className="ui-card mx-auto mt-20 flex max-w-lg flex-col items-center py-12 text-center">
        <Blocks className="h-8 w-8 text-primary" /><h1 className="mt-4 type-h2 text-ink">方案实践需要登录</h1>
        <p className="mt-2 text-sm text-ink-muted">登录后可管理自己的方案背景。</p><Link href="/auth/login" className="ui-button-primary mt-5">前往登录</Link>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <SectionHeader
        badge="Workbench / Practices"
        title="方案实践"
        subtitle="收纳方案背景、来源材料和 AI 工作上下文。"
        action={<Link href="/workbench/solutions/new" className="ui-button-primary"><Plus className="h-4 w-4" />创建方案实践</Link>}
      />
      {error && <div role="alert" className="rounded-xl bg-warning-soft px-5 py-4 text-sm text-warning">{error}</div>}
      {loading || authLoading ? (
        <div className="grid gap-3 lg:grid-cols-2">{Array.from({ length: 4 }).map((_, index) => <div key={index} className="h-52 animate-shimmer rounded-xl bg-white" />)}</div>
      ) : items.length ? (
        <div className="grid gap-3 lg:grid-cols-2">
          {items.map((item) => (
            <article key={item.id} className="ui-card ui-card-interactive group flex min-h-52 flex-col">
              <div className="flex items-start justify-between gap-4">
                <div className="flex flex-wrap gap-2"><span className="ui-tag">{item.category}</span><span className="ui-tag">{solutionStatusLabels[item.status]}</span><span className="ui-tag">{item.version}</span></div>
                <button onClick={() => void remove(item)} aria-label={`删除 ${item.name}`} className="rounded-lg p-2 text-ink-muted transition-colors hover:bg-warning-soft hover:text-warning"><Trash2 className="h-4 w-4" /></button>
              </div>
              <h2 className="mt-5 type-h3 text-ink">{item.name}</h2>
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-ink-muted">{item.description || "尚未补充背景信息"}</p>
              <div className="mt-auto flex items-end justify-between gap-4 pt-6">
                <div className="text-xs leading-5 text-ink-muted"><p className="flex items-center gap-1.5"><ClipboardList className="h-3.5 w-3.5" />{item.requirement_count || 0} 项背景材料</p><p>更新于 {formatWorkbenchDate(item.updated_at)}</p></div>
                <Link href={`/workbench/solutions/${item.id}`} className="ui-link flex items-center gap-1.5 text-sm">查看详情<ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" /></Link>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="ui-card flex min-h-72 flex-col items-center justify-center text-center"><Blocks className="h-8 w-8 text-primary" /><h2 className="mt-4 type-h3 text-ink">还没有方案实践</h2><p className="mt-2 text-sm text-ink-muted">先收纳方案背景，再进入 AI 工作区分析。</p><Link href="/workbench/solutions/new" className="ui-button-primary mt-5">创建方案实践</Link></div>
      )}
    </div>
  );
}
