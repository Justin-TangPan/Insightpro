"use client";

import { Check, RefreshCw, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { ExportButtons } from "../export-buttons";
import { usePreferences } from "@/lib/preferences";

type Candidate = { id: number; business_scopes: string[]; title: string; canonical_url?: string; source_count: number; mention_count: number; evidence_count: number; discovery_score: number; sources: string[]; first_seen_at: string; last_seen_at: string };
const scopes = [["technology_ecosystem", "技术生态", "Technology ecosystem"], ["ai_applications", "AI 应用", "AI applications"], ["solutions", "解决方案", "Solutions"], ["community_insights", "社区洞察", "Community insights"], ["competitor_dynamics", "友商动态", "Competitor updates"]];

export default function AdminCandidatesPage() {
  const { user, loading } = useAuth();
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [items, setItems] = useState<Candidate[]>([]);
  const [scope, setScope] = useState<Record<number, string[]>>({});
  const [error, setError] = useState("");
  const [working, setWorking] = useState(0);
  const load = useCallback(async () => {
    try {
      const response = await authenticatedFetch(API + "/api/v2/admin/candidates?status=pending&limit=100");
      if (!response.ok) throw new Error(en ? "Candidate queue unavailable." : "候选队列加载失败。");
      setItems((await response.json()).items || []);
      setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Error"); }
  }, [en]);
  useEffect(() => { if (user?.app_metadata?.role === "admin") void Promise.resolve().then(load); }, [load, user]);
  const act = async (item: Candidate, action: "approve" | "ignore") => {
    setWorking(item.id);
    try {
      const selectedScopes = scope[item.id] || item.business_scopes || ["technology_ecosystem"];
      if (action === "approve" && !selectedScopes.length) throw new Error("至少选择一个目标业务");
      const response = await authenticatedFetch(API + "/api/v2/admin/candidates/" + item.id + "/" + action, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(action === "approve" ? { business_scopes: selectedScopes } : { reason: "人工确认该候选不构成独立事件" }),
      });
      if (!response.ok) throw new Error((await response.text()).slice(0, 300));
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Error"); }
    finally { setWorking(0); }
  };
  if (loading) return <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "Checking access…" : "正在验证权限…"}</div>;
  if (user?.app_metadata?.role !== "admin") return <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "Administrator access required." : "需要管理员权限。"}</div>;
  return <div className="page-stack">
    <ExportButtons dataset="candidate" filters={{ status: "pending" }} />
    <SectionHeader badge="Admin / Discovery" title={en ? "Discovered candidates" : "发现候选"} subtitle={en ? "Repeated unlinked signals await human verification before becoming events." : "跨来源重复且尚未归档的信号先进入候选，经人工核验后才生成正式事件。"} action={<button className="ui-button-secondary" onClick={() => void load()}><RefreshCw size={15} />{en ? "Refresh" : "刷新"}</button>} />
    {error && <div role="alert" className="ui-card py-3 text-sm text-warning">{error}</div>}
    <section className="space-y-3">{items.map(item => <article key={item.id} className="ui-card">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-semibold text-ink">{item.title}</h2>{item.canonical_url && <a className="mt-1 block break-all text-xs text-primary" href={item.canonical_url} target="_blank" rel="noreferrer">{item.canonical_url}</a>}<p className="mt-2 text-xs text-ink-muted">{item.evidence_count} {en ? "evidence" : "条证据"} · {item.source_count} {en ? "sources" : "个来源"} · {item.mention_count} {en ? "mentions" : "次出现"}</p><div className="mt-2 flex flex-wrap gap-1">{item.sources.map(source => <span className="ui-tag" key={source}>{source}</span>)}</div></div><div className="rounded-xl bg-primary-soft px-3 py-2 text-center"><strong className="font-mono text-primary">{Math.round(Number(item.discovery_score))}</strong><p className="text-[10px] text-ink-muted">{en ? "signal score" : "发现分"}</p></div></div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-grid pt-3"><fieldset><legend className="text-xs text-ink-muted">{en ? "Target businesses" : "目标业务（首项为主业务）"}</legend><div className="mt-2 flex flex-wrap gap-3">{scopes.map(([key, zh, english]) => <label key={key} className="flex min-h-10 items-center gap-1 text-xs"><input type="checkbox" checked={(scope[item.id] || item.business_scopes || ["technology_ecosystem"]).includes(key)} onChange={e => setScope(current => ({ ...current, [item.id]: e.target.checked ? [...(current[item.id] || item.business_scopes || []), key] : (current[item.id] || item.business_scopes || []).filter(value => value !== key) }))} />{en ? english : zh}</label>)}</div></fieldset><div className="flex gap-2"><button type="button" disabled={working === item.id} className="ui-button-secondary" onClick={() => void act(item, "ignore")}><X size={14} />{en ? "Ignore" : "忽略"}</button><button type="button" disabled={working === item.id} className="ui-button-primary" onClick={() => void act(item, "approve")}><Check size={14} />{en ? "Create event" : "核验并建事件"}</button></div></div>
    </article>)}</section>
    {!items.length && !error && <div className="ui-card py-14 text-center text-sm text-ink-muted">{en ? "No candidates meet the repeated-signal threshold." : "暂无达到重复信号门槛的候选。"}</div>}
  </div>;
}
