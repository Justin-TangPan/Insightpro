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

// 瑞士色盘：柠檬黄 / 柠檬绿 / 安全橙 / 黑 / 灰
const COLORS = ["#0A0A0A", "#84CC16", "#FF6B00", "#F5D300", "#737373", "#3F3F3F"];

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
  "/insights/industry": "行业全景",
  "/insights/industry/cases": "案例库",
  "/insights/hotspots": "技术热点",
  "/insights/competitors": "友商洞察",
  "/insights/policy": "政策法规",
  "/insights/news": "商业快讯",
  "/insights/opportunities": "增长机会",
};

const tooltipStyle = {
  background: "#FFFFFF",
  border: "1px solid #E5E5E0",
  borderRadius: "0",
  boxShadow: "none",
  fontSize: "12px",
  color: "#0A0A0A",
};

const kpiTiles = ["bg-ink text-paper", "bg-lime text-ink", "bg-signal text-paper", "bg-lemon text-ink"];

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
    <div className="space-y-10">
      <SectionHeader
        badge="Data Dashboard"
        title="数据大屏 · 运营看板"
        subtitle="实时页面访问统计：PV、UV、页面热度、访问趋势"
        action={
          <div className="flex gap-px border border-grid">
            {(["week", "month"] as const).map((r) => (
              <button
                key={r}
                onClick={() => setTimeRange(r)}
                className={`px-4 py-1.5 text-xs font-semibold transition-colors ${
                  timeRange === r
                    ? "bg-ink text-paper"
                    : "bg-white text-ink-secondary hover:text-ink"
                }`}
              >
                {r === "week" ? "近 7 天" : "近 30 天"}
              </button>
            ))}
          </div>
        }
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-grid border border-grid">
        {[
          { label: "今日 PV", value: analytics?.today?.pv ?? 0, icon: Eye },
          { label: "今日 UV", value: analytics?.today?.uv ?? 0, icon: UserCheck },
          { label: "累计 PV", value: analytics?.total?.pv ?? 0, icon: Activity },
          { label: "累计 UV", value: analytics?.total?.uv ?? 0, icon: Users },
        ].map((kpi, i) => (
          <div key={i} className="bg-white p-5">
            <div className="flex items-center justify-between mb-4">
              <div className={`h-10 w-10 flex items-center justify-center ${kpiTiles[i]}`}>
                <kpi.icon className="h-5 w-5" strokeWidth={1.5} />
              </div>
            </div>
            <p className="swiss-kicker text-ink-muted mb-1">{kpi.label}</p>
            <p className="text-3xl serif-stat text-ink">{kpi.value.toLocaleString()}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-px bg-grid border border-grid">
        {/* Daily PV/UV Trend */}
        <div className="bg-white p-6">
          <h3 className="serif-heading text-xl text-ink mb-6">每日 PV/UV 趋势</h3>
          <div className="h-64">
            {analytics?.daily && analytics.daily.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={analytics.daily}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E5E0" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#737373" }} stroke="#E5E5E0" tickFormatter={(v) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 10, fill: "#737373" }} stroke="#E5E5E0" />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Area type="monotone" dataKey="pv" stroke="#0A0A0A" fill="#0A0A0A" fillOpacity={0.08} strokeWidth={2} name="PV" />
                  <Area type="monotone" dataKey="uv" stroke="#84CC16" fill="#84CC16" fillOpacity={0.12} strokeWidth={2} name="UV" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-ink-muted text-sm">暂无数据，浏览页面后自动生成</div>
            )}
          </div>
        </div>

        {/* Top Pages Bar Chart */}
        <div className="bg-white p-6">
          <h3 className="serif-heading text-xl text-ink mb-6">页面访问排行</h3>
          <div className="h-64">
            {analytics?.pages && analytics.pages.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.pages.slice(0, 8).map((p) => ({ name: pageNameMap[p.page_path] || p.page_path, pv: p.pv, uv: p.uv }))} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E5E0" />
                  <XAxis type="number" tick={{ fontSize: 10, fill: "#737373" }} stroke="#E5E5E0" />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: "#737373" }} stroke="#E5E5E0" width={80} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="pv" fill="#0A0A0A" name="PV" />
                  <Bar dataKey="uv" fill="#84CC16" name="UV" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-ink-muted text-sm">暂无数据</div>
            )}
          </div>
        </div>

        {/* Page Trend by Module */}
        <div className="bg-white p-6 lg:col-span-2">
          <h3 className="serif-heading text-xl text-ink mb-6">各模块访问趋势</h3>
          <div className="h-64">
            {trendChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E5E0" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#737373" }} stroke="#E5E5E0" tickFormatter={(v) => String(v).slice(5)} />
                  <YAxis tick={{ fontSize: 10, fill: "#737373" }} stroke="#E5E5E0" />
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
      <div className="bg-white border border-grid p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="serif-heading text-xl text-ink">最近访问记录</h3>
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
