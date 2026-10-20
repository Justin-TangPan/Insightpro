"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { ArrowLeft, ArrowRight, Blocks } from "lucide-react";
import { BackgroundFillDialog } from "@/components/background-fill-dialog";
import { SectionHeader } from "@/components/section-header";
import { useToast } from "@/components/ui";
import { Solution, workbenchFetch } from "@/lib/workbench";
import { usePreferences } from "@/lib/preferences";

function SolutionCreateForm() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const router = useRouter();
  const { toast } = useToast();
  const params = useSearchParams();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: params.get("title") || "", description: params.get("description") || "", category: "", status: "draft", version: "v0.1.0", reference_url: params.get("source_url") || "" });
  const field = (name: keyof typeof form, value: string) => setForm((current) => ({ ...current, [name]: value }));
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const item = await workbenchFetch<Solution>("/solutions", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, category: form.category || "Uncategorized", reference_url: form.reference_url || null }),
      });
      toast(en ? "Practice created; opening details." : "方案实践已创建，正在打开详情。", "success");
      router.replace(`/workbench/solutions/${item.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : (en ? "Create failed" : "创建失败"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-stack">
      <SectionHeader badge={en ? "Workbench / Practices" : "Workbench / 方案实践"} title={en ? "Create a Practice" : "创建方案实践"} subtitle={en ? "Save reusable solution context for Insight Agent." : "收纳可复用的方案背景，供 Insight Agent 使用。"} />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
        <form onSubmit={submit} className="ui-card space-y-5">
          {error && <div role="alert" className="rounded-lg bg-warning-soft p-3 text-sm text-warning">{error}</div>}
          <Field label={en ? "Practice name" : "实践名称"}><input required maxLength={200} value={form.name} onChange={(event) => field("name", event.target.value)} className="ui-input w-full px-4 py-3" placeholder={en ? "Solution practice name" : "方案实践名称"} /></Field>
          <Field label={en ? "Context" : "背景信息"}><div className="mb-2 flex justify-end"><BackgroundFillDialog name={form.name} description={form.description} referenceUrl={form.reference_url} onApply={(content) => field("description", content)} /></div><textarea rows={7} maxLength={5000} value={form.description} onChange={(event) => field("description", event.target.value)} className="ui-input w-full resize-y px-4 py-3" placeholder={en ? "Business context, solution capabilities, use cases and constraints" : "业务背景、方案能力、适用场景和关键约束"} /></Field>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label={en ? "Category" : "分类"}><input value={form.category} onChange={(event) => field("category", event.target.value)} className="ui-input w-full px-3 py-3" placeholder={en ? "Uncategorized" : "未分类"} /></Field>
            <Field label={en ? "Status" : "状态"}><select value={form.status} onChange={(event) => field("status", event.target.value)} className="ui-input w-full px-3 py-3"><option value="draft">{en ? "Draft" : "草稿"}</option><option value="active">{en ? "Active" : "使用中"}</option><option value="deprecated">{en ? "Deprecated" : "已弃用"}</option><option value="archived">{en ? "Archived" : "已归档"}</option></select></Field>
            <Field label={en ? "Version" : "版本"}><input value={form.version} onChange={(event) => field("version", event.target.value)} className="ui-input w-full px-3 py-3" /></Field>
          </div>
          <Field label={en ? "Reference URL" : "参考链接"}><input type="url" value={form.reference_url} onChange={(event) => field("reference_url", event.target.value)} className="ui-input w-full px-4 py-3" placeholder="https://" /></Field>
          <div className="flex flex-wrap justify-between gap-3 pt-2">
            <Link href="/workbench/solutions" className="ui-button-secondary"><ArrowLeft className="h-4 w-4" />{en ? "Back" : "返回"}</Link>
            <button disabled={saving} className="ui-button-primary">{saving ? (en ? "Creating..." : "正在创建") : (en ? "Create practice" : "创建方案实践")}<ArrowRight className="h-4 w-4" /></button>
          </div>
        </form>
        <aside className="rounded-xl bg-primary-dark p-6 text-white lg:sticky lg:top-20 lg:self-start"><Blocks className="h-5 w-5 text-white/70" /><p className="mt-5 font-mono text-xs text-white/50">CONTEXT</p><h2 className="mt-2 type-h3">{en ? "A manageable solution" : "形成可管理方案"}</h2><p className="mt-3 text-sm leading-6 text-white/65">{en ? "This context is injected into Insight Agent and maintained with the practice." : "背景信息会在进入 Insight Agent 时自动注入，并随方案实践持续维护。"}</p></aside>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="block"><span className="mb-2 block text-sm font-semibold text-ink-secondary">{label}</span>{children}</div>;
}

export default function SolutionCreatePage() {
  return <Suspense fallback={<div className="h-96 animate-shimmer rounded-xl bg-white" />}><SolutionCreateForm /></Suspense>;
}
