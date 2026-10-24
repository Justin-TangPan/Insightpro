"use client";

import Link from "next/link";
import { ArrowRight, BookOpenCheck, ChartNoAxesCombined, Database, Mail, Plus, ShieldCheck, UsersRound } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { API } from "@/lib/api";
import { taskStatus } from "@/lib/admin-task-status";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { usePreferences } from "@/lib/preferences";

type Health = "success" | "running" | "waiting" | "error";
type Run = { status: string; started_at: string; finished_at: string | null };
type Task = { key: string; name: string; schedule: string; uses_ai: boolean; next_run_at: string | null; last_run: Run | null };
type Delivery = { status: string; delivery_date: string };
type Metric = { label: string; value: string | number };
type Overview = {
  updatedAt: string; available: number; totalServices: number;
  runtime: { health: Health; model: string; requests: number | null; activeRuntimes: number | null; sources: number | null };
  access: { health: Health; users: number | null; admins: number | null; active: number | null; spaces: number | null };
  knowledge: { health: Health; documents: number | null; chunks: number | null; pending: number | null };
  analytics: { health: Health; pv: number | null; uv: number | null; pages: number | null; daily: { date: string; pv: number; uv: number }[] };
  tasks: { health: Health; items: Task[]; loaded: boolean; running: number; failed: number };
  email: { health: Health; items: Delivery[]; loaded: boolean; running: number; failed: number };
  applications: { total: number; done: number; failed: number; byVendor: { vendor: string; total: number; done: number }[] };
};

const modules: { href: string; title: string; titleEn: string; description: string; descriptionEn: string; icon: LucideIcon; kind: "email" | "runtime" | "access" | "knowledge" | "analytics" }[] = [
  { href: "/admin/emails", title: "邮件投递", titleEn: "Email delivery", description: "商业与技术简报投递状态", descriptionEn: "Business and technical brief delivery", icon: Mail, kind: "email" },
  { href: "/admin/runtime", title: "运行与数据", titleEn: "Runtime & data", description: "模型连接、运行实例与数据源", descriptionEn: "Models, runtimes and data sources", icon: Database, kind: "runtime" },
  { href: "/admin/access", title: "用户与权限", titleEn: "Users & access", description: "成员、角色与 AI Space", descriptionEn: "Members, roles and AI Spaces", icon: UsersRound, kind: "access" },
  { href: "/admin/knowledge", title: "知识库与产物", titleEn: "Knowledge & artifacts", description: "公共知识、向量索引与产物审核", descriptionEn: "Knowledge, indexes and artifact review", icon: BookOpenCheck, kind: "knowledge" },
  { href: "/admin/dashboard", title: "数据看板", titleEn: "Analytics dashboard", description: "近 7 天访问与页面使用", descriptionEn: "Visits and page usage over 7 days", icon: ChartNoAxesCombined, kind: "analytics" },
];

const dateTime = (value?: string | null) => value ? new Date(value).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }) : "—";

function StatusBadge({ health, en, task = false }: { health: Health; en: boolean; task?: boolean }) {
  const labels = task ? { success: en ? "Success" : "成功", running: en ? "Running" : "运行中", waiting: en ? "Pending" : "等待", error: en ? "Failed" : "失败" } : { success: en ? "Healthy" : "正常", running: en ? "Running" : "运行中", waiting: en ? "Pending" : "等待", error: en ? "Issue" : "异常" };
  return <span className={`admin-status admin-status-${health}`}><i aria-hidden="true" />{labels[health]}</span>;
}

function MiniTrend({ values, tone = "blue" }: { values: number[]; tone?: "blue" | "green" }) {
  if (values.length < 2) return null;
  const max = Math.max(1, ...values);
  const points = values.map((value, index) => `${index * 100 / (values.length - 1)},${27 - value * 23 / max}`).join(" ");
  return <svg className={`admin-trend admin-trend-${tone}`} viewBox="0 0 100 30" preserveAspectRatio="none" role="img" aria-label="近期变化趋势"><polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" vectorEffect="non-scaling-stroke" /></svg>;
}

