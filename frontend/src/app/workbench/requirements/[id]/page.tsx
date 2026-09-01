"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { ArrowLeft, ArrowUpRight, Bot, Link2, Plus, Save, Trash2, Unlink } from "lucide-react";
import { SectionHeader } from "@/components/section-header";
import { AgentAction } from "@/components/agent-action";
import {
  priorityLabels, Requirement, requirementStatusLabels, Solution, solutionStatusLabels, workbenchFetch,
} from "@/lib/workbench";

export default function RequirementDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [item, setItem] = useState<Requirement | null>(null);
  const [solutions, setSolutions] = useState<Solution[]>([]);
  const [selectedSolution, setSelectedSolution] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [requirement, allSolutions] = await Promise.all([
        workbenchFetch<Requirement>(`/requirements/${id}`), workbenchFetch<Solution[]>("/solutions"),
      ]);
      setItem(requirement);
      setSolutions(allSolutions);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Requirement 加载失败");
    }
  }, [id]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (!item) return;
    setSaving(true);
    try {
      setItem(await workbenchFetch<Requirement>(`/requirements/${id}`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: item.title, description: item.description, status: item.status, priority: item.priority,
          source_type: item.source_type, source_id: item.source_id, source_url: item.source_url || null,
        }),
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const link = async () => {
    if (!selectedSolution) return;
    try {
      await workbenchFetch(`/requirements/${id}/solutions/${selectedSolution}`, { method: "POST" });
      setSelectedSolution("");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "关联失败");
    }
  };

  const unlink = async (solutionId: number) => {
    try {
      await workbenchFetch(`/requirements/${id}/solutions/${solutionId}`, { method: "DELETE" });
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "取消关联失败");
    }
  };

  const remove = async () => {
    if (!item || !window.confirm(`删除 Requirement“${item.title}”？`)) return;
    try {
      await workbenchFetch(`/requirements/${id}`, { method: "DELETE" });
      router.push("/workbench/requirements");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "删除失败");
    }
  };

  if (!item) return <div className="page-stack">{error ? <ErrorBox message={error} /> : <div className="h-96 animate-shimmer rounded-xl bg-white" />}</div>;
  const availableSolutions = solutions.filter((solution) => !item.solutions?.some((linked) => linked.id === solution.id));

  return (
    <div className="page-stack">
      <SectionHeader
        badge="Insight → Requirement → Solution"
        title={item.title}
        subtitle={`${requirementStatusLabels[item.status]} · ${priorityLabels[item.priority]}优先级`}
        action={<div className="flex gap-2"><AgentAction contextType="requirement" contextId={item.id} actionKey="refine" className="ui-button-primary"><Bot className="h-4 w-4" />完善需求</AgentAction><Link href="/workbench/requirements" className="ui-button-secondary"><ArrowLeft className="h-4 w-4" />返回列表</Link></div>}
      />
      {error && <ErrorBox message={error} />}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <form onSubmit={save} className="ui-card space-y-5">
          <div className="ui-card-header"><div><p className="swiss-kicker text-primary">Requirement</p><h2 className="mt-1 type-h2 text-ink">需求信息</h2></div></div>
          <Field label="标题"><input required value={item.title} onChange={(event) => setItem({ ...item, title: event.target.value })} className="ui-input w-full px-4 py-3" /></Field>
          <Field label="描述"><textarea rows={7} value={item.description} onChange={(event) => setItem({ ...item, description: event.target.value })} className="ui-input w-full resize-y px-4 py-3" /></Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="状态"><select value={item.status} onChange={(event) => setItem({ ...item, status: event.target.value as Requirement["status"] })} className="ui-input w-full px-3 py-3">{Object.entries(requirementStatusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
            <Field label="优先级"><select value={item.priority} onChange={(event) => setItem({ ...item, priority: event.target.value as Requirement["priority"] })} className="ui-input w-full px-3 py-3">{Object.entries(priorityLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
          </div>
          <div className="rounded-xl bg-surface-subtle p-4">
            <p className="swiss-kicker text-primary">来源信息</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <Field label="来源类型"><input value={item.source_type} onChange={(event) => setItem({ ...item, source_type: event.target.value })} className="ui-input w-full px-3 py-2.5" /></Field>
              <Field label="原始数据 ID"><input value={item.source_id || ""} onChange={(event) => setItem({ ...item, source_id: event.target.value })} className="ui-input w-full px-3 py-2.5" /></Field>
            </div>
            <div className="mt-4"><Field label="原始链接"><input type="url" value={item.source_url || ""} onChange={(event) => setItem({ ...item, source_url: event.target.value })} className="ui-input w-full px-3 py-2.5" /></Field></div>
            {item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer" className="ui-link mt-3 inline-flex items-center gap-1 text-xs">查看原始洞察<ArrowUpRight className="h-3.5 w-3.5" /></a>}
          </div>
          <div className="flex flex-wrap justify-between gap-3 pt-2">
            <button type="button" onClick={() => void remove()} className="ui-button-secondary text-warning"><Trash2 className="h-4 w-4" />删除</button>
            <button disabled={saving} className="ui-button-primary"><Save className="h-4 w-4" />{saving ? "保存中" : "保存修改"}</button>
          </div>
        </form>

        <aside className="space-y-4">
          <section className="ui-card">
            <p className="swiss-kicker text-primary">Requirement → Solution</p>
            <h2 className="mt-1 type-h3 text-ink">关联已有 Solution</h2>
            <div className="mt-4 flex gap-2">
              <select value={selectedSolution} onChange={(event) => setSelectedSolution(event.target.value)} className="ui-input min-w-0 flex-1 px-3 py-2.5 text-sm">
                <option value="">选择 Solution</option>
                {availableSolutions.map((solution) => <option key={solution.id} value={solution.id}>{solution.name}</option>)}
              </select>
              <button type="button" disabled={!selectedSolution} onClick={() => void link()} className="ui-button-primary px-3"><Link2 className="h-4 w-4" /></button>
            </div>
            <Link href={`/workbench/solutions/new?requirement_id=${item.id}`} className="ui-button-secondary mt-3 w-full"><Plus className="h-4 w-4" />创建并自动关联</Link>
          </section>

          <section className="rounded-xl bg-surface-subtle p-4">
            <div className="flex items-center justify-between"><h2 className="type-h3 text-ink">已关联 Solution</h2><span className="ui-tag">{item.solutions?.length || 0}</span></div>
            <div className="mt-4 space-y-2">
              {item.solutions?.map((solution) => (
                <div key={solution.id} className="rounded-lg bg-white p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div><Link href={`/workbench/solutions/${solution.id}`} className="ui-link font-semibold">{solution.name}</Link><p className="mt-1 text-xs text-ink-muted">{solution.version} · {solutionStatusLabels[solution.status]}</p></div>
                    <button onClick={() => void unlink(solution.id)} aria-label={`取消关联 ${solution.name}`} className="rounded-md p-1.5 text-ink-muted hover:bg-warning-soft hover:text-warning"><Unlink className="h-3.5 w-3.5" /></button>
                  </div>
                </div>
              ))}
              {!item.solutions?.length && <p className="py-4 text-center text-sm text-ink-muted">尚未关联 Solution</p>}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-2 block text-sm font-semibold text-ink-secondary">{label}</span>{children}</label>;
}

function ErrorBox({ message }: { message: string }) {
  return <div role="alert" className="rounded-xl bg-warning-soft px-5 py-4 text-sm text-warning">{message}</div>;
}
