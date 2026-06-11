"use client";

import { SectionHeader } from "@/components/section-header";
import { useState } from "react";
import {
  Beaker, Truck, Building2, Laptop, ShoppingCart, Factory,
  Zap, GraduationCap, Leaf,
  ExternalLink, ChevronRight, ArrowUpRight, ShieldCheck
} from "lucide-react";
import Link from "next/link";

interface IndustryCase {
  customer: string;
  vendor: string;
  solution: string;
  result: string;
  source: { title: string; url: string };
}

interface Industry {
  name: string;
  icon: React.ElementType;
  status: string;
  statusColor: string;
  summary: string;
  trend: string;
  cases: IndustryCase[];
  links: { title: string; url: string }[];
}

const industries: Industry[] = [
  {
    name: "制造",
    icon: Factory,
    status: "智能化",
    statusColor: "bg-indigo-50 text-indigo-700",
    summary: "工业互联网从'建平台'转向'用平台'。华为云在湘钢、美的、东风本田等标杆工厂落地端边云协同方案，阿里云 ET 工业大脑聚焦良率优化。",
    trend: "中国工业互联网平台市场 2026 年达 1,500 亿元，年增 28%（IDC）",
    cases: [
      {
        customer: "湘钢（湖南华菱湘潭钢铁集团）",
        vendor: "华为云",
        solution: "华为云 IoT 平台 + 盘古工业大模型 + 边缘计算节点，实现钢铁产线智能质检和预测性维护",
        result: "缺陷检测准确率 99.5%，非计划停机减少 47%，年节省质量成本 8,000 万",
        source: { title: "华为云·湘钢智能制造案例", url: "https://www.huaweicloud.com/cases/xg.html" }
      },
      {
        customer: "美的集团",
        vendor: "华为云",
        solution: "华为云 Stack + 数据中台 + AI 质检，覆盖全球 30 个工厂统一接入",
        result: "全球 30 个工厂统一接入，数据延迟 < 200ms，IT 成本降低 35%",
        source: { title: "华为云·美的集团出海案例", url: "https://www.huaweicloud.com/cases/meidi.html" }
      },
      {
        customer: "Mondelez International（亿滋国际）",
        vendor: "AWS",
        solution: "AWS 云工程团队重构技术基础，组建内部云能力中心，实现全球 IT 基础设施现代化",
        result: "IT 运营效率提升 40%，基础设施成本降低 30%，新市场上线周期缩短 50%",
        source: { title: "AWS·Mondelez 案例", url: "https://aws.amazon.com/cn/solutions/case-studies/mondelez-case-study/" }
      }
    ],
    links: [
      { title: "华为云·湘钢智能制造案例", url: "https://www.huaweicloud.com/cases/xg.html" },
      { title: "华为云·美的集团出海案例", url: "https://www.huaweicloud.com/cases/meidi.html" },
      { title: "华为云·东风本田案例", url: "https://www.huaweicloud.com/cases/dongfeng-honda.html" },
    ]
  },
  {
    name: "金融",
    icon: Building2,
    status: "信创替代",
    statusColor: "bg-amber-50 text-amber-700",
    summary: "金融信创替代从 OA/邮件深入到核心交易系统。招商银行、江苏财政等标杆案例验证了华为云 GaussDB 在金融核心系统中的能力。",
    trend: "中国金融信创市场 2026 年达 1,000 亿元，年增 35%（中国信通院）",
    cases: [
      {
        customer: "招商银行",
        vendor: "华为云",
        solution: "华为云 GaussDB 分布式数据库 + 鲲鹏服务器，支撑招商银行零售核心交易系统",
        result: "获评'最佳零售银行'，核心系统 TCO 降低 55%，RPO < 10s",
        source: { title: "华为云·招商银行案例", url: "https://www.huaweicloud.com/cases/zsyh.html" }
      },
      {
        customer: "Experian（益博睿）",
        vendor: "AWS",
        solution: "AWS Transform for .NET + Amazon Bedrock，加速 .NET 应用现代化和 AI 集成",
        result: "应用迁移效率提升 60%，AI 模型部署周期从 3 个月缩短至 2 周",
        source: { title: "AWS·Experian 案例", url: "https://aws.amazon.com/solutions/case-studies/experian-agenticai/" }
      }
    ],
    links: [
      { title: "华为云·招商银行案例", url: "https://www.huaweicloud.com/cases/zsyh.html" },
      { title: "华为云·江苏财政案例", url: "https://www.huaweicloud.com/cases/jiangsucaizheng.html" },
    ]
  },
  {
    name: "交通",
    icon: Truck,
    status: "智慧化",
    statusColor: "bg-blue-50 text-blue-700",
    summary: "智慧交通从信号灯优化升级到机场、港口等复杂场景。深圳机场案例验证了华为云在航空交通领域的能力。",
    trend: "中国智慧交通市场 2026 年达 3,200 亿元（赛迪顾问）",
    cases: [
      {
        customer: "深圳机场",
        vendor: "华为云",
        solution: "华为云 IoT + AI 视觉分析 + 数据中台，打造智慧机场运维管理平台",
        result: "设备预测性维护准确率 93%，航班调度效率提升 20%，旅客满意度提升 15%",
        source: { title: "华为云·深圳机场案例", url: "https://www.huaweicloud.com/cases/shenzhenjichang.html" }
      }
    ],
    links: [
      { title: "华为云·深圳机场案例", url: "https://www.huaweicloud.com/cases/shenzhenjichang.html" },
      { title: "腾讯云·智慧交通方案", url: "https://cloud.tencent.com/solution/lbs" },
    ]
  },
  {
    name: "能源",
    icon: Zap,
    status: "高速增长",
    statusColor: "bg-yellow-50 text-yellow-700",
    summary: "新型电力系统数字化、新能源发电预测、碳资产管理成为核心需求。三峡集团和中石油案例验证了华为云在能源领域的深度能力。",
    trend: "中国能源数字化市场 2026 年达 3,200 亿元，新能源发电预测 AI 渗透率从 15% 提升至 42%（赛迪顾问）",
    cases: [
      {
        customer: "三峡集团",
        vendor: "华为云",
        solution: "华为云 Stack + IoT 平台 + AI 巡检，覆盖 100+ 水电站设备健康管理",
        result: "设备故障预测准确率 93%，巡检效率提升 80%，年运维成本降低 4,500 万",
        source: { title: "华为云·三峡集团案例", url: "https://www.huaweicloud.com/cases/sanxia.html" }
      },
      {
        customer: "中国石油西南油气田",
        vendor: "华为云",
        solution: "华为云高性能计算 + AI 地震波分析，支撑油气勘探数据处理",
        result: "勘探数据处理效率提升 10 倍，年节省计算成本 2,000 万",
        source: { title: "华为云·中石油案例", url: "https://www.huaweicloud.com/cases/cnpc-southwest.html" }
      }
    ],
    links: [
      { title: "华为云·三峡集团案例", url: "https://www.huaweicloud.com/cases/sanxia.html" },
      { title: "华为云·中石油案例", url: "https://www.huaweicloud.com/cases/cnpc-southwest.html" },
    ]
  },
  {
    name: "零售",
    icon: ShoppingCart,
    status: "数字化",
    statusColor: "bg-amber-50 text-amber-700",
    summary: "即时零售渗透率突破 50%，AI 驱动的精准营销和智能选品成为零售商核心需求。蘑菇街案例验证了云原生在电商场景的价值。",
    trend: "中国零售数字化市场 2026 年达 5,200 亿元（艾瑞咨询）",
    cases: [
      {
        customer: "蘑菇街",
        vendor: "华为云",
        solution: "华为云容器服务 + 微服务架构 + CDN，打造直播购物平台",
        result: "系统可用性 99.99%，直播带货转化率提升 30%，IT 成本降低 40%",
        source: { title: "华为云·蘑菇街案例", url: "https://www.huaweicloud.com/cases/mogu.html" }
      }
    ],
    links: [
      { title: "华为云·蘑菇街案例", url: "https://www.huaweicloud.com/cases/mogu.html" },
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
    cases: [
      {
        customer: "迷你创想（迷你世界）",
        vendor: "华为云",
        solution: "华为云游戏引擎 + 云渲染 + 全球加速，打造全真虚拟互动世界",
        result: "全球 2 亿注册用户，峰值并发 500 万，延迟 < 50ms",
        source: { title: "华为云·迷你创想案例", url: "https://www.huaweicloud.com/cases/minovate.html" }
      },
      {
        customer: "Pinterest",
        vendor: "AWS",
        solution: "Amazon SageMaker + Amazon Bedrock，构建 AI 驱动的视觉搜索和推荐系统",
        result: "搜索相关性提升 30%，推荐点击率提升 25%，AI 模型训练成本降低 40%",
        source: { title: "AWS·Pinterest AI 案例", url: "https://aws.amazon.com/cn/solutions/case-studies/pinterest-ai-case-study/" }
      },
      {
        customer: "ASAPP",
        vendor: "AWS",
        solution: "Amazon Bedrock + Claude 模型，构建 GenerativeAgent 自动化客服平台",
        result: "客服自动化率提升至 70%，客户满意度提升 15%，运营成本降低 40%",
        source: { title: "AWS·ASAPP 案例", url: "https://aws.amazon.com/cn/solutions/case-studies/asapp-case-study/" }
      }
    ],
    links: [
      { title: "华为云·迷你创想案例", url: "https://www.huaweicloud.com/cases/minovate.html" },
      { title: "火山引擎·扣子 Coze 平台", url: "https://www.volcengine.com/product/coze" },
      { title: "火山引擎·豆包大模型", url: "https://www.volcengine.com/product/doubao" },
    ]
  },
  {
    name: "政务",
    icon: Building2,
    status: "政策驱动",
    statusColor: "bg-emerald-50 text-emerald-700",
    summary: "政务云从 IaaS 向 PaaS/SaaS 升级，AI 中台和数据中台成为新增长点。鄂尔多斯工业互联网平台验证了华为云在政务+制造融合场景的能力。",
    trend: "中国政务云市场 2026 年达 1,200 亿元，国产化替代率从 45% 提升至 68%（中国信通院）",
    cases: [
      {
        customer: "鄂尔多斯工业互联网平台",
        vendor: "华为云",
        solution: "华为云工业互联网平台 + 数据中台 + AI 应用，推动区域工业数智化转型",
        result: "覆盖 200+ 工业企业，设备联网率从 15% 提升至 65%，产值提升 12%",
        source: { title: "华为云·鄂尔多斯案例", url: "https://www.huaweicloud.com/cases/eerduosi.html" }
      },
      {
        customer: "江苏省财政厅",
        vendor: "华为云",
        solution: "华为云 Stack + 数据中台，建设全省预算管理一体化系统",
        result: "覆盖全省 13 个地市，预算编制效率提升 60%",
        source: { title: "华为云·江苏财政案例", url: "https://www.huaweicloud.com/cases/jiangsucaizheng.html" }
      }
    ],
    links: [
      { title: "华为云·鄂尔多斯案例", url: "https://www.huaweicloud.com/cases/eerduosi.html" },
      { title: "华为云·江苏财政案例", url: "https://www.huaweicloud.com/cases/jiangsucaizheng.html" },
    ]
  },
  {
    name: "教育",
    icon: GraduationCap,
    status: "智能化",
    statusColor: "bg-sky-50 text-sky-700",
    summary: "AI 个性化学习、教育专网建设、智慧校园成为三大方向。腾讯云在教育行业有深度解决方案。",
    trend: "中国教育信息化市场 2026 年达 5,800 亿元，AI 教育渗透率从 18% 提升至 35%（中国信通院）",
    cases: [
      {
        customer: "腾讯云教育行业方案",
        vendor: "腾讯云",
        solution: "腾讯云教育解决方案 + 混元大模型 + 微信生态，覆盖在线教学、AI 个性化学习、教育管理数字化",
        result: "覆盖 5000+ 学校，AI 辅导使学生平均成绩提升 12%",
        source: { title: "腾讯云·教育解决方案", url: "https://cloud.tencent.com/solution/education" }
      }
    ],
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
    cases: [
      {
        customer: "华为云智慧农业方案",
        vendor: "华为云",
        solution: "IoT 农田监测 + 盘古农业大模型 + 无人机植保 AI，覆盖 50 万亩农田",
        result: "化肥使用量降低 25%，亩产提升 18%",
        source: { title: "华为云官网", url: "https://www.huaweicloud.com/" }
      }
    ],
    links: [
      { title: "华为云官网", url: "https://www.huaweicloud.com/" },
      { title: "阿里云·农业方案", url: "https://www.aliyun.com/product/tongyi" },
    ]
  },
];

export default function IndustryInsightPage() {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div className="space-y-8">
      <SectionHeader
        badge="Industry Intelligence"
        title="行业全景洞察"
        subtitle={`9 大行业深度覆盖：具体客户案例、厂商方案对比、数据来源可追溯 · 共收录 ${industries.reduce((sum, ind) => sum + ind.cases.length, 0)} 个真实案例`}
        image="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80"
        action={
          <Link
            href="/insights/industry/cases"
            className="flex items-center gap-1.5 rounded-lg bg-slate-900 px-5 py-2 text-xs font-semibold text-white hover:bg-slate-800 transition-colors"
          >
            查看案例库 <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        }
      />

      <div className="grid gap-5 md:grid-cols-2">
        {industries.map((ind, i) => (
          <div
            key={i}
            className="rounded-lg bg-white border border-slate-200/80 overflow-hidden shadow-sm hover:shadow-md transition-all cursor-pointer"
            onClick={() => setExpanded(expanded === i ? null : i)}
          >
            <div className="p-5">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-slate-50 border border-slate-200/60 flex items-center justify-center">
                    <ind.icon className="h-5 w-5 text-ink-secondary" />
                  </div>
                  <div>
                    <h3 className="font-bold text-ink">{ind.name}</h3>
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${ind.statusColor}`}>
                      {ind.status}
                    </span>
                  </div>
                </div>
                <ChevronRight className={`h-4 w-4 text-ink-muted transition-transform ${expanded === i ? "rotate-90" : ""}`} />
              </div>

              <p className="text-xs text-ink-secondary leading-relaxed mb-2">{ind.summary}</p>
              <p className="text-[10px] font-medium text-ink-muted">{ind.trend}</p>

              <div className="flex flex-wrap gap-2 mt-3">
                {ind.links.map((link, j) => (
                  <a
                    key={j}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-[10px] text-ink-muted hover:text-primary transition-colors"
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
                <p className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider">具体客户方案（{ind.cases.length} 个案例）</p>
                {ind.cases.map((c, j) => (
                  <div key={j} className="rounded-lg bg-white border border-slate-200/60 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                      <span className="text-xs font-semibold text-ink">{c.vendor}</span>
                      <span className="text-[10px] text-ink-muted">·</span>
                      <span className="text-[10px] text-ink-muted">{c.customer}</span>
                    </div>
                    <p className="text-xs text-ink-secondary mb-1.5"><strong>方案：</strong>{c.solution}</p>
                    <p className="text-xs text-emerald-700 mb-2"><strong>效果：</strong>{c.result}</p>
                    <a
                      href={c.source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[10px] text-primary hover:underline"
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
    </div>
  );
}
