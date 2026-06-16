"use client";

import { SectionHeader } from "@/components/section-header";
import { useEffect, useState } from "react";
import {
  Gavel, RefreshCw, FileText, ExternalLink, Building2,
  Factory, Stethoscope, Landmark, ShoppingCart, Globe,
  GraduationCap, Truck, Zap, Leaf, Loader2, Calendar,
  TrendingUp, Target, Clock, DollarSign, ChevronRight,
  AlertTriangle, CheckCircle2, Lightbulb, ChevronLeft
} from "lucide-react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface BiddingItem {
  id: number;
  bid_date: string;
  industry: string;
  title: string;
  procuring_entity: string;
  budget: string;
  deadline: string;
  summary: string;
  requirements: string;
  qualification: string;
  contact: string;
  url: string;
  relevance_score: number;
  status: string;
}

interface BiddingStats {
  total: number;
  open_count: number;
  by_industry: { industry: string; count: number; open_count: number; avg_score: number }[];
  total_budget: string;
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

export default function BiddingPage() {
  const [items, setItems] = useState<BiddingItem[]>([]);
  const [stats, setStats] = useState<BiddingStats | null>(null);
  const [analysis, setAnalysis] = useState("");
  const [loading, setLoading] = useState(true);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [activeIndustry, setActiveIndustry] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const pageSize = 10;

  const industries = stats ? stats.by_industry.map(i => i.industry) : [];

  const fetchData = async (p?: number) => {
    const currentPage = p ?? page;
    setLoading(true);
    try {
      const [listRes, statsRes] = await Promise.all([
        fetch(`${API}/api/bidding/list?days=30&page=${currentPage}&page_size=${pageSize}${activeIndustry ? `&industry=${activeIndustry}` : ""}`),
        fetch(`${API}/api/bidding/stats`),
      ]);
      const listData = await listRes.json();
      const statsData = await statsRes.json();
      setItems(listData.items || []);
      setTotal(listData.total || 0);
      setTotalPages(listData.total_pages || 1);
      setStats(statsData);
    } catch (err) {
      console.error("Failed to fetch bidding data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    try {
      await fetch(`${API}/api/bidding/refresh`, { method: "POST" });
      setPage(1);
      await fetchData(1);
    } catch (err) {
      console.error("Refresh failed:", err);
    }
  };

  const handleAnalyze = async () => {
    setAnalysisLoading(true);
    setShowAnalysis(true);
    try {
      const res = await fetch(`${API}/api/bidding/analyze`, { method: "POST" });
      const data = await res.json();
      setAnalysis(data.analysis || "分析生成失败");
    } catch {
      setAnalysis("分析生成失败，请检查后端服务");
    } finally {
      setAnalysisLoading(false);
    }
  };

  useEffect(() => { setPage(1); fetchData(1); }, [activeIndustry]);

  const urgencyInfo = (deadline: string) => {
    const days = Math.ceil((new Date(deadline).getTime() - Date.now()) / 86400000);
    if (days < 0) return { label: `已截止`, color: "bg-slate-100 text-slate-500 border-slate-200" };
    if (days < 30) return { label: `紧急 ${days}天`, color: "bg-rose-50 text-rose-700 border-rose-200" };
    if (days < 60) return { label: `适中 ${days}天`, color: "bg-amber-50 text-amber-700 border-amber-200" };
    return { label: `充裕 ${days}天`, color: "bg-emerald-50 text-emerald-700 border-emerald-200" };
  };

  return (
    <div className="space-y-8">
      <SectionHeader
        badge="Bidding Intelligence"
        title="招标信息 · 商机雷达"
        subtitle="覆盖政务、制造、医疗、金融、教育、交通、能源、农业 8 大行业的招标信息，AI 分析商机，实时追踪"
        image="https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=1200&q=80"
        action={
          <div className="flex gap-2">
            <button onClick={handleRefresh} disabled={loading}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-white border border-slate-200 text-ink-secondary hover:border-primary/30 transition-all disabled:opacity-50">
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              刷新数据
            </button>
            <button onClick={handleAnalyze} disabled={analysisLoading}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 transition-all disabled:opacity-50">
              {analysisLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Lightbulb className="h-3.5 w-3.5" />}
              AI 分析商机
            </button>
          </div>
        }
      />

      {/* Stats Overview */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="rounded-xl bg-white border border-slate-200/60 p-5 shadow-sm">
            <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider">招标项目</p>
            <p className="text-2xl font-serif font-bold text-ink mt-1">{stats.total}</p>
            <span className="text-[10px] text-emerald-600 font-medium">近30天活跃</span>
          </div>
          <div className="rounded-xl bg-white border border-slate-200/60 p-5 shadow-sm">
            <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider">开放中</p>
            <p className="text-2xl font-serif font-bold text-ink mt-1">{stats.open_count}</p>
            <span className="text-[10px] text-amber-600 font-medium">可投标</span>
          </div>
          <div className="rounded-xl bg-white border border-slate-200/60 p-5 shadow-sm">
            <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider">覆盖行业</p>
            <p className="text-2xl font-serif font-bold text-ink mt-1">{industries.length}</p>
          </div>
          <div className="rounded-xl bg-white border border-slate-200/60 p-5 shadow-sm">
            <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider">估算总预算</p>
            <p className="text-sm font-serif font-bold text-ink mt-1">{stats.total_budget || "—"}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <button onClick={() => setActiveIndustry(null)}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${!activeIndustry ? "bg-slate-900 text-white" : "bg-white border border-slate-200 text-ink-secondary hover:border-slate-300"}`}>
          全部行业
        </button>
        {industries.map((ind) => {
          const Icon = industryIcons[ind] || Globe;
          return (
            <button key={ind} onClick={() => setActiveIndustry(activeIndustry === ind ? null : ind)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${activeIndustry === ind ? "bg-slate-900 text-white" : "bg-white border border-slate-200 text-ink-secondary hover:border-slate-300"}`}>
              <Icon className="h-3 w-3" />
              {ind}
            </button>
          );
        })}
      </div>

      {/* Bidding List */}
      {loading ? (
        <div className="space-y-4">
          {[1,2,3,4].map(i => <div key={i} className="h-32 bg-slate-100 animate-shimmer rounded-xl" />)}
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16">
          <Gavel className="h-12 w-12 text-ink-muted mx-auto mb-3" />
          <p className="text-ink-muted">暂无招标信息，点击"刷新数据"获取</p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item) => {
            const Icon = industryIcons[item.industry] || Globe;
            const urgency = urgencyInfo(item.deadline);
            return (
              <div key={item.id}
                className="rounded-xl bg-white border border-slate-200/80 overflow-hidden shadow-sm hover:shadow-md transition-all">
                <div className="flex items-start justify-between p-5 cursor-pointer"
                  onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}>
                  <div className="flex items-start gap-4 flex-1 min-w-0">
                    <div className={`h-10 w-10 rounded-lg bg-gradient-to-br ${industryColors[item.industry] || "from-slate-500 to-gray-500"} flex items-center justify-center shrink-0`}>
                      <Icon className="h-5 w-5 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                        <span className="text-[9px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-primary">{item.industry}</span>
                        <span className={`text-[9px] font-semibold px-2 py-0.5 rounded-full border ${urgency.color}`}>
                          {urgency.label}
                        </span>
                        {item.budget && (
                          <span className="text-[9px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700">
                            {item.budget}
                          </span>
                        )}
                        <span className="text-[9px] font-semibold text-amber-600">
                          匹配度 {Math.round(item.relevance_score * 100)}%
                        </span>
                      </div>
                      <h3 className="font-bold text-sm text-ink mb-1">{item.title}</h3>
                      <p className="text-xs text-ink-muted">{item.procuring_entity}</p>
                    </div>
                  </div>
                  <ChevronRight className={`h-4 w-4 text-ink-muted shrink-0 mt-2 transition-transform ${expandedId === item.id ? "rotate-90" : ""}`} />
                </div>

                {expandedId === item.id && (
                  <div className="border-t border-slate-100 px-5 py-4 space-y-4 bg-slate-50/50">
                    <p className="text-xs text-ink-secondary leading-relaxed">{item.summary}</p>
                    {item.requirements && (
                      <div className="rounded-lg border border-slate-200/60 p-3 bg-white">
                        <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider mb-1">技术要求</p>
                        <p className="text-xs text-ink-secondary whitespace-pre-line">{item.requirements}</p>
                      </div>
                    )}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {item.qualification && (
                        <div className="rounded-lg border-l-4 border-amber-400 bg-amber-50/30 p-3">
                          <p className="text-[10px] font-semibold text-amber-700 uppercase tracking-wider mb-1">资质要求</p>
                          <p className="text-xs text-ink-secondary">{item.qualification}</p>
                        </div>
                      )}
                      <div className="rounded-lg border-l-4 border-primary bg-indigo-50/30 p-3">
                        <p className="text-[10px] font-semibold text-primary uppercase tracking-wider mb-1">截止时间</p>
                        <p className="text-xs font-bold text-ink">{item.deadline}</p>
                      </div>
                      {item.contact && (
                        <div className="rounded-lg border-l-4 border-emerald-400 bg-emerald-50/30 p-3">
                          <p className="text-[10px] font-semibold text-emerald-700 uppercase tracking-wider mb-1">联系方式</p>
                          <p className="text-xs text-ink-secondary">{item.contact}</p>
                        </div>
                      )}
                    </div>
                    {item.url && (
                      <a href={item.url} target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline">
                        <ExternalLink className="h-3 w-3" />
                        查看原始公告
                      </a>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-ink-muted">
            共 {total} 条，第 {page}/{totalPages} 页
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => { const p = page - 1; setPage(p); fetchData(p); }}
              disabled={page <= 1}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-slate-200 text-ink-secondary hover:border-slate-300 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              上一页
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter(p => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
              .reduce<(number | string)[]>((acc, p, i, arr) => {
                if (i > 0 && typeof arr[i - 1] === "number" && p - (arr[i - 1] as number) > 1) acc.push("...");
                acc.push(p);
                return acc;
              }, [])
              .map((p, i) =>
                typeof p === "string" ? (
                  <span key={`ellipsis-${i}`} className="px-1.5 text-xs text-ink-muted">...</span>
                ) : (
                  <button
                    key={p}
                    onClick={() => { setPage(p); fetchData(p); }}
                    className={`w-8 h-8 rounded-lg text-xs font-semibold transition-all ${
                      p === page
                        ? "bg-slate-900 text-white"
                        : "bg-white border border-slate-200 text-ink-secondary hover:border-slate-300"
                    }`}
                  >
                    {p}
                  </button>
                )
              )}
            <button
              onClick={() => { const p = page + 1; setPage(p); fetchData(p); }}
              disabled={page >= totalPages}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-slate-200 text-ink-secondary hover:border-slate-300 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            >
              下一页
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* AI Analysis */}
      {showAnalysis && (
        <div className="rounded-xl bg-white border border-slate-200/80 p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
            <Lightbulb className="h-4 w-4 text-amber-500" />
            <h3 className="font-semibold text-sm text-ink">AI 招标市场分析报告</h3>
            {analysisLoading && <Loader2 className="h-3.5 w-3.5 animate-spin text-ink-muted" />}
          </div>
          {analysisLoading ? (
            <div className="space-y-3">
              {[1,2,3].map(i => <div key={i} className="h-4 bg-slate-100 animate-shimmer rounded w-full" />)}
            </div>
          ) : (
            <div className="prose prose-sm max-w-none text-ink-secondary leading-relaxed whitespace-pre-wrap">
              {analysis}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
