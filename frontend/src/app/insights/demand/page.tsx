"use client";

import { SectionHeader } from "@/components/section-header";
import { useEffect, useState } from "react";
import {
  Target, TrendingUp, FileText, Building2, Stethoscope,
  ShoppingCart, Landmark, Factory, RefreshCw, ExternalLink,
  BarChart3, Zap, Shield, Globe, ChevronRight, Loader2
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface DemandSignal {
  id: number;
  signal_date: string;
  source_type: string;
  industry: string;
  title: string;
  summary: string;
  url: string;
  relevance_score: number;
  demand_tags: string;
}

interface DemandTrends {
  total_signals: number;
  by_industry: Record<string, { count: number; top_tags: string[] }>;
  by_type: Record<string, number>;
  hot_tags: { tag: string; count: number }[];
}

const industryIcons: Record<string, React.ElementType> = {
  "制造": Factory, "医疗": Stethoscope, "零售": ShoppingCart,
  "金融": Landmark, "政务": Building2, "通用": Globe,
};

const industryColors: Record<string, string> = {
  "制造": "from-blue-500 to-cyan-500",
  "医疗": "from-rose-500 to-pink-500",
  "零售": "from-amber-500 to-orange-500",
  "金融": "from-emerald-500 to-teal-500",
  "政务": "from-violet-500 to-purple-500",
  "通用": "from-slate-500 to-gray-500",
};

const sourceTypeMap: Record<string, { label: string; color: string }> = {
  "policy": { label: "政策文件", color: "bg-blue-50 text-blue-700 border-blue-200" },
  "bidding": { label: "招标信息", color: "bg-rose-50 text-rose-700 border-rose-200" },
  "report": { label: "行业报告", color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  "tech_trend": { label: "技术趋势", color: "bg-violet-50 text-violet-700 border-violet-200" },
};

export default function DemandPage() {
  const [signals, setSignals] = useState<DemandSignal[]>([]);
  const [trends, setTrends] = useState<DemandTrends | null>(null);
  const [report, setReport] = useState("");
  const [loading, setLoading] = useState(true);
  const [reportLoading, setReportLoading] = useState(false);
  const [activeIndustry, setActiveIndustry] = useState<string | null>(null);
  const [activeType, setActiveType] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sigRes, trendRes] = await Promise.all([
        fetch(`${API}/api/demand/signals?days=30${activeIndustry ? `&industry=${activeIndustry}` : ""}${activeType ? `&source_type=${activeType}` : ""}`),
        fetch(`${API}/api/demand/trends`),
      ]);
      const sigData = await sigRes.json();
      const trendData = await trendRes.json();
      setSignals(sigData.signals || []);
      setTrends(trendData);
    } catch (err) {
      console.error("Failed to fetch demand data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    try {
      await fetch(`${API}/api/demand/refresh`, { method: "POST" });
      await fetchData();
    } catch (err) {
      console.error("Failed to refresh:", err);
    }
  };

  const handleGenerateReport = async () => {
    setReportLoading(true);
    try {
      const res = await fetch(`${API}/api/demand/report${activeIndustry ? `?industry=${activeIndustry}` : ""}`);
      const data = await res.json();
      setReport(data.report || "报告生成失败");
    } catch (err) {
      setReport("报告生成失败，请检查后端服务");
    } finally {
      setReportLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [activeIndustry, activeType]);

  const industries = Object.keys(trends?.by_industry || {});

  return (
    <div className="space-y-8">
      <SectionHeader
        badge="Demand Intelligence"
        title="行业需求智能挖掘"
        subtitle="自动化采集政策文件、招标信息、行业报告，AI 分析数字化需求趋势，生成行业洞察报告"
        action={
          <div className="flex gap-2">
            <button onClick={handleRefresh} disabled={loading}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-white border border-slate-200 text-ink-secondary hover:border-slate-300 disabled:opacity-50 transition-all">
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              采集信号
            </button>
            <button onClick={handleGenerateReport} disabled={reportLoading}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50 transition-all">
              {reportLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5" />}
              AI 生成报告
            </button>
          </div>
        }
      />

      {/* Trend Overview */}
      {trends && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="rounded-lg bg-white border border-slate-200/80 p-4 shadow-sm">
            <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider">信号总量</p>
            <p className="text-2xl font-serif font-bold text-ink mt-1">{trends.total_signals}</p>
          </div>
          <div className="rounded-lg bg-white border border-slate-200/80 p-4 shadow-sm">
            <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider">覆盖行业</p>
            <p className="text-2xl font-serif font-bold text-ink mt-1">{industries.length}</p>
          </div>
          <div className="rounded-lg bg-white border border-slate-200/80 p-4 shadow-sm">
            <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider">数据来源</p>
            <p className="text-2xl font-serif font-bold text-ink mt-1">{Object.keys(trends.by_type).length} 类</p>
          </div>
          <div className="rounded-lg bg-white border border-slate-200/80 p-4 shadow-sm">
            <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider">热门标签</p>
            <div className="flex flex-wrap gap-1 mt-2">
              {trends.hot_tags.slice(0, 3).map((t, i) => (
                <span key={i} className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-indigo-50 text-primary">{t.tag}</span>
              ))}
            </div>
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

      <div className="flex flex-wrap gap-1.5">
        <button onClick={() => setActiveType(null)}
          className={`px-2.5 py-1 rounded text-[10px] font-semibold transition-all ${!activeType ? "bg-slate-900 text-white" : "bg-white border border-slate-200 text-ink-muted"}`}>
          全部类型
        </button>
        {Object.entries(sourceTypeMap).map(([key, val]) => (
          <button key={key} onClick={() => setActiveType(activeType === key ? null : key)}
            className={`px-2.5 py-1 rounded text-[10px] font-semibold transition-all ${activeType === key ? "bg-slate-900 text-white" : `border ${val.color}`}`}>
            {val.label}
          </button>
        ))}
      </div>

      {/* Signals List */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-24 bg-slate-100 animate-shimmer rounded-lg" />)}
        </div>
      ) : signals.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-ink-muted">暂无需求信号，点击"采集信号"获取数据</p>
        </div>
      ) : (
        <div className="space-y-3">
          {signals.map((sig) => {
            const typeInfo = sourceTypeMap[sig.source_type] || { label: sig.source_type, color: "bg-slate-50 text-slate-700" };
            const IndIcon = industryIcons[sig.industry] || Globe;
            return (
              <div key={sig.id} className="rounded-lg bg-white border border-slate-200/80 p-5 shadow-sm hover:shadow-md transition-all">
                <div className="flex items-start gap-4">
                  <div className={`h-10 w-10 rounded-lg bg-gradient-to-br ${industryColors[sig.industry] || "from-slate-500 to-gray-500"} flex items-center justify-center shrink-0`}>
                    <IndIcon className="h-5 w-5 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                      <span className={`text-[9px] font-semibold px-2 py-0.5 rounded border ${typeInfo.color}`}>{typeInfo.label}</span>
                      <span className="text-[9px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-ink-muted">{sig.industry}</span>
                      <span className="text-[9px] font-semibold text-amber-600">相关度 {Math.round(sig.relevance_score * 100)}%</span>
                    </div>
                    <h4 className="font-semibold text-sm text-ink mb-1">{sig.title}</h4>
                    <p className="text-xs text-ink-secondary leading-relaxed line-clamp-2">{sig.summary}</p>
                    {sig.demand_tags && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {sig.demand_tags.split(",").map((tag, i) => (
                          <span key={i} className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-indigo-50 text-primary">{tag.trim()}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  {sig.url && (
                    <a href={sig.url} target="_blank" rel="noopener noreferrer"
                      className="shrink-0 p-2 rounded-lg hover:bg-slate-50 text-ink-muted hover:text-primary transition-colors">
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* AI Report */}
      {report && (
        <div className="rounded-lg bg-white border border-slate-200/80 p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
            <FileText className="h-4 w-4 text-primary" />
            <h3 className="font-semibold text-sm text-ink">AI 行业需求洞察报告</h3>
          </div>
          <div className="prose prose-sm max-w-none text-ink-secondary leading-relaxed whitespace-pre-wrap">
            {report}
          </div>
        </div>
      )}
    </div>
  );
}
