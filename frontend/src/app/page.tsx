"use client";

import {
  TrendingUp, Users, ArrowUpRight, Activity,
  Zap, Globe, History, Building2, Radio,
  BarChart3, ChevronRight, Lightbulb, ShieldCheck, BookOpen,
  Clock, Sparkles, Gavel
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

interface HotSearchItem {
  rank: number;
  title: string;
  hot: string;
  link: string;
}

interface DailyInsight {
  date: string;
  industry: { name: string; summary: string; link: string }[];
  hotspots: { platform: string; title: string; link: string }[];
  news: { title: string; link: string }[];
  opportunities: { target: string; advice: string; opportunity: string }[];
}

const subModules = [
  {
    id: "market", label: "市场情报", icon: TrendingUp, href: "/insights/market",
    color: "bg-indigo-50 text-indigo-600",
    items: [
      { title: "AI 驱动市场全景分析 · 9 大行业热度矩阵", tag: "新" },
      { title: "行业深度分析 · 趋势研判与机会发现", tag: "智能" },
      { title: "综合研判 · 市场状态与增长预测", tag: "AI" },
    ]
  },
  {
    id: "industry", label: "行业全景", icon: Building2, href: "/insights/industry",
    color: "bg-blue-50 text-blue-600",
    items: [
      { title: "生物医疗 · CRISPR 2.0 基因编辑进入临床三期", tag: "高速增长" },
      { title: "交通 · 低空经济政策放宽，eVTOL 适航证核发加速", tag: "政策驱动" },
      { title: "基础设施 · 新型数据中心能效标准发布", tag: "稳健" },
    ]
  },
  {
    id: "hotspots", label: "技术热点", icon: Radio, href: "/insights/hotspots",
    color: "bg-violet-50 text-violet-600",
    items: [
      { title: "GitHub · Auto-GPT-Next 全自主商业智能代理", tag: "Trending" },
      { title: "CSDN · 2026 开发者生态报告：低代码 + AI 融合", tag: "Hot List" },
      { title: "高价值 · Project Stellar 区块链跨境结算协议", tag: "Featured" },
    ]
  },
  {
    id: "competitors", label: "友商洞察", icon: ShieldCheck, href: "/insights/competitors",
    color: "bg-rose-50 text-rose-600",
    items: [
      { title: "AWS 综合评分 92 · 全球基础设施最广", tag: "对比分析" },
      { title: "阿里云国内份额第一 · 华为云政企覆盖率领先", tag: "竞争格局" },
      { title: "华为云 6 大场景差距 · 出海/AI平台/开发者", tag: "深度洞察" },
    ]
  },
  {
    id: "policy", label: "政策法规", icon: BookOpen, href: "/insights/policy",
    color: "bg-amber-50 text-amber-600",
    items: [
      { title: "等保 2.0 · 新规覆盖制造业和零售业", tag: "高影响" },
      { title: "信创替代 · 2027 党政 100%，金融教育扩大", tag: "政策加速" },
      { title: "数字化补贴 · 24 省已出台，单企最高 500 万", tag: "补贴红利" },
    ]
  },
  {
    id: "opportunities", label: "商业机会", icon: Lightbulb, href: "/insights/opportunities",
    color: "bg-emerald-50 text-emerald-600",
    items: [
      { title: "腰部客户 · 订阅制安全合规服务市场激增", tag: "增长建议" },
      { title: "长尾客户 · 轻量化 AI 工具降低运营成本", tag: "效率提升" },
      { title: "初创企业 · 分布式 AI 算力众包", tag: "融资机会" },
    ]
  },
  {
    id: "news", label: "商业快讯", icon: Globe, href: "/insights/news",
    color: "bg-sky-50 text-sky-600",
    items: [
      { title: "全球半导体供应链重组：东南亚份额升至 30%", tag: "Reuters" },
      { title: "新能源汽车价格战趋缓，品牌忠诚度成核心", tag: "Bloomberg" },
      { title: "低空经济试点扩至 6 城，市场规模 95 亿", tag: "财新网" },
    ]
  },
  {
    id: "bidding", label: "招标信息", icon: TrendingUp, href: "/insights/bidding",
    color: "bg-rose-50 text-rose-600",
    items: [
      { title: "政务/制造/医疗等多行业招标实时追踪", tag: "商机雷达" },
      { title: "AI 分析高价值标段和投标策略", tag: "智能分析" },
      { title: "预算总额超 25 亿元 · 覆盖 9 个行业", tag: "精选" },
    ]
  },
];

export default function DashboardPage() {
  const [hotSearch, setHotSearch] = useState<HotSearchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [dailyInsight, setDailyInsight] = useState<DailyInsight | null>(null);
  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    const fetchHotSearch = async () => {
      try {
        const response = await fetch(`${API}/api/baidu-hotsearch`);
        const data = await response.json();
        setHotSearch(data);
      } catch (error) {
        console.error("Failed to fetch hot search:", error);
      } finally {
        setLoading(false);
      }
    };
    const fetchDailyInsight = async () => {
      try {
        const response = await fetch(`${API}/api/daily-insight`);
        const data = await response.json();
        setDailyInsight(data);
      } catch (error) {
        console.error("Failed to fetch daily insight:", error);
      }
    };
    fetchHotSearch();
    fetchDailyInsight();
    const interval = setInterval(fetchHotSearch, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [API]);

  return (
    <div className="space-y-7">
      {/* Hero */}
      <div className="rounded-xl bg-slate-900 text-white overflow-hidden">
        <div className="relative">
          <div className="absolute inset-0 opacity-[0.06]">
            <img src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1400&q=80" alt="" className="w-full h-full object-cover" />
          </div>
          <div className="relative px-8 py-10 md:py-12">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
              <div className="space-y-3 max-w-xl">
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-white/10 text-[11px] font-semibold">
                  <Clock className="h-3 w-3" />
                  Daily Business Intelligence
                </div>
                <h1 className="text-4xl md:text-5xl font-serif font-bold tracking-tight leading-tight">
                  今日商业市场洞察
                </h1>
                <p className="text-sm text-white/60 leading-relaxed">
                  实时监测 6 大核心板块 · AI 驱动的深度价值拆解 · 捕捉每一个微小的商业先机
                </p>
              </div>
              <div className="flex flex-col items-end gap-3 shrink-0">
                <div className="text-right">
                  <p className="text-[10px] text-white/40 font-medium uppercase tracking-wider">Edition</p>
                  <p className="text-lg font-serif font-bold">{new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
                </div>
                <Link href="/dashboard" className="flex items-center gap-2 rounded-lg bg-white/10 px-5 py-2 text-[13px] font-semibold hover:bg-white/20 transition-colors border border-white/10">
                  <BarChart3 className="h-4 w-4" />
                  进入数据大屏
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Kanban */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2.5">
        {[
          { label: "行业覆盖", value: "9", unit: "大行业", icon: Building2, href: "/insights/industry" },
          { label: "热点追踪", value: "156", unit: "个项目", icon: Radio, href: "/insights/hotspots" },
          { label: "友商监控", value: "5", unit: "家", icon: ShieldCheck, href: "/insights/competitors" },
          { label: "政策法规", value: "6", unit: "项核心", icon: BookOpen, href: "/insights/policy" },
          { label: "商业机会", value: "29", unit: "个", icon: Lightbulb, href: "/insights/opportunities" },
          { label: "实时快讯", value: "∞", unit: "持续", icon: Globe, href: "/insights/news" },
          { label: "AI 分析", value: "24/7", unit: "不间断", icon: Activity, href: "/dashboard" },
        ].map((item, i) => (
          <Link key={i} href={item.href} className="group rounded-lg bg-white border border-slate-200/80 p-3 shadow-sm hover:shadow-md hover:border-slate-300 transition-all">
            <div className="h-8 w-8 rounded-md bg-slate-50 border border-slate-200/60 flex items-center justify-center mb-2">
              <item.icon className="h-4 w-4 text-ink-secondary" />
            </div>
            <p className="text-[10px] font-medium text-ink-muted uppercase tracking-wider mb-0.5">{item.label}</p>
            <div className="flex items-baseline gap-1">
              <span className="text-lg font-serif font-bold text-ink">{item.value}</span>
              <span className="text-[10px] text-ink-muted">{item.unit}</span>
            </div>
          </Link>
        ))}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left */}
        <div className="lg:col-span-2 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="font-serif text-xl font-bold text-ink">市场洞察看板</h2>
            <span className="text-xs text-ink-muted">点击模块查看详情 →</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {subModules.map((mod) => (
              <Link
                key={mod.id}
                href={mod.href}
                className="group rounded-lg bg-white border border-slate-200/80 p-4 shadow-sm hover:shadow-md hover:border-slate-300 transition-all"
              >
                <div className="flex items-center gap-2.5 mb-3 pb-2.5 border-b border-slate-100">
                  <div className={`h-8 w-8 rounded-md ${mod.color} flex items-center justify-center`}>
                    <mod.icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 flex items-center justify-between">
                    <h3 className="font-semibold text-[13px] text-ink">{mod.label}</h3>
                    <ChevronRight className="h-3.5 w-3.5 text-ink-muted group-hover:text-ink transition-colors" />
                  </div>
                </div>
                <div className="space-y-2">
                  {mod.items.map((item, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="h-1 w-1 rounded-full bg-slate-300 mt-1.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-ink-secondary leading-relaxed line-clamp-1">{item.title}</p>
                        <span className="text-[10px] font-medium text-ink-muted">{item.tag}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </Link>
            ))}
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap gap-2">
            <Link href="/history" className="flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 transition-colors">
              <History className="h-3.5 w-3.5" />
              历史日报
            </Link>
            <Link href="/insights/market" className="flex items-center gap-1.5 rounded-lg bg-indigo-50 border border-indigo-200 px-4 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors">
              <Sparkles className="h-3.5 w-3.5" />
              市场情报
            </Link>
            <Link href="/insights/bidding" className="flex items-center gap-1.5 rounded-lg bg-rose-50 border border-rose-200 px-4 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-100 transition-colors">
              <Gavel className="h-3.5 w-3.5" />
              招标信息
            </Link>
            <Link href="/insights/competitors" className="flex items-center gap-1.5 rounded-lg bg-white border border-slate-200 px-4 py-2 text-xs font-medium text-ink-secondary hover:border-slate-300 hover:text-ink transition-colors">
              <ShieldCheck className="h-3.5 w-3.5" />
              友商对比
            </Link>
            <Link href="/dashboard" className="flex items-center gap-1.5 rounded-lg bg-white border border-slate-200 px-4 py-2 text-xs font-medium text-ink-secondary hover:border-slate-300 hover:text-ink transition-colors">
              <BarChart3 className="h-3.5 w-3.5" />
              数据大屏
            </Link>
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="space-y-4">
          {/* Baidu Hot Search */}
          <div className="rounded-lg bg-white border border-slate-200/80 p-4 shadow-sm">
            <div className="flex items-center justify-between mb-3 pb-2.5 border-b border-slate-100">
              <h3 className="font-serif text-base font-bold text-ink flex items-center gap-1.5">
                <span>🔥</span> 百度实时热搜
              </h3>
              <div className="h-1.5 w-1.5 rounded-full bg-rose-500 animate-pulse" />
            </div>
            <div className="space-y-2.5">
              {loading ? (
                <div className="space-y-2">
                  {[1, 2, 3, 4, 5].map((i) => <div key={i} className="h-5 w-full bg-slate-100 animate-shimmer rounded" />)}
                </div>
              ) : (
                hotSearch.map((item) => (
                  <a href={item.link} target="_blank" rel="noopener noreferrer" key={item.rank} className="flex items-center justify-between group cursor-pointer">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`flex h-4.5 w-4.5 items-center justify-center rounded text-[9px] font-bold shrink-0 ${item.rank <= 3 ? 'bg-slate-900 text-white' : 'bg-slate-100 text-ink-muted'}`}>{item.rank}</span>
                      <span className="text-xs text-ink-secondary group-hover:text-ink transition-colors truncate">{item.title}</span>
                    </div>
                    <span className="text-[10px] font-medium text-ink-muted shrink-0 ml-2">{item.hot}</span>
                  </a>
                ))
              )}
            </div>
            <p className="text-[10px] text-ink-muted text-center mt-3 pt-2.5 border-t border-slate-100">每 5 分钟自动刷新</p>
          </div>

          {/* Stats */}
          <div className="rounded-lg bg-white border border-slate-200/80 p-4 shadow-sm">
            <h3 className="font-serif text-base font-bold text-ink mb-3 pb-2.5 border-b border-slate-100">📊 今日数据</h3>
            <div className="space-y-2">
              {[
                { label: "新增分析任务", value: "18", trend: "+5" },
                { label: "生成报告数", value: "12", trend: "3 进行中" },
                { label: "数据源更新", value: "47", trend: "+8" },
                { label: "AI 调用次数", value: "156", trend: "+23" },
              ].map((stat, i) => (
                <div key={i} className="flex items-center justify-between py-1">
                  <span className="text-xs text-ink-secondary">{stat.label}</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[13px] font-serif font-bold text-ink">{stat.value}</span>
                    <span className="text-[10px] text-emerald-600 font-medium">{stat.trend}</span>
                  </div>
                </div>
              ))}
            </div>
            <Link href="/dashboard" className="mt-2.5 pt-2.5 border-t border-slate-100 flex items-center justify-center gap-1 text-xs text-ink-muted hover:text-ink transition-colors">
              查看完整看板 <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>

          {/* Status */}
          <div className="rounded-lg bg-white border border-slate-200/80 p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2.5">
              <h3 className="font-serif text-base font-bold text-ink">⚡ 系统状态</h3>
              <div className="flex items-center gap-1.5">
                <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[10px] font-medium text-emerald-600">正常</span>
              </div>
            </div>
            <div className="space-y-1.5">
              {[
                { label: "DeepSeek AI", latency: "45ms" },
                { label: "数据库连接", latency: "12ms" },
                { label: "数据爬虫", latency: "—" },
              ].map((sys, i) => (
                <div key={i} className="flex items-center justify-between text-xs py-0.5">
                  <div className="flex items-center gap-1.5">
                    <div className="h-1 w-1 rounded-full bg-emerald-500" />
                    <span className="text-ink-secondary">{sys.label}</span>
                  </div>
                  <span className="text-[10px] text-ink-muted">{sys.latency}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
