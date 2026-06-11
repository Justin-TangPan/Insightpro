"use client";

import { SectionHeader } from "@/components/section-header";
import { useEffect, useState } from "react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell
} from "recharts";
import {
  TrendingUp, Users, Activity, Globe, Eye, UserCheck,
  ArrowUpRight, BarChart3
} from "lucide-react";

const COLORS = ["#6366f1", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#f43f5e"];
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: "12px",
  boxShadow: "0 4px 16px rgba(0,0,0,0.06)",
  fontSize: "12px",
};

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [timeRange, setTimeRange] = useState<"week" | "month">("week");

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const days = timeRange === "week" ? 7 : 30;
        const res = await fetch(`${API}/api/analytics?days=${days}`);
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

  // 按页面分组的趋势数据
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
    <div className="space-y-8">
      <SectionHeader
        badge="Data Dashboard"
        title="数据大屏 · 运营看板"
        subtitle="实时页面访问统计：PV、UV、页面热度、访问趋势"
        action={
          <div className="flex gap-1.5">
            {(["week", "month"] as const).map((r) => (
              <button
                key={r}
                onClick={() => setTimeRange(r)}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  timeRange === r
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-ink-secondary hover:bg-slate-200"
                }`}
              >
                {r === "week" ? "近 7 天" : "近 30 天"}
              </button>
            ))}
          </div>
        }
      />

      {/* KPI Cards - Real Data */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "今日 PV", value: analytics?.today?.pv ?? 0, icon: Eye, color: "from-indigo-500 to-purple-500" },
          { label: "今日 UV", value: analytics?.today?.uv ?? 0, icon: UserCheck, color: "from-cyan-500 to-blue-500" },
          { label: "累计 PV", value: analytics?.total?.pv ?? 0, icon: Activity, color: "from-emerald-500 to-teal-500" },
          { label: "累计 UV", value: analytics?.total?.uv ?? 0, icon: Users, color: "from-amber-500 to-orange-500" },
        ].map((kpi, i) => (
          <div key={i} className="rounded-xl bg-white border border-slate-200/60 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className={`h-10 w-10 rounded-xl bg-gradient-to-br ${kpi.color} flex items-center justify-center`}>
                <kpi.icon className="h-5 w-5 text-white" />
              </div>
            </div>
            <p className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-0.5">{kpi.label}</p>
            <p className="text-2xl font-serif font-bold text-ink">{kpi.value.toLocaleString()}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily PV/UV Trend */}
        <div className="rounded-xl bg-white border border-slate-200/60 p-6 shadow-sm">
          <h3 className="font-serif text-lg font-bold text-ink mb-5">每日 PV/UV 趋势</h3>
          <div className="h-64">
            {analytics?.daily && analytics.daily.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={analytics.daily}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#94a3b8" tickFormatter={(v) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Area type="monotone" dataKey="pv" stroke="#6366f1" fill="#6366f1" fillOpacity={0.1} strokeWidth={2} name="PV" />
                  <Area type="monotone" dataKey="uv" stroke="#10b981" fill="#10b981" fillOpacity={0.1} strokeWidth={2} name="UV" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-ink-muted text-sm">暂无数据，浏览页面后自动生成</div>
            )}
          </div>
        </div>

        {/* Top Pages Bar Chart */}
        <div className="rounded-xl bg-white border border-slate-200/60 p-6 shadow-sm">
          <h3 className="font-serif text-lg font-bold text-ink mb-5">页面访问排行</h3>
          <div className="h-64">
            {analytics?.pages && analytics.pages.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.pages.slice(0, 8).map((p) => ({ name: pageNameMap[p.page_path] || p.page_path, pv: p.pv, uv: p.uv }))} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis type="number" tick={{ fontSize: 10 }} stroke="#94a3b8" />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} stroke="#94a3b8" width={80} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="pv" fill="#6366f1" radius={[0, 4, 4, 0]} name="PV" />
                  <Bar dataKey="uv" fill="#10b981" radius={[0, 4, 4, 0]} name="UV" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-ink-muted text-sm">暂无数据</div>
            )}
          </div>
        </div>

        {/* Page Trend by Module */}
        <div className="rounded-xl bg-white border border-slate-200/60 p-6 shadow-sm lg:col-span-2">
          <h3 className="font-serif text-lg font-bold text-ink mb-5">各模块访问趋势</h3>
          <div className="h-64">
            {trendChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#94a3b8" tickFormatter={(v) => String(v).slice(5)} />
                  <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" />
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
            <div className="flex flex-wrap justify-center gap-4 mt-3 pt-3 border-t border-slate-100">
              {topPageNames.map((name, i) => (
                <div key={i} className="flex items-center gap-1.5">
                  <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                  <span className="text-[11px] font-medium text-ink-secondary">{name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Visits Table */}
      <div className="rounded-xl bg-white border border-slate-200/60 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-serif text-lg font-bold text-ink">最近访问记录</h3>
          <span className="text-xs text-ink-muted">实时更新</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left py-2 px-3 text-[11px] font-semibold text-ink-muted uppercase tracking-wider">页面</th>
                <th className="text-left py-2 px-3 text-[11px] font-semibold text-ink-muted uppercase tracking-wider">访客 ID</th>
                <th className="text-left py-2 px-3 text-[11px] font-semibold text-ink-muted uppercase tracking-wider">访问时间</th>
              </tr>
            </thead>
            <tbody>
              {(analytics?.recent || []).map((item, i) => (
                <tr key={i} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
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
