"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { ArrowLeft, ArrowUpRight, Bot, ClipboardList, Save, Trash2 } from "lucide-react";
import { SectionHeader } from "@/components/section-header";
import { AgentAction } from "@/components/agent-action";
import { priorityLabels, Solution, solutionStatusLabels, workbenchFetch } from "@/lib/workbench";

export default function SolutionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [item, setItem] = useState<Solution | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try { setItem(await workbenchFetch<Solution>(`/solutions/${id}`)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Solution 加载失败"); }
  }, [id]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (!item) return;
    setSaving(true);
    try {
      setItem(await workbenchFetch<Solution>(`/solutions/${id}`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: item.name, description: item.description, category: item.category, status: item.status, version: item.version, reference_url: item.reference_url || null }),
      }));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "保存失败"); }
    finally { setSaving(false); }
  };

  const remove = async () => {
    if (!item || !window.confirm(`删除 Solution“${item.name}”？`)) return;
    try {
      await workbenchFetch(`/solutions/${id}`, { method: "DELETE" });
      router.push("/workbench/solutions");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "删除失败");
    }
  };

  if (!item) return <div className="page-stack">{error ? <ErrorBox message={error} /> : <div className="h-96 animate-shimmer rounded-xl bg-white" />}</div>;
  return (
    <div className="page-stack">
      <SectionHeader badge="Insight → 方案实践 → AI 工作" title={item.name} subtitle={`${item.category} · ${solutionStatusLabels[item.status]} · ${item.version}`} action={<div className="flex gap-2"><AgentAction contextType="solution" contextId={item.id} actionKey="architecture" className="ui-button-primary"><Bot className="h-4 w-4" />进入 AI 分析</AgentAction><Link href="/workbench/solutions" className="ui-button-secondary"><ArrowLeft className="h-4 w-4" />返回列表</Link></div>} />
      {error && <ErrorBox message={error} />}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <form onSubmit={save} className="ui-card space-y-5">
          <div><p className="swiss-kicker text-primary">方案实践</p><h2 className="mt-1 type-h2 text-ink">背景信息</h2></div>
          <Field label="实践名称"><input required value={item.name} onChange={(event) => setItem({ ...item, name: event.target.value })} className="ui-input w-full px-4 py-3" /></Field>
          <Field label="背景信息"><textarea rows={8} value={item.description} onChange={(event) => setItem({ ...item, description: event.target.value })} className="ui-input w-full resize-y px-4 py-3" /></Field>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="分类"><input value={item.category} onChange={(event) => setItem({ ...item, category: event.target.value })} className="ui-input w-full px-3 py-3" /></Field>
            <Field label="状态"><select value={item.status} onChange={(event) => setItem({ ...item, status: event.target.value as Solution["status"] })} className="ui-input w-full px-3 py-3">{Object.entries(solutionStatusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
            <Field label="版本"><input value={item.version} onChange={(event) => setItem({ ...item, version: event.target.value })} className="ui-input w-full px-3 py-3" /></Field>
          </div>
          <Field label="参考链接"><input type="url" value={item.reference_url || ""} onChange={(event) => setItem({ ...item, reference_url: event.target.value })} className="ui-input w-full px-4 py-3" /></Field>
          {item.reference_url && <a href={item.reference_url} target="_blank" rel="noreferrer" className="ui-link inline-flex items-center gap-1 text-sm">打开参考链接<ArrowUpRight className="h-4 w-4" /></a>}
          <div className="flex flex-wrap justify-between gap-3 pt-2"><button type="button" onClick={() => void remove()} className="ui-button-secondary text-warning"><Trash2 className="h-4 w-4" />删除</button><button disabled={saving} className="ui-button-primary"><Save className="h-4 w-4" />{saving ? "保存中" : "保存修改"}</button></div>
        </form>
        <aside className="rounded-xl bg-surface-subtle p-4 self-start">
          <div className="flex items-center justify-between"><div><p className="swiss-kicker text-primary">Background</p><h2 className="mt-1 type-h3 text-ink">背景材料</h2></div><span className="ui-tag">{item.requirements?.length || 0}</span></div>
          <div className="mt-4 space-y-2">
            {item.requirements?.map((requirement) => (
              <Link key={requirement.id} href={`/workbench/requirements/${requirement.id}`} className="block rounded-lg bg-white p-4 transition-shadow hover:shadow-[var(--shadow-card)]">
                <div className="flex items-start gap-3"><ClipboardList className="mt-0.5 h-4 w-4 shrink-0 text-primary" /><div><p className="text-sm font-semibold text-ink">{requirement.title}</p><p className="mt-1 text-xs text-ink-muted">{priorityLabels[requirement.priority]}优先级</p></div></div>
              </Link>
            ))}
            {!item.requirements?.length && <div className="rounded-lg bg-white p-5 text-center text-sm text-ink-muted">尚未关联 Requirement</div>}
          </div>
        </aside>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-2 block text-sm font-semibold text-ink-secondary">{label}</span>{children}</label>;
}
function ErrorBox({ message }: { message: string }) { return <div role="alert" className="rounded-xl bg-warning-soft px-5 py-4 text-sm text-warning">{message}</div>; }
