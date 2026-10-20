"use client";

import Link from "next/link";
import { Activity, ArrowRight, Database, FolderKanban, ShieldCheck, UsersRound } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { usePreferences } from "@/lib/preferences";

type Module = { href: string; title: string; titleEn: string; description: string; descriptionEn: string; icon: LucideIcon; meta: string; metaEn: string };
type Metric = { label: string; value: string | number };
type Health = "success" | "warning" | "error";
type Overview = {
  runtime: { health: Health; model: string; requests: number; activeRuntimes: number };
  access: { health: Health; users: number; admins: number; active: number };
  knowledge: { health: Health; documents: number; chunks: number; pending: number };
  analytics: { health: Health; pv: number; uv: number; pages: number };
  tasks: { health: Health; total: number; running: number; failed: number };
  applications: { health: Health; total: number; done: number; failed: number; pending: number; byVendor: { vendor: string; total: number; done: number }[] };
};

const modules: Module[] = [
  { href: "/admin/runtime", title: "运行与数据", titleEn: "Runtime & data", description: "模型连接、数据源与邮件订阅", descriptionEn: "Models, data sources and email subscriptions", icon: Database, meta: "配置层", metaEn: "Configure" },
  { href: "/admin/access", title: "用户与权限", titleEn: "Users & access", description: "成员、角色、AI Space 与 Runtime", descriptionEn: "Members, roles, AI Spaces and runtimes", icon: UsersRound, meta: "权限层", metaEn: "Access" },
  { href: "/admin/knowledge", title: "知识库与产物", titleEn: "Knowledge & artifacts", description: "公共知识、向量索引与产物审核", descriptionEn: "Public knowledge, indexes and artifact review", icon: FolderKanban, meta: "内容层", metaEn: "Content" },
  { href: "/admin/dashboard", title: "数据看板", titleEn: "Analytics dashboard", description: "访问趋势、用户身份与页面使用", descriptionEn: "Traffic, identities and page usage", icon: Activity, meta: "观测", metaEn: "Observe" },
  { href: "/admin/tasks", title: "任务中心", titleEn: "Task center", description: "采集、AI 分析、同步与邮件执行", descriptionEn: "Crawling, AI, sync and email jobs", icon: ShieldCheck, meta: "运行", metaEn: "Operate" },
];

