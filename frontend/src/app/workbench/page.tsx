"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Blocks, Bot, FileCode2, FileText, MessageSquare, Plus, Sparkles } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { AgentAction } from "@/components/agent-action";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { Solution, workbenchFetch } from "@/lib/workbench";
import { usePreferences } from "@/lib/preferences";

type Session = { id: string; title: string; task_title?: string; context_title?: string; task_status?: string };
type Artifact = { id: string; filename?: string; title: string; type: string; knowledge_status?: string; created_at: string };

export default function AIWorkbenchPage() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const { user, loading: authLoading } = useAuth();
  const [solutions, setSolutions] = useState<Solution[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) return;
    Promise.all([
      workbenchFetch<Solution[]>("/solutions"),
      authenticatedFetch("/api/agent/chat/sessions").then((response) => response.ok ? response.json() : { items: [] }),
      authenticatedFetch("/api/agent/artifacts").then((response) => response.ok ? response.json() : { items: [] }),
    ]).then(([solutionItems, sessionData, artifactData]) => {
      setSolutions(solutionItems);
      setSessions(sessionData.items || []);
      setArtifacts(artifactData.items || []);
    }).catch((reason) => setError(reason instanceof Error ? reason.message : (en ? "Could not load Insight Agent" : "Insight Agent 加载失败")))
      .finally(() => setLoading(false));
  }, [user]);

  if (!authLoading && !user) return <div className="ui-card mx-auto mt-20 max-w-lg py-12 text-center"><Bot className="mx-auto h-8 w-8 text-primary" /><h1 className="mt-4 type-h2 text-ink"> {en ? "Sign in to use Insight Agent" : "登录后进入 Insight Agent"}</h1><p className="mt-2 text-sm text-ink-muted"> {en ? "Solution practices, Insight Agent sessions and artifacts are visible only to their owner." : "方案实践、Insight Agent 和成果仅对所属用户可见。"}</p><Link href="/auth/login?next=/workbench" className="ui-button-primary mt-5"> {en ? "Sign in" : "前往登录"}</Link></div>;

  const solution = solutions[0];
  const stages = [
    [Blocks, en ? "Solution Practices" : "方案实践", solutions.length, "/workbench/solutions"],
    [MessageSquare, "Insight Agent", sessions.length, "/workbench/ai"],
    [FileCode2, en ? "Working files" : "工作文件", artifacts.length, "/workbench/ai"],
    [FileText, en ? "Artifacts" : "成果", artifacts.filter((item) => item.knowledge_status === "published").length, "/workbench/ai"],
  ] as const;

  return <div className="page-stack">
    <section className="overflow-hidden rounded-2xl bg-primary-dark text-white shadow-[var(--shadow-elevated)]">
      <div className="grid gap-8 px-6 py-8 lg:grid-cols-[1fr_auto] lg:items-end lg:px-9 lg:py-10">
        <div><p className="font-mono text-[11px] font-semibold uppercase tracking-[.14em] text-white/60">Insight Agent</p><h1 className="mt-3 text-3xl font-semibold tracking-[-.035em] sm:text-4xl"> {en ? "Move from context to output in one place" : "从背景到成果，在一个地方推进"}</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-white/70"> {en ? "Solution practices organize context for Insight Agent; working files and artifacts stay together." : "方案实践会整理背景信息并自动注入 Insight Agent，生成的工作文件和成果也集中保留。"}</p></div>
        <Link href="/workbench/ai" className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-primary-dark shadow-lg hover:bg-primary-soft"><Sparkles className="h-4 w-4" /> {en ? "Start Insight Agent" : "开始 Insight Agent"}</Link>
      </div>
      <div className="grid border-t border-white/15 sm:grid-cols-4">{stages.map(([Icon, label, count, href], index) => <Link key={label} href={href} className="group flex items-center gap-3 border-white/15 px-5 py-4 hover:bg-white/10 sm:border-r sm:last:border-r-0"><span className="font-mono text-xs text-white/40">0{index + 1}</span><Icon className="h-4 w-4 text-white/75" /><span className="text-sm font-medium">{label}</span><span className="ml-auto font-mono text-sm text-white/55">{count}</span></Link>)}</div>
    </section>

    {error && <div role="alert" className="rounded-xl bg-warning-soft px-5 py-4 text-sm text-warning">{error}</div>}

    <section className="grid gap-3 lg:grid-cols-3">
      <Link href="/workbench/solutions/new" className="ui-card ui-card-interactive group"><div className="flex items-center justify-between"><Blocks className="h-5 w-5 text-primary" /><Plus className="h-4 w-4 text-ink-muted" /></div><h2 className="mt-6 type-h3 text-ink"> {en ? "Save a solution practice" : "收纳方案实践"}</h2><p className="mt-2 text-sm text-ink-muted"> {en ? "Gather business context, sources and constraints for AI analysis." : "整理业务背景、来源信息和关键约束，作为 AI 的工作上下文。"}</p></Link>
      {solution ? <AgentAction contextType="solution" contextId={solution.id} actionKey="architecture" className="ui-card ui-card-interactive text-left"><Bot className="h-5 w-5 text-primary" /><h2 className="mt-6 type-h3 text-ink"> {en ? "Analyze a recent practice" : "分析最近实践"}</h2><p className="mt-2 truncate text-sm text-ink-muted">{solution.name}</p></AgentAction> : <Link href="/workbench/solutions/new" className="ui-card ui-card-interactive"><Bot className="h-5 w-5 text-primary" /><h2 className="mt-6 type-h3 text-ink"> {en ? "Start solution analysis" : "开始方案分析"}</h2><p className="mt-2 text-sm text-ink-muted"> {en ? "Save a solution practice first." : "先收纳一项方案实践。"}</p></Link>}
      {solution ? <AgentAction contextType="solution" contextId={solution.id} actionKey="implement" className="ui-card ui-card-interactive text-left"><Sparkles className="h-5 w-5 text-primary" /><h2 className="mt-6 type-h3 text-ink"> {en ? "Continue Insight Agent" : "继续 Insight Agent"}</h2><p className="mt-2 truncate text-sm text-ink-muted">{solution.name}</p></AgentAction> : <Link href="/workbench/ai" className="ui-card ui-card-interactive"><Sparkles className="h-5 w-5 text-primary" /><h2 className="mt-6 type-h3 text-ink"> {en ? "Start Insight Agent" : "开始 Insight Agent"}</h2><p className="mt-2 text-sm text-ink-muted"> {en ? "You can also begin with a free discussion." : "也可以从自由讨论开始。"}</p></Link>}
    </section>

    <section className="grid gap-4 xl:grid-cols-2">
      <WorkList title={en ? "Recent solution practices" : "最近方案实践"} links={solutions.slice(0, 6).map((item) => ({ id: `s-${item.id}`, title: item.name, meta: en ? "Solution Practice" : "方案实践", href: `/workbench/solutions/${item.id}` }))} empty={en ? "No solution practices yet" : "还没有方案实践"} loading={loading || authLoading} />
      <WorkList title={en ? "Recent Insight Agent sessions and files" : "最近 Insight Agent 与文件"} links={[...sessions.slice(0, 4).map((item) => ({ id: `a-${item.id}`, title: item.task_title || item.title, meta: item.context_title || "Insight Agent", href: `/workbench/ai?session=${item.id}` })), ...artifacts.slice(0, 2).map((item) => ({ id: `f-${item.id}`, title: item.filename || item.title, meta: item.type || (en ? "Working file" : "工作文件"), href: "/workbench/ai" }))]} empty={en ? "No Insight Agent records yet" : "还没有 Insight Agent 记录"} loading={loading || authLoading} />
    </section>
  </div>;
}

function WorkList({ title, links, empty, loading }: { title: string; links: { id: string; title: string; meta: string; href: string }[]; empty: string; loading: boolean }) {
  return <section className="ui-card"><div className="flex items-center justify-between"><h2 className="type-h3 text-ink">{title}</h2><span className="font-mono text-xs text-ink-muted">{links.length}</span></div><div className="mt-5 divide-y divide-grid">{loading ? <div className="h-28 animate-shimmer rounded-xl" /> : links.length ? links.map((item) => <Link key={item.id} href={item.href} className="group flex items-center gap-4 py-3.5"><span className="ui-tag shrink-0">{item.meta}</span><span className="min-w-0 flex-1 truncate text-sm font-medium text-ink-secondary">{item.title}</span><ArrowRight className="h-4 w-4 text-ink-muted transition-transform group-hover:translate-x-1 group-hover:text-primary" /></Link>) : <p className="py-10 text-center text-sm text-ink-muted">{empty}</p>}</div></section>;
}
