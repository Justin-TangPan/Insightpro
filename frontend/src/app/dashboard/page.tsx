"use client";

import { SectionHeader } from "@/components/section-header";
import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, AreaChart, Area
} from "recharts";
import {
  Users, Activity, Eye, UserCheck
} from "lucide-react";

const COLORS = ["var(--color-primary)", "var(--color-chart-secondary)", "var(--color-chart-tertiary)", "var(--color-ink-muted)", "var(--color-ink-secondary)"];

interface AnalyticsData {
  today: { pv: number; uv: number };
  total: { pv: number; uv: number };
  daily: { date: string; pv: number; uv: number }[];
  pages: { page_path: string; pv: number; uv: number }[];
  trend: { date: string; page_path: string; pv: number }[];
  recent: { page_path: string; visitor_id: string; created_at: string }[];
}

const pageNameMap: Record<string, string> = {
  "/": "首页",
  "/dashboard": "数据大屏",
  "/history": "历史日报",
  "/settings": "系统设置",
  "/reports": "深度研报",
  "/insights/hotspots": "技术热点",
  "/insights/solutions": "解决方案洞察",
  "/insights/competitors": "友商洞察",
};

const tooltipStyle = {
  background: "var(--color-surface-elevated)",
  border: "1px solid var(--color-grid)",
  borderRadius: "10px",
  boxShadow: "var(--shadow-card)",
  fontSize: "12px",
  color: "var(--color-ink)",
};

