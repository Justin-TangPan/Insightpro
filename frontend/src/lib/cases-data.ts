/**
 * 统一案例数据中心
 * 所有页面的案例数据从此文件导入，避免重复定义
 */

export interface CaseItem {
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

import {
  Building2, Factory, ShoppingCart, Stethoscope, Landmark,
  Cpu, TrendingUp, Truck, Zap, Leaf, GraduationCap
} from "lucide-react";

// 行业图标映射
export const industryIcons: Record<string, React.ElementType> = {
  "政务": Building2, "制造": Factory, "医疗": Stethoscope,
  "金融": Landmark, "零售": ShoppingCart, "教育": GraduationCap,
  "交通": Truck, "能源": Zap, "农业": Leaf, "通用": Cpu,
  "互联网": Cpu,
};

// 所有案例数据（30个）
const allCases: CaseItem[] = [
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
    icon: Truck,
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
    icon: Truck,
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
  // ── Azure 案例 ──
  {
    industry: "金融",
    icon: Landmark,
    title: "Maersk × Azure：全球物流 SAP 现代化",
    customer: "Maersk（马士基）",
    vendor: "Azure",
    vendorColor: "bg-blue-50 text-blue-700 border-blue-200",
    solution: "Azure + SAP 现代化，在 3 周内部署 500 台 SAP 服务器，实现秒级弹性扩容",
    result: "500 台 SAP 服务器 3 周部署，零事故近 100% 正常运行，技术债务大幅削减",
    source: { title: "Azure·Maersk SAP 现代化案例", url: "https://www.microsoft.com/en/customers/story/26271-maersk-sap-on-azure" },
    tag: "物流 · SAP 现代化"
  },
  {
    industry: "医疗",
    icon: Stethoscope,
    title: "Philips × AWS：AI 健康科技平台",
    customer: "Philips（飞利浦）",
    vendor: "AWS",
    vendorColor: "bg-orange-50 text-orange-700 border-orange-200",
    solution: "AWS HealthSuite + SageMaker AI + IoT，构建全球健康科技平台，实现 MRI 影像重建加速",
    result: "MRI 扫描时间缩短 10 倍，AI 部署速度提升 80%，5,000+ 员工掌握 AI 技能",
    source: { title: "AWS·Philips 健康科技案例", url: "https://aws.amazon.com/cn/solutions/case-studies/innovators/philips/" },
    tag: "医疗 · AI 影像"
  },
  // ── 阿里云案例 ──
  {
    industry: "零售",
    icon: ShoppingCart,
    title: "资生堂 × 阿里云：新零售数字化战略",
    customer: "资生堂中国（SHISEIDO）",
    vendor: "阿里云",
    vendorColor: "bg-orange-50 text-orange-700 border-orange-200",
    solution: "阿里云负载均衡 + WAF + China Gateway，支撑资生堂中国新零售数字化战略",
    result: "线上线下全渠道数据打通，新零售业务敏捷上线，全球统一管理",
    source: { title: "阿里云·资生堂案例", url: "https://www.alibabacloud.com/en/customers/shiseido" },
    tag: "零售 · 新零售"
  },
  {
    industry: "交通",
    icon: Truck,
    title: "JakLingko × 阿里云：雅加达多模式交通整合",
    customer: "JakLingko",
    vendor: "阿里云",
    vendorColor: "bg-orange-50 text-orange-700 border-orange-200",
    solution: "阿里云云计算 + 大数据平台，整合雅加达多种公共交通模式，实现统一票务与调度",
    result: "多种交通模式统一票务管理，出行效率大幅提升，城市交通数字化转型标杆",
    source: { title: "阿里云·JakLingko 交通案例", url: "https://www.alibabacloud.com/en/customers/jaklingko" },
    tag: "交通 · 智慧出行"
  },
  // ── 腾讯云案例 ──
  {
    industry: "游戏",
    icon: Cpu,
    title: "米哈游 × 腾讯云：全球化游戏部署",
    customer: "米哈游（HoYoverse）",
    vendor: "腾讯云",
    vendorColor: "bg-green-50 text-green-700 border-green-200",
    solution: "腾讯云游戏引擎 + 全球加速网络，支撑《原神》全球 6000 万日活用户",
    result: "全球延迟 < 80ms，游戏卡顿率降低 60%，海外用户占比从 30% 提升至 65%",
    source: { title: "腾讯云·米哈游案例", url: "https://cloud.tencent.com/case/mihoyo" },
    tag: "游戏 · 全球化"
  },
  {
    industry: "金融",
    icon: Landmark,
    title: "微众银行 × 腾讯云：互联网银行核心系统",
    customer: "微众银行",
    vendor: "腾讯云",
    vendorColor: "bg-green-50 text-green-700 border-green-200",
    solution: "腾讯云 TDSQL 分布式数据库 + 微服务架构，支撑微众银行 3 亿用户核心交易",
    result: "日均交易 5 亿笔，账户成本降至 3 元/年，系统可用性 99.999%",
    source: { title: "腾讯云·微众银行案例", url: "https://cloud.tencent.com/case/webank" },
    tag: "金融 · 分布式数据库"
  },
  // ── 火山云案例 ──
  {
    industry: "电商",
    icon: ShoppingCart,
    title: "抖音电商 × 火山云：直播电商基础设施",
    customer: "抖音电商",
    vendor: "火山云",
    vendorColor: "bg-blue-50 text-blue-700 border-blue-200",
    solution: "火山引擎云原生架构 + 实时内容审核，支撑抖音电商万亿 GMV",
    result: "直播延迟 < 1s，内容审核准确率 99.5%，峰值 QPS 达 1000 万",
    source: { title: "火山云·抖音电商案例", url: "https://www.volcengine.com/case/douyin-ecommerce" },
    tag: "电商 · 直播"
  },
  {
    industry: "互联网",
    icon: Cpu,
    title: "得物 × 火山云：潮流电商 AI 推荐",
    customer: "得物",
    vendor: "火山云",
    vendorColor: "bg-blue-50 text-blue-700 border-blue-200",
    solution: "火山引擎豆包大模型 + 智能推荐系统，实现得物平台商品智能匹配",
    result: "推荐点击率提升 35%，用户停留时长增加 40%，GMV 增长 25%",
    source: { title: "火山云·得物案例", url: "https://www.volcengine.com/case/dewu" },
    tag: "互联网 · AI 推荐"
  },
];

// 行业洞察只保留竞品案例，不展示华为云自身案例。
export const cases = allCases.filter((item) => item.vendor !== "华为云");

// 按行业分组
export function getCasesByIndustry(industry: string): CaseItem[] {
  return cases.filter(c => c.industry === industry);
}

// 按厂商分组
export function getCasesByVendor(vendor: string): CaseItem[] {
  return cases.filter(c => c.vendor === vendor);
}

// 获取所有行业列表
export function getAllIndustries(): string[] {
  return [...new Set(cases.map(c => c.industry))];
}

// 获取所有厂商列表
export function getAllVendors(): string[] {
  return [...new Set(cases.map(c => c.vendor))];
}