export default function AdminPage() {
  const { user, loading } = useAuth();
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [overview, setOverview] = useState<Overview | null>(null);

  useEffect(() => {
    if (user?.app_metadata?.role !== "admin") return;
    let active = true;
    const get = (path: string) => authenticatedFetch(`${API}${path}`).then(response => response.ok ? response.json() : Promise.reject());
    void Promise.allSettled([
      get("/api/auth/admin/runtime-config"), get("/api/auth/agent-spaces"), get("/api/auth/users"),
      get("/api/agent/knowledge/overview"), get("/api/agent/admin/artifacts/requests"),
      get("/api/analytics?days=7"), get("/api/admin/tasks?limit=10"),
      get("/api/agent-launches/progress"),
    ]).then(([runtimeResult, spacesResult, usersResult, knowledgeResult, artifactsResult, analyticsResult, tasksResult, progressResult]) => {
      if (!active) return;
      const runtime = runtimeResult.status === "fulfilled" ? runtimeResult.value : {};
      const spaces = spacesResult.status === "fulfilled" ? spacesResult.value : {};
      const users = usersResult.status === "fulfilled" ? usersResult.value : {};
      const knowledge = knowledgeResult.status === "fulfilled" ? knowledgeResult.value : {};
      const artifacts = artifactsResult.status === "fulfilled" ? artifactsResult.value : {};
      const analytics = analyticsResult.status === "fulfilled" ? analyticsResult.value : {};
      const tasks = tasksResult.status === "fulfilled" ? tasksResult.value : {};
      const progress = progressResult.status === "fulfilled" ? progressResult.value : {};
      const accounts = users.users || [];
      const taskItems = tasks.tasks || [];
      const failedTasks = taskItems.filter((item: { last_run?: { status?: string } }) => item.last_run?.status === "failed").length;
      const runningTasks = taskItems.filter((item: { last_run?: { status?: string } }) => item.last_run?.status === "running").length;
      setOverview({
        runtime: { health: runtimeResult.status === "rejected" || spacesResult.status === "rejected" ? "error" : runtime.api_key_configured ? "success" : "warning", model: runtime.config?.CHAT_MODEL || "—", requests: runtime.usage?.today?.requests || 0, activeRuntimes: spaces.active_runtimes || 0 },
        access: { health: usersResult.status === "fulfilled" ? "success" : "error", users: users.total || accounts.length, admins: accounts.filter((item: { role?: string }) => item.role === "admin").length, active: accounts.filter((item: { status?: string }) => item.status !== "disabled").length },
        knowledge: { health: knowledgeResult.status === "rejected" || artifactsResult.status === "rejected" ? "error" : (artifacts.items || []).length ? "warning" : "success", documents: knowledge.documents || 0, chunks: knowledge.chunks || 0, pending: (artifacts.items || []).length },
        analytics: { health: analyticsResult.status === "fulfilled" ? "success" : "error", pv: analytics.today?.pv || 0, uv: analytics.today?.uv || 0, pages: (analytics.pages || []).length },
        tasks: { health: tasksResult.status === "rejected" || failedTasks ? "error" : runningTasks ? "warning" : "success", total: taskItems.length, running: runningTasks, failed: failedTasks },
        applications: { health: progressResult.status === "rejected" ? "error" : (progress.failed || 0) > 0 ? "warning" : (progress.done || 0) > 0 && progress.done === progress.total ? "success" : "warning", total: progress.total || 0, done: progress.done || 0, failed: progress.failed || 0, pending: progress.pending || 0, byVendor: progress.by_vendor || [] },
      });
    });
    return () => { active = false; };
  }, [user]);
  if (loading) return <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "Checking permissions…" : "正在验证权限…"}</div>;
  if (user?.app_metadata?.role !== "admin") return <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "Administrator access required." : "需要管理员权限。"}</div>;
  const healths = overview ? [overview.runtime.health, overview.access.health, overview.knowledge.health, overview.analytics.health, overview.tasks.health] : [];
  const overall: Health = healths.includes("error") ? "error" : healths.includes("warning") ? "warning" : "success";
  return <div className="page-stack">
    <SectionHeader badge="Admin" title={en ? "Platform overview" : "平台管理"} subtitle={en ? "Configure, operate and observe InsightPro from one screen." : "在一个界面中完成配置、运行与观测。"} action={overview ? <StatusBadge health={overall} en={en} /> : <div className="h-7 w-20 animate-shimmer rounded-full" />} />
    <section aria-labelledby="control-title"><div className="mb-3 flex items-center justify-between"><h2 id="control-title" className="type-h3 text-ink">{en ? "Platform controls" : "平台控制"}</h2><span className="text-xs text-ink-muted">{en ? "Live overview" : "实时摘要"}</span></div><div className="grid gap-3 lg:grid-cols-3">{modules.slice(0, 3).map(item => <ModuleCard key={item.href} item={item} en={en} metrics={metricsFor(item.href, overview, en)} health={healthFor(item.href, overview)} loading={!overview} />)}</div></section>
    <section aria-labelledby="operations-title"><div className="mb-3 flex items-center justify-between"><h2 id="operations-title" className="type-h3 text-ink">{en ? "Operations & visibility" : "运行与观测"}</h2><span className="text-xs text-ink-muted">{en ? "Execution to outcome" : "从任务到结果"}</span></div><div className="grid gap-3 md:grid-cols-2">{modules.slice(3).map(item => <ModuleCard key={item.href} item={item} en={en} metrics={metricsFor(item.href, overview, en)} health={healthFor(item.href, overview)} loading={!overview} />)}</div></section>
    <section aria-labelledby="ai-apps-title" className="ui-card">
      <div className="mb-4 flex items-center justify-between gap-3"><h2 id="ai-apps-title" className="type-h3 text-ink">{en ? "AI application analysis" : "AI 应用分析进度"}</h2><span className="text-xs text-ink-muted">{en ? "Structured analysis pipeline" : "结构化分析管线"}</span></div>
      {overview ? <ApplicationProgress app={overview.applications} en={en} /> : <div className="h-16 animate-shimmer rounded-xl" />}
    </section>
  </div>;
}

function ModuleCard({ item, en, metrics, health, loading }: { item: Module; en: boolean; metrics: Metric[]; health: Health; loading: boolean }) {
  return <Link href={item.href} className="ui-card ui-card-interactive group flex min-h-52 flex-col"><div className="flex items-start justify-between gap-4"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-soft text-primary"><item.icon className="h-5 w-5" /></span>{loading ? <div className="h-6 w-16 animate-shimmer rounded-full" /> : <StatusBadge health={health} en={en} />}</div><div className="mt-5 flex items-center justify-between gap-3"><h3 className="type-h3 text-ink">{en ? item.titleEn : item.title}</h3><ArrowRight className="h-4 w-4 text-ink-muted transition-transform group-hover:translate-x-1 group-hover:text-primary" /></div><p className="mt-1 text-xs text-ink-muted">{en ? item.descriptionEn : item.description}</p>{loading ? <div className="mt-auto grid grid-cols-3 gap-2 pt-5">{[0, 1, 2].map(item => <div key={item} className="h-14 animate-shimmer rounded-xl" />)}</div> : <dl className="mt-auto grid grid-cols-3 gap-2 pt-5">{metrics.map(metric => <div key={metric.label} className="rounded-xl bg-surface-subtle px-3 py-2.5"><dt className="truncate text-[10px] text-ink-muted">{metric.label}</dt><dd className="mt-1 truncate font-mono text-base font-semibold text-ink">{metric.value}</dd></div>)}</dl>}</Link>;
}

