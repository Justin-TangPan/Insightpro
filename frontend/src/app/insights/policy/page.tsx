"use client";

import { InsightCard, InsightCardHeader } from "@/components/insight-card";
import { SectionHeader } from "@/components/section-header";
import { useState } from "react";
import {
  Shield, FileText, AlertTriangle, CheckCircle2, ExternalLink,
  Globe, Lock, RefreshCw, DollarSign, BookOpen, ChevronRight,
  ArrowUpRight, Clock, Scale, Target, TrendingUp
} from "lucide-react";
import Link from "next/link";

const policies: Array<{
  id: string;
  icon: any;
  title: string;
  subtitle: string;
  status: string;
  severity: string;
  summary: string;
  impact: string;
  action: string;
  deadline: string;
  source: string;
}> = [
  {
    id: "dengbao",
    icon: Shield,
    title: "等保 2.0",
    subtitle: "网络安全等级保护制度",
    status: "强制执行",
    severity: "high",
    summary: "所有云服务采购方需满足对应等级的安全要求，等保三级为腰部客户刚需。2025 年起等保三级覆盖范围扩大到制造业和零售业。",
    impact: "直接影响云服务选型：未通过等保测评的云平台无法进入政企采购清单。华为云已通过等保三级/四级测评，可作为合规基座。",
    action: "建议在销售流程中嵌入等保咨询环节，帮助客户完成定级→备案→整改→测评全流程。",
    deadline: "新系统上线前须完成定级备案",
    source: "公安部 · GB/T 22239-2019"
  },
  {
    id: "xinchang",
    icon: RefreshCw,
    title: "信创替代",
    subtitle: "信息技术应用创新",
    status: "政策加速",
    severity: "high",
    summary: "2027 年底前，党政机关和关键基础设施领域完成 100% 信创替代。金融、教育、医疗等行业信创试点范围持续扩大。",
    impact: "华为云鲲鹏 + GaussDB + 欧拉的全栈自主可控方案，是目前信创替代最完整的云平台选择。腰部客户的信创替代需求将从 2026 年下半年集中释放。",
    action: '提前锁定区域信创试点项目，输出标准化的"信创迁移工具包"和"信创架构评估服务"。',
    deadline: "党政 2027 · 行业 2025-2028",
    source: "国务院 · 工信部信创工作组"
  },
  {
    id: "data-cross",
    icon: Globe,
    title: "数据出境安全评估",
    subtitle: "数据跨境传输合规要求",
    status: "需持续关注",
    severity: "medium",
    summary: "《数据出境安全评估办法》要求向境外提供数据的机构须通过安全评估。对跨境电商、出海 SaaS、跨国制造企业影响显著。",
    impact: "使用海外云服务（AWS/Azure 海外 region）的腰部客户需进行数据出境自评估。华为云国内 Region 可帮助客户规避数据出境合规风险。",
    action: "对于有跨境业务的中腰部客户，建议优先采用国内部署+安全沙箱的混合架构。",
    deadline: "每年定期评估",
    source: "国家网信办"
  },
  {
    id: "opc",
    icon: Lock,
    title: "OPC（海外云服务提供商合规）",
    subtitle: "海外云服务提供商监管框架",
    status: "新规酝酿",
    severity: "medium",
    summary: "监管部门拟对海外云服务提供商在华业务实施更严格的合规审查，涉及数据主权、运维本地化、源代码审查等维度。",
    impact: "AWS 中国、Azure 中国等海外云厂商可能面临更严格的运营限制，部分客户将加速转向国内云平台。华为云作为国内云厂商，在合规方面具备天然优势。",
    action: "关注 OPC 正式稿发布节奏，锁定外资转内资的迁移需求。准备好厂商对比白皮书和迁移方案。",
    deadline: "征求意见中，预计 2027 年落地",
    source: "工信部信息通信管理局"
  },
  {
    id: "subsidy",
    icon: DollarSign,
    title: "行业数字化补贴",
    subtitle: "企业上云专项财政补贴",
    status: "多省推行",
    severity: "high",
    summary: "全国 24 个省级行政区已出台企业上云补贴政策，单家企业最高可获 500 万补贴。覆盖领域：智能制造、中小企业数字化、农业电商等。",
    impact: "各地补贴政策直接降低客户上云决策门槛，是销售切入的最佳时机。但补贴申请流程复杂，客户需要专业指导。",
    action: '建立各省补贴政策数据库，将补贴申请咨询作为获客钩子。华为云可提供"补贴申报 + 方案设计"一站式服务。',
    deadline: "各省申报窗口期不同（通常 Q2/Q4）",
    source: "各省工信厅 · 财政局"
  },
  {
    id: "soc",
    icon: BookOpen,
    title: "SOC / 安全运营资质",
    subtitle: "安全运营中心认证及相关技能要求",
    status: "行业趋势",
    severity: "medium",
    summary: "金融、医疗等监管严格行业对云服务商的安全运营能力提出更高要求。SOC 2 报告、ISO 27001 认证等成为腰部客户招标的准入门槛。",
    impact: "多数中腰部客户缺乏内部安全运营能力，需要云服务商提供托管安全运营服务。华为云乾坤安全运营服务可满足该需求。",
    action: "在解决方案中嵌入安全运营服务包，提供 SOC 2 合规报告模板。",
    deadline: "招标资质要求 · 持续满足",
    source: "ISACA · ISO 标准组织"
  },
];

