"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Blocks, Bot, ClipboardList, FileCode2, FileText, MessageSquare, Plus, Sparkles } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { AgentAction } from "@/components/agent-action";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { Requirement, Solution, workbenchFetch } from "@/lib/workbench";

type Session = { id: string; title: string; task_title?: string; context_title?: string; task_status?: string };
type Artifact = { id: string; title: string; type: string; created_at: string };

export default function AIWorkbenchPage() {
  const { user, loading: authLoading } = useAuth();
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [solutions, setSolutions] = useState<Solution[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) return;
    Promise.all([
      workbenchFetch<Requirement[]>("/requirements"),
      workbenchFetch<Solution[]>("/solutions"),
      authenticatedFetch("/api/agent/chat/sessions").then((response) => response.ok ? response.json() : { items: [] }),
      authenticatedFetch("/api/agent/artifacts").then((response) => response.ok ? response.json() : { items: [] }),
    ]).then(([requirementItems, solutionItems, sessionData, artifactData]) => {
      setRequirements(requirementItems);
      setSolutions(solutionItems);
      setSessions(sessionData.items || []);
      setArtifacts(artifactData.items || []);
    }).catch((reason) => setError(reason instanceof Error ? reason.message : "AI 工作台加载失败"))
      .finally(() => setLoading(false));
  }, [user]);

  if (!authLoading && !user) return <div className="ui-card mx-auto mt-20 max-w-lg py-12 text-center"><Bot className="mx-auto h-8 w-8 text-primary" /><h1 className="mt-4 type-h2 text-ink">登录后进入 AI 工作台</h1><p className="mt-2 text-sm text-ink-muted">需求、方案、AI 工作和成果仅对所属用户可见。</p><Link href="/auth/login?next=/workbench" className="ui-button-primary mt-5">前往登录</Link></div>;

  const requirement = requirements[0];
  const solution = solutions[0];
  const stages = [
    [ClipboardList, "需求", requirements.length, "/workbench/requirements"],
    [Blocks, "方案", solutions.length, "/workbench/solutions"],
    [MessageSquare, "AI 工作", sessions.length, "/workbench/ai"],
    [FileCode2, "工作文件", "—", "/workbench/ai"],
    [FileText, "成果", artifacts.length, "/workbench/ai"],
  ] as const;

  return <div className="page-stack">
    <section className="overflow-hidden rounded-2xl bg-primary-dark text-white shadow-[var(--shadow-elevated)]">
      <div className="grid gap-8 px-6 py-8 lg:grid-cols-[1fr_auto] lg:items-end lg:px-9 lg:py-10">
        <div><p className="font-mono text-[11px] font-semibold uppercase tracking-[.14em] text-white/60">AI Workbench</p><h1 className="mt-3 text-3xl font-semibold tracking-[-.035em] sm:text-4xl">从问题到成果，在一个地方推进</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-white/70">Requirement、Solution、AI 对话、工作文件和 Artifact 使用同一条工作链，不再分散成多个工作区。</p></div>
        <Link href="/workbench/ai" className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-primary-dark shadow-lg hover:bg-primary-soft"><Sparkles className="h-4 w-4" />开始 AI 工作</Link>
      </div>
      <div className="grid border-t border-white/15 sm:grid-cols-5">{stages.map(([Icon, label, count, href], index) => <Link key={label} href={href} className="group flex items-center gap-3 border-white/15 px-5 py-4 hover:bg-white/10 sm:border-r sm:last:border-r-0"><span className="font-mono text-xs text-white/40">0{index + 1}</span><Icon className="h-4 w-4 text-white/75" /><span className="text-sm font-medium">{label}</span><span className="ml-auto font-mono text-sm text-white/55">{count}</span></Link>)}</div>
    </section>

    {error && <div role="alert" className="rounded-xl bg-warning-soft px-5 py-4 text-sm text-warning">{error}</div>}

    <section className="grid gap-3 lg:grid-cols-3">
      <Link href="/workbench/requirements/new" className="ui-card ui-card-interactive group"><div className="flex items-center justify-between"><ClipboardList className="h-5 w-5 text-primary" /><Plus className="h-4 w-4 text-ink-muted" /></div><h2 className="mt-6 type-h3 text-ink">记录需求</h2><p className="mt-2 text-sm text-ink-muted">把洞察收敛为可跟踪的问题、约束和验收标准。</p></Link>
      {requirement ? <AgentAction contextType="requirement" contextId={requirement.id} actionKey="solution_design" className="ui-card ui-card-interactive text-left"><Bot className="h-5 w-5 text-primary" /><h2 className="mt-6 type-h3 text-ink">为需求设计方案</h2><p className="mt-2 truncate text-sm text-ink-muted">{requirement.title}</p></AgentAction> : <Link href="/workbench/requirements/new" className="ui-card ui-card-interactive"><Bot className="h-5 w-5 text-primary" /><h2 className="mt-6 type-h3 text-ink">为需求设计方案</h2><p className="mt-2 text-sm text-ink-muted">先创建一个 Requirement。</p></Link>}
      {solution ? <AgentAction contextType="solution" contextId={solution.id} actionKey="implement" className="ui-card ui-card-interactive text-left"><Sparkles className="h-5 w-5 text-primary" /><h2 className="mt-6 type-h3 text-ink">继续实现方案</h2><p className="mt-2 truncate text-sm text-ink-muted">{solution.name}</p></AgentAction> : <Link href="/workbench/solutions/new" className="ui-card ui-card-interactive"><Sparkles className="h-5 w-5 text-primary" /><h2 className="mt-6 type-h3 text-ink">继续实现方案</h2><p className="mt-2 text-sm text-ink-muted">先创建一个 Solution。</p></Link>}
    </section>

    <section className="grid gap-4 xl:grid-cols-2">
      <WorkList title="最近业务对象" links={[...requirements.slice(0, 3).map((item) => ({ id: `r-${item.id}`, title: item.title, meta: "Requirement", href: `/workbench/requirements/${item.id}` })), ...solutions.slice(0, 3).map((item) => ({ id: `s-${item.id}`, title: item.name, meta: "Solution", href: `/workbench/solutions/${item.id}` }))]} empty="还没有需求或方案" loading={loading || authLoading} />
      <WorkList title="最近 AI 工作与成果" links={[...sessions.slice(0, 4).map((item) => ({ id: `a-${item.id}`, title: item.task_title || item.title, meta: item.context_title || "AI Session", href: `/workbench/ai?session=${item.id}` })), ...artifacts.slice(0, 2).map((item) => ({ id: `f-${item.id}`, title: item.title, meta: item.type || "Artifact", href: "/workbench/ai" }))]} empty="还没有 AI 工作记录" loading={loading || authLoading} />
    </section>
  </div>;
}

function WorkList({ title, links, empty, loading }: { title: string; links: { id: string; title: string; meta: string; href: string }[]; empty: string; loading: boolean }) {
  return <section className="ui-card"><div className="flex items-center justify-between"><h2 className="type-h3 text-ink">{title}</h2><span className="font-mono text-xs text-ink-muted">{links.length}</span></div><div className="mt-5 divide-y divide-grid">{loading ? <div className="h-28 animate-shimmer rounded-xl" /> : links.length ? links.map((item) => <Link key={item.id} href={item.href} className="group flex items-center gap-4 py-3.5"><span className="ui-tag shrink-0">{item.meta}</span><span className="min-w-0 flex-1 truncate text-sm font-medium text-ink-secondary">{item.title}</span><ArrowRight className="h-4 w-4 text-ink-muted transition-transform group-hover:translate-x-1 group-hover:text-primary" /></Link>) : <p className="py-10 text-center text-sm text-ink-muted">{empty}</p>}</div></section>;
}
