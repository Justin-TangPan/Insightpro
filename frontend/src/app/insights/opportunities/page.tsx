"use client";

import { SectionHeader } from "@/components/section-header";
import {
  Lightbulb, Target, TrendingUp, ShieldCheck, Globe, BookOpen,
  Activity, Zap, ExternalLink, ArrowRight, CheckCircle2,
  AlertTriangle
} from "lucide-react";
import Link from "next/link";

const opportunityMatrix = [
  {
    id: "xinchang-manufacturing",
    title: "信创 + 制造业：双重政策红利叠加",
    priority: "最高",
    priorityColor: "bg-rose-50 text-rose-700 border-rose-200",
    marketSize: "2025 年信创制造业市场约 600 亿元",
    sources: [
      { module: "政策法规", insight: "等保 2.0 新规覆盖制造业，200+ 工厂面临合规整改；信创替代 2027 党政 100%", href: "/insights/policy" },
      { module: "行业全景", insight: "三一重工 × 华为云：60 万台设备接入 IoT 平盘，故障预测准确率 92%", href: "/insights/industry" },
      { module: "友商洞察", insight: "阿里云 ET 工业大脑聚焦良率优化单一场景，缺乏端边云硬件能力", href: "/insights/competitors" },
    ],
    analysis: "信创政策要求'全栈国产化'，制造业客户需要从 IBM/Oracle 迁移到国产方案。华为云是唯一能提供'鲲鹏芯片 + 欧拉系统 + GaussDB 数据库'全栈方案的厂商。叠加工业互联网需求（AI 质检、预测性维护），华为云在制造业的机会是'信创替换 + AI 升级'一箭双雕。",
    action: "优先锁定 20+ 家年营收 50 亿以上的制造龙头，推出'信创 + 工业 AI'打包方案",
    huaweiAdvantage: "端边云全栈（昇腾 Atlas 边缘推理 + 盘古工业大模型 + GaussDB）",
  },
  {
    id: "medical-compliance",
    title: "医疗数据合规：海外云的死穴，华为云的护城河",
    priority: "最高",
    priorityColor: "bg-rose-50 text-rose-700 border-rose-200",
    marketSize: "2025 年中国医疗云市场约 280 亿元",
    sources: [
      { module: "行业全景", insight: "某省级医疗集团 × 华为云：AI 影像准确率 95.2%，数据全程不出境", href: "/insights/industry" },
      { module: "友商洞察", insight: "AWS HealthScribe 仅美区可用，Azure 中国无影像 AI，两者均受限于数据出境法规", href: "/insights/competitors" },
      { module: "政策法规", insight: "数据出境安全评估办法要求医疗数据不得出境，海外云厂商无法提供完整 AI 训练-推理-存储闭环", href: "/insights/policy" },
    ],
    analysis: "医疗数据是最敏感的数据类型之一。《数据出境安全评估办法》明确要求医疗数据不得出境，这意味着 AWS/Azure 无法在中国提供完整的 AI 医疗方案。华为云 EIHealth 基于昇腾芯片训练和推理，数据全程存储在国内 Region，完全合规。这是海外云厂商无法跨越的壁垒。",
    action: "重点攻克 30+ 家省级医疗集团，推出'医疗 AI 合规方案包'（影像 AI + 远程会诊 + 数据不出境）",
    huaweiAdvantage: "全栈国产化 + 数据不出境 + 等保三级/四级认证",
  },
  {
    id: "v2x-transport",
    title: "车路协同：阿里云的短板，华为云的主场",
    priority: "高",
    priorityColor: "bg-amber-50 text-amber-700 border-amber-200",
    marketSize: "2025 年中国 V2X 市场约 500 亿元",
    sources: [
      { module: "行业全景", insight: "某省会城市 × 华为云：V2X 响应延迟 < 30ms，覆盖 800 个路口 + 50 公里高速", href: "/insights/industry" },
      { module: "友商洞察", insight: "阿里云城市大脑是云端集中式架构，路侧数据回传延迟 > 500ms，无法满足 V2X 的 < 50ms 要求", href: "/insights/competitors" },
      { module: "热点追踪", insight: "L3/L4 自动驾驶试点推进，工信部批准 20 城开展载人飞行器运营", href: "/insights/hotspots" },
    ],
    analysis: "车路协同需要'端边云一体化'——路侧设备做本地推理（< 30ms），区域 MEC 做协同决策，云端做全局优化。阿里云的纯云端架构无法满足这一需求。华为云的优势在于 Atlas 500 边缘盒子 + 5G 基站 + C-V2X 标准的完整布局。随着自动驾驶试点扩至 20 城，V2X 基础设施需求将集中释放。",
    action: "锁定首批 20 个自动驾驶试点城市，推出'车路协同基础设施方案包'",
    huaweiAdvantage: "端边云一体化 + 5G 基站 + C-V2X 标准积累",
  },
  {
    id: "ai-agent-platform",
    title: "AI Agent 平台战：开发者生态决定胜负",
    priority: "高",
    priorityColor: "bg-amber-50 text-amber-700 border-amber-200",
    marketSize: "2025 年中国 AI Agent 市场约 200 亿元",
    sources: [
      { module: "热点追踪", insight: "GitHub AI Agent 项目 Star 总数增长 340%，ECC 达 20 万星，skills 生态爆发", href: "/insights/hotspots" },
      { module: "友商洞察", insight: "Azure OpenAI Service 10 行代码接入 GPT-4o，华为云盘古 API 接入周期长 3-5 倍", href: "/insights/competitors" },
      { module: "行业全景", insight: "字节豆包、阿里通义、腾讯混元在 AI 平台战争中加速布局", href: "/insights/industry" },
    ],
    analysis: "AI Agent 正在从'单次对话'转向'可复用的 Skill 生态'。开发者是平台选型的隐形决策者。Azure 靠 OpenAI 独占优势收割了 70% 的企业 AI 需求。华为云的差距在于：API 标准化不足、SDK 覆盖语言少、缺乏 MCP Server 生态。但如果能在 6 个月内完成 API 平台标准化 + MCP Server 集成，有机会在信创 AI 市场形成差异化。",
    action: "6 个月内发布盘古 API V2（全语言 SDK + MCP Server），推出'华为云 Skills'计划",
    huaweiAdvantage: "昇腾算力成本优势 + 信创 AI 合规",
  },
  {
    id: "retail-midmarket",
    title: "腰部零售客户：阿里云生态绑定的反面机会",
    priority: "中",
    priorityColor: "bg-blue-50 text-blue-700 border-blue-200",
    marketSize: "腰部零售客户（年云消费 50-500 万）约 50 万家",
    sources: [
      { module: "行业全景", insight: "某连锁便利店从阿里云迁移至华为云：IT 成本降 43%，数据完全自主", href: "/insights/industry" },
      { module: "友商洞察", insight: "阿里云零售中台服务 1,000+ 品牌，但数据与阿里电商生态绑定，迁移成本高", href: "/insights/competitors" },
      { module: "商业机会", insight: "腰部客户关注'性价比'和'数据自主权'，不依赖阿里电商生态的线下品牌是最佳目标", href: "/insights/opportunities" },
    ],
    analysis: "阿里云在零售行业的优势建立在淘宝/天猫/支付宝生态之上。但对于不依赖阿里生态的线下连锁品牌来说，'生态绑定'反而是劣势——数据迁移成本高，定价缺乏灵活性。华为云定位'中立的数据基础设施'，恰好满足这类客户的核心诉求。火山云（字节跳动）在零售增长侧（抖音电商）也在快速侵蚀阿里云份额，竞争格局正在松动。",
    action: "锁定 500+ 家不依赖阿里生态的线下连锁品牌，推出'零售数据自主方案'（GaussDB + 数据湖 + AI 推荐）",
    huaweiAdvantage: "中立平台 + 定价灵活 + 数据自主权",
  },
  {
    id: "southeast-asia",
    title: "东南亚出海：华为品牌的天然延伸",
    priority: "中",
    priorityColor: "bg-blue-50 text-blue-700 border-blue-200",
    marketSize: "东南亚云服务市场年增 35%，2025 年约 120 亿美元",
    sources: [
      { module: "友商洞察", insight: "华为云仅 27 个 Region，东南亚仅新加坡 1 个节点，AWS 33 个 Region 覆盖全球", href: "/insights/competitors" },
      { module: "商业快讯", insight: "中资出海企业云市场约 480 亿元，腰部制造、跨境电商客户出海时 100% 首选 AWS", href: "/insights/news" },
      { module: "政策法规", insight: "一带一路政策支持中国企业出海，东南亚数字化补贴政策密集出台", href: "/insights/policy" },
    ],
    analysis: "东南亚云渗透率低（< 15%），市场增长快。华为品牌在东南亚有天然认知度（手机业务积累），但云服务 Region 覆盖不足是最大短板。如果 2026 年 Q3 前在越南、印尼、泰国建成 3 个本地化 Region，可以抢占中资出海企业的首选云平台位置。窗口期 6-12 个月。",
    action: "2026 年 Q3 前落地首批东南亚 Region，推出'出海合规加速器'",
    huaweiAdvantage: "华为品牌认知 + 一带一路政策支持",
  },
];