function metricsFor(kind: (typeof modules)[number]["kind"], data: Overview): Metric[] {
  const show = (value: number | null) => value ?? "—";
  if (kind === "email") {
    const sent = data.email.items.filter(item => item.status === "sent").length;
    const finished = data.email.items.filter(item => item.status === "sent" || item.status === "failed").length;
    return [{ label: "近期记录", value: data.email.loaded ? data.email.items.length : "—" }, { label: "运行中", value: data.email.loaded ? data.email.running : "—" }, { label: "失败", value: data.email.loaded ? data.email.failed : "—" }, { label: "近期成功率", value: finished ? `${Math.round(sent / finished * 100)}%` : "—" }];
  }
  if (kind === "runtime") return [{ label: "当前模型", value: data.runtime.model }, { label: "今日 AI", value: show(data.runtime.requests) }, { label: "Runtime", value: show(data.runtime.activeRuntimes) }, { label: "数据源", value: show(data.runtime.sources) }];
  if (kind === "access") return [{ label: "用户", value: show(data.access.users) }, { label: "启用", value: show(data.access.active) }, { label: "管理员", value: show(data.access.admins) }, { label: "AI Space", value: show(data.access.spaces) }];
  if (kind === "knowledge") return [{ label: "知识对象", value: show(data.knowledge.documents) }, { label: "向量片段", value: show(data.knowledge.chunks) }, { label: "待审产物", value: show(data.knowledge.pending) }];
  return [{ label: "今日 PV", value: show(data.analytics.pv) }, { label: "今日 UV", value: show(data.analytics.uv) }, { label: "访问页面", value: show(data.analytics.pages) }];
}

function ModuleCard({ item, data, en }: { item: (typeof modules)[number]; data: Overview | null; en: boolean }) {
  const health = data?.[item.kind].health ?? "waiting";
  const emailDays = data?.email.items.reduce<Record<string, number>>((days, item) => {
    if (item.status === "sent") days[item.delivery_date] = (days[item.delivery_date] || 0) + 1;
    return days;
  }, {}) || {};
  const trend = item.kind === "email" ? Object.entries(emailDays).sort(([a], [b]) => a.localeCompare(b)).slice(-7).map(([, count]) => count)
    : item.kind === "analytics" ? data?.analytics.daily.map(day => day.pv) || [] : [];
  return <Link href={item.href} className="admin-module-card"><div className="admin-module-top"><span className="admin-module-icon"><item.icon size={21} strokeWidth={1.9} /></span><StatusBadge health={health} en={en} /></div><div className="admin-module-title"><div><h3>{en ? item.titleEn : item.title}</h3><p>{en ? item.descriptionEn : item.description}</p></div><ArrowRight size={16} aria-hidden="true" /></div><MiniTrend values={trend} tone={item.kind === "email" ? "green" : "blue"} /><dl className="admin-module-metrics">{data ? metricsFor(item.kind, data).map(metric => <div key={metric.label}><dt>{metric.label}</dt><dd title={String(metric.value)}>{metric.value}</dd></div>) : [0, 1, 2, 3].slice(0, item.kind === "knowledge" || item.kind === "analytics" ? 3 : 4).map(index => <div key={index}><dt>读取中</dt><dd>—</dd></div>)}</dl></Link>;
}

