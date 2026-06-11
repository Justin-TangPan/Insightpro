import { ExternalLink, Calendar, Newspaper } from "lucide-react";
import Link from "next/link";
import { SectionHeader } from "@/components/section-header";

export default function NewsPage() {
  const news = [
    { title: "全球半导体供应链重组：东南亚份额占比升至 30%", source: "Reuters", date: "2026-05-30", summary: "受地缘政治及劳动力成本影响，主要芯片代工厂商正加速向越南、马来西亚转移产能。", link: "https://www.reuters.com/business/" },
    { title: "新能源汽车价格战告一段落，品牌忠诚度成为核心", source: "Bloomberg", date: "2026-05-30", summary: "主流车企开始减少价格补贴，转而投入用户社区与售后服务体系建设，追求长期溢价能力。", link: "https://www.bloomberg.com/asia" },
    { title: "低空经济试点扩至 6 城，eVTOL 市场规模预计 95 亿", source: "财新网", date: "2026-05-29", summary: "工信部发布最新指导意见，支持在粤港澳、长三角等核心城市群开展载人飞行器常态化运营。", link: "https://www.caixin.com" },
    { title: "分布式 AI 算力网络标准化协议发布", source: "Wired", date: "2026-05-29", summary: "由 NVIDIA 与多国电信运营商牵头的分布式算力协议将大幅降低中小企业 AI 训练成本。", link: "https://www.wired.com" },
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-10 pb-20">
      <SectionHeader
        badge="商业快讯"
        title="商业快讯实时监测"
        subtitle={`汇聚全球核心商业媒体头条 · 实时更新 · ${new Date().toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric" })}`}
        image="https://images.unsplash.com/photo-1504711434969-e33886168d6c?w=800&q=80"
      />

      <div className="grid gap-6 md:grid-cols-2">
        {news.map((item, i) => (
          <div
            key={i}
            className="flex flex-col rounded-xl bg-white border border-slate-200/60 overflow-hidden shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-card-hover)] transition-all duration-200 group"
          >
            <div className="p-6 space-y-4 flex-1">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center px-3 py-1 rounded-full gradient-primary text-white text-[10px] font-semibold">
                  {item.source}
                </span>
                <span className="flex items-center gap-1.5 text-[11px] font-medium text-ink-muted">
                  <Calendar className="h-3 w-3" />
                  {item.date}
                </span>
              </div>

              <h3 className="text-lg font-semibold text-ink group-hover:text-primary transition-colors leading-snug">
                {item.title}
              </h3>

              <p className="text-sm text-ink-secondary leading-relaxed">
                {item.summary}
              </p>
            </div>

            <div className="px-6 py-4 bg-slate-50 border-t border-slate-100">
              <a
                href={item.link}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-xs font-semibold text-primary hover:text-indigo-700 transition-colors"
              >
                <ExternalLink className="h-3 w-3" />
                阅读全文
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
