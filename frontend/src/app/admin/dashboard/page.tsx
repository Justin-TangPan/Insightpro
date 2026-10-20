"use client";

import { Activity, Eye, UserCheck, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { useAuth } from "@/components/auth-provider";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

interface AnalyticsData {
  today: { pv: number; uv: number };
  total: { pv: number; uv: number };
  daily: { date: string; pv: number; uv: number }[];
  pages: { page_path: string; pv: number; uv: number }[];
  recent_visits: { page_path: string; visitor_id: string; user_id: string | null; user_email: string | null; display_name: string | null; visited_at: string }[];
}

interface ProjectInsight {
  name: string;
  momentum: number;
  value: number;
  stars: number;
  level: string;
}

const pageNames: Record<string, string> = { "/": "首页", "/insights/hotspots": "GitHub", "/insights/app-launches": "AI 应用", "/insights/solutions": "解决方案", "/insights/competitors": "友商洞察", "/knowledge": "知识库", "/workbench/ai": "Insight Agent" };
const pageName = (path: string) => pageNames[path] || (path.startsWith("/workbench/solutions/") ? "方案实践详情" : path);
const tooltipStyle = { background: "var(--color-surface-elevated)", border: "1px solid var(--color-grid)", borderRadius: "10px", fontSize: "12px" };

export default function AdminDashboardPage() {
  const { user, loading } = useAuth();
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [projects, setProjects] = useState<ProjectInsight[]>([]);
  const [days, setDays] = useState(7);

  useEffect(() => {
    if (user?.app_metadata?.role !== "admin") return;
    void authenticatedFetch(`${API}/api/analytics?days=${days}`).then((response) => response.ok ? response.json() : Promise.reject()).then(setAnalytics).catch(() => setAnalytics(null));
  }, [days, user]);

  useEffect(() => {
    if (user?.app_metadata?.role !== "admin") return;
    void Promise.all([
      fetch(`${API}/api/github-trending?since=daily`).then((response) => response.ok ? response.json() : Promise.reject()),
      fetch(`${API}/api/github-trending/business-eval`).then((response) => response.ok ? response.json() : Promise.reject()),
    ]).then(([trending, evaluation]) => {
      const scores = new Map((evaluation.items || []).map((item: { repo_name: string; total: number; level: string }) => [item.repo_name, item]));
      setProjects((trending.items || []).map((item: { repo_name: string; today_stars: string; stars: string }) => {
        const score = scores.get(item.repo_name) as { total: number; level: string } | undefined;
        return { name: item.repo_name, momentum: Number(item.today_stars?.replace(/\D/g, "")) || 0, value: Number(score?.total) || 0, stars: Number(item.stars?.replace(/\D/g, "")) || 0, level: score?.level || "待评估" };
      }).filter((item: ProjectInsight) => item.value > 0).slice(0, 12));
    }).catch(() => setProjects([]));
  }, [user]);

  if (loading) return <div className="ui-card py-12 text-center text-sm text-ink-muted">正在验证权限…</div>;
  if (user?.app_metadata?.role !== "admin") return <div className="ui-card py-12 text-center text-sm text-ink-muted">需要管理员权限。</div>;

  const metrics = [
    ["今日 PV", analytics?.today.pv || 0, Eye], ["今日 UV", analytics?.today.uv || 0, UserCheck],
    ["累计 PV", analytics?.total.pv || 0, Activity], ["累计 UV", analytics?.total.uv || 0, Users],
  ] as const;
  const pages = (analytics?.pages || []).slice(0, 8).map((item) => ({ ...item, name: pageName(item.page_path) }));

  return <div className="page-stack">
    <SectionHeader badge="Admin / Analytics" title="平台数据看板" subtitle="仅管理员可见的访问趋势与页面使用情况" action={<div className="flex rounded-xl bg-white p-1">{[7, 30].map((value) => <button key={value} type="button" onClick={() => setDays(value)} className={`rounded-lg px-3 py-2 text-xs font-semibold ${days === value ? "bg-primary text-white" : "text-ink-muted"}`}>近 {value} 天</button>)}</div>} />
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{metrics.map(([label, value, Icon]) => <div key={label} className="ui-card"><Icon className="h-5 w-5 text-primary" /><p className="mt-7 swiss-kicker text-ink-muted">{label}</p><p className="mt-1 text-3xl font-semibold text-ink">{value.toLocaleString()}</p></div>)}</div>
    <section className="ui-card" aria-labelledby="project-opportunity-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><p className="swiss-kicker text-primary">Project radar</p><h2 id="project-opportunity-title" className="mt-1 type-h3 text-ink">项目热点机会图</h2><p className="mt-1 text-xs text-ink-muted">越靠右增长越快，越靠上业务价值越高，气泡越大代表累计关注越多。</p></div>
        <span className="ui-tag ui-tag-warning">国内舆情待接入</span>
      </div>
      {projects.length ? <>
        <div className="mt-5 h-80" role="img" aria-label={`项目热点机会图，共 ${projects.length} 个项目；右上区域为优先关注项目。`}><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{ top: 12, right: 12, bottom: 16, left: 4 }}><CartesianGrid strokeDasharray="3 3" stroke="var(--color-grid)" /><XAxis type="number" dataKey="momentum" name="今日新增 Star" unit="" tick={{ fontSize: 10 }} label={{ value: "技术动量（今日新增 Star）", position: "insideBottom", offset: -10, fontSize: 11 }} /><YAxis type="number" dataKey="value" name="业务价值" domain={[0, 10]} tick={{ fontSize: 10 }} label={{ value: "业务价值", angle: -90, position: "insideLeft", fontSize: 11 }} /><ZAxis type="number" dataKey="stars" range={[90, 700]} name="累计 Star" /><ReferenceLine x={projects.reduce((sum, item) => sum + item.momentum, 0) / projects.length} stroke="var(--color-grid-strong)" strokeDasharray="4 4" /><ReferenceLine y={7} stroke="var(--color-grid-strong)" strokeDasharray="4 4" /><Tooltip cursor={{ strokeDasharray: "3 3" }} contentStyle={tooltipStyle} /><Scatter name="项目" data={projects} fill="var(--color-primary)" /></ScatterChart></ResponsiveContainer></div>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3" aria-label="项目机会摘要">{[...projects].sort((a, b) => (b.value * b.momentum) - (a.value * a.momentum)).slice(0, 3).map((item, index) => <div key={item.name} className="rounded-xl bg-surface-subtle px-4 py-3"><p className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">优先级 {index + 1}</p><p className="mt-1 truncate text-sm font-semibold text-ink">{item.name}</p><p className="mt-1 text-xs text-ink-muted">新增 {item.momentum.toLocaleString()} Star · 价值 {item.value.toFixed(1)} · {item.level}</p></div>)}</div>
      </> : <p className="py-16 text-center text-sm text-ink-muted">暂无已完成业务评估的项目</p>}
    </section>
    <div className="grid gap-3 lg:grid-cols-2">
      <div className="ui-card"><h2 className="type-h3 text-ink">访问趋势</h2><div className="mt-6 h-72"><ResponsiveContainer width="100%" height="100%"><AreaChart data={analytics?.daily || []}><CartesianGrid strokeDasharray="3 3" stroke="var(--color-grid)" /><XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(value) => String(value).slice(5)} /><YAxis tick={{ fontSize: 10 }} /><Tooltip contentStyle={tooltipStyle} /><Area type="monotone" dataKey="pv" stroke="var(--color-primary)" fill="var(--color-primary-soft)" name="PV" /><Area type="monotone" dataKey="uv" stroke="var(--color-chart-secondary)" fill="transparent" name="UV" /></AreaChart></ResponsiveContainer></div></div>
      <div className="ui-card"><h2 className="type-h3 text-ink">页面访问排行</h2><div className="mt-6 h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={pages} layout="vertical"><CartesianGrid strokeDasharray="3 3" stroke="var(--color-grid)" /><XAxis type="number" tick={{ fontSize: 10 }} /><YAxis type="category" dataKey="name" width={84} tick={{ fontSize: 10 }} /><Tooltip contentStyle={tooltipStyle} /><Bar dataKey="pv" fill="var(--color-primary)" name="PV" radius={[0, 5, 5, 0]} /></BarChart></ResponsiveContainer></div></div>
    </div>
    <section className="ui-card" aria-labelledby="recent-visits-title">
      <div><h2 id="recent-visits-title" className="type-h3 text-ink">最近访问明细</h2><p className="mt-1 text-xs text-ink-muted">展示所选时间范围内最近 100 次访问；历史数据未记录账号身份时按匿名访问显示。</p></div>
      <div className="mt-5 overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead><tr className="border-b border-grid text-xs text-ink-muted"><th className="px-3 py-3 font-medium">访问时间</th><th className="px-3 py-3 font-medium">访问页面</th><th className="px-3 py-3 font-medium">访问者</th><th className="px-3 py-3 font-medium">登录状态</th></tr></thead>
          <tbody className="divide-y divide-grid/70">{(analytics?.recent_visits || []).map((visit, index) => <tr key={`${visit.visited_at}-${visit.visitor_id}-${index}`} className="text-ink-secondary"><td className="whitespace-nowrap px-3 py-3 text-xs text-ink-muted">{new Date(visit.visited_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false })}</td><td className="px-3 py-3"><span className="font-medium text-ink">{pageName(visit.page_path)}</span><span className="ml-2 font-mono text-[10px] text-ink-muted">{visit.page_path}</span></td><td className="px-3 py-3">{visit.user_id ? <><span className="font-medium text-ink">{visit.display_name || visit.user_email}</span>{visit.display_name && visit.user_email && <span className="mt-0.5 block text-xs text-ink-muted">{visit.user_email}</span>}</> : <span className="font-mono text-xs text-ink-muted">匿名 · {visit.visitor_id.slice(-8)}</span>}</td><td className="px-3 py-3"><span className={`ui-tag ${visit.user_id ? "" : "ui-tag-warning"}`}>{visit.user_id ? "已登录" : "未登录"}</span></td></tr>)}</tbody>
        </table>
        {!analytics?.recent_visits?.length && <p className="py-12 text-center text-sm text-ink-muted">暂无访问记录</p>}
      </div>
    </section>
  </div>;
}
