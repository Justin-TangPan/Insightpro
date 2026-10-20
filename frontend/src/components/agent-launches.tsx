"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight } from "lucide-react";
import { API } from "@/lib/api";
import { usePreferences } from "@/lib/preferences";
import type { Intelligence } from "@/lib/intelligence";
import { ExpandableText } from "@/components/expandable-text";

type Launch = { vendor: string; title: string; published: string; url: string; analysis: string | null; kind: "launch" | "product"; summary?: string; capability?: string; opportunity?: string; limitation?: string; intelligence?: Intelligence };
const vendorZh: Record<string, string> = { "Tencent Cloud": "腾讯云", "Alibaba Cloud": "阿里云", Volcengine: "火山引擎", "Microsoft Azure": "微软 Azure", Google: "谷歌", AWS: "亚马逊云科技" };

export function AgentLaunches() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [items, setItems] = useState<Launch[]>([]);
  const [vendors, setVendors] = useState<string[]>([]);
  const [selectedVendor, setSelectedVendor] = useState("");
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const response = await fetch(`${API}/api/agent-launches`, { signal: controller.signal });
        if (!response.ok) throw new Error("Agent launches unavailable");
        const data = await response.json();
        setItems(data.items || []);
        setVendors(data.vendors || []);
        setRefreshing(Boolean(data.refreshing));
        setLoading(false);
        if (data.refreshing) timer = setTimeout(load, 5000);
      } catch {
        if (!controller.signal.aborted) { setError(true); setLoading(false); }
      }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, []);
  return <section aria-labelledby="agent-launches-heading">
    <div className="mb-4"><p className="swiss-kicker text-primary">{en ? "AI APPLICATION INTELLIGENCE" : "AI 应用情报"}</p><h2 id="agent-launches-heading" className="mt-1 type-h2 text-ink">{en ? "Official AI application launches" : "各大厂商 AI 应用发布与分析"}</h2><p className="mt-2 text-sm text-ink-muted">{en ? "Discover official launches across AI vendors, with source-grounded analysis." : "检索各大厂商官方发布，包括智能体和其他 AI 应用；分析以原文为依据。"}</p></div>
    {error && <p role="status" className="text-sm text-ink-muted">{en ? "Launch feed is temporarily unavailable." : "发布信息暂不可用。"}</p>}
    {loading && <p role="status" className="text-sm text-ink-muted">{en ? "Checking official sources and analyzing launches…" : "正在检索官方发布并进行 AI 分析…"}</p>}
    {vendors.length > 0 && <div className="mb-4 flex flex-wrap gap-2" aria-label={en ? "Filter AI vendors" : "筛选 AI 厂商"}>
      {["", ...vendors].map(vendor => <button key={vendor} type="button" aria-pressed={selectedVendor === vendor} onClick={() => setSelectedVendor(vendor)} className={`rounded-lg px-3 py-2 text-xs ${selectedVendor === vendor ? "bg-primary text-white" : "bg-surface-subtle text-ink-secondary hover:bg-primary-soft"}`}>{en ? vendor || "All" : vendorZh[vendor] || vendor || "全部"}{vendor ? ` · ${items.filter(item => item.vendor === vendor).length}` : ""}</button>)}
    </div>}
    {!loading && !error && selectedVendor && !items.some(item => item.vendor === selectedVendor) && <p role="status" className="mb-4 text-sm text-ink-muted">{en ? "No verified application signal in the current sources. This does not mean the vendor has no Agent product." : "当前来源暂无已核实的应用线索；这不代表该厂商没有 Agent 产品。"}</p>}
    <div className="grid gap-4 lg:grid-cols-2">{items.filter(item => !selectedVendor || item.vendor === selectedVendor).map(item => <article key={item.url} className="ui-card">
      <div className="flex items-center justify-between gap-3 text-xs text-ink-muted"><span>{en ? item.vendor : vendorZh[item.vendor] || item.vendor} · {item.kind === "product" ? (en ? "Official product" : "官方产品") : (en ? "Launch announcement" : "发布公告")}</span><time>{item.published || (item.kind === "product" ? (en ? "Product page" : "产品页") : (en ? "Date pending" : "发布日期待核实"))}</time></div>
      <h3 className="mt-3 text-lg font-semibold text-ink">{item.intelligence?.title || item.title}</h3>
      {item.intelligence?.brief && <ExpandableText lines={2} en={en} className="mt-3 text-sm leading-6 text-ink-muted">{item.intelligence.brief}</ExpandableText>}
      {item.capability || item.opportunity || item.limitation ? <div className="mt-3 space-y-1.5 text-sm leading-6 text-ink-secondary">{item.capability && <p><span className="font-semibold text-primary">{en ? "What: " : "能做什么："}</span>{item.capability}</p>}{item.opportunity && <p><span className="font-semibold text-primary">{en ? "Opportunity: " : "生态机会："}</span>{item.opportunity}</p>}{item.limitation && <p><span className="font-semibold text-primary">{en ? "To verify: " : "待验证："}</span>{item.limitation}</p>}</div> : !item.summary && <p className="mt-3 whitespace-pre-line text-sm leading-6 text-ink-secondary">{refreshing ? (en ? "Analysis in progress…" : "分析生成中…") : (en ? "Analysis pending; check the official source." : "分析待生成，请查看官方原文。")}</p>}
      <a href={item.intelligence?.source || item.url} target="_blank" rel="noopener noreferrer" className="ui-link mt-4 inline-flex items-center gap-1 text-xs">{en ? "Official source" : "查看官方原文"}<ArrowUpRight className="h-3.5 w-3.5" /></a>
    </article>)}</div>
  </section>;
}
