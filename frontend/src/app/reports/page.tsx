import {
  FileText, Download, Share2, TrendingUp, ShieldAlert,
  Lightbulb, Target, ArrowLeft, Calendar, Globe, Zap, BarChart4
} from "lucide-react";
import Link from "next/link";

export default function ReportsPage() {
  const dateStr = new Date().toISOString().slice(0, 10);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="relative overflow-hidden rounded-2xl bg-white border border-slate-200/60 shadow-[var(--shadow-card)]">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-50/50 via-transparent to-purple-50/30" />
        <div className="absolute inset-0 opacity-[0.05]">
          <img src="https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?w=1200&q=80" alt="" className="w-full h-full object-cover" />
        </div>
        <div className="relative px-8 py-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="flex items-center gap-5">
              <Link href="/" className="h-10 w-10 rounded-xl bg-slate-100 border border-slate-200/60 flex items-center justify-center hover:bg-primary hover:text-white hover:border-primary transition-all">
                <ArrowLeft className="h-4.5 w-4.5" />
              </Link>
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded-full gradient-primary text-white text-[10px] font-semibold">Industry Report</span>
                  <span className="text-ink-muted text-xs">•</span>
                  <span className="text-[11px] text-ink-muted font-medium flex items-center gap-1">
                    <Calendar className="h-3 w-3" /> {dateStr}
                  </span>
                </div>
                <h1 className="text-3xl font-serif font-bold tracking-tight text-ink">2026年新能源汽车市场深度洞察</h1>
              </div>
            </div>
            <div className="flex items-center gap-2.5">
              <button className="flex items-center gap-2 rounded-xl border border-slate-200/60 bg-white px-5 py-2.5 text-sm font-semibold text-ink-secondary hover:border-primary/30 hover:text-primary transition-all">
                <Share2 className="h-4 w-4" />
                分享
              </button>
              <button className="flex items-center gap-2 rounded-xl gradient-primary px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-500/20 hover:shadow-lg hover:shadow-indigo-500/30 transition-all">
                <Download className="h-4 w-4" />
                导出 PDF
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Left Column */}
        <div className="space-y-6">
          {/* Market Sentiment */}
          <div className="rounded-xl bg-white border border-slate-200/60 p-6 shadow-[var(--shadow-card)]">
            <h3 className="font-serif text-base font-bold mb-5 flex items-center gap-2 text-ink">
              <BarChart4 className="h-4.5 w-4.5 text-primary" />
              市场情绪指数
            </h3>
            <div className="space-y-5">
              {[
                { label: "行业热度", value: "88/100", color: "bg-rose-500", w: "88%" },
                { label: "竞争烈度", value: "94/100", color: "gradient-primary", w: "94%" },
                { label: "政策支持", value: "72/100", color: "bg-emerald-500", w: "72%" },
              ].map((m) => (
                <div key={m.label}>
                  <div className="flex justify-between text-[11px] font-semibold mb-1.5">
                    <span className="text-ink-muted uppercase tracking-wider">{m.label}</span>
                    <span className="text-ink">{m.value}</span>
                  </div>
                  <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${m.color}`} style={{ width: m.w }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Key Takeaways */}
          <div className="space-y-3.5">
            <h3 className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider pl-1">核心结论提炼</h3>

            <div className="rounded-xl border-l-4 border-primary bg-white border border-slate-200/60 p-5 shadow-[var(--shadow-card)]">
              <div className="flex items-center gap-2 text-primary mb-2.5">
                <TrendingUp className="h-4 w-4" />
                <h4 className="text-xs font-semibold uppercase tracking-wider">市场核心痛点</h4>
              </div>
              <p className="text-sm text-ink-secondary leading-relaxed italic">
                "下沉市场充电设施不足与二手车残值评估体系缺失，是制约销量进一步爆发的双重枷锁。"
              </p>
            </div>

            <div className="rounded-xl border-l-4 border-emerald-500 bg-white border border-slate-200/60 p-5 shadow-[var(--shadow-card)]">
              <div className="flex items-center gap-2 text-emerald-600 mb-2.5">
                <Target className="h-4 w-4" />
                <h4 className="text-xs font-semibold uppercase tracking-wider">竞品优势分析</h4>
              </div>
              <p className="text-sm text-ink-secondary leading-relaxed">
                <strong className="text-ink">特斯拉</strong>：极致供应链控制力。<br />
                <strong className="text-ink">比亚迪</strong>：全产业链垂直整合。
              </p>
            </div>

            <div className="rounded-xl border-l-4 border-amber-500 bg-white border border-slate-200/60 p-5 shadow-[var(--shadow-card)]">
              <div className="flex items-center gap-2 text-amber-600 mb-2.5">
                <Lightbulb className="h-4 w-4" />
                <h4 className="text-xs font-semibold uppercase tracking-wider">潜在机会点</h4>
              </div>
              <p className="text-sm text-ink-secondary leading-relaxed">
                换电模式在营运车辆市场的快速渗透，以及智能化座舱带来的软件订阅收入。
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Editorial Report */}
        <div className="lg:col-span-2">
          <div className="rounded-xl bg-white border border-slate-200/60 p-8 md:p-10 shadow-[var(--shadow-card)]">
            <article className="prose prose-slate prose-headings:font-serif prose-headings:font-medium prose-p:text-ink-secondary prose-p:leading-8 max-w-none">
              <div className="flex items-center gap-2 mb-8">
                <div className="h-1 w-10 gradient-primary rounded-full" />
                <span className="text-[10px] font-semibold text-primary uppercase tracking-[0.3em]">Deep Insight Editorial</span>
              </div>

              <h2 className="text-2xl text-ink mb-6">执行摘要：从政策驱动到价值回归</h2>
              <p>
                本报告基于 AI 对全球及中国新能源汽车（NEV）市场的海量数据分析得出。我们观察到市场正经历一次深刻的范式转移：从过去的补贴依赖型"政策驱动"，彻底转向以产品力和成本控制为核心的"价值驱动"。
              </p>

              <div className="my-10 bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-7 border border-indigo-100 relative overflow-hidden">
                <Zap className="absolute -right-3 -top-3 h-20 w-20 text-primary/5 rotate-12" />
                <p className="text-base text-ink font-serif leading-relaxed relative z-10">
                  "2026 年将是行业洗牌的'分水岭'。纯电增速放缓，插混（PHEV/EREV）成为增长主力，解决了续航焦虑与成本平衡的痛点。"
                </p>
                <div className="mt-3 flex items-center gap-2 not-italic">
                  <span className="h-px w-4 bg-ink-muted" />
                  <span className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider">AI Analyst Perspective</span>
                </div>
              </div>

              <h3 className="text-xl text-ink mt-10 mb-5">市场格局演变与价格战</h3>
              <p>
                随着电池原材料价格的进一步下探，10-15 万元价格区间已成为竞争最为激烈的"红海"。这一区间的消费者对价格极度敏感，品牌忠诚度较低。相比之下，30 万元以上的高端市场开始强调"城市智驾"作为核心护城河。
              </p>

              <ul className="my-8 space-y-4">
                <li className="flex gap-4">
                  <span className="h-6 w-6 rounded-lg bg-indigo-50 flex items-center justify-center text-[10px] font-bold text-primary shrink-0 mt-1">01</span>
                  <span><strong className="text-ink">供应链韧性</strong>：垂直整合能力决定了车企在价格战中的生存空间。</span>
                </li>
                <li className="flex gap-4">
                  <span className="h-6 w-6 rounded-lg bg-indigo-50 flex items-center justify-center text-[10px] font-bold text-primary shrink-0 mt-1">02</span>
                  <span><strong className="text-ink">全球化布局</strong>：面对国内内卷，东南亚与中东市场成为车企的新增长极。</span>
                </li>
              </ul>

              <h3 className="text-xl text-ink mt-10 mb-5">结论与战略建议</h3>
              <div className="grid md:grid-cols-2 gap-5 mt-6 not-prose">
                <div className="p-5 rounded-xl bg-slate-50 border border-slate-200/60">
                  <h5 className="text-[10px] font-semibold text-primary uppercase tracking-wider mb-2">短期策略</h5>
                  <p className="text-sm text-ink-secondary leading-relaxed">
                    优化供应链成本结构，通过规模效应确保现金流安全，应对持续全年的价格挑战。
                  </p>
                </div>
                <div className="p-5 rounded-xl gradient-primary text-white shadow-md shadow-indigo-500/20">
                  <h5 className="text-[10px] font-semibold text-white/70 uppercase tracking-wider mb-2">长期战略</h5>
                  <p className="text-sm text-white/90 leading-relaxed">
                    加大 AI 算法自研投入，构建差异化的智能座舱与自动驾驶体验，从"卖硬件"向"卖服务"转型。
                  </p>
                </div>
              </div>

              <div className="mt-14 pt-6 border-t border-slate-100 flex items-center justify-between text-[10px] text-ink-muted font-medium uppercase tracking-wider">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1"><Globe className="h-3 w-3" /> Data: Multiple Sources</span>
                  <span>•</span>
                  <span>Ref: BIP-2026-NEV-001</span>
                </div>
                <span>InsightPro Proprietary Analysis</span>
              </div>
            </article>
          </div>
        </div>
      </div>
    </div>
  );
}
