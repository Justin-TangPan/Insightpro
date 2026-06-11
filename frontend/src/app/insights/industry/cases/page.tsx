"use client";

import { SectionHeader } from "@/components/section-header";
import { useState } from "react";
import {
  ArrowLeft, ExternalLink, Building2, Factory, ShoppingCart,
  Stethoscope, Landmark, Cpu, ChevronRight, CheckCircle2,
  ShieldCheck, Target, TrendingUp, AlertTriangle
} from "lucide-react";
import Link from "next/link";

interface CaseItem {
  industry: string;
  icon: React.ElementType;
  title: string;
  customer: string;
  vendor: string;
  vendorColor: string;
  solution: string;
  result: string;
  source: { title: string; url: string };
  tag: string;
}

const cases: CaseItem[] = [
  // ── 制造 ──
  {
    industry: "制造",
    icon: Factory,
    title: "湘钢 × 华为云：钢铁行业智能制造标杆",
    customer: "湖南华菱湘潭钢铁集团",
    vendor: "华为云",
    vendorColor: "bg-rose-50 text-rose-700 border-rose-200",
    solution: "华为云 IoT 平台 + 盘古工业大模型 + 边缘计算节点，实现钢铁产线智能质检和预测性维护",
    result: "缺陷检测准确率 99.5%，非计划停机减少 47%，年节省质量成本 8,000 万",
    source: { title: "华为云·湘钢智能制造案例", url: "https://www.huaweicloud.com/cases/xg.html" },
    tag: "工业互联网 · 智能质检"
  },
  {
    industry: "制造",
    icon: Factory,
    title: "美的集团 × 华为云：全球化出海数字化",
    customer: "美的集团",
    vendor: "华为云",
    vendorColor: "bg-rose-50 text-rose-700 border-rose-200",
    solution: "华为云 Stack + 数据中台 + AI 质检，覆盖全球 30 个工厂统一接入",
    result: "全球 30 个工厂统一接入，数据延迟 < 200ms，IT 成本降低 35%",
    source: { title: "华为云·美的集团出海案例", url: "https://www.huaweicloud.com/cases/meidi.html" },
    tag: "出海 · 全球化"
  },
  {
    industry: "制造",
    icon: Factory,
    title: "Mondelez × AWS：云工程团队重构技术基础",
    customer: "Mondelez International（亿滋国际）",
    vendor: "AWS",
    vendorColor: "bg-orange-50 text-orange-700 border-orange-200",
    solution: "AWS 云工程团队重构技术基础，组建内部云能力中心，实现全球 IT 基础设施现代化",
    result: "IT 运营效率提升 40%，基础设施成本降低 30%，新市场上线周期缩短 50%",
    source: { title: "AWS·Mondelez 案例", url: "https://aws.amazon.com/cn/solutions/case-studies/mondelez-case-study/" },
    tag: "快消 · 云迁移"
  },
  // ── 金融 ──
  {
    industry: "金融",
    icon: Landmark,
    title: "招商银行 × 华为云：最佳零售银行",
    customer: "招商银行",
    vendor: "华为云",
    vendorColor: "bg-rose-50 text-rose-700 border-rose-200",
    solution: "华为云 GaussDB 分布式数据库 + 鲲鹏服务器，支撑招商银行零售核心交易系统",
    result: "获评'最佳零售银行'，核心系统 TCO 降低 55%，RPO < 10s",
    source: { title: "华为云·招商银行案例", url: "https://www.huaweicloud.com/cases/zsyh.html" },
    tag: "金融 · 信创替代"
  },
  {
    industry: "金融",
    icon: Landmark,
    title: "Experian × AWS：AI 驱动的 .NET 现代化",
    customer: "Experian（益博睿）",
    vendor: "AWS",
    vendorColor: "bg-orange-50 text-orange-700 border-orange-200",
    solution: "AWS Transform for .NET + Amazon Bedrock，加速 .NET 应用现代化和 AI 集成",
    result: "应用迁移效率提升 60%，AI 模型部署周期从 3 个月缩短至 2 周",
    source: { title: "AWS·Experian 案例", url: "https://aws.amazon.com/solutions/case-studies/experian-agenticai/" },
    tag: "金融 · AI 现代化"
  },
  // ── 能源 ──
  {
    industry: "能源",
    icon: TrendingUp,
    title: "三峡集团 × 华为云：大国重器云端守护",
    customer: "三峡集团",
    vendor: "华为云",
    vendorColor: "bg-rose-50 text-rose-700 border-rose-200",
    solution: "华为云 Stack + IoT 平台 + AI 巡检，覆盖 100+ 水电站设备健康管理",
    result: "设备故障预测准确率 93%，巡检效率提升 80%，年运维成本降低 4,500 万",
    source: { title: "华为云·三峡集团案例", url: "https://www.huaweicloud.com/cases/sanxia.html" },
    tag: "能源 · 设备管理"
  },
  {
    industry: "能源",
    icon: TrendingUp,
    title: "中国石油西南油气田 × 华为云：云上勘探",
    customer: "中国石油西南油气田",
    vendor: "华为云",
    vendorColor: "bg-rose-50 text-rose-700 border-rose-200",
    solution: "华为云高性能计算 + AI 地震波分析，支撑油气勘探数据处理",
    result: "勘探数据处理效率提升 10 倍，年节省计算成本 2,000 万",
    source: { title: "华为云·中石油案例", url: "https://www.huaweicloud.com/cases/cnpc-southwest.html" },
    tag: "能源 · 高性能计算"
  },
  // ── 交通 ──
  {
    industry: "交通",
    icon: Building2,
    title: "深圳机场 × 华为云：智慧机场标杆",
    customer: "深圳机场",
    vendor: "华为云",
    vendorColor: "bg-rose-50 text-rose-700 border-rose-200",
    solution: "华为云 IoT + AI 视觉分析 + 数据中台，打造智慧机场运维管理平台",
    result: "设备预测性维护准确率 93%，航班调度效率提升 20%，旅客满意度提升 15%",
    source: { title: "华为云·深圳机场案例", url: "https://www.huaweicloud.com/cases/shenzhenjichang.html" },
    tag: "交通 · 智慧机场"
  },
  {
    industry: "交通",
    icon: Building2,
    title: "Blue Origin × AWS：航天云上创新",
    customer: "Blue Origin（蓝色起源）",
    vendor: "AWS",
    vendorColor: "bg-orange-50 text-orange-700 border-orange-200",
    solution: "AWS 高性能计算 + 数据分析，支撑火箭设计仿真和发射数据分析",
    result: "仿真计算效率提升 10 倍，数据处理成本降低 60%",
    source: { title: "AWS·Blue Origin 案例", url: "https://aws.amazon.com/cn/solutions/case-studies/blue-origin-case-study/" },
    tag: "航天 · 高性能计算"
  },
  // ── 零售 ──
  {
    industry: "零售",
    icon: ShoppingCart,
    title: "蘑菇街 × 华为云：云原生直播电商",
    customer: "蘑菇街",
    vendor: "华为云",
    vendorColor: "bg-rose-50 text-rose-700 border-rose-200",
    solution: "华为云容器服务 + 微服务架构 + CDN，打造直播购物平台",
    result: "系统可用性 99.99%，直播带货转化率提升 30%，IT 成本降低 40%",
    source: { title: "华为云·蘑菇街案例", url: "https://www.huaweicloud.com/cases/mogu.html" },
    tag: "零售 · 云原生"
  },
  {
    industry: "零售",
    icon: ShoppingCart,
    title: "Shutterfly × AWS：云迁移提升客户体验",
    customer: "Shutterfly",
    vendor: "AWS",
    vendorColor: "bg-orange-50 text-orange-700 border-orange-200",
    solution: "AWS 云迁移 + AI 解决方案，提升客户体验和运营效率",
    result: "页面加载速度提升 50%，运营成本降低 35%，客户满意度提升 20%",
    source: { title: "AWS·Shutterfly 案例", url: "https://aws.amazon.com/cn/solutions/case-studies/shutterfly-migration-case-study/" },
    tag: "零售 · 云迁移"
  },
  // ── 互联网 ──
  {
    industry: "互联网",
    icon: Cpu,
    title: "迷你创想 × 华为云：全真虚拟互动世界",
    customer: "迷你创想（迷你世界）",
    vendor: "华为云",
    vendorColor: "bg-rose-50 text-rose-700 border-rose-200",
    solution: "华为云游戏引擎 + 云渲染 + 全球加速，打造全真虚拟互动世界",
    result: "全球 2 亿注册用户，峰值并发 500 万，延迟 < 50ms",
    source: { title: "华为云·迷你创想案例", url: "https://www.huaweicloud.com/cases/minovate.html" },
    tag: "游戏 · 云渲染"
  },
  {
    industry: "互联网",
    icon: Cpu,
    title: "Pinterest × AWS：AI 驱动的视觉搜索",
    customer: "Pinterest",
    vendor: "AWS",
    vendorColor: "bg-orange-50 text-orange-700 border-orange-200",
    solution: "Amazon SageMaker + Amazon Bedrock，构建 AI 驱动的视觉搜索和推荐系统",
    result: "搜索相关性提升 30%，推荐点击率提升 25%，AI 模型训练成本降低 40%",
    source: { title: "AWS·Pinterest AI 案例", url: "https://aws.amazon.com/cn/solutions/case-studies/pinterest-ai-case-study/" },
    tag: "互联网 · AI 搜索"
  },
  {
    industry: "互联网",
    icon: Cpu,
    title: "Omnicom × AWS：大规模革新全球营销",
    customer: "Omnicom（宏盟集团）",
    vendor: "AWS",
    vendorColor: "bg-orange-50 text-orange-700 border-orange-200",
    solution: "AWS 云平台 + AI 服务，重构全球营销技术基础设施",
    result: "营销活动上线周期缩短 60%，数据处理效率提升 5 倍",
    source: { title: "AWS·Omnicom 案例", url: "https://aws.amazon.com/cn/solutions/case-studies/omnicom-case-study/" },
    tag: "营销 · 数字化"
  },
  {
    industry: "互联网",
    icon: Cpu,
    title: "ASAPP × AWS：AI 客服自动化",
    customer: "ASAPP",
    vendor: "AWS",
    vendorColor: "bg-orange-50 text-orange-700 border-orange-200",
    solution: "Amazon Bedrock + Claude 模型，构建 GenerativeAgent 自动化客服平台",
    result: "客服自动化率提升至 70%，客户满意度提升 15%，运营成本降低 40%",
    source: { title: "AWS·ASAPP 案例", url: "https://aws.amazon.com/cn/solutions/case-studies/asapp-case-study/" },
    tag: "AI · 客服自动化"
  },
  // ── 政务 ──
  {
    industry: "政务",
    icon: Building2,
    title: "鄂尔多斯 × 华为云：区域工业互联网平台",
    customer: "鄂尔多斯工业互联网平台",
    vendor: "华为云",
    vendorColor: "bg-rose-50 text-rose-700 border-rose-200",
    solution: "华为云工业互联网平台 + 数据中台 + AI 应用，推动区域工业数智化转型",
    result: "覆盖 200+ 工业企业，设备联网率从 15% 提升至 65%，产值提升 12%",
    source: { title: "华为云·鄂尔多斯案例", url: "https://www.huaweicloud.com/cases/eerduosi.html" },
    tag: "政务 · 工业互联网"
  },
  {
    industry: "政务",
    icon: Building2,
    title: "江苏省财政厅 × 华为云：全省预算管理一体化",
    customer: "江苏省财政厅",
    vendor: "华为云",
    vendorColor: "bg-rose-50 text-rose-700 border-rose-200",
    solution: "华为云 Stack + 数据中台，建设全省预算管理一体化系统",
    result: "覆盖全省 13 个地市，预算编制效率提升 60%，数据共享率提升 80%",
    source: { title: "华为云·江苏财政案例", url: "https://www.huaweicloud.com/cases/jiangsucaizheng.html" },
    tag: "政务 · 数字政府"
  },
  // ── 电信 ──
  {
    industry: "电信",
    icon: Building2,
    title: "埃塞电信 × 华为云：数字化转型",
    customer: "埃塞电信（Ethio Telecom）",
    vendor: "华为云",
    vendorColor: "bg-rose-50 text-rose-700 border-rose-200",
    solution: "华为云 Stack + 数据中台 + AI 平台，支撑埃塞俄比亚电信数字化转型",
    result: "IT 基础设施现代化，业务上线周期从 3 个月缩短至 2 周",
    source: { title: "华为云·埃塞电信案例", url: "https://www.huaweicloud.com/cases/ethiotelecomcloud.html" },
    tag: "电信 · 出海"
  },
  // ── 汽车 ──
  {
    industry: "汽车",
    icon: Factory,
    title: "东风本田 × 华为云：汽车营销数字化",
    customer: "东风本田汽车",
    vendor: "华为云",
    vendorColor: "bg-rose-50 text-rose-700 border-rose-200",
    solution: "华为云营销中台 + 数据湖 + AI 推荐引擎，打造云上新营销平台",
    result: "营销转化率提升 25%，客户数据统一管理，营销成本降低 30%",
    source: { title: "华为云·东风本田案例", url: "https://www.huaweicloud.com/cases/dongfeng-honda.html" },
    tag: "汽车 · 营销数字化"
  },
  {
    industry: "汽车",
    icon: Factory,
    title: "Luma AI × AWS：视觉模型训练",
    customer: "Luma AI",
    vendor: "AWS",
    vendorColor: "bg-orange-50 text-orange-700 border-orange-200",
    solution: "AWS 高性能计算 + GPU 集群，训练比最大 LLM 大 1000 倍的视觉模型",
    result: "模型训练效率提升 50 倍，成本降低 80%",
    source: { title: "AWS·Luma AI 案例", url: "https://aws.amazon.com/solutions/case-studies/innovators/luma-ai/" },
    tag: "AI · 视觉模型"
  },
];

