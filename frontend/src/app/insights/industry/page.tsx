"use client";

import { SectionHeader } from "@/components/section-header";
import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import {
  Truck, Building2, Laptop, ShoppingCart, Factory,
  Zap, GraduationCap, Leaf,
  ExternalLink, ChevronRight, ShieldCheck, Cloud, FileText, Activity
} from "lucide-react";
import { cases, getCasesByIndustry } from "@/lib/cases-data";

// 行业元数据
interface IndustryMeta {
  name: string;
  icon: React.ElementType;
  status: string;
  statusColor: string;
  summary: string;
  trend: string;
  links: { title: string; url: string }[];
}

const industries: IndustryMeta[] = [
  {
    name: "制造",
    icon: Factory,
    status: "智能化",
    statusColor: "bg-indigo-50 text-indigo-700",
    summary: "工业互联网从'建平台'转向'用平台'。AWS、Azure 与阿里云持续通过工业 AI、IoT 和数据平台帮助制造业客户优化质量与供应链。",
    trend: "中国工业互联网平台市场 2026 年达 1,500 亿元，年增 28%（IDC）",
    links: [
      { title: "AWS·Mondelez 制造业云迁移", url: "https://aws.amazon.com/cn/solutions/case-studies/mondelez-case-study/" },
      { title: "Microsoft 客户案例", url: "https://www.microsoft.com/en-us/customers" },
    ]
  },
  {
    name: "金融",
    icon: Building2,
    status: "信创替代",
    statusColor: "bg-amber-50 text-amber-700",
    summary: "金融业正加速核心系统现代化和生成式 AI 落地。AWS、Azure、阿里云与腾讯云的竞争焦点已转向数据治理、智能客服和分布式数据库。",
    trend: "中国金融信创市场 2026 年达 1,000 亿元，年增 35%（中国信通院）",
    links: [
      { title: "AWS·Experian AI 现代化", url: "https://aws.amazon.com/solutions/case-studies/experian-agenticai/" },
      { title: "腾讯云·金融客户案例", url: "https://cloud.tencent.com/case" },
    ]
  },
  {
    name: "交通",
    icon: Truck,
    status: "智慧化",
    statusColor: "bg-blue-50 text-blue-700",
    summary: "智慧交通从信号灯优化升级到机场、港口和多模式公交。云厂商正围绕实时调度、数据平台和 AI 预测开展合作。",
    trend: "中国智慧交通市场 2026 年达 3,200 亿元（赛迪顾问）",
    links: [
      { title: "阿里云·JakLingko 交通案例", url: "https://www.alibabacloud.com/en/customers/jaklingko" },
      { title: "腾讯云·智慧交通方案", url: "https://cloud.tencent.com/solution/lbs" },
    ]
  },
  {
    name: "能源",
    icon: Zap,
    status: "高速增长",
    statusColor: "bg-yellow-50 text-yellow-700",
    summary: "新型电力系统数字化、新能源发电预测和碳资产管理成为核心需求。AWS 与 Azure 的能源行业合作重点集中在 HPC、IoT 和数据分析。",
    trend: "中国能源数字化市场 2026 年达 3,200 亿元，新能源发电预测 AI 渗透率从 15% 提升至 42%（赛迪顾问）",
    links: [
      { title: "AWS 能源行业案例", url: "https://aws.amazon.com/energy/" },
      { title: "Microsoft 能源行业", url: "https://www.microsoft.com/en-us/industry/energy" },
    ]
  },
  {
    name: "零售",
    icon: ShoppingCart,
    status: "数字化",
    statusColor: "bg-amber-50 text-amber-700",
    summary: "即时零售渗透率突破 50%，AI 驱动的精准营销和智能选品成为零售商核心需求。蘑菇街案例验证了云原生在电商场景的价值。",
    trend: "中国零售数字化市场 2026 年达 5,200 亿元（艾瑞咨询）",
    links: [
      { title: "阿里云·资生堂新零售案例", url: "https://www.alibabacloud.com/en/customers/shiseido" },
      { title: "火山引擎·电商解决方案", url: "https://www.volcengine.com/solution/ecommerce" },
      { title: "阿里云·零售方案", url: "https://www.aliyun.com/product/tongyi" },
    ]
  },
  {
    name: "互联网",
    icon: Laptop,
    status: "范式转移",
    statusColor: "bg-violet-50 text-violet-700",
    summary: "AI Agent 成为互联网行业新范式。扣子 Coze 用户突破千万，GitHub AI Agent 项目 Star 增长 340%。字节、阿里、腾讯在 AI 平台战争中加速布局。",
    trend: "GitHub 上 AI Agent 相关项目 2026 年 Star 总数增长 340%（GitHub Octoverse）",
    links: [
      { title: "AWS·Pinterest AI 案例", url: "https://aws.amazon.com/cn/solutions/case-studies/pinterest-ai-case-study/" },
      { title: "火山引擎·扣子 Coze 平台", url: "https://www.volcengine.com/product/coze" },
      { title: "火山引擎·豆包大模型", url: "https://www.volcengine.com/product/doubao" },
    ]
  },
  {
    name: "政务",
    icon: Building2,
    status: "政策驱动",
    statusColor: "bg-emerald-50 text-emerald-700",
    summary: "政务云从 IaaS 向 PaaS/SaaS 升级，AI 中台和数据中台成为新增长点。重点观察 Azure、AWS、阿里云与腾讯云在公共服务和数据治理方面的合作。",
    trend: "中国政务云市场 2026 年达 1,200 亿元，国产化替代率从 45% 提升至 68%（中国信通院）",
    links: [
      { title: "Microsoft 公共部门案例", url: "https://www.microsoft.com/en-us/industry/government" },
      { title: "AWS 公共部门", url: "https://aws.amazon.com/government-education/government/" },
    ]
  },
  {
    name: "教育",
    icon: GraduationCap,
    status: "智能化",
    statusColor: "bg-sky-50 text-sky-700",
    summary: "AI 个性化学习、教育专网建设、智慧校园成为三大方向。腾讯云在教育行业有深度解决方案。",
    trend: "中国教育信息化市场 2026 年达 5,800 亿元，AI 教育渗透率从 18% 提升至 35%（中国信通院）",
    links: [
      { title: "腾讯云·教育解决方案", url: "https://cloud.tencent.com/solution/education" },
      { title: "阿里云·教育方案", url: "https://www.aliyun.com/product/tongyi" },
    ]
  },
  {
    name: "农业",
    icon: Leaf,
    status: "新兴市场",
    statusColor: "bg-green-50 text-green-700",
    summary: "智慧农业进入快速发展期，物联网+AI 在农田监测、精准施肥、农产品溯源场景加速落地。",
    trend: "中国智慧农业市场 2026 年达 2,100 亿元，年增 30%（艾瑞咨询）",
    links: [
      { title: "AWS 农业解决方案", url: "https://aws.amazon.com/solutions/agriculture/" },
      { title: "阿里云·农业方案", url: "https://www.aliyun.com/product/tongyi" },
    ]
  },
];

