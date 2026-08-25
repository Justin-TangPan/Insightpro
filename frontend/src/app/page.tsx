"use client";

import {
  ArrowUpRight,
  BarChart3,
  ChevronRight,
  Clock,
  History,
  Layers3,
  Radio,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import type { LucideIcon } from "lucide-react";

type Accent = "lime" | "signal" | "ink";

interface InsightModule {
  id: string;
  label: string;
  icon: LucideIcon;
  href: string;
  accent: Accent;
  items: { title: string; tag: string }[];
}

interface ApiModule {
  id: string;
  items?: { title: string; tag?: string }[];
}

const modules: InsightModule[] = [
  { id: "hotspots", label: "技术热点", icon: Radio, href: "/insights/hotspots", accent: "lime", items: [] },
  { id: "solutions", label: "解决方案洞察", icon: Layers3, href: "/insights/solutions", accent: "signal", items: [] },
  { id: "competitors", label: "友商洞察", icon: ShieldCheck, href: "/insights/competitors", accent: "ink", items: [] },
];

const accentBar: Record<Accent, string> = {
  lime: "swiss-accent-bar swiss-accent-bar-lime",
  signal: "swiss-accent-bar swiss-accent-bar-signal",
  ink: "swiss-accent-bar",
};

const accentTile: Record<Accent, string> = {
  lime: "bg-lime text-ink",
  signal: "bg-signal text-paper",
  ink: "bg-ink text-paper",
};

export default function HomePage() {
  const [dynamicModules, setDynamicModules] = useState(modules);
  const [stats, setStats] = useState<Record<string, number>>({});

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
            const items = data.find((item) => item.id === module.id)?.items || [];
            return { ...module, items: items.map((item) => ({ title: item.title, tag: item.tag || "" })) };
          }));
        }
        if (statsResponse.ok) setStats(await statsResponse.json());
      } catch {
        // The empty states below keep the homepage usable while data refreshes.
      }
    };
    void load();
  }, []);

  return (
    <div className="space-y-10">
      <section className="overflow-hidden bg-ink text-paper">
        <div className="grid lg:grid-cols-[1.4fr_0.6fr]">
          <div className="px-8 py-12 md:px-12 md:py-16">
            <div className="inline-flex items-center gap-1.5 bg-lime px-2.5 py-1 text-ink swiss-kicker">
              <Clock className="h-3 w-3" />
              Technical Solution Intelligence
            </div>
            <h1 className="mt-6 max-w-3xl text-5xl text-paper serif-display md:text-7xl">
              技术方案，先看懂变化。
            </h1>
            <p className="mt-6 max-w-xl text-sm leading-7 text-paper/60">
              持续跟踪技术项目、云厂商解决方案与产品动向，把分散更新整理成可比较、可落地的方案判断。
            </p>
          </div>
          <div className="grid grid-rows-3 border-t border-paper/15 lg:border-l lg:border-t-0">
            {[
              ["发现", "捕捉技术与方案更新"],
              ["理解", "提炼能力、场景与价值"],
              ["应用", "对比路径并辅助选型"],
            ].map(([title, description], index) => (
              <div key={title} className="flex items-center gap-5 border-b border-paper/15 px-8 py-6 last:border-b-0">
                <span className="text-xs font-semibold text-lime">0{index + 1}</span>
                <div>
                  <p className="text-lg font-bold">{title}</p>
                  <p className="mt-1 text-xs text-paper/45">{description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-px border border-grid bg-grid lg:grid-cols-4">
        {[
          { label: "方案目录", value: stats.solution_count || 0, unit: "项", icon: Layers3, href: "/insights/solutions" },
          { label: "近 7 日变化", value: stats.solution_recent_count || 0, unit: "项", icon: ArrowUpRight, href: "/insights/solutions" },
          { label: "今日技术热点", value: stats.trending_today || 0, unit: "个", icon: Radio, href: "/insights/hotspots" },
          { label: "AI 价值评估", value: stats.evaluation_today || 0, unit: "项", icon: ShieldCheck, href: "/insights/hotspots" },
        ].map((item) => (
          <Link key={item.label} href={item.href} className="group bg-white p-5 transition-colors hover:bg-paper">
            <item.icon className="mb-5 h-5 w-5 text-ink-secondary" strokeWidth={1.5} />
            <p className="mb-1 swiss-kicker text-ink-muted">{item.label}</p>
            <div className="flex items-baseline gap-1">
              <span className="text-3xl text-ink serif-stat">{item.value}</span>
              <span className="text-xs text-ink-muted">{item.unit}</span>
            </div>
          </Link>
        ))}
      </section>

      <section className="space-y-6">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="swiss-kicker text-signal">Solution intelligence desk</p>
            <h2 className="mt-1 text-3xl text-ink serif-heading">技术解决方案洞察</h2>
          </div>
          <span className="hidden text-xs text-ink-muted sm:block">从变化到选型判断 →</span>
        </div>

        <div className="grid gap-px border border-grid bg-grid lg:grid-cols-3">
          {dynamicModules.map((module) => (
            <Link key={module.id} href={module.href} className={`group bg-white p-6 transition-colors hover:bg-paper ${accentBar[module.accent]}`}>
              <div className="mb-5 flex items-center gap-3 border-b border-grid pb-4">
                <div className={`flex h-9 w-9 items-center justify-center ${accentTile[module.accent]}`}>
                  <module.icon className="h-4 w-4" strokeWidth={1.5} />
                </div>
                <h3 className="flex-1 text-sm font-semibold text-ink">{module.label}</h3>
                <ChevronRight className="h-4 w-4 text-ink-muted transition-transform group-hover:translate-x-1" />
              </div>
              <div className="space-y-3">
                {module.items.length === 0 && <p className="text-xs text-ink-muted">数据更新中</p>}
                {module.items.map((item) => (
                  <div key={`${module.id}-${item.title}`} className="border-l border-grid pl-3">
                    <p className="line-clamp-2 text-xs leading-5 text-ink-secondary">{item.title}</p>
                    <span className="mt-1 block text-[10px] font-semibold text-ink-muted">{item.tag}</span>
                  </div>
                ))}
              </div>
            </Link>
          ))}
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        <Link href="/insights/solutions" className="flex items-center gap-1.5 bg-ink px-4 py-2 text-xs font-semibold text-paper transition-colors hover:bg-signal">
          <Layers3 className="h-3.5 w-3.5" />
          浏览方案目录
        </Link>
        <Link href="/history" className="flex items-center gap-1.5 border border-grid px-4 py-2 text-xs font-medium text-ink-secondary transition-colors hover:border-ink hover:text-ink">
          <History className="h-3.5 w-3.5" />
          历史日报
        </Link>
        <Link href="/dashboard" className="flex items-center gap-1.5 border border-grid px-4 py-2 text-xs font-medium text-ink-secondary transition-colors hover:border-ink hover:text-ink">
          <BarChart3 className="h-3.5 w-3.5" />
          数据大屏
        </Link>
      </div>
    </div>
  );
}
