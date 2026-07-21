"use client";

import {
  TrendingUp, ArrowUpRight, Activity,
  Globe, History, Building2, Radio,
  BarChart3, ChevronRight, Lightbulb, ShieldCheck, BookOpen,
  Clock, Gavel
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import type { LucideIcon } from "lucide-react";

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

type Accent = "lemon" | "lime" | "signal" | "ink";
const accentBar: Record<Accent, string> = {
  lemon: "swiss-accent-bar swiss-accent-bar-lemon",
  lime: "swiss-accent-bar swiss-accent-bar-lime",
  signal: "swiss-accent-bar swiss-accent-bar-signal",
  ink: "swiss-accent-bar",
};
const accentTile: Record<Accent, string> = {
  lemon: "bg-lemon text-ink",
  lime: "bg-lime text-ink",
  signal: "bg-signal text-paper",
  ink: "bg-ink text-paper",
};

interface SubModuleItem {
  title: string;
  tag: string;
}

interface SubModule {
  id: string;
  label: string;
  icon: LucideIcon;
  href: string;
  accent: Accent;
  items: SubModuleItem[];
}

interface ApiModule {
  id: string;
  label?: string;
  href?: string;
  items?: { title: string; tag?: string }[];
}

const subModules: SubModule[] = [
  {
    id: "industry", label: "行业全景", icon: Building2, href: "/insights/industry", accent: "lemon",
    items: [
      { title: "生物医疗 · CRISPR 2.0 基因编辑进入临床三期", tag: "高速增长" },
      { title: "交通 · 低空经济政策放宽，eVTOL 适航证核发加速", tag: "政策驱动" },
      { title: "基础设施 · 新型数据中心能效标准发布", tag: "稳健" },
    ]
  },
  {
    id: "hotspots", label: "技术热点", icon: Radio, href: "/insights/hotspots", accent: "lime",
    items: [
      { title: "GitHub · Auto-GPT-Next 全自主商业智能代理", tag: "Trending" },
      { title: "CSDN · 2026 开发者生态报告：低代码 + AI 融合", tag: "Hot List" },
      { title: "高价值 · Project Stellar 区块链跨境结算协议", tag: "Featured" },
    ]
  },
  {
    id: "competitors", label: "友商洞察", icon: ShieldCheck, href: "/insights/competitors", accent: "signal",
    items: [
      { title: "AWS 综合评分 92 · 全球基础设施最广", tag: "对比分析" },
      { title: "阿里云国内份额第一 · 华为云政企覆盖率领先", tag: "竞争格局" },
      { title: "华为云 6 大场景差距 · 出海/AI平台/开发者", tag: "深度洞察" },
    ]
  },
  {
    id: "policy", label: "政策法规", icon: BookOpen, href: "/insights/policy", accent: "lemon",
    items: [
      { title: "等保 2.0 · 新规覆盖制造业和零售业", tag: "高影响" },
      { title: "信创替代 · 2027 党政 100%，金融教育扩大", tag: "政策加速" },
      { title: "数字化补贴 · 24 省已出台，单企最高 500 万", tag: "补贴红利" },
    ]
  },
  {
    id: "opportunities", label: "商业机会", icon: Lightbulb, href: "/insights/opportunities", accent: "lime",
    items: [
      { title: "腰部客户 · 订阅制安全合规服务市场激增", tag: "增长建议" },
      { title: "长尾客户 · 轻量化 AI 工具降低运营成本", tag: "效率提升" },
      { title: "初创企业 · 分布式 AI 算力众包", tag: "融资机会" },
    ]
  },
  {
    id: "news", label: "商业快讯", icon: Globe, href: "/insights/news", accent: "signal",
    items: [
      { title: "全球半导体供应链重组：东南亚份额升至 30%", tag: "Reuters" },
      { title: "新能源汽车价格战趋缓，品牌忠诚度成核心", tag: "Bloomberg" },
      { title: "低空经济试点扩至 6 城，市场规模 95 亿", tag: "财新网" },
    ]
  },
  {
    id: "bidding", label: "招标信息", icon: TrendingUp, href: "/insights/bidding", accent: "ink",
    items: [
      { title: "政务/制造/医疗等多行业招标实时追踪", tag: "商机雷达" },
      { title: "AI 分析高价值标段和投标策略", tag: "智能分析" },
      { title: "预算总额超 25 亿元 · 覆盖 9 个行业", tag: "精选" },
    ]
  },
];

// Map API module data to subModules
const moduleIconMap: Record<string, LucideIcon> = {
  market: Building2, industry: Building2, hotspots: Radio, competitors: ShieldCheck,
  policy: BookOpen, opportunities: Lightbulb, news: Globe, bidding: TrendingUp,
};
const moduleAccentMap: Record<string, Accent> = {
  market: "lemon", industry: "lemon", hotspots: "lime", competitors: "signal",
  policy: "lemon", opportunities: "lime", news: "signal", bidding: "ink",
};

export default function DashboardPage() {
  const [hotSearch, setHotSearch] = useState<HotSearchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [, setDailyInsight] = useState<DailyInsight | null>(null);
  const [dynamicModules, setDynamicModules] = useState<typeof subModules>(() =>
    subModules.map((module) => ({ ...module, items: [] }))
  );
  const [homepageStats, setHomepageStats] = useState<Record<string, number>>({});

  useEffect(() => {
    const fetchHotSearch = async () => {
      try {
        const response = await fetch(`${API}/api/baidu-hotsearch`);
        if (!response.ok) { throw new Error(`API error: ${response.status}`); }
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
        if (!response.ok) { throw new Error(`API error: ${response.status}`); }
        const data = await response.json();
        setDailyInsight(data);
      } catch (error) {
        console.error("Failed to fetch daily insight:", error);
      }
    };
    const fetchModules = async () => {
      try {
        const response = await fetch(`${API}/api/homepage/modules`);
        if (!response.ok) return;
        const data = await response.json();
        if (Array.isArray(data) && data.length > 0) {
          // Real-time modules must not fall back to stale static content.
          const modules = data as ApiModule[];
          const merged = subModules.map(sm => {
            const apiMod = modules.find((m) => m.id === sm.id);
            if (apiMod && apiMod.items && apiMod.items.length > 0) {
              return { ...sm, items: apiMod.items.map((it) => ({ title: it.title, tag: it.tag || "" })) };
            }
            return { ...sm, items: [] };
          });
          // Add any API modules not in our static list
          modules.forEach((m) => {
            if (!merged.find(sm => sm.id === m.id) && m.items && m.items.length > 0) {
              merged.push({
                id: m.id, label: m.label || m.id, icon: moduleIconMap[m.id] || Globe,
                href: m.href || `/insights/${m.id}`, accent: moduleAccentMap[m.id] || "ink",
                items: m.items.map((it) => ({ title: it.title, tag: it.tag || "" })),
              });
            }
          });
          setDynamicModules(merged);
        }
      } catch {}
    };
    const fetchStats = async () => {
      try {
        const response = await fetch(`${API}/api/homepage/stats`);
        if (!response.ok) return;
        const data = await response.json();
        setHomepageStats(data);
      } catch {}
    };
    fetchHotSearch();
    fetchDailyInsight();
    fetchModules();
    fetchStats();
    const interval = setInterval(fetchHotSearch, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-10">
      {/* Hero — 瑞士式黑底全宽 */}
      <div className="bg-ink text-paper overflow-hidden">
        <div className="relative">
          <div className="absolute inset-0 opacity-[0.05] grayscale">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1400&q=80" alt="" className="w-full h-full object-cover" />
          </div>
          <div className="relative px-8 lg:px-12 py-12 md:py-16">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
              <div className="space-y-5 max-w-xl">
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-lemon text-ink swiss-kicker">
                  <Clock className="h-3 w-3" />
                  Daily Business Intelligence
                </div>
                <h1 className="text-5xl md:text-6xl serif-display text-paper">
                  今日商业市场洞察
                </h1>
                <p className="text-sm text-paper/60 leading-relaxed max-w-lg">
                  实时监测 6 大核心板块 · AI 驱动的深度价值拆解 · 捕捉每一个微小的商业先机
                </p>
              </div>
              <div className="flex flex-col items-end gap-4 shrink-0">
                <div className="text-right">
                  <p className="swiss-kicker text-paper/40">Edition</p>
                  <p className="text-lg font-bold tracking-tight">{new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
                </div>
                <Link href="/dashboard" className="flex items-center gap-2 bg-paper text-ink px-5 py-2 text-[13px] font-semibold hover:bg-lemon transition-colors">
                  <BarChart3 className="h-4 w-4" strokeWidth={1.5} />
                  进入数据大屏
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Kanban — 瑞士式锐角统计格 */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-px bg-grid border border-grid">
        {[
          { label: "行业覆盖", value: String(homepageStats.industry_count || 9), unit: "大行业", icon: Building2, href: "/insights/industry" },
          { label: "热点追踪", value: String(homepageStats.trending_today || homepageStats.trending_total || 0), unit: "个项目", icon: Radio, href: "/insights/hotspots" },
          { label: "友商监控", value: String(homepageStats.competitor_count || 0), unit: "条动态", icon: ShieldCheck, href: "/insights/competitors" },
          { label: "政策法规", value: String(homepageStats.policy_count || 0), unit: "条", icon: BookOpen, href: "/insights/policy" },
          { label: "商业机会", value: String(homepageStats.bidding_count || 0), unit: "条招标", icon: Lightbulb, href: "/insights/opportunities" },
          { label: "实时快讯", value: String(homepageStats.news_count || 0), unit: "条", icon: Globe, href: "/insights/news" },
          { label: "需求信号", value: String(homepageStats.demand_count || 0), unit: "条", icon: Activity, href: "/insights/demand" },
        ].map((item, i) => (
          <Link key={i} href={item.href} className="group bg-white p-4 hover:bg-paper transition-colors">
            <div className="h-8 w-8 flex items-center justify-center mb-3 border border-grid">
              <item.icon className="h-4 w-4 text-ink-secondary" strokeWidth={1.5} />
            </div>
            <p className="swiss-kicker text-ink-muted mb-1">{item.label}</p>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl serif-stat text-ink">{item.value}</span>
              <span className="text-xs text-ink-muted">{item.unit}</span>
            </div>
          </Link>
        ))}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="serif-heading text-2xl text-ink">市场洞察看板</h2>
            <span className="swiss-kicker text-ink-muted">点击模块查看详情 →</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-grid border border-grid">
            {dynamicModules.map((mod) => (
              <Link
                key={mod.id}
                href={mod.href}
                className={`group bg-white p-5 hover:bg-paper transition-colors ${accentBar[mod.accent]}`}
              >
                <div className="flex items-center gap-2.5 mb-3 pb-3 border-b border-grid">
                  <div className={`h-8 w-8 flex items-center justify-center ${accentTile[mod.accent]}`}>
                    <mod.icon className="h-4 w-4" strokeWidth={1.5} />
                  </div>
                  <div className="flex-1 flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-ink">{mod.label}</h3>
                    <ChevronRight className="h-3.5 w-3.5 text-ink-muted group-hover:text-ink transition-colors" strokeWidth={1.5} />
                  </div>
                </div>
                <div className="space-y-2">
                  {mod.items.length === 0 && (
                    <p className="text-xs leading-relaxed text-amber-700">暂无满足时效要求的数据</p>
                  )}
                  {mod.items.map((item, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="h-1 w-1 bg-ink-muted mt-1.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-ink-secondary leading-relaxed line-clamp-1">{item.title}</p>
                        <span className="text-xs font-medium text-ink-muted">{item.tag}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </Link>
            ))}
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap gap-2">
            <Link href="/history" className="flex items-center gap-1.5 bg-ink px-4 py-2 text-xs font-semibold text-paper hover:bg-ink-secondary transition-colors">
              <History className="h-3.5 w-3.5" strokeWidth={1.5} />
              历史日报
            </Link>
            <Link href="/insights/bidding" className="flex items-center gap-1.5 border border-ink px-4 py-2 text-xs font-semibold text-ink hover:bg-ink hover:text-paper transition-colors">
              <Gavel className="h-3.5 w-3.5" strokeWidth={1.5} />
              招标信息
            </Link>
            <Link href="/insights/competitors" className="flex items-center gap-1.5 border border-grid px-4 py-2 text-xs font-medium text-ink-secondary hover:border-ink hover:text-ink transition-colors">
              <ShieldCheck className="h-3.5 w-3.5" strokeWidth={1.5} />
              友商对比
            </Link>
            <Link href="/dashboard" className="flex items-center gap-1.5 border border-grid px-4 py-2 text-xs font-medium text-ink-secondary hover:border-ink hover:text-ink transition-colors">
              <BarChart3 className="h-3.5 w-3.5" strokeWidth={1.5} />
              数据大屏
            </Link>
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="space-y-6">
          {/* Baidu Hot Search */}
          <div className="bg-white border border-grid p-5">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-grid">
              <h3 className="serif-heading text-lg text-ink flex items-center gap-1.5">
                <span className="text-signal">●</span> 百度实时热搜
              </h3>
              <div className="h-1.5 w-1.5 rounded-full bg-signal animate-pulse" />
            </div>
            <div className="space-y-2.5">
              {loading ? (
                <div className="space-y-2">
                  {[1, 2, 3, 4, 5].map((i) => <div key={i} className="h-5 w-full animate-shimmer" />)}
                </div>
              ) : (
                hotSearch.map((item) => (
                  <a href={item.link} target="_blank" rel="noopener noreferrer" key={item.rank} className="flex items-center justify-between group cursor-pointer">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`flex h-5 w-5 items-center justify-center text-[10px] font-bold shrink-0 ${item.rank <= 3 ? 'bg-ink text-paper' : 'bg-paper text-ink-muted border border-grid'}`}>{item.rank}</span>
                      <span className="text-xs text-ink-secondary group-hover:text-ink transition-colors truncate">{item.title}</span>
                    </div>
                    <span className="text-xs font-medium text-ink-muted shrink-0 ml-2">{item.hot}</span>
                  </a>
                ))
              )}
            </div>
            <p className="text-xs text-ink-muted text-center mt-4 pt-3 border-t border-grid">每 5 分钟自动刷新</p>
          </div>

          {/* Stats */}
          <div className="bg-white border border-grid p-5">
            <h3 className="serif-heading text-lg text-ink mb-4 pb-3 border-b border-grid">今日数据</h3>
            <div className="space-y-2.5">
              {[
                { label: "行业新闻", value: String(homepageStats.news_count || 0), trend: "本周" },
                { label: "招标信息", value: String(homepageStats.bidding_count || 0), trend: "本周" },
                { label: "需求信号", value: String(homepageStats.demand_count || 0), trend: "本周" },
                { label: "政策法规", value: String(homepageStats.policy_count || 0), trend: "本周" },
              ].map((stat, i) => (
                <div key={i} className="flex items-center justify-between py-1">
                  <span className="text-xs text-ink-secondary">{stat.label}</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-semibold text-ink">{stat.value}</span>
                    <span className="text-xs text-lime font-medium">{stat.trend}</span>
                  </div>
                </div>
              ))}
            </div>
            <Link href="/dashboard" className="mt-4 pt-3 border-t border-grid flex items-center justify-center gap-1 text-xs text-ink-muted hover:text-ink transition-colors">
              查看完整看板 <ArrowUpRight className="h-3 w-3" strokeWidth={1.5} />
            </Link>
          </div>

          {/* Status */}
          <div className="bg-white border border-grid p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="serif-heading text-lg text-ink">系统状态</h3>
              <div className="flex items-center gap-1.5">
                <div className="h-1.5 w-1.5 rounded-full bg-lime animate-pulse" />
                <span className="text-xs font-medium text-lime">正常</span>
              </div>
            </div>
            <div className="space-y-2">
              {[
                { label: "AI 服务", latency: "45ms" },
                { label: "数据库连接", latency: "12ms" },
                { label: "数据爬虫", latency: "—" },
              ].map((sys, i) => (
                <div key={i} className="flex items-center justify-between text-xs py-0.5">
                  <div className="flex items-center gap-1.5">
                    <div className="h-1 w-1 bg-lime" />
                    <span className="text-ink-secondary">{sys.label}</span>
                  </div>
                  <span className="text-xs text-ink-muted">{sys.latency}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