const competitorMatrix = [
  {
    vendor: "阿里云",
    position: "国内公有云份额领先",
    strengths: "电商生态、云原生数据库、通义大模型和零售中台经验",
    focus: "零售、互联网、金融",
  },
  {
    vendor: "腾讯云",
    position: "连接与内容生态优势",
    strengths: "微信生态、实时音视频、游戏和社交场景技术积累",
    focus: "教育、文娱、交通、金融",
  },
  {
    vendor: "火山云",
    position: "AI 应用和增长侧进攻",
    strengths: "豆包模型、Coze Agent 平台、内容推荐和低成本推理",
    focus: "互联网、零售、营销科技",
  },
  {
    vendor: "AWS",
    position: "全球云市场与基础设施领先",
    strengths: "全球 Region 覆盖、Bedrock、SageMaker 和成熟的开发者生态",
    focus: "出海、跨国企业、AI 平台",
  },
  {
    vendor: "Azure",
    position: "企业软件与混合云生态强势",
    strengths: "Azure OpenAI、Microsoft 365、Azure Arc 和企业级身份体系",
    focus: "企业 AI、混合云、全球化业务",
  },
];

interface CooperationItem {
  title: string;
  url: string;
  vendor: string;
  category: string;
  crawl_date: string;
}

export default function IndustryInsightPage() {
  const [expanded, setExpanded] = useState<number | null>(null);
  const [cooperations, setCooperations] = useState<CooperationItem[]>([]);
  const vendors = [...new Set(cases.map((c) => c.vendor))];
  const featuredCases = cases.slice(0, 8);

  useEffect(() => {
    fetch(`${API}/api/industry-partnerships?days=30&limit=8`)
      .then((res) => res.ok ? res.json() : Promise.reject(res.status))
      .then((data) => setCooperations(data.items || []))
      .catch(() => setCooperations([]));
  }, []);

  return (
    <div className="space-y-8">
      <SectionHeader
        badge="Industry Intelligence"
        title="行业洞察"
        subtitle={`融合行业全景、云厂商竞争格局和标杆案例库 · 覆盖 9 大行业、${vendors.length} 家云厂商、${cases.length} 个真实案例`}
        image="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80"
      />

      <div className="grid gap-px overflow-hidden rounded-2xl border border-grid bg-grid md:grid-cols-3">
        {[
          { label: "行业覆盖", value: industries.length, unit: "大行业", icon: Activity },
          { label: "云厂商", value: vendors.length, unit: "家", icon: Cloud },
          { label: "标杆案例", value: cases.length, unit: "个", icon: FileText },
        ].map((item) => (
          <div key={item.label} className="bg-white p-5">
            <item.icon className="mb-3 h-5 w-5 text-ink-muted" strokeWidth={1.5} />
            <p className="swiss-kicker text-ink-muted">{item.label}</p>
            <div className="mt-1 flex items-baseline gap-1">
              <span className="serif-stat text-3xl text-ink">{item.value}</span>
              <span className="text-xs text-ink-muted">{item.unit}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        {industries.map((ind, i) => (
          <div
            key={i}
            className="rounded-2xl bg-white border border-slate-200/80 overflow-hidden shadow-sm hover:shadow-md transition-all cursor-pointer"
            onClick={() => setExpanded(expanded === i ? null : i)}
          >
            <div className="p-5">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-slate-50 border border-slate-200/60 flex items-center justify-center">
                    <ind.icon className="h-5 w-5 text-ink-secondary" />
                  </div>
                  <div>
                    <h3 className="serif-heading text-lg text-ink">{ind.name}</h3>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${ind.statusColor}`}>
                      {ind.status}
                    </span>
                  </div>
                </div>
                <ChevronRight className={`h-4 w-4 text-ink-muted transition-transform ${expanded === i ? "rotate-90" : ""}`} />
              </div>

              <p className="text-sm text-ink-secondary leading-relaxed mb-2">{ind.summary}</p>
              <p className="text-xs font-medium text-ink-muted">{ind.trend}</p>

              <div className="flex flex-wrap gap-2 mt-3">
                {ind.links.map((link, j) => (
                  <a
                    key={j}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-ink-muted hover:text-primary transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="h-2.5 w-2.5" />
                    {link.title}
                  </a>
                ))}
              </div>
            </div>

            {expanded === i && (
              <div className="border-t border-slate-100 p-5 bg-slate-50/50 space-y-4">
                <p className="text-xs font-semibold text-ink-muted uppercase tracking-wider">具体客户方案（{getCasesByIndustry(ind.name).length} 个案例）</p>
                {getCasesByIndustry(ind.name).map((c, j) => (
                  <div key={j} className="rounded-xl bg-white border border-slate-200/60 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                      <span className="text-xs font-semibold text-ink">{c.vendor}</span>
                      <span className="text-[10px] text-ink-muted">·</span>
                      <span className="text-xs text-ink-muted">{c.customer}</span>
                    </div>
                    <p className="text-xs text-ink-secondary mb-1.5"><strong>方案：</strong>{c.solution}</p>
                    <p className="text-xs text-emerald-700 mb-2"><strong>效果：</strong>{c.result}</p>
                    <a
                      href={c.source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                    >
                      <ExternalLink className="h-2.5 w-2.5" />
                      {c.source.title}
                    </a>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <section className="space-y-4">
        <div className="flex items-end justify-between border-b border-grid pb-3">
          <div>
            <p className="swiss-kicker text-ink-muted">Latest Cooperation</p>
            <h2 className="serif-heading text-2xl text-ink">近期云厂商合作动态</h2>
          </div>
          <span className="text-xs text-ink-muted">每日采集并存入 Supabase</span>
        </div>
        {cooperations.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2">
            {cooperations.map((item) => (
              <a key={`${item.vendor}-${item.title}`} href={item.url} target="_blank" rel="noopener noreferrer"
                className="group rounded-2xl border border-grid bg-white p-5 transition-all hover:-translate-y-0.5 hover:shadow-md">
                <div className="flex items-center justify-between gap-3">
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-ink-secondary">{item.vendor}</span>
                  <span className="text-[10px] text-ink-muted">{item.crawl_date}</span>
                </div>
                <p className="mt-3 text-sm font-semibold leading-relaxed text-ink group-hover:text-primary">{item.title}</p>
              </a>
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-8 text-center text-sm text-ink-muted">
            暂无近期合作动态，下一次每日采集后自动更新
          </div>
        )}
      </section>

      <section className="space-y-4">
        <div className="flex items-end justify-between border-b border-grid pb-3">
          <div>
            <p className="swiss-kicker text-ink-muted">Competitive Landscape</p>
            <h2 className="serif-heading text-2xl text-ink">云厂商竞争格局</h2>
          </div>
          <span className="text-xs text-ink-muted">已融合原友商洞察入口</span>
        </div>
        <div className="grid gap-px overflow-hidden rounded-2xl border border-grid bg-grid lg:grid-cols-5">
          {competitorMatrix.map((item) => (
            <div key={item.vendor} className="bg-white p-5">
              <h3 className="text-sm font-bold text-ink">{item.vendor}</h3>
              <p className="mt-1 text-xs font-semibold text-ink-secondary">{item.position}</p>
              <p className="mt-3 text-xs leading-relaxed text-ink-muted">{item.strengths}</p>
              <div className="mt-4 border-t border-grid pt-3">
                <p className="swiss-kicker text-ink-muted">重点行业</p>
                <p className="mt-1 text-xs text-ink-secondary">{item.focus}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-end justify-between border-b border-grid pb-3">
          <div>
            <p className="swiss-kicker text-ink-muted">Case Library</p>
            <h2 className="serif-heading text-2xl text-ink">标杆案例库</h2>
          </div>
          <span className="text-xs text-ink-muted">{cases.length} 个案例 · {vendors.length} 家厂商</span>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {featuredCases.map((c, i) => (
            <a
              key={`${c.title}-${i}`}
              href={c.source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group rounded-2xl border border-grid bg-white p-5 transition-colors hover:bg-paper"
            >
              <div className="mb-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-grid bg-paper">
                    <c.icon className="h-4 w-4 text-ink-secondary" strokeWidth={1.5} />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-ink">{c.title}</p>
                    <p className="text-xs text-ink-muted">{c.industry} · {c.customer}</p>
                  </div>
                </div>
                <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${c.vendorColor}`}>
                  {c.vendor}
                </span>
              </div>
              <p className="text-xs leading-relaxed text-ink-secondary">{c.solution}</p>
              <p className="mt-2 text-xs leading-relaxed text-emerald-700">{c.result}</p>
              <span className="mt-3 inline-flex items-center gap-1 text-xs text-primary group-hover:underline">
                <ExternalLink className="h-3 w-3" />
                {c.source.title}
              </span>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}
