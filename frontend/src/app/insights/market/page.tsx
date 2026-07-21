"use client";

import { SectionHeader } from "@/components/section-header";
import { useEffect, useState } from "react";
import {
  TrendingUp, Target, Activity, Globe, Zap, BarChart3,
  Lightbulb, ShieldCheck, RefreshCw, ExternalLink,
  ChevronRight, ArrowUpRight, AlertTriangle, CheckCircle2,
  Clock, Building2, Factory, Stethoscope, ShoppingCart,
  Landmark, Truck, GraduationCap, Leaf, Loader2, Sparkles,
  Brain, Eye
} from "lucide-react";
import Link from "next/link";
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, ResponsiveContainer, Tooltip, Legend
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface MarketOverview {
  summary: string;
  market_status: string;
  top_industries: { name: string; driver: string; growth: string }[];
  hot_tags: string[];
  outlook: string;
}

interface HeatMapItem {
  industry: string;
  demand: number;
  competition: number;
  policy: number;
  growth: string;
  trend: string;
}

interface IndustryAnalysis {
  industry: string;
  market_size: string;
  key_trends: string[];
  pain_points: string[];
  opportunities: { title: string; priority: string; action: string }[];
  competition: string;
  huawei_advantage: string;
  recommendation: string;
}

const industryIcons: Record<string, React.ElementType> = {
  "政务": Building2, "制造": Factory, "医疗": Stethoscope,
  "金融": Landmark, "零售": ShoppingCart, "教育": GraduationCap,
  "交通": Truck, "能源": Zap, "农业": Leaf,
};

const industryColors: Record<string, string> = {
  "政务": "from-violet-500 to-purple-500", "制造": "from-blue-500 to-cyan-500",
  "医疗": "from-rose-500 to-pink-500", "金融": "from-emerald-500 to-teal-500",
  "零售": "from-amber-500 to-orange-500", "教育": "from-sky-500 to-indigo-500",
  "交通": "from-orange-500 to-red-500", "能源": "from-yellow-500 to-amber-500",
  "农业": "from-green-500 to-emerald-500",
};