export default function AdminPage() {
  const { user, loading } = useAuth();
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [overview, setOverview] = useState<Overview | null>(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    if (user?.app_metadata?.role !== "admin") return;
    let active = true;
    const get = (path: string) => authenticatedFetch(`${API}${path}`).then(response => response.ok ? response.json() : Promise.reject(new Error(String(response.status))));
    void Promise.allSettled([
      get("/api/auth/admin/runtime-config"), get("/api/auth/agent-spaces"), get("/api/auth/users"),
      get("/api/agent/knowledge/overview"), get("/api/agent/admin/artifacts/requests"),
      get("/api/analytics?days=7"), get("/api/admin/tasks?limit=10"),
      get("/api/agent-launches/progress"), get("/api/admin/email-deliveries?limit=100"), get("/api/v2/admin/sources"),
    ]).then(results => {
      if (!active) return;
      const values = results.map(result => result.status === "fulfilled" ? result.value : null);
      const [runtime, spaces, users, knowledge, artifacts, analytics, tasks, progress, deliveries, sources] = values;
      const accounts = users?.users || [];
      const taskItems: Task[] = tasks?.tasks || [];
      const emailItems: Delivery[] = deliveries?.items || [];
      const running = taskItems.filter(task => taskStatus(task) === "running").length;
      const failed = taskItems.filter(task => taskStatus(task) === "error").length;
      const emailTask = taskItems.filter(task => task.key === "scheduled_email");
      setOverview({
        updatedAt: new Date().toISOString(), available: values.filter(Boolean).length, totalServices: values.length,
        runtime: { health: !runtime || !spaces || !sources ? "error" : runtime.api_key_configured ? "success" : "waiting", model: runtime?.config?.CHAT_MODEL || "—", requests: runtime?.usage?.today?.requests ?? null, activeRuntimes: spaces?.active_runtimes ?? null, sources: sources?.items?.filter((item: { enabled: boolean }) => item.enabled).length ?? null },
        access: { health: users && spaces ? "success" : "error", users: users?.total ?? (users ? accounts.length : null), admins: users ? accounts.filter((item: { role?: string }) => item.role === "admin").length : null, active: users ? accounts.filter((item: { status?: string }) => item.status !== "disabled").length : null, spaces: spaces?.spaces?.length ?? null },
        knowledge: { health: !knowledge || !artifacts ? "error" : artifacts.items?.length ? "waiting" : "success", documents: knowledge?.documents ?? null, chunks: knowledge?.chunks ?? null, pending: artifacts?.items?.length ?? null },
        analytics: { health: analytics ? "success" : "error", pv: analytics?.today?.pv ?? null, uv: analytics?.today?.uv ?? null, pages: analytics?.pages?.length ?? null, daily: analytics?.daily || [] },
        tasks: { health: !tasks ? "error" : failed ? "error" : running ? "running" : "success", items: taskItems, loaded: !!tasks, running, failed },
        email: { health: !deliveries || !tasks ? "error" : emailItems.some(item => item.status === "failed") ? "error" : emailTask.some(task => taskStatus(task) === "running") ? "running" : "success", items: emailItems, loaded: !!deliveries, running: emailTask.filter(task => taskStatus(task) === "running").length, failed: emailItems.filter(item => item.status === "failed").length },
        applications: { total: progress?.total || 0, done: progress?.done || 0, failed: progress?.failed || 0, byVendor: progress?.by_vendor || [] },
      });
    });
    return () => { active = false; };
  }, [user]);

  if (loading) return <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "Checking permissions…" : "正在验证权限…"}</div>;
  if (user?.app_metadata?.role !== "admin") return <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "Administrator access required." : "需要管理员权限。"}</div>;

  const healths = overview ? [overview.runtime.health, overview.access.health, overview.knowledge.health, overview.analytics.health, overview.tasks.health, overview.email.health] : [];
  const overall: Health = !overview ? "waiting" : healths.includes("error") ? "error" : overview.tasks.running ? "running" : healths.includes("waiting") ? "waiting" : "success";
  const nextRun = overview?.tasks.items.map(task => task.next_run_at).filter((value): value is string => !!value && new Date(value).getTime() > Date.parse(overview.updatedAt)).sort()[0];
  const filteredTasks = (overview?.tasks.items || []).filter(task => filter === "all" || filter === "scheduled" && !!task.next_run_at || taskStatus(task) === filter).sort((a, b) => (b.last_run?.started_at || "").localeCompare(a.last_run?.started_at || "")).slice(0, 6);
  const completed = overview?.tasks.items.filter(task => taskStatus(task) === "success").length || 0;

  return <div className="admin-home">
    <section className="admin-hero" aria-labelledby="admin-home-title"><div className="admin-hero-main"><span className="admin-eyebrow">ADMIN</span><h1 id="admin-home-title">{en ? "Platform management" : "平台管理"}</h1><p>{en ? "Configure, operate and observe InsightPro from one place." : "在一个界面中完成配置、运行与观测，保障 InsightPro 全链路稳定运行。"}</p><div className="admin-hero-meta"><StatusBadge health={overall} en={en} /><span>{en ? "Updated" : "最近更新"} {dateTime(overview?.updatedAt)}</span><span>{en ? "Next schedule" : "下次调度"} {dateTime(nextRun)}</span></div></div><div className="admin-hero-summary"><div className="admin-summary-head"><strong>{en ? "System status" : "系统状态"}</strong><StatusBadge health={overall} en={en} /></div><div className="admin-summary-metrics"><div><strong>{overview?.tasks.loaded ? overview.tasks.running : "—"}</strong><span>运行中任务</span></div><div><strong>{overview?.tasks.loaded ? overview.tasks.failed : "—"}</strong><span>失败任务</span></div><div><strong>{overview ? `${overview.available}/${overview.totalServices}` : "—"}</strong><span>数据接口可用</span></div></div></div></section>

    <section className="admin-home-section" aria-labelledby="admin-control-title"><div className="admin-section-title"><h2 id="admin-control-title">{en ? "Platform controls" : "平台控制"}</h2><span>关键配置与投递状态</span></div><div className="admin-control-grid">{modules.slice(0, 3).map(item => <ModuleCard key={item.href} item={item} data={overview} en={en} />)}</div></section>

    <section className="admin-home-section" aria-labelledby="admin-observe-title"><div className="admin-section-title"><h2 id="admin-observe-title">{en ? "Operations & visibility" : "运行与观测"}</h2><span>从数据到结果的全链路观测</span></div><div className="admin-observe-grid">{modules.slice(3).map(item => <ModuleCard key={item.href} item={item} data={overview} en={en} />)}</div></section>

    <section className="admin-task-center" aria-labelledby="admin-tasks-title"><div className="admin-task-head"><div className="admin-task-heading"><span className="admin-module-icon"><ShieldCheck size={21} /></span><div><h2 id="admin-tasks-title">{en ? "Task center" : "任务中心"}</h2><p>采集、AI 分析、同步与邮件执行</p></div></div><Link href="/admin/tasks">查看全部 <ArrowRight size={15} /></Link></div><div className="admin-task-toolbar"><div role="group" aria-label="筛选任务状态">{[["all", "全部"], ["running", "运行中"], ["success", "成功"], ["error", "失败"], ["scheduled", "定时任务"]].map(([key, label]) => <button key={key} type="button" className={filter === key ? "is-active" : ""} aria-pressed={filter === key} onClick={() => setFilter(key)}>{label}{overview?.tasks.loaded && key === "all" ? ` (${overview.tasks.items.length})` : key === "running" ? ` (${overview?.tasks.running ?? 0})` : key === "error" ? ` (${overview?.tasks.failed ?? 0})` : key === "success" ? ` (${completed})` : ""}</button>)}</div><Link href="/admin/scheduler" className="admin-task-config"><Plus size={15} />调度配置</Link></div><div className="admin-table-wrap"><table className="admin-task-table"><thead><tr><th>任务名称</th><th>类型</th><th>调度</th><th>状态</th><th>进度</th><th>最近运行时间</th><th>操作</th></tr></thead><tbody>{filteredTasks.map(task => <tr key={task.key}><td><strong>{task.name}</strong><small>{task.key}</small></td><td>{task.uses_ai ? "AI 分析" : "平台任务"}</td><td>{task.schedule}</td><td><StatusBadge health={taskStatus(task)} en={en} task /></td><td><span className={`admin-progress admin-progress-${taskStatus(task)}`}><i /></span></td><td>{dateTime(task.last_run?.started_at)}</td><td><Link href="/admin/tasks" aria-label={`查看${task.name}详情`}>查看 <ArrowRight size={13} /></Link></td></tr>)}</tbody></table>{!filteredTasks.length && <p className="admin-table-empty">{overview?.tasks.loaded ? "当前筛选下暂无任务" : "任务数据读取中或暂不可用"}</p>}</div></section>

    <details className="admin-app-progress"><summary><div><h2>{en ? "AI application analysis" : "AI 应用分析进度"}</h2><p>展开查看处理进度与厂商分布</p></div><span>{overview ? `${overview.applications.done}/${overview.applications.total}` : "—"}</span></summary>{overview && <ApplicationProgress app={overview.applications} />}</details>
  </div>;
}

function ApplicationProgress({ app }: { app: Overview["applications"] }) {
  const pct = app.total ? Math.round(app.done / app.total * 100) : 0;
  return <div className="admin-app-progress-body"><div className="admin-app-progress-stats"><span>已分析 {app.done}</span><span>失败 {app.failed}</span><span>总数 {app.total}</span></div><div className="admin-progress admin-progress-success"><i style={{ width: `${pct}%` }} /></div>{app.byVendor.length > 0 && <div className="admin-app-vendors">{app.byVendor.slice(0, 12).map(row => <div key={row.vendor}><span>{row.vendor}</span><strong>{row.done}/{row.total}</strong></div>)}</div>}</div>;
}