export default function OpportunitiesPage() {
  return (
    <div className="space-y-8">
      <SectionHeader
        badge="Growth Analysis"
        title="增长机会洞察"
        subtitle="基于行业全景、热点追踪、友商洞察、政策法规、商业快讯五大模块的综合分析，识别华为云的核心增长机会"
        action={
          <div className="flex items-center gap-2 text-xs text-ink-muted">
            <Lightbulb className="h-4 w-4" />
            <span>{opportunityMatrix.length} 个机会点</span>
          </div>
        }
      />

      {/* Source Modules Summary */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { label: "行业全景", icon: Activity, href: "/insights/industry", color: "text-blue-600" },
          { label: "热点追踪", icon: Zap, href: "/insights/hotspots", color: "text-violet-600" },
          { label: "友商洞察", icon: ShieldCheck, href: "/insights/competitors", color: "text-rose-600" },
          { label: "政策法规", icon: BookOpen, href: "/insights/policy", color: "text-amber-600" },
          { label: "商业快讯", icon: Globe, href: "/insights/news", color: "text-sky-600" },
        ].map((mod, i) => (
          <Link
            key={i}
            href={mod.href}
            className="flex items-center gap-2 rounded-lg bg-white border border-slate-200/80 px-3 py-2.5 text-xs font-medium text-ink-secondary hover:border-slate-300 hover:text-ink transition-all"
          >
            <mod.icon className={`h-3.5 w-3.5 ${mod.color}`} />
            {mod.label}
            <ArrowRight className="h-3 w-3 text-ink-muted ml-auto" />
          </Link>
        ))}
      </div>

      {/* Opportunity Cards */}
      <div className="space-y-5">
        {opportunityMatrix.map((opp, i) => (
          <div key={opp.id} className="rounded-lg bg-white border border-slate-200/80 overflow-hidden shadow-sm">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3 bg-slate-50 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <span className="flex h-6 w-6 items-center justify-center rounded bg-slate-900 text-white text-[10px] font-bold">
                  {i + 1}
                </span>
                <h3 className="font-bold text-ink text-sm">{opp.title}</h3>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${opp.priorityColor}`}>
                  {opp.priority}优先级
                </span>
                <span className="text-[10px] text-ink-muted">{opp.marketSize}</span>
              </div>
            </div>

            <div className="p-5 space-y-4">
              {/* Source References */}
              <div>
                <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider mb-2">信息来源（关联子版块）</p>
                <div className="space-y-1.5">
                  {opp.sources.map((src, j) => (
                    <Link
                      key={j}
                      href={src.href}
                      className="flex items-start gap-2 text-xs text-ink-secondary hover:text-primary transition-colors"
                    >
                      <span className="text-[10px] font-semibold text-primary shrink-0 mt-px">[{src.module}]</span>
                      <span>{src.insight}</span>
                    </Link>
                  ))}
                </div>
              </div>

              {/* Analysis */}
              <div className="rounded-lg bg-slate-50 border border-slate-100 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Target className="h-4 w-4 text-primary" />
                  <span className="text-[10px] font-semibold text-ink uppercase tracking-wider">综合分析</span>
                </div>
                <p className="text-sm text-ink-secondary leading-relaxed">{opp.analysis}</p>
              </div>

              {/* Action + Advantage */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="rounded-lg border-l-4 border-primary bg-indigo-50/30 p-3">
                  <p className="text-[10px] font-semibold text-primary uppercase tracking-wider mb-1">建议行动</p>
                  <p className="text-xs text-ink-secondary leading-relaxed">{opp.action}</p>
                </div>
                <div className="rounded-lg border-l-4 border-emerald-500 bg-emerald-50/30 p-3">
                  <p className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wider mb-1">华为云优势</p>
                  <p className="text-xs text-emerald-800 leading-relaxed">{opp.huaweiAdvantage}</p>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