function StatusBadge({ health, en }: { health: Health; en: boolean }) {
  const label = health === "success" ? (en ? "Healthy" : "正常") : health === "warning" ? (en ? "Attention" : "待处理") : (en ? "Error" : "异常");
  return <span className={`ui-tag ${health === "success" ? "ui-tag-success" : health === "warning" ? "ui-tag-warning" : "ui-tag-danger"}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{label}</span>;
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: "warning" }) {
  return <div className="text-right"><p className={`font-mono text-lg font-semibold ${tone === "warning" ? "text-warning" : "text-ink"}`}>{value}</p><p className="text-[10px] text-ink-muted">{label}</p></div>;
}

function ApplicationProgress({ app, en }: { app: Overview["applications"]; en: boolean }) {
  const pct = app.total ? Math.round((app.done / app.total) * 100) : 0;
  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="flex-1">
          <div className="mb-1.5 flex justify-between text-xs text-ink-muted">
            <span>{en ? "Completed" : "完成进度"}</span>
            <span className="font-mono">{app.done}/{app.total}</span>
          </div>
          <div className="h-2 rounded-full bg-surface-subtle">
            <div className="h-2 rounded-full bg-primary transition-[width]" style={{ width: `${pct}%` }} />
          </div>
        </div>
        <div className="flex gap-5">
          <Stat label={en ? "Done" : "已分析"} value={app.done} />
          <Stat label={en ? "Failed" : "失败"} value={app.failed} tone={app.failed ? "warning" : undefined} />
          <Stat label={en ? "Total" : "总数"} value={app.total} />
        </div>
      </div>
      {app.byVendor.length > 0 && (
        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {app.byVendor.slice(0, 12).map((row) => {
            const vpct = row.total ? Math.round((row.done / row.total) * 100) : 0;
            return (
              <div key={row.vendor} className="rounded-lg bg-surface-subtle px-3 py-2">
                <div className="flex justify-between text-xs">
                  <span className="truncate text-ink-secondary">{row.vendor}</span>
                  <span className="font-mono text-ink-muted">{row.done}/{row.total}</span>
                </div>
                <div className="mt-1.5 h-1.5 rounded-full bg-grid">
                  <div className="h-1.5 rounded-full bg-primary" style={{ width: `${vpct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function healthFor(href: string, data: Overview | null): Health {
  if (!data) return "warning";
  if (href === "/admin/runtime") return data.runtime.health;
  if (href === "/admin/access") return data.access.health;
  if (href === "/admin/knowledge") return data.knowledge.health;
  if (href === "/admin/dashboard") return data.analytics.health;
  return data.tasks.health;
}

function metricsFor(href: string, data: Overview | null, en: boolean): Metric[] {
  if (!data) return [];
  if (href === "/admin/runtime") return [{ label: en ? "Model" : "当前模型", value: data.runtime.model }, { label: en ? "AI requests" : "今日 AI", value: data.runtime.requests }, { label: "Runtime", value: data.runtime.activeRuntimes }];
  if (href === "/admin/access") return [{ label: en ? "Users" : "用户", value: data.access.users }, { label: en ? "Active" : "启用", value: data.access.active }, { label: en ? "Admins" : "管理员", value: data.access.admins }];
  if (href === "/admin/knowledge") return [{ label: en ? "Documents" : "知识对象", value: data.knowledge.documents }, { label: en ? "Chunks" : "向量片段", value: data.knowledge.chunks }, { label: en ? "Pending" : "待审产物", value: data.knowledge.pending }];
  if (href === "/admin/dashboard") return [{ label: en ? "PV today" : "今日 PV", value: data.analytics.pv }, { label: en ? "UV today" : "今日 UV", value: data.analytics.uv }, { label: en ? "Pages" : "访问页面", value: data.analytics.pages }];
  return [{ label: en ? "Tasks" : "任务数", value: data.tasks.total }, { label: en ? "Running" : "运行中", value: data.tasks.running }, { label: en ? "Failed" : "失败", value: data.tasks.failed }];
}