const kpiTiles = Array(4).fill("bg-primary-soft text-primary");

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [timeRange, setTimeRange] = useState<"week" | "month">("week");

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const days = timeRange === "week" ? 7 : 30;
        const res = await authenticatedFetch(`${API}/api/analytics?days=${days}`);
        if (!res.ok) { throw new Error(`API error: ${res.status}`); }
        const data = await res.json();
        setAnalytics(data);
      } catch (err) {
        console.error("Failed to fetch analytics:", err);
      }
    };
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 30000);
    return () => clearInterval(interval);
  }, [timeRange]);

  const pageTrendMap: Record<string, Record<string, number>> = {};
  if (analytics?.trend) {
    for (const item of analytics.trend) {
      const name = pageNameMap[item.page_path] || item.page_path;
      if (!pageTrendMap[item.date]) pageTrendMap[item.date] = {};
      pageTrendMap[item.date][name] = (pageTrendMap[item.date][name] || 0) + item.pv;
    }
  }
  const trendChartData = Object.entries(pageTrendMap).map(([date, pages]) => ({ date, ...pages })).sort((a, b) => (a.date as string).localeCompare(b.date as string));
  const topPageNames = analytics?.pages?.slice(0, 5).map((p) => pageNameMap[p.page_path] || p.page_path) || [];

  return (
    <div className="page-stack">
      <SectionHeader
        badge="Data Dashboard"
        title="数据大屏 · 运营看板"
        subtitle="实时页面访问统计：PV、UV、页面热度、访问趋势"
        action={
          <div className="flex gap-1 rounded-xl bg-white/70 p-1">
            {(["week", "month"] as const).map((r) => (
              <button
                key={r}
                onClick={() => setTimeRange(r)}
                className={`rounded-lg px-4 py-2 text-xs font-semibold transition-colors ${
                  timeRange === r
                    ? "bg-primary text-white shadow-[var(--shadow-card)]"
                    : "text-ink-secondary hover:bg-primary-soft hover:text-primary"
                }`}
              >
                {r === "week" ? "近 7 天" : "近 30 天"}
              </button>
            ))}
          </div>
        }
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          { label: "今日 PV", value: analytics?.today?.pv ?? 0, icon: Eye },
          { label: "今日 UV", value: analytics?.today?.uv ?? 0, icon: UserCheck },
          { label: "累计 PV", value: analytics?.total?.pv ?? 0, icon: Activity },
          { label: "累计 UV", value: analytics?.total?.uv ?? 0, icon: Users },
        ].map((kpi, i) => (
          <div key={i} className="ui-card min-h-40">
            <div className="mb-7 flex items-center justify-between">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${kpiTiles[i]}`}>
                <kpi.icon className="h-5 w-5" strokeWidth={1.5} />
              </div>
            </div>
            <p className="swiss-kicker text-ink-muted mb-1">{kpi.label}</p>
            <p className="text-3xl serif-stat text-ink">{kpi.value.toLocaleString()}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {/* Daily PV/UV Trend */}
        <div className="ui-card">
          <h3 className="type-h3 mb-6 text-ink">每日 PV/UV 趋势</h3>
          <div className="h-64">
            {analytics?.daily && analytics.daily.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={analytics.daily}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-grid)" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--color-ink-muted)" }} stroke="var(--color-grid)" tickFormatter={(v) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 10, fill: "var(--color-ink-muted)" }} stroke="var(--color-grid)" />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Area type="monotone" dataKey="pv" stroke="var(--color-primary)" fill="var(--color-primary)" fillOpacity={0.08} strokeWidth={2} name="PV" />
                  <Area type="monotone" dataKey="uv" stroke="var(--color-chart-secondary)" fill="var(--color-chart-secondary)" fillOpacity={0.12} strokeWidth={2} name="UV" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-ink-muted text-sm">暂无数据，浏览页面后自动生成</div>
            )}
          </div>
        </div>

        {/* Top Pages Bar Chart */}
        <div className="ui-card">
          <h3 className="type-h3 mb-6 text-ink">页面访问排行</h3>
          <div className="h-64">
            {analytics?.pages && analytics.pages.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.pages.slice(0, 8).map((p) => ({ name: pageNameMap[p.page_path] || p.page_path, pv: p.pv, uv: p.uv }))} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-grid)" />
                  <XAxis type="number" tick={{ fontSize: 10, fill: "var(--color-ink-muted)" }} stroke="var(--color-grid)" />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: "var(--color-ink-muted)" }} stroke="var(--color-grid)" width={80} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="pv" fill="var(--color-primary)" name="PV" />
                  <Bar dataKey="uv" fill="var(--color-chart-secondary)" name="UV" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-ink-muted text-sm">暂无数据</div>
            )}
          </div>
        </div>

        {/* Page Trend by Module */}
        <div className="ui-card lg:col-span-2">
          <h3 className="type-h3 mb-6 text-ink">各模块访问趋势</h3>
          <div className="h-64">
            {trendChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-grid)" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--color-ink-muted)" }} stroke="var(--color-grid)" tickFormatter={(v) => String(v).slice(5)} />
                  <YAxis tick={{ fontSize: 10, fill: "var(--color-ink-muted)" }} stroke="var(--color-grid)" />
                  <Tooltip contentStyle={tooltipStyle} />
                  {topPageNames.map((name, i) => (
                    <Line key={name} type="monotone" dataKey={name} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={{ r: 3 }} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-ink-muted text-sm">暂无数据</div>
            )}
          </div>
          {topPageNames.length > 0 && (
            <div className="flex flex-wrap justify-center gap-4 mt-4 pt-4 border-t border-grid">
              {topPageNames.map((name, i) => (
                <div key={i} className="flex items-center gap-1.5">
                  <div className="h-2.5 w-2.5" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                  <span className="text-[11px] font-medium text-ink-secondary">{name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Visits Table */}
      <div className="ui-card">
        <div className="flex items-center justify-between mb-5">
          <h3 className="type-h3 text-ink">最近访问记录</h3>
          <span className="swiss-kicker text-ink-muted">实时更新</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-grid">
                <th className="text-left py-2 px-3 swiss-kicker text-ink-muted">页面</th>
                <th className="text-left py-2 px-3 swiss-kicker text-ink-muted">访客 ID</th>
                <th className="text-left py-2 px-3 swiss-kicker text-ink-muted">访问时间</th>
              </tr>
            </thead>
            <tbody>
              {(analytics?.recent || []).map((item, i) => (
                <tr key={i} className="border-b border-grid hover:bg-paper transition-colors">
                  <td className="py-2.5 px-3">
                    <span className="font-medium text-ink">{pageNameMap[item.page_path] || item.page_path}</span>
                    <span className="text-[10px] text-ink-muted ml-2">{item.page_path}</span>
                  </td>
                  <td className="py-2.5 px-3 text-xs text-ink-secondary font-mono">{item.visitor_id.slice(0, 12)}...</td>
                  <td className="py-2.5 px-3 text-xs text-ink-muted">{item.created_at}</td>
                </tr>
              ))}
              {(!analytics?.recent || analytics.recent.length === 0) && (
                <tr><td colSpan={3} className="py-8 text-center text-ink-muted text-sm">暂无访问记录</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