const severityMap: Record<string, { label: string; class: string }> = {
  high: { label: "高影响", class: "bg-rose-50 text-rose-600 border border-rose-200" },
  medium: { label: "中影响", class: "bg-amber-50 text-amber-600 border border-amber-200" },
};

export default function PolicyPage() {
  const [activePolicy, setActivePolicy] = useState<string | null>(null);

  return (
    <div className="space-y-10">
      <SectionHeader
        badge="Policy Radar"
        title="政策法规雷达"
        subtitle="实时追踪影响中长尾/腰部客户云采购决策的核心政策法规，包括等保、信创、数据出境、OPC、数字化补贴、安全运营资质等"
        image="https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=1200&q=80"
        action={
          <div className="flex items-center gap-2 px-4 py-2 rounded-full border border-slate-200/60 bg-white shadow-[var(--shadow-card)]">
            <div className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
            <span className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">实时监测中</span>
          </div>
        }
      />

      {/* Executive Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: "监测政策数", value: "6", unit: "项核心法规", icon: FileText, color: "text-indigo-600" },
          { label: "高影响政策", value: "3", unit: "项", icon: AlertTriangle, color: "text-rose-600" },
          { label: "关联商机窗口", value: "4", unit: "个行业", icon: Target, color: "text-amber-600" },
          { label: "涉及补贴总额", value: "500万+", unit: "元/企业", icon: DollarSign, color: "text-emerald-600" },
        ].map((stat, i) => (
          <div key={i} className="rounded-xl bg-white border border-slate-200/60 p-5 shadow-[var(--shadow-card)]">
            <div className="flex items-center justify-between mb-3">
              <div className={`h-9 w-9 rounded-full bg-indigo-50 flex items-center justify-center`}>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </div>
            </div>
            <p className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-0.5">{stat.label}</p>
            <div className="flex items-baseline gap-1">
              <span className={`text-2xl font-serif font-bold ${stat.color}`}>{stat.value}</span>
              <span className="text-[11px] font-medium text-ink-muted">{stat.unit}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Policy Cards */}
      <div className="grid grid-cols-1 gap-6">
        {policies.map((p) => (
          <div
            key={p.id}
            className="rounded-xl bg-white border border-slate-200/60 overflow-hidden transition-all shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-card-hover)]"
          >
            {/* Header */}
            <div
              className="flex items-center justify-between px-8 py-4 cursor-pointer"
              onClick={() => setActivePolicy(activePolicy === p.id ? null : p.id)}
            >
              <div className="flex items-center gap-4">
                <div className={`h-10 w-10 rounded-full flex items-center justify-center ${
                  p.severity === "high" ? "bg-rose-50" : "bg-amber-50"
                }`}>
                  <p.icon className={`h-5 w-5 ${p.severity === "high" ? "text-rose-600" : "text-amber-600"}`} />
                </div>
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="font-bold text-lg text-ink">{p.title}</h3>
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${severityMap[p.severity].class}`}>
                      {severityMap[p.severity].label}
                    </span>
                    <span className="text-[10px] font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                      {p.status}
                    </span>
                  </div>
                  <p className="text-xs text-ink-secondary font-medium">{p.subtitle}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className="hidden md:block text-[11px] text-ink-muted font-medium">{p.source}</span>
                <ChevronRight className={`h-5 w-5 text-ink-muted transition-transform ${activePolicy === p.id ? "rotate-90" : ""}`} />
              </div>
            </div>

            {/* Expanded Detail */}
            {activePolicy === p.id && (
              <div className="px-8 pb-8 pt-2 border-t border-slate-100">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                  <div className="space-y-4">
                    <div>
                      <p className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">政策概要</p>
                      <p className="text-sm text-ink-secondary leading-relaxed">{p.summary}</p>
                    </div>
                    <div>
                      <p className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">对业务的影响</p>
                      <div className="border-l-4 border-rose-400 pl-4 py-2 bg-rose-50/50 rounded-r-lg">
                        <p className="text-sm text-ink-secondary leading-relaxed">{p.impact}</p>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <p className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">建议行动</p>
                      <div className="border-l-4 border-emerald-400 pl-4 py-2 bg-emerald-50/50 rounded-r-lg">
                        <p className="text-sm font-medium text-ink-secondary leading-relaxed">{p.action}</p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between rounded-xl border border-slate-200/60 p-4 bg-slate-50/50">
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-ink-muted" />
                        <div>
                          <p className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">关键时间节点</p>
                          <p className="text-sm font-bold text-ink">{p.deadline}</p>
                        </div>
                      </div>
                      <span className="text-[11px] text-ink-muted font-medium">{p.source}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Strategic Summary */}
      <div className="rounded-xl bg-white border border-slate-200/60 p-5 shadow-[var(--shadow-card)]">
        <div className="mb-6">
          <h3 className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">Policy Radar</h3>
          <h2 className="text-xl font-serif font-bold text-ink">政策雷达 · 商机洞察</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="rounded-xl border-l-4 border-emerald-400 bg-emerald-50/30 p-5">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="h-5 w-5 text-emerald-600" />
              <h4 className="font-bold text-sm text-ink">近期商机窗口</h4>
            </div>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start gap-2">
                <span className="font-bold text-indigo-600">1.</span>
                <span className="text-xs text-ink-secondary">Q3 多省开放数字化补贴申报，锁定 100+ 目标客户</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="font-bold text-indigo-600">2.</span>
                <span className="text-xs text-ink-secondary">信创替代从党政扩展到金融/教育行业，500+ 腰部客户进入选型期</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="font-bold text-indigo-600">3.</span>
                <span className="text-xs text-ink-secondary">等保三级新规覆盖制造业，200+ 工厂面临合规整改需求</span>
              </li>
            </ul>
          </div>

          <div className="rounded-xl border-l-4 border-indigo-400 bg-indigo-50/30 p-5">
            <div className="flex items-center gap-2 mb-3">
              <Target className="h-5 w-5 text-indigo-600" />
              <h4 className="font-bold text-sm text-ink">华为人优势</h4>
            </div>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start gap-2">
                <span className="font-bold text-emerald-600">+</span>
                <span className="text-xs text-ink-secondary">等保三级/四级 + 信创全栈认证，合规门槛即是壁垒</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="font-bold text-emerald-600">+</span>
                <span className="text-xs text-ink-secondary">国内部署规避数据出境风险，相对海外云厂商合规优势显著</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="font-bold text-emerald-600">+</span>
                <span className="text-xs text-ink-secondary">可提供补贴申报 + 方案设计一站式服务，降低客户决策成本</span>
              </li>
            </ul>
          </div>

          <div className="rounded-xl border-l-4 border-amber-400 bg-amber-50/30 p-5">
            <div className="flex items-center gap-2 mb-3">
              <Scale className="h-5 w-5 text-amber-600" />
              <h4 className="font-bold text-sm text-ink">需关注的风险</h4>
            </div>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start gap-2">
                <span className="font-bold text-rose-500">!</span>
                <span className="text-xs text-ink-secondary">OPC 新规可能导致 AWS/Azure 降价抢单，需提前锁定迁移客户</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="font-bold text-rose-500">!</span>
                <span className="text-xs text-ink-secondary">各地补贴政策口径不统一，需建立本地化团队做政策解读</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="font-bold text-rose-500">!</span>
                <span className="text-xs text-ink-secondary">信创替代时间表可能受国际关系影响调整，需保持方案灵活性</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