export default function MarketIntelligencePage() {
  const [overview, setOverview] = useState<MarketOverview | null>(null);
  const [heatmap, setHeatmap] = useState<HeatMapItem[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedIndustry, setSelectedIndustry] = useState<string | null>(null);
  const [industryAnalysis, setIndustryAnalysis] = useState<IndustryAnalysis | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [radarIndustries, setRadarIndustries] = useState<string[]>(["政务", "医疗", "制造", "金融", "能源"]);

  const radarColors: Record<string, string> = {
    "政务": "#8b5cf6", "制造": "#3b82f6", "医疗": "#f43f5e",
    "金融": "#10b981", "零售": "#f59e0b", "教育": "#6366f1",
    "交通": "#ef4444", "能源": "#eab308", "农业": "#22c55e",
  };

  // Transform heatmap data into radar chart format
  const radarData = heatmap.length > 0
    ? [
        { dimension: "需求热度", ...Object.fromEntries(heatmap.map(h => [h.industry, h.demand])) },
        { dimension: "竞争烈度", ...Object.fromEntries(heatmap.map(h => [h.industry, h.competition])) },
        { dimension: "政策支持", ...Object.fromEntries(heatmap.map(h => [h.industry, h.policy])) },
      ]
    : [];

  const toggleRadarIndustry = (industry: string) => {
    setRadarIndustries(prev =>
      prev.includes(industry) ? prev.filter(i => i !== industry) : [...prev, industry]
    );
  };

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [overviewRes, heatmapRes] = await Promise.all([
        fetch(`${API}/api/market/overview`),
        fetch(`${API}/api/market/heatmap`),
      ]);
      const overviewData = await overviewRes.json();
      const heatmapData = await heatmapRes.json();
      setOverview(overviewData.overview);
      setStats(overviewData.stats);
      setHeatmap(heatmapData.items || []);
    } catch (err) {
      console.error("Failed to fetch market data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleIndustrySelect = async (industry: string) => {
    setSelectedIndustry(industry);
    setAnalysisLoading(true);
    try {
      const res = await fetch(`${API}/api/market/industry-analysis?industry=${industry}`);
      const data = await res.json();
      setIndustryAnalysis(data.analysis || null);
    } catch {
      setIndustryAnalysis(null);
    } finally {
      setAnalysisLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

  const statusColor = (status: string) => {
    if (status === "扩张") return "text-emerald-600 bg-emerald-50 border-emerald-200";
    if (status === "稳定") return "text-blue-600 bg-blue-50 border-blue-200";
    return "text-amber-600 bg-amber-50 border-amber-200";
  };

  return (
    <div className="space-y-8">
      <SectionHeader
        badge="Market Intelligence"
        title="市场智能洞察"
        subtitle="AI 驱动的市场全景分析 · 行业热度监测 · 趋势研判 · 机会发现"
        image="https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80"
        action={
          <button onClick={fetchAll} disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-white border border-slate-200 text-ink-secondary hover:border-primary/30 transition-all disabled:opacity-50">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            刷新
          </button>
        }
      />

      {/* Loading State */}
      {loading && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[1,2,3,4].map(i => <div key={i} className="h-28 bg-slate-100 animate-shimmer rounded-xl" />)}
          </div>
          <div className="h-64 bg-slate-100 animate-shimmer rounded-xl" />
        </div>
      )}

      {/* Market Overview */}
      {overview && !loading && (
        <>
          <div className="rounded-xl bg-white border border-slate-200/80 p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="h-5 w-5 text-primary" />
              <h3 className="font-serif font-bold text-lg text-ink">市场全景速览</h3>
            </div>
            <p className="text-sm text-ink-secondary leading-relaxed mb-5">{overview.summary}</p>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-5">
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider mb-1">市场状态</p>
                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold border ${statusColor(overview.market_status)}`}>
                  {overview.market_status === "扩张" ? "↑ 扩张" : overview.market_status === "稳定" ? "→ 稳定" : "↓ 收缩"}
                </span>
              </div>
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider mb-1">覆盖行业</p>
                <p className="text-xl font-serif font-bold text-ink">{stats?.industries || 0} 个</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider mb-1">需求信号</p>
                <p className="text-xl font-serif font-bold text-ink">{stats?.signals || 0} 条</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider mb-1">招标项目</p>
                <p className="text-xl font-serif font-bold text-ink">{stats?.tenders || 0} 个</p>
              </div>
            </div>

            {/* Top Industries */}
            {overview.top_industries && overview.top_industries.length > 0 && (
              <div className="mb-5">
                <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider mb-3">TOP 高增长行业</p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {overview.top_industries.map((ind, i) => (
                    <div key={i} className="rounded-lg border border-slate-200/60 p-4 bg-gradient-to-br from-slate-50 to-white">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="flex h-5 w-5 items-center justify-center rounded bg-primary text-white text-[9px] font-bold">
                          {i + 1}
                        </span>
                        <p className="font-bold text-sm text-ink">{ind.name}</p>
                      </div>
                      <p className="text-xs text-ink-secondary mb-1">{ind.driver}</p>
                      <span className="text-[10px] font-semibold text-emerald-600">{ind.growth}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Hot Tags */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] font-semibold text-ink-muted">热门需求标签：</span>
              {overview.hot_tags?.map((tag, i) => (
                <span key={i} className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-primary">{tag}</span>
              ))}
            </div>

            {overview.outlook && (
              <div className="mt-4 rounded-lg bg-slate-50 border border-slate-100 p-3 flex items-start gap-2">
                <Brain className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                <div>
                  <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider">综合研判</p>
                  <p className="text-xs text-ink-secondary">{overview.outlook}</p>
                </div>
              </div>
            )}
          </div>

          {/* Heatmap Table */}
          <div className="rounded-xl bg-white border border-slate-200/80 overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                <h3 className="font-bold text-sm text-ink">行业热度矩阵</h3>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/50">
                    <th className="text-left py-3 px-6 text-[10px] font-semibold text-ink-muted uppercase tracking-wider">行业</th>
                    <th className="text-center py-3 px-4 text-[10px] font-semibold text-ink-muted uppercase tracking-wider">需求热度</th>
                    <th className="text-center py-3 px-4 text-[10px] font-semibold text-ink-muted uppercase tracking-wider">竞争烈度</th>
                    <th className="text-center py-3 px-4 text-[10px] font-semibold text-ink-muted uppercase tracking-wider">政策支持</th>
                    <th className="text-center py-3 px-4 text-[10px] font-semibold text-ink-muted uppercase tracking-wider">增长状态</th>
                    <th className="text-right py-3 px-6 text-[10px] font-semibold text-ink-muted uppercase tracking-wider"></th>
                  </tr>
                </thead>
                <tbody>
                  {heatmap.map((item, i) => {
                    const Icon = industryIcons[item.industry] || Globe;
                    const heatColor = (val: number) =>
                      val >= 85 ? "bg-emerald-500" : val >= 70 ? "bg-amber-500" : val >= 50 ? "bg-orange-500" : "bg-slate-300";
                    return (
                      <tr key={i} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                        <td className="py-3 px-6">
                          <div className="flex items-center gap-2.5">
                            <div className={`h-7 w-7 rounded-lg bg-gradient-to-br ${industryColors[item.industry] || "from-slate-500 to-gray-500"} flex items-center justify-center`}>
                              <Icon className="h-3.5 w-3.5 text-white" />
                            </div>
                            <span className="font-semibold text-ink">{item.industry}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <div className="w-20 h-2 rounded-full bg-slate-100 overflow-hidden">
                              <div className={`h-full rounded-full ${heatColor(item.demand)} transition-all`} style={{ width: `${item.demand}%` }} />
                            </div>
                            <span className="text-xs font-semibold text-ink">{item.demand}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <div className="w-16 h-2 rounded-full bg-slate-100 overflow-hidden">
                              <div className={`h-full rounded-full ${heatColor(item.competition)} transition-all`} style={{ width: `${item.competition}%` }} />
                            </div>
                            <span className="text-xs text-ink-secondary">{item.competition}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <div className="w-16 h-2 rounded-full bg-slate-100 overflow-hidden">
                              <div className={`h-full rounded-full ${heatColor(item.policy)} transition-all`} style={{ width: `${item.policy}%` }} />
                            </div>
                            <span className="text-xs text-ink-secondary">{item.policy}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span className={`text-xs font-semibold ${
                            item.growth.includes("高速") ? "text-emerald-600" : item.growth.includes("稳健") ? "text-blue-600" : "text-amber-600"
                          }`}>
                            {item.growth}
                          </span>
                          <span className="text-[10px] text-ink-muted ml-1">{item.trend}</span>
                        </td>
                        <td className="py-3 px-6 text-right">
                          <button
                            onClick={() => handleIndustrySelect(item.industry)}
                            className="text-xs font-semibold text-primary hover:underline flex items-center gap-1 ml-auto"
                          >
                            深度分析
                            <ArrowUpRight className="h-3 w-3" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Industry Comparison Radar Chart */}
          {radarData.length > 0 && (
            <div className="rounded-xl bg-white border border-slate-200/80 overflow-hidden shadow-sm">
              <div className="px-6 py-4 border-b border-slate-100">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-primary" />
                    <h3 className="font-bold text-sm text-ink">行业对比雷达图</h3>
                    <span className="text-[10px] text-ink-muted ml-1">需求 · 竞争 · 政策 三维度对比</span>
                  </div>
                </div>
              </div>
              <div className="p-6">
                {/* Industry Toggle Buttons */}
                <div className="flex flex-wrap gap-2 mb-6">
                  {heatmap.map(item => {
                    const isActive = radarIndustries.includes(item.industry);
                    const Icon = industryIcons[item.industry] || Globe;
                    return (
                      <button
                        key={item.industry}
                        onClick={() => toggleRadarIndustry(item.industry)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                          isActive
                            ? "border-primary/30 bg-indigo-50 text-primary shadow-sm"
                            : "border-slate-200 bg-white text-ink-muted hover:border-slate-300"
                        }`}
                      >
                        <Icon className="h-3 w-3" />
                        {item.industry}
                      </button>
                    );
                  })}
                </div>

                {/* Radar Chart */}
                <div className="flex flex-col lg:flex-row gap-6">
                  <div className="flex-1 min-h-[360px]">
                    <ResponsiveContainer width="100%" height={360}>
                      <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="75%">
                        <PolarGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                        <PolarAngleAxis
                          dataKey="dimension"
                          tick={{ fill: "#475569", fontSize: 13, fontWeight: 600 }}
                        />
                        <PolarRadiusAxis
                          angle={90}
                          domain={[0, 100]}
                          tick={{ fill: "#94a3b8", fontSize: 10 }}
                          axisLine={false}
                        />
                        {radarIndustries.map(industry => (
                          <Radar
                            key={industry}
                            name={industry}
                            dataKey={industry}
                            stroke={radarColors[industry] || "#6366f1"}
                            fill={radarColors[industry] || "#6366f1"}
                            fillOpacity={0.12}
                            strokeWidth={2}
                            dot={{ r: 4, fill: radarColors[industry] || "#6366f1", strokeWidth: 0 }}
                          />
                        ))}
                        <Tooltip
                          contentStyle={{
                            background: "#fff",
                            border: "1px solid #e2e8f0",
                            borderRadius: "10px",
                            boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
                            fontSize: "12px",
                            padding: "10px 14px",
                          }}
                          formatter={(value, name) => [`${value} 分`, name]}
                        />
                        <Legend
                          iconType="circle"
                          iconSize={8}
                          wrapperStyle={{ fontSize: "12px", paddingTop: "12px" }}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Right side: Industry Score Summary */}
                  <div className="lg:w-64 space-y-3">
                    <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider">选中行业评分</p>
                    {radarIndustries.map(industry => {
                      const item = heatmap.find(h => h.industry === industry);
                      if (!item) return null;
                      const avg = Math.round((item.demand + item.competition + item.policy) / 3);
                      return (
                        <div key={industry} className="rounded-lg border border-slate-100 p-3">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-1.5">
                              <div className="w-2 h-2 rounded-full" style={{ background: radarColors[industry] || "#6366f1" }} />
                              <span className="text-xs font-bold text-ink">{industry}</span>
                            </div>
                            <span className="text-xs font-bold text-primary">{avg}</span>
                          </div>
                          <div className="grid grid-cols-3 gap-1.5">
                            <div className="text-center">
                              <p className="text-[9px] text-ink-muted">需求</p>
                              <p className="text-xs font-semibold text-ink">{item.demand}</p>
                            </div>
                            <div className="text-center">
                              <p className="text-[9px] text-ink-muted">竞争</p>
                              <p className="text-xs font-semibold text-ink">{item.competition}</p>
                            </div>
                            <div className="text-center">
                              <p className="text-[9px] text-ink-muted">政策</p>
                              <p className="text-xs font-semibold text-ink">{item.policy}</p>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                    {radarIndustries.length === 0 && (
                      <p className="text-xs text-ink-muted text-center py-4">请在上方选择行业</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Industry Deep Analysis Panel */}
          {selectedIndustry && (
            <div className="rounded-xl bg-white border border-slate-200/80 overflow-hidden shadow-sm">
              <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-indigo-500 to-purple-500">
                <div className="flex items-center gap-3">
                  {(() => {
                    const Icon = industryIcons[selectedIndustry] || Globe;
                    return <Icon className="h-5 w-5 text-white" />;
                  })()}
                  <h3 className="font-bold text-white">{selectedIndustry}行业 · 深度分析</h3>
                </div>
                <button onClick={() => { setSelectedIndustry(null); setIndustryAnalysis(null); }}
                  className="text-xs text-white/70 hover:text-white">
                  关闭 ✕
                </button>
              </div>

              {analysisLoading ? (
                <div className="p-6 space-y-3">
                  {[1,2,3,4].map(i => <div key={i} className="h-4 bg-slate-100 animate-shimmer rounded w-full" />)}
                </div>
              ) : industryAnalysis ? (
                <div className="p-6 space-y-5">
                  {/* Market Size */}
                  <div className="rounded-lg bg-slate-50 border border-slate-100 p-4">
                    <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider mb-1">市场规模</p>
                    <p className="text-sm font-bold text-ink">{industryAnalysis.market_size}</p>
                  </div>

                  {/* Key Trends */}
                  <div>
                    <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider mb-2">关键趋势</p>
                    <div className="flex flex-wrap gap-2">
                      {industryAnalysis.key_trends?.map((t, i) => (
                        <span key={i} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-50 text-xs text-primary border border-indigo-100">
                          <TrendingUp className="h-3 w-3" />
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Pain Points */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider mb-2">客户痛点</p>
                      <div className="space-y-2">
                        {industryAnalysis.pain_points?.map((p, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs text-ink-secondary">
                            <AlertTriangle className="h-3.5 w-3.5 text-rose-500 mt-0.5 shrink-0" />
                            {p}
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider mb-2">竞争格局</p>
                      <div className="rounded-lg bg-rose-50/50 border border-rose-100 p-3">
                        <p className="text-xs text-ink-secondary leading-relaxed">{industryAnalysis.competition}</p>
                      </div>
                    </div>
                  </div>

                  {/* Opportunities */}
                  <div>
                    <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider mb-2">机会点</p>
                    <div className="space-y-2">
                      {industryAnalysis.opportunities?.map((opp, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 rounded-lg border border-slate-200/60">
                          <div className={`h-6 w-6 rounded-full flex items-center justify-center text-[9px] font-bold shrink-0 ${
                            opp.priority === "高" ? "bg-rose-50 text-rose-600" : "bg-amber-50 text-amber-600"
                          }`}>
                            {i + 1}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <p className="text-xs font-bold text-ink">{opp.title}</p>
                              <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${
                                opp.priority === "高" ? "bg-rose-50 text-rose-600" : "bg-amber-50 text-amber-600"
                              }`}>{opp.priority}优先级</span>
                            </div>
                            <p className="text-xs text-ink-secondary">{opp.action}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Huawei Advantage + Recommendation */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="rounded-lg border-l-4 border-emerald-400 bg-emerald-50/30 p-4">
                      <p className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wider mb-1">华为云优势</p>
                      <p className="text-xs text-emerald-800 leading-relaxed">{industryAnalysis.huawei_advantage}</p>
                    </div>
                    <div className="rounded-lg border-l-4 border-primary bg-indigo-50/30 p-4">
                      <p className="text-[10px] font-semibold text-primary uppercase tracking-wider mb-1">综合建议</p>
                      <p className="text-xs text-ink-secondary leading-relaxed">{industryAnalysis.recommendation}</p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-6 text-center text-ink-muted">无法加载分析数据</div>
              )}
            </div>
          )}

          {/* Bottom CTA */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link href="/insights/industry"
              className="flex items-center gap-3 rounded-xl bg-white border border-slate-200/80 p-5 hover:shadow-md transition-all group">
              <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
                <Eye className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-xs font-bold text-ink group-hover:text-primary transition-colors">行业全景</p>
                <p className="text-[10px] text-ink-muted">查看 9 大行业详细分析</p>
              </div>
              <ChevronRight className="h-4 w-4 text-ink-muted ml-auto" />
            </Link>
            <Link href="/insights/bidding"
              className="flex items-center gap-3 rounded-xl bg-white border border-slate-200/80 p-5 hover:shadow-md transition-all group">
              <div className="h-10 w-10 rounded-lg bg-rose-50 flex items-center justify-center">
                <Target className="h-5 w-5 text-rose-600" />
              </div>
              <div>
                <p className="text-xs font-bold text-ink group-hover:text-primary transition-colors">招标信息</p>
                <p className="text-[10px] text-ink-muted">浏览最新招标商机</p>
              </div>
              <ChevronRight className="h-4 w-4 text-ink-muted ml-auto" />
            </Link>
            <Link href="/insights/opportunities"
              className="flex items-center gap-3 rounded-xl bg-white border border-slate-200/80 p-5 hover:shadow-md transition-all group">
              <div className="h-10 w-10 rounded-lg bg-amber-50 flex items-center justify-center">
                <Lightbulb className="h-5 w-5 text-amber-600" />
              </div>
              <div>
                <p className="text-xs font-bold text-ink group-hover:text-primary transition-colors">增长机会</p>
                <p className="text-[10px] text-ink-muted">发现高价值商业机会</p>
              </div>
              <ChevronRight className="h-4 w-4 text-ink-muted ml-auto" />
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
