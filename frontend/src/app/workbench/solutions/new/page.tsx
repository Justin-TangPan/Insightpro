"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { ArrowLeft, ArrowRight, Blocks } from "lucide-react";
import { SectionHeader } from "@/components/section-header";
import { Solution, workbenchFetch } from "@/lib/workbench";

function SolutionCreateForm() {
  const router = useRouter();
  const params = useSearchParams();
  const requirementId = params.get("requirement_id");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", description: "", category: "未分类", status: "draft", version: "v0.1.0", reference_url: "" });
  const field = (name: keyof typeof form, value: string) => setForm((current) => ({ ...current, [name]: value }));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const item = await workbenchFetch<Solution>("/solutions", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, reference_url: form.reference_url || null, requirement_id: requirementId ? Number(requirementId) : null }),
      });
      router.push(`/workbench/solutions/${item.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "创建失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-stack">
      <SectionHeader badge={requirementId ? "Requirement → Solution" : "Workbench / Solutions"} title="创建 Solution" subtitle={requirementId ? "创建完成后将自动关联当前 Requirement。" : "记录可复用、可追溯的团队技术方案。"} />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
        <form onSubmit={submit} className="ui-card space-y-5">
          {error && <div role="alert" className="rounded-lg bg-warning-soft p-3 text-sm text-warning">{error}</div>}
          <Field label="名称"><input required maxLength={200} value={form.name} onChange={(event) => field("name", event.target.value)} className="ui-input w-full px-4 py-3" placeholder="Solution 名称" /></Field>
          <Field label="描述"><textarea rows={7} maxLength={5000} value={form.description} onChange={(event) => field("description", event.target.value)} className="ui-input w-full resize-y px-4 py-3" placeholder="说明方案能力、适用场景和关键约束" /></Field>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="分类"><input value={form.category} onChange={(event) => field("category", event.target.value)} className="ui-input w-full px-3 py-3" /></Field>
            <Field label="状态"><select value={form.status} onChange={(event) => field("status", event.target.value)} className="ui-input w-full px-3 py-3"><option value="draft">草稿</option><option value="active">使用中</option><option value="deprecated">已弃用</option><option value="archived">已归档</option></select></Field>
            <Field label="版本"><input value={form.version} onChange={(event) => field("version", event.target.value)} className="ui-input w-full px-3 py-3" /></Field>
          </div>
          <Field label="参考链接"><input type="url" value={form.reference_url} onChange={(event) => field("reference_url", event.target.value)} className="ui-input w-full px-4 py-3" placeholder="https://" /></Field>
          <div className="flex flex-wrap justify-between gap-3 pt-2">
            <Link href={requirementId ? `/workbench/requirements/${requirementId}` : "/workbench/solutions"} className="ui-button-secondary"><ArrowLeft className="h-4 w-4" />返回</Link>
            <button disabled={saving} className="ui-button-primary">{saving ? "正在创建" : "创建 Solution"}<ArrowRight className="h-4 w-4" /></button>
          </div>
        </form>
        <aside className="rounded-xl bg-primary-dark p-6 text-white lg:sticky lg:top-20 lg:self-start"><Blocks className="h-5 w-5 text-white/70" /><p className="mt-5 font-mono text-xs text-white/50">03 / 03</p><h2 className="mt-2 type-h3">形成可管理方案</h2><p className="mt-3 text-sm leading-6 text-white/65">这里管理的是团队自己的 Solution，与外部 `aliyun_solutions` 洞察目录完全独立。</p></aside>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-2 block text-sm font-semibold text-ink-secondary">{label}</span>{children}</label>;
}

export default function SolutionCreatePage() {
  return <Suspense fallback={<div className="h-96 animate-shimmer rounded-xl bg-white" />}><SolutionCreateForm /></Suspense>;
}
