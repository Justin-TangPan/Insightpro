"use client";

import { SectionHeader } from "@/components/section-header";
import { useState } from "react";
import {
  Cloud, ExternalLink, ChevronRight, ArrowUpRight,
  Globe, Server, Cpu, Zap, ShieldCheck, Star,
  TrendingUp, Package, FileText, Newspaper,
  ShoppingCart, Building2, Factory, Activity
} from "lucide-react";

interface VendorNews {
  category: "产品发布" | "案例发布" | "解决方案" | "最新动态";
  title: string;
  summary: string;
  url: string;
  date?: string;
}

interface Vendor {
  id: string;
  name: string;
  fullName: string;
  region: string;
  color: string;
  bgColor: string;
  icon: string;
  marketShare: string;
  description: string;
  products: { name: string; url: string }[];
  news: VendorNews[];
}

const vendors: Vendor[] = [
  {
    id: "aws",
    name: "AWS",
    fullName: "Amazon Web Services",
    region: "全球",
    color: "text-orange-600",
    bgColor: "bg-orange-50 border-orange-200",
    icon: "🟠",
    marketShare: "全球 32% · 中国区 < 5%",
    description: "全球云市场份额第一，AI/ML 服务成熟度最高。中国区由光环新网（北京）和西云数据（宁夏）运营，服务可用性受限。",
    products: [
      { name: "Amazon Bedrock (AI 模型平台)", url: "https://aws.amazon.com/bedrock/" },
      { name: "Amazon SageMaker (机器学习)", url: "https://aws.amazon.com/sagemaker/" },
      { name: "Amazon Q (AI 助手)", url: "https://aws.amazon.com/q/" },
      { name: "AWS Lambda (无服务器)", url: "https://aws.amazon.com/lambda/" },
    ],
    news: [
      { category: "产品发布", title: "Amazon Bedrock AgentCore 正式发布", summary: "支持多 Agent 编排、工具调用和长期记忆，企业客户可一键部署生产级 AI Agent。集成 Anthropic Claude、Meta Llama、Mistral 等 15+ 模型。", url: "https://aws.amazon.com/bedrock/" },
      { category: "产品发布", title: "Amazon Q Developer 正式可用", summary: "面向企业的 AI 编程助手，支持代码补全、Bug 修复、代码审查、单测生成。已集成到 VS Code 和 JetBrains IDE。", url: "https://aws.amazon.com/q/" },
      { category: "产品发布", title: "AWS Lambda 支持 GPU 实例", summary: "Lambda 新增 GPU 函数支持，企业可在无服务器架构中运行 AI 推理任务，按调用计费。AI 推理成本降低 40%。", url: "https://aws.amazon.com/lambda/" },
      { category: "最新动态", title: "AWS 中国区新增银川可用区", summary: "西云数据运营的宁夏区域新增第三个可用区，为中国西部客户提供更低延迟的云服务。", url: "https://aws.amazon.com/cn/" },
    ],
  },
  {
    id: "azure",
    name: "Microsoft Azure",
    fullName: "Microsoft Azure",
    region: "全球",
    color: "text-blue-600",
    bgColor: "bg-blue-50 border-blue-200",
    icon: "🔵",
    marketShare: "全球 23% · 中国区 < 3%",
    description: "全球第二大云厂商，OpenAI 独占整合优势。中国区由世纪互联运营，Azure OpenAI Service 已在中国区有限可用。",
    products: [
      { name: "Azure AI Foundry (AI 开发平台)", url: "https://azure.microsoft.com/zh-cn/products/ai-foundry/" },
      { name: "Azure OpenAI Service", url: "https://azure.microsoft.com/zh-cn/products/cognitive-services/openai-service/" },
      { name: "Azure Arc (混合云)", url: "https://azure.microsoft.com/zh-cn/products/azure-arc/" },
    ],
    news: [
      { category: "产品发布", title: "Azure AI Foundry 正式发布", summary: "统一的 AI 开发平台，整合 Azure AI Studio、Azure Machine Learning 和 Azure OpenAI Service。支持可视化 RAG 编排、多模型路由。", url: "https://azure.microsoft.com/zh-cn/products/ai-foundry/" },
      { category: "产品发布", title: "Azure OpenAI 在中国区上线 GPT-4o", summary: "世纪互联运营的 Azure 中国区正式提供 GPT-4o 多模态模型，支持图文混合理解和实时语音。", url: "https://azure.microsoft.com/zh-cn/products/cognitive-services/openai-service/" },
      { category: "最新动态", title: "Microsoft 365 Copilot 在华定价下调 30%", summary: "面对国内办公 AI 竞争加剧，微软下调中国区 Copilot 定价以争夺中小企业市场。", url: "https://www.microsoft.com/zh-cn/" },
      { category: "解决方案", title: "Azure Arc 新增边缘 K8s 管理能力", summary: "Azure Arc 支持在边缘设备上统一管理 Kubernetes 集群，面向制造和零售场景。", url: "https://azure.microsoft.com/zh-cn/products/azure-arc/" },
    ],
  },
  {
    id: "aliyun",
    name: "阿里云",
    fullName: "阿里云计算有限公司",
    region: "中国",
    color: "text-orange-500",
    bgColor: "bg-orange-50 border-orange-200",
    icon: "🟧",
    marketShare: "国内 34% · 第一",
    description: "国内市场份额第一，双11 高并发验证。通义千问大模型持续开源，百炼平台为企业提供一站式 AI 应用开发能力。",
    products: [
      { name: "通义千问 (大模型)", url: "https://www.aliyun.com/product/tongyi" },
      { name: "百炼 (AI 应用平台)", url: "https://www.aliyun.com/product/bailian" },
      { name: "PAI (机器学习平台)", url: "https://www.aliyun.com/product/pai" },
      { name: "PolarDB (云原生数据库)", url: "https://www.aliyun.com/product/polardb" },
      { name: "ECS (云服务器)", url: "https://www.aliyun.com/product/ecs" },
      { name: "OSS (对象存储)", url: "https://www.aliyun.com/product/oss" },
    ],
    news: [
      { category: "产品发布", title: "通义千问 3.0 发布，推理成本降低 60%", summary: "阿里云发布通义千问 3.0 大模型，在代码和数学推理能力上接近 GPT-4。Qwen3 系列在多项基准测试中表现优异。API 价格大幅下调。", url: "https://www.aliyun.com/product/tongyi" },
      { category: "产品发布", title: "PolarDB Serverless V2 正式可用", summary: "支持秒级弹性伸缩，数据库成本降低 70%。适合波峰波谷明显的业务场景（电商、教育）。", url: "https://www.aliyun.com/product/polardb" },
      { category: "最新动态", title: "钉钉 AI 助手全面开放", summary: "钉钉内置 AI 助手支持文档总结、会议纪要、智能审批等 20+ 场景。已接入通义千问 3.0，月活用户超 2 亿。", url: "https://www.dingtalk.com/" },
      { category: "案例发布", title: "阿里云与浙江省签署数字政务战略合作", summary: "阿里云将为浙江省提供全域政务云底座，覆盖 11 个地市 80+ 委办局的数字化转型。", url: "https://www.aliyun.com/" },
    ],
  },
  {
    id: "volcano",
    name: "火山云",
    fullName: "火山引擎（字节跳动）",
    region: "中国",
    color: "text-blue-500",
    bgColor: "bg-blue-50 border-blue-200",
    icon: "🔥",
    marketShare: "国内 5% · 增速最快",
    description: "依托字节跳动抖音生态，在 AI 推理和内容分发上增长迅猛。豆包大模型以极低价格抢占市场，Coze 成为中国最流行的 AI Agent 搭建平台之一。",
    products: [
      { name: "豆包大模型 (AI 模型)", url: "https://www.volcengine.com/product/doubao" },
      { name: "火山方舟 (模型服务平台)", url: "https://www.volcengine.com/product/ark" },
      { name: "扣子 Coze (AI Agent 平台)", url: "https://www.volcengine.com/product/coze" },
      { name: "火山引擎 ECS", url: "https://www.volcengine.com/product/ecs" },
    ],
    news: [
      { category: "产品发布", title: "火山方舟 3.0 发布，新增 MoE 架构支持", summary: "方舟平台 3.0 支持混合专家模型部署，企业客户可自定义路由策略。推理成本再降 40%，已接入豆包、DeepSeek 等多款模型。", url: "https://www.volcengine.com/product/ark" },
      { category: "产品发布", title: "扣子 Coze 平台用户突破 1000 万", summary: "Coze 成为中国最受欢迎的 AI Agent 搭建平台之一。支持可视化工作流、插件市场、多平台发布（微信、飞书、网页）。", url: "https://www.volcengine.com/product/coze" },
      { category: "案例发布", title: "火山云与抖音电商联合发布零售 AI 方案", summary: "基于豆包大模型的智能选品和直播脚本生成工具，已服务 5,000+ 抖音商家。", url: "https://www.volcengine.com/" },
      { category: "最新动态", title: "豆包 App 日活突破 1600 万", summary: "豆包已成为中国最受欢迎的 AI 对话应用。火山引擎持续以低价策略抢占市场，AI 推理价格降至 0.8 元/千 Token。", url: "https://www.volcengine.com/product/doubao" },
    ],
  },
  {
    id: "huawei",
    name: "华为云",
    fullName: "华为云计算技术有限公司",
    region: "中国",
    color: "text-rose-600",
    bgColor: "bg-rose-50 border-rose-200",
    icon: "🔴",
    marketShare: "国内第二 · 政企市场第一",
    description: "国内政企市场份额第一，全栈自主可控（鲲鹏+欧拉+GaussDB+盘古）。端边云协同能力在制造、政务、能源等重资产行业具有独特优势。",
    products: [
      { name: "ModelArts (AI 开发平台)", url: "https://www.huaweicloud.com/product/modelarts.html" },
      { name: "GaussDB (分布式数据库)", url: "https://www.huaweicloud.com/product/gaussdb.html" },
      { name: "OBS (对象存储)", url: "https://www.huaweicloud.com/product/obs.html" },
      { name: "ROMA (应用集成平台)", url: "https://www.huaweicloud.com/product/roma.html" },
      { name: "ECS (弹性云服务器)", url: "https://www.huaweicloud.com/product/ecs.html" },
    ],
    news: [
      { category: "产品发布", title: "盘古大模型 5.0 发布，多模态能力全面升级", summary: "盘古大模型 5.0 在气象预测、药物研发、矿山、铁路等行业场景中持续迭代。新增具身智能和多模态理解能力。", url: "https://www.huaweicloud.com/product/modelarts.html" },
      { category: "案例发布", title: "湘钢 × 华为云：钢铁行业智能制造标杆", summary: "湖南华菱湘潭钢铁集团基于华为云实现智能质检和预测性维护，缺陷检测准确率 99.5%。", url: "https://www.huaweicloud.com/cases/xg.html" },
      { category: "案例发布", title: "深圳机场 × 华为云：智慧机场标杆", summary: "深圳机场基于华为云打造智慧运维管理平台，覆盖设备预测性维护、航班智能调度。", url: "https://www.huaweicloud.com/cases/shenzhenjichang.html" },
      { category: "案例发布", title: "招商银行 × 华为云：最佳零售银行", summary: "华为云携手招商银行打造业界'最佳零售银行'，GaussDB 分布式数据库支撑核心交易系统。", url: "https://www.huaweicloud.com/cases/zsyh.html" },
      { category: "案例发布", title: "三峡集团 × 华为云：大国重器云端守护", summary: "三峡集团基于华为云实现水电站智能巡检和设备健康管理，覆盖 100+ 水电站。", url: "https://www.huaweicloud.com/cases/sanxia.html" },
    ],
  },
  {
    id: "tencent",
    name: "腾讯云",
    fullName: "腾讯云计算（深圳）有限公司",
    region: "中国",
    color: "text-green-600",
    bgColor: "bg-green-50 border-green-200",
    icon: "🟢",
    marketShare: "国内 16% · 第三",
    description: "依托微信生态（13亿用户）在 C 端场景占据优势。混元大模型深度集成到微信、QQ、腾讯文档等产品中。游戏和社交场景技术领先。",
    products: [
      { name: "混元大模型", url: "https://cloud.tencent.com/product/hunyuan" },
      { name: "TI-ONE (机器学习平台)", url: "https://cloud.tencent.com/product/tione" },
      { name: "大模型知识引擎 LKE", url: "https://cloud.tencent.com/product/lke" },
      { name: "CVM (云服务器)", url: "https://cloud.tencent.com/product/cvm" },
      { name: "COS (对象存储)", url: "https://cloud.tencent.com/product/cos" },
      { name: "TKE (容器服务)", url: "https://cloud.tencent.com/product/tke" },
    ],
    news: [
      { category: "产品发布", title: "混元大模型 Turbo S 发布", summary: "混元 Turbo S 推理速度提升 3 倍，成本降低 50%。重点面向游戏、广告和社交场景优化。已深度集成到微信和 QQ 中。", url: "https://cloud.tencent.com/product/hunyuan" },
      { category: "产品发布", title: "腾讯云大模型知识引擎 LKE 上线", summary: "企业级 RAG 知识库平台，支持零代码构建 AI 问答系统。可对接微信客服、企业微信等腾讯生态。", url: "https://cloud.tencent.com/product/lke" },
      { category: "案例发布", title: "腾讯云 TDSQL 中标六大行分布式数据库项目", summary: "腾讯云 TDSQL 在六大国有银行分布式数据库招标中中标 3 个，金融行业份额持续扩大。", url: "https://cloud.tencent.com/product/tdsql" },
      { category: "最新动态", title: "腾讯云与深圳地铁签署智慧交通协议", summary: "腾讯云将为深圳地铁提供 AI 调度和客流预测系统，覆盖 16 条线路 300+ 站点。", url: "https://cloud.tencent.com/" },
    ],
  },
];

