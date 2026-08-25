"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { ArrowLeft, ArrowRight, Lightbulb } from "lucide-react";
import { SectionHeader } from "@/components/section-header";
import { Requirement, workbenchFetch } from "@/lib/workbench";

function RequirementCreateForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    title: params.get("title") || "",
    description: "",
    status: "draft",
    priority: "medium",
    source_type: params.get("source_type") || "manual",
    source_id: params.get("source_id") || "",
    source_url: params.get("source_url") || "",
  });

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const item = await workbenchFetch<Requirement>("/requirements", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, source_url: form.source_url || null }),
      });
      router.push(`/workbench/requirements/${item.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "创建失败");
    } finally {
      setSaving(false);
    }
  };

  const field = (name: keyof typeof form, value: string) => setForm((current) => ({ ...current, [name]: value }));

  return (
    <div className="page-stack">
      <SectionHeader badge="Insight → Requirement" title="创建 Requirement" subtitle="保留洞察来源，把观察转为可推进的技术需求。" />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
        <form onSubmit={submit} className="ui-card space-y-5">
          {error && <div role="alert" className="rounded-lg bg-warning-soft p-3 text-sm text-warning">{error}</div>}
          <Field label="标题" required><input required maxLength={200} value={form.title} onChange={(event) => field("title", event.target.value)} className="ui-input w-full px-4 py-3" placeholder="要解决的技术问题" /></Field>
          <Field label="描述"><textarea maxLength={5000} rows={6} value={form.description} onChange={(event) => field("description", event.target.value)} className="ui-input w-full resize-y px-4 py-3" placeholder="补充背景、约束和期望结果" /></Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="状态"><select value={form.status} onChange={(event) => field("status", event.target.value)} className="ui-input w-full px-3 py-3"><option value="draft">草稿</option><option value="active">进行中</option><option value="planned">已规划</option></select></Field>
            <Field label="优先级"><select value={form.priority} onChange={(event) => field("priority", event.target.value)} className="ui-input w-full px-3 py-3"><option value="low">低</option><option value="medium">中</option><option value="high">高</option><option value="critical">紧急</option></select></Field>
          </div>
          <div className="rounded-xl bg-surface-subtle p-4">
            <p className="swiss-kicker text-primary">来源信息</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <Field label="来源类型"><input value={form.source_type} onChange={(event) => field("source_type", event.target.value)} className="ui-input w-full px-3 py-2.5" /></Field>
              <Field label="原始数据 ID"><input value={form.source_id} onChange={(event) => field("source_id", event.target.value)} className="ui-input w-full px-3 py-2.5" /></Field>
            </div>
            <div className="mt-4"><Field label="原始链接"><input type="url" value={form.source_url} onChange={(event) => field("source_url", event.target.value)} className="ui-input w-full px-3 py-2.5" placeholder="https://" /></Field></div>
          </div>
          <div className="flex flex-wrap justify-between gap-3 pt-2">
            <Link href="/workbench/requirements" className="ui-button-secondary"><ArrowLeft className="h-4 w-4" />返回列表</Link>
            <button disabled={saving} className="ui-button-primary">{saving ? "正在创建" : "创建并查看"}<ArrowRight className="h-4 w-4" /></button>
          </div>
        </form>
        <aside className="rounded-xl bg-primary-dark p-6 text-white lg:sticky lg:top-20 lg:self-start">
          <Lightbulb className="h-5 w-5 text-white/70" />
          <p className="mt-5 font-mono text-xs text-white/50">01 / 03</p>
          <h2 className="mt-2 type-h3">从洞察保留上下文</h2>
          <p className="mt-3 text-sm leading-6 text-white/65">来源字段会记录原始方案，不会修改外部洞察数据。创建后即可关联或新建自己的 Solution。</p>
        </aside>
      </div>
    </div>
  );
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return <label className="block"><span className="mb-2 block text-sm font-semibold text-ink-secondary">{label}{required && <span className="text-warning"> *</span>}</span>{children}</label>;
}

export default function RequirementCreatePage() {
  return <Suspense fallback={<div className="h-96 animate-shimmer rounded-xl bg-white" />}><RequirementCreateForm /></Suspense>;
}
