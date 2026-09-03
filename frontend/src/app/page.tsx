"use client";

import {
  ArrowUpRight,
  BarChart3,
  ChevronRight,
  Clock,
  History,
  Layers3,
  Blocks,
  Radio,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import type { LucideIcon } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { Solution, solutionStatusLabels, workbenchFetch } from "@/lib/workbench";

interface InsightModule {
  id: string;
  label: string;
  icon: LucideIcon;
  href: string;
  items: { title: string; tag: string }[];
  freshness?: string;
  status?: "fresh" | "empty";
}

interface ApiModule {
  id: string;
  items?: { title: string; tag?: string }[];
  as_of?: string;
  status?: "fresh" | "empty";
}

const modules: InsightModule[] = [
  { id: "hotspots", label: "技术热点", icon: Radio, href: "/insights/hotspots", items: [] },
  { id: "solutions", label: "解决方案洞察", icon: Layers3, href: "/insights/solutions", items: [] },
  { id: "competitors", label: "友商洞察", icon: ShieldCheck, href: "/insights/competitors", items: [] },
];

export default function HomePage() {
  const { user } = useAuth();
  const [dynamicModules, setDynamicModules] = useState(modules);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [practices, setPractices] = useState<Solution[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const [moduleResponse, statsResponse] = await Promise.all([
          fetch(`${API}/api/homepage/modules`),
          fetch(`${API}/api/homepage/stats`),
        ]);
        if (moduleResponse.ok) {
          const data = await moduleResponse.json() as ApiModule[];
          setDynamicModules(modules.map((module) => {
            const source = data.find((item) => item.id === module.id);
            const items = source?.items || [];
            return { ...module, items: items.map((item) => ({ title: item.title, tag: item.tag || "" })), freshness: source?.as_of, status: source?.status };
          }));
        }
        if (statsResponse.ok) setStats(await statsResponse.json());
      } catch {
        // The empty states below keep the homepage usable while data refreshes.
      }
    };
    void load();
  }, []);

  useEffect(() => {
    if (!user) return;
    void workbenchFetch<Solution[]>("/solutions").then(setPractices).catch(() => setPractices([]));
  }, [user]);

  return (
    <div className="page-stack">
      <section className="overflow-hidden rounded-2xl bg-primary-dark text-white shadow-[var(--shadow-brand)]">
        <div className="grid lg:grid-cols-[1.08fr_0.92fr]">
          <div className="flex flex-col justify-center px-6 py-10 md:px-10 md:py-12 lg:px-12">
            <div className="inline-flex w-fit items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-white/80">
              <Clock className="h-3 w-3" />
              Technical Solution Intelligence
            </div>
            <h1 className="mt-6 max-w-2xl serif-display text-white">
              从技术信号，到可落地的方案实践。
            </h1>
            <p className="mt-5 max-w-xl text-[0.9375rem] leading-7 text-white/70">
              发现值得关注的技术变化，判断落地价值，再用 AI 协作沉淀为可验证、可交付的解决方案实践。
            </p>
          </div>
          <div className="grid gap-2 bg-white/5 p-3 md:p-4 lg:grid-rows-3">
            {[
              ["发现信号", "捕捉技术与方案变化"],
              ["判断价值", "提炼场景、能力与风险"],
              ["形成实践", "协作完成验证与交付"],
            ].map(([title, description], index) => (
              <div key={title} className="group flex min-h-28 items-center gap-5 rounded-xl bg-white/[0.08] px-6 py-5 transition-colors hover:bg-white/[0.13]">
                <span className="font-mono text-3xl font-bold tracking-[-0.08em] text-white/25 transition-colors group-hover:text-white/45">0{index + 1}</span>
                <div className="min-w-0">
                  <p className="text-xl font-bold tracking-tight text-white">{title}</p>
                  <p className="mt-1 text-sm leading-6 text-white/65">{description}</p>
                </div>
                <ChevronRight className="ml-auto h-5 w-5 text-white/30 transition-transform group-hover:translate-x-1 group-hover:text-white/70" />
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { label: "方案目录", value: stats.solution_count || 0, unit: "项", icon: Layers3, href: "/insights/solutions" },
          { label: "近 7 日变化", value: stats.solution_recent_count || 0, unit: "项", icon: ArrowUpRight, href: "/insights/solutions" },
          { label: "今日技术热点", value: stats.trending_today || 0, unit: "个", icon: Radio, href: "/insights/hotspots" },
          { label: "AI 价值评估", value: stats.evaluation_today || 0, unit: "项", icon: ShieldCheck, href: "/insights/hotspots" },
        ].map((item) => (
          <Link key={item.label} href={item.href} className="ui-card ui-card-interactive group flex min-h-40 flex-col justify-between">
            <item.icon className="h-5 w-5 text-primary" strokeWidth={1.7} />
            <div>
            <p className="mb-2 swiss-kicker">{item.label}</p>
            <div className="flex items-baseline gap-1">
              <span className="text-[2rem] text-ink serif-stat">{item.value}</span>
              <span className="type-meta">{item.unit}</span>
            </div>
            </div>
          </Link>
        ))}
      </section>

      <section className="space-y-5">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="swiss-kicker text-primary">Technology radar</p>
            <h2 className="mt-1 type-h2 text-ink">今日技术信号</h2>
          </div>
          <span className="type-meta hidden sm:block">从变化到选型判断 →</span>
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          {dynamicModules.map((module) => (
            <Link key={module.id} href={module.href} className="ui-card ui-card-interactive group">
              <div className="ui-card-header">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-soft text-primary">
                  <module.icon className="h-4 w-4" strokeWidth={1.5} />
                </div>
                <h3 className="type-h3 flex-1 text-ink">{module.label}</h3>
                <ChevronRight className="h-4 w-4 text-primary transition-transform group-hover:translate-x-1" />
              </div>
              <div className="space-y-2">
                <p className="text-[11px] text-ink-muted">{module.status === "fresh" ? `数据状态 · ${module.freshness || "已更新"}` : "数据状态 · 暂无可用数据"}</p>
                {module.items.length === 0 && <p className="type-meta">暂无可用数据，请稍后重试</p>}
                {module.items.map((item) => (
                  <div key={`${module.id}-${item.title}`} className="rounded-lg bg-surface-subtle px-3.5 py-3">
                    <p className="line-clamp-2 text-[0.8125rem] leading-5 text-ink-secondary">{item.title}</p>
                    <span className="mt-1.5 block font-mono text-[10px] font-semibold text-ink-muted">{item.tag}</span>
                  </div>
                ))}
              </div>
            </Link>
          ))}
        </div>
      </section>

      <section className="rounded-2xl bg-surface-subtle p-4 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div><p className="swiss-kicker text-primary">Solution practice</p><h2 className="mt-1 type-h2 text-ink">把有价值的信号变成方案实践</h2></div>
          <div className="flex gap-2"><Link href="/workbench/ai" className="ui-button-secondary">AI 工作</Link><Link href="/workbench/solutions/new" className="ui-button-primary">收纳方案实践</Link></div>
        </div>
        <div className="mt-5 grid gap-3 lg:grid-cols-[220px_minmax(0,1fr)]">
          <Link href="/workbench/solutions" className="rounded-xl bg-white p-5 transition-shadow hover:shadow-[var(--shadow-card)]"><Blocks className="h-5 w-5 text-primary" /><p className="mt-5 swiss-kicker text-ink-muted">方案实践</p><p className="mt-1 serif-stat text-3xl text-ink">{user ? practices.length : 0}</p></Link>
          <div className="rounded-xl bg-white p-5"><div className="flex items-center justify-between"><h3 className="type-h3 text-ink">最近方案实践</h3><Link href="/workbench/solutions/new" className="ui-link text-xs">收纳实践</Link></div><div className="mt-3 space-y-2">{practices.slice(0, 3).map((item) => <Link key={item.id} href={`/workbench/solutions/${item.id}`} className="flex items-center justify-between gap-3 rounded-lg bg-surface-subtle px-3 py-2.5 text-sm transition-colors hover:bg-primary-soft"><span className="truncate font-medium text-ink-secondary">{item.name}</span><span className="ui-tag shrink-0">{solutionStatusLabels[item.status]}</span></Link>)}{!practices.length && <p className="py-5 text-center text-sm text-ink-muted">{user ? "还没有方案实践" : "登录后查看工作台信息"}</p>}</div></div>
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        <Link href="/insights/solutions" className="ui-button-primary">
          <Layers3 className="h-3.5 w-3.5" />
          浏览方案目录
        </Link>
        <Link href="/history" className="ui-button-secondary">
          <History className="h-3.5 w-3.5" />
          历史日报
        </Link>
        <Link href="/dashboard" className="ui-button-secondary">
          <BarChart3 className="h-3.5 w-3.5" />
          数据大屏
        </Link>
      </div>
    </div>
  );
}