const categoryIcons: Record<string, React.ElementType> = {
  "产品发布": Package, "案例发布": FileText, "解决方案": ShieldCheck, "最新动态": Newspaper,
};

const categoryColors: Record<string, string> = {
  "产品发布": "bg-indigo-50 text-indigo-700 border-indigo-200",
  "案例发布": "bg-emerald-50 text-emerald-700 border-emerald-200",
  "解决方案": "bg-amber-50 text-amber-700 border-amber-200",
  "最新动态": "bg-sky-50 text-sky-700 border-sky-200",
};

export default function CompetitorsPage() {
  const [activeVendor, setActiveVendor] = useState<string | null>(null);
  const selectedVendor = vendors.find((v) => v.id === activeVendor);

  return (
    <div className="space-y-10">
      <SectionHeader
        badge="Cloud Vendor Research"
        title="云厂商商业调研"
        subtitle="六大云厂商最新动态：新产品发布、新案例、新解决方案、商业策略追踪"
        image="https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&q=80"
      />

      {/* Vendor Selector */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {vendors.map((v) => (
          <button
            key={v.id}
            onClick={() => setActiveVendor(activeVendor === v.id ? null : v.id)}
            className={`group text-left rounded-xl bg-white border p-5 transition-all duration-200 ${
              activeVendor === v.id
                ? "border-primary/40 shadow-[var(--shadow-card-hover)] ring-1 ring-primary/20"
                : "border-slate-200/60 shadow-[var(--shadow-card)] hover:border-primary/30 hover:shadow-[var(--shadow-card-hover)]"
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className={`h-10 w-10 rounded-xl flex items-center justify-center transition-colors ${
                  activeVendor === v.id
                    ? "bg-gradient-to-r from-indigo-500 to-purple-500 text-white"
                    : "bg-slate-100 text-ink-secondary"
                }`}>
                  <Cloud className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-bold text-base text-ink">{v.name}</h3>
                  <span className={`rounded-full text-[10px] font-semibold px-2 py-0.5 ${v.bgColor} ${v.color}`}>{v.region}</span>
                </div>
              </div>
              <ChevronRight className={`h-5 w-5 text-slate-300 transition-transform duration-200 ${
                activeVendor === v.id ? "rotate-90 text-primary" : ""
              }`} />
            </div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">份额</span>
              <span className="text-xs font-semibold text-ink-secondary">{v.marketShare}</span>
            </div>
            <p className="text-xs text-ink-secondary leading-relaxed line-clamp-2">{v.description}</p>
          </button>
        ))}
      </div>

      {/* Vendor Detail Panel */}
      {selectedVendor && (
        <div className="space-y-6">
          {/* Vendor Header */}
          <div className="rounded-2xl bg-white border border-slate-200/60 overflow-hidden shadow-[var(--shadow-card)]">
            <div className="bg-gradient-to-r from-indigo-500 to-purple-500 px-8 py-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="h-10 w-10 rounded-lg bg-white/20 flex items-center justify-center text-white text-lg font-bold">
                  {selectedVendor.icon}
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">{selectedVendor.fullName}</h3>
                  <p className="text-sm text-white/70">{selectedVendor.marketShare}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-[11px] text-white/60 font-semibold uppercase tracking-wider">核心产品</p>
                <div className="flex flex-wrap gap-2 mt-1">
                  {selectedVendor.products.slice(0, 3).map((p, i) => (
                    <a key={i} href={p.url} target="_blank" rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-white/15 text-[10px] font-semibold text-white hover:bg-white/25 transition-colors">
                      {p.name.split("(")[0].trim()}
                      <ExternalLink className="h-2.5 w-2.5" />
                    </a>
                  ))}
                </div>
              </div>
            </div>
            <div className="p-8">
              <p className="text-sm text-ink-secondary leading-relaxed border-l-4 border-primary pl-6">
                {selectedVendor.description}
              </p>
            </div>
          </div>

          {/* Products */}
          <div className="rounded-xl bg-white border border-slate-200/60 p-6 shadow-[var(--shadow-card)]">
            <div className="flex items-center gap-2 mb-4">
              <Package className="h-4 w-4 text-primary" />
              <h4 className="font-bold text-sm text-ink">核心产品与服务</h4>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {selectedVendor.products.map((p, i) => (
                <a key={i} href={p.url} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-3 p-3 rounded-lg border border-slate-200/60 hover:border-primary/30 hover:bg-indigo-50/30 transition-all group">
                  <div className="h-8 w-8 rounded-lg bg-slate-100 flex items-center justify-center group-hover:bg-primary/10 transition-colors">
                    <Server className="h-4 w-4 text-ink-muted group-hover:text-primary" />
                  </div>
                  <span className="text-xs font-semibold text-ink-secondary group-hover:text-primary transition-colors">{p.name}</span>
                  <ArrowUpRight className="h-3 w-3 text-ink-muted ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
                </a>
              ))}
            </div>
          </div>

          {/* News Feed */}
          <div className="rounded-xl bg-white border border-slate-200/60 overflow-hidden shadow-[var(--shadow-card)]">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
              <Newspaper className="h-4 w-4 text-primary" />
              <h4 className="font-bold text-sm text-ink">最新动态</h4>
              <span className="text-[10px] text-ink-muted ml-auto">{selectedVendor.news.length} 条</span>
            </div>
            <div className="divide-y divide-slate-100">
              {selectedVendor.news.map((item, i) => {
                const CatIcon = categoryIcons[item.category] || Newspaper;
                return (
                  <a key={i} href={item.url} target="_blank" rel="noopener noreferrer"
                    className="flex items-start gap-4 p-5 hover:bg-slate-50/50 transition-colors group">
                    <div className="h-8 w-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0 group-hover:bg-primary/10 transition-colors">
                      <CatIcon className="h-4 w-4 text-ink-muted group-hover:text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                        <span className={`text-[9px] font-semibold px-2 py-0.5 rounded-full border ${categoryColors[item.category]}`}>
                          {item.category}
                        </span>
                        {item.date && <span className="text-[10px] text-ink-muted">{item.date}</span>}
                      </div>
                      <h5 className="font-bold text-sm text-ink group-hover:text-primary transition-colors mb-1">
                        {item.title}
                      </h5>
                      <p className="text-xs text-ink-secondary leading-relaxed">{item.summary}</p>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-ink-muted shrink-0 mt-2 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </a>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Overview - No vendor selected */}
      {!activeVendor && (
        <div className="space-y-6">
          {/* Quick Comparison */}
          <div className="rounded-xl bg-white border border-slate-200/60 overflow-hidden shadow-[var(--shadow-card)]">
            <div className="px-6 py-4 border-b border-slate-100">
              <h4 className="font-bold text-sm text-ink">六大云厂商一览</h4>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/50">
                    <th className="text-left py-3 px-5 text-[10px] font-semibold text-ink-muted uppercase tracking-wider">厂商</th>
                    <th className="text-left py-3 px-4 text-[10px] font-semibold text-ink-muted uppercase tracking-wider">市场份额</th>
                    <th className="text-left py-3 px-4 text-[10px] font-semibold text-ink-muted uppercase tracking-wider">AI 核心产品</th>
                    <th className="text-left py-3 px-4 text-[10px] font-semibold text-ink-muted uppercase tracking-wider">核心优势</th>
                  </tr>
                </thead>
                <tbody>
                  {vendors.map((v, i) => {
                    const advantage: Record<string, string> = {
                      aws: "全球基础设施最广，AI/ML 服务成熟度最高",
                      azure: "OpenAI 独占整合，企业办公生态绑定",
                      aliyun: "国内份额第一，开源生态成熟",
                      volcano: "价格最低，抖音电商生态",
                      huawei: "全栈自主可控，政企市场深耕",
                      tencent: "微信 13 亿用户生态，游戏场景领先",
                    };
                    return (
                      <tr key={v.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors cursor-pointer"
                        onClick={() => setActiveVendor(v.id)}>
                        <td className="py-3 px-5">
                          <div className="flex items-center gap-2">
                            <span className="text-base">{v.icon}</span>
                            <span className="font-semibold text-ink">{v.name}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-xs text-ink-secondary">{v.marketShare}</td>
                        <td className="py-3 px-4 text-xs text-ink-secondary">{v.products[0]?.name.split("(")[0] || "—"}</td>
                        <td className="py-3 px-4 text-xs text-ink-secondary max-w-xs">{advantage[v.id] || "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* CTA */}
          <div className="text-center py-6">
            <p className="text-sm text-ink-muted mb-2">点击上方任意厂商卡片，查看该厂商最新动态详情</p>
            <p className="text-xs text-ink-muted">每个厂商包含：产品发布 · 案例发布 · 解决方案 · 最新动态</p>
          </div>
        </div>
      )}
    </div>
  );
}
