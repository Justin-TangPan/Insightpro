"use client";

import { SectionHeader } from "@/components/section-header";
import { useState } from "react";
import {
  ExternalLink, ChevronRight,
  ShieldCheck
} from "lucide-react";
import Link from "next/link";
import { cases } from "@/lib/cases-data";

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
            className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all ${
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
            className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all ${
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
          return (
            <div key={v} className="rounded-xl bg-white border border-slate-200/60 p-4 shadow-sm">
              <p className="text-xs font-semibold text-ink-muted uppercase tracking-wider">{v}</p>
              <p className="text-2xl font-serif font-bold text-ink mt-1">{count}</p>
              <span className="text-xs text-ink-muted">个案例</span>
            </div>
          );
        })}
      </div>

      {/* Case Cards */}
      <div className="space-y-6">
        {filtered.map((c, i) => (
          <div key={i} className="rounded-2xl bg-white border border-slate-200/80 overflow-hidden shadow-sm">
            <div className="bg-slate-900 px-6 py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-7 w-7 rounded bg-white/10 flex items-center justify-center">
                  <c.icon className="h-3.5 w-3.5 text-white" />
                </div>
                <span className="text-xs font-semibold text-white/80 uppercase tracking-wider">{c.industry} · {c.tag}</span>
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
                <div className="rounded-xl border-l-4 border-primary bg-indigo-50/30 p-4">
                  <p className="text-xs font-semibold text-primary uppercase tracking-wider mb-2">方案</p>
                  <p className="text-xs text-ink font-medium leading-relaxed">{c.solution}</p>
                </div>
                <div className="rounded-xl border-l-4 border-emerald-500 bg-emerald-50/30 p-4 md:col-span-2">
                  <p className="text-xs font-semibold text-emerald-600 uppercase tracking-wider mb-2">效果</p>
                  <p className="text-xs text-ink-secondary leading-relaxed">{c.result}</p>
                </div>
              </div>

              <a
                href={c.source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-50 border border-slate-200/60 text-xs text-ink-muted hover:text-ink hover:border-slate-300 transition-colors"
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