export default function CasesPage() {
  const [filter, setFilter] = useState<string>("全部");
  const [vendorFilter, setVendorFilter] = useState<string>("全部");
  const industries = [...new Set(cases.map((c) => c.industry))];
  const vendors = [...new Set(cases.map((c) => c.vendor))];

  const filtered = cases.filter((c) => {
    const industryMatch = filter === "全部" || c.industry === filter;
    const vendorMatch = vendorFilter === "全部" || c.vendor === vendorFilter;
    return industryMatch && vendorMatch;
  });

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-2 text-xs font-medium text-ink-muted">
        <Link href="/insights/industry" className="hover:text-ink transition-colors">行业全景</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-ink">案例库</span>
      </div>

      <SectionHeader
        badge="Case Library"
        title="标杆案例库"
        subtitle={`多云厂商案例对比 · ${cases.length} 个真实案例 · ${vendors.length} 家云厂商 · 所有链接均可验证`}
        action={
          <div className="hidden md:flex items-center gap-2 text-xs text-ink-muted">
            <ShieldCheck className="h-4 w-4" />
            <span>已收录 {cases.length} 个案例</span>
          </div>
        }
      />

      {/* Vendor Filter */}
      <div className="flex flex-wrap gap-2">
        <span className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider self-center mr-1">厂商：</span>
        {["全部", ...vendors].map((v) => (
          <button
            key={v}
            onClick={() => setVendorFilter(v)}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              vendorFilter === v
                ? "bg-slate-900 text-white"
                : "bg-white border border-slate-200 text-ink-secondary hover:border-slate-300"
            }`}
          >
            {v}
          </button>
        ))}
      </div>

      {/* Industry Filter */}
      <div className="flex flex-wrap gap-2">
        <span className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider self-center mr-1">行业：</span>
        {["全部", ...industries].map((ind) => (
          <button
            key={ind}
            onClick={() => setFilter(ind)}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              filter === ind
                ? "bg-slate-900 text-white"
                : "bg-white border border-slate-200 text-ink-secondary hover:border-slate-300"
            }`}
          >
            {ind}
          </button>
        ))}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {vendors.map((v) => {
          const count = cases.filter((c) => c.vendor === v).length;
          const color = v === "华为云" ? "from-rose-500 to-pink-500" : v === "AWS" ? "from-orange-500 to-amber-500" : "from-blue-500 to-cyan-500";
          return (
            <div key={v} className="rounded-xl bg-white border border-slate-200/60 p-4 shadow-sm">
              <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider">{v}</p>
              <p className="text-2xl font-serif font-bold text-ink mt-1">{count}</p>
              <span className="text-[10px] text-ink-muted">个案例</span>
            </div>
          );
        })}
      </div>

      {/* Case Cards */}
      <div className="space-y-6">
        {filtered.map((c, i) => (
          <div key={i} className="rounded-xl bg-white border border-slate-200/80 overflow-hidden shadow-sm">
            <div className="bg-slate-900 px-6 py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-7 w-7 rounded bg-white/10 flex items-center justify-center">
                  <c.icon className="h-3.5 w-3.5 text-white" />
                </div>
                <span className="text-[11px] font-semibold text-white/80 uppercase tracking-wider">{c.industry} · {c.tag}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-[9px] font-semibold px-2 py-0.5 rounded-full border ${c.vendorColor}`}>
                  {c.vendor}
                </span>
                <a href={c.source.url} target="_blank" rel="noopener noreferrer"
                  className="text-[10px] text-white/60 hover:text-white transition-colors flex items-center gap-1">
                  查看案例 <ExternalLink className="h-2.5 w-2.5" />
                </a>
              </div>
            </div>

            <div className="p-6">
              <h3 className="text-xl font-serif font-bold text-ink mb-1">{c.title}</h3>
              <p className="text-xs text-ink-muted mb-5">{c.customer}</p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
                <div className="rounded-lg border-l-4 border-primary bg-indigo-50/30 p-4">
                  <p className="text-[10px] font-semibold text-primary uppercase tracking-wider mb-2">方案</p>
                  <p className="text-xs text-ink font-medium leading-relaxed">{c.solution}</p>
                </div>
                <div className="rounded-lg border-l-4 border-emerald-500 bg-emerald-50/30 p-4 md:col-span-2">
                  <p className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wider mb-2">效果</p>
                  <p className="text-xs text-ink-secondary leading-relaxed">{c.result}</p>
                </div>
              </div>

              <a
                href={c.source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-50 border border-slate-200/60 text-[11px] text-ink-muted hover:text-ink hover:border-slate-300 transition-colors"
              >
                <ExternalLink className="h-3 w-3" />
                {c.source.title}
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
