"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

const domains = [
  ["technology_ecosystem", "技术生态"], ["ai_applications", "AI 应用"], ["solutions", "解决方案"],
  ["community_insights", "社区洞察"], ["competitor_dynamics", "友商动态"],
] as const;
type Event = { id: number; title: string; summary?: string; event_type: string; business_scopes: string[]; scores: Record<string, unknown>; evidence_count: number; source_count: number; last_seen_at: string };
type Evidence = { id: number; source_name: string; title: string; canonical_url?: string; published_at?: string; observed_at?: string; original_summary?: string };
type Detail = Event & { evidence: Evidence[]; entity_key?: string };
export default function ReviewPanel() {
  const params = useSearchParams();
  const domain = params.get("domain") || "";
  const [items, setItems] = useState<Event[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [mergeTarget, setMergeTarget] = useState("");
  const [published, setPublished] = useState<{id: number; scopes: string[]} | null>(null);
  const load = useCallback(async () => {
    try {
      const response = await authenticatedFetch(API + `/api/v2/admin/events?status=pending_review&limit=100${domain ? `&business_scope=${encodeURIComponent(domain)}` : ""}`);
      if (!response.ok) throw new Error("待审事件加载失败");
      setItems((await response.json()).items || []); setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "待审事件加载失败"); }
  }, [domain]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  const open = async (id: number) => {
    setWorking(true);
    try {
      const response = await authenticatedFetch(API + `/api/v2/admin/events/${id}`);
      if (!response.ok) throw new Error("事件详情加载失败");
      setDetail(await response.json()); setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "事件详情加载失败"); }
    finally { setWorking(false); }
  };
  const saveText = async () => {
    if (!detail || !detail.title.trim()) return;
    setWorking(true);
    try {
      const response = await authenticatedFetch(API + `/api/v2/admin/events/${detail.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: detail.title.trim(), summary: detail.summary || "" }) });
      if (!response.ok) { const body = await response.json(); throw new Error(body.detail || "事件修改失败"); }
      await open(detail.id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "事件修改失败"); }
    finally { setWorking(false); }
  };
  const saveScopes = async (scopes: string[]) => {
    if (!detail || !scopes.length) return;
    setWorking(true);
    try {
      const response = await authenticatedFetch(API + `/api/v2/admin/events/${detail.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ business_scopes: scopes }) });
      if (!response.ok) throw new Error("目标业务保存失败");
      await open(detail.id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "目标业务保存失败"); }
    finally { setWorking(false); }
  };
  const analyze = async () => {
    if (!detail) return;
    setWorking(true); setError("");
    try {
      const response = await authenticatedFetch(API + `/api/v2/admin/events/${detail.id}/analyze`, { method: "POST" });
      if (!response.ok) { const body = await response.json(); throw new Error(body.detail || "AI 分析失败"); }
      await open(detail.id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "AI 分析失败"); }
    finally { setWorking(false); }
  };
  const merge = async () => {
    if (!detail) return;
    const target = Number(mergeTarget);
    if (!Number.isInteger(target) || target <= 0 || target === detail.id) { setError("请输入其他有效事件 ID"); return; }
    if (!window.confirm(`将事件 #${detail.id} 合并到 #${target}？目标事件需要重新审核。`)) return;
    setWorking(true);
    try {
      const response = await authenticatedFetch(API + `/api/v2/admin/events/${detail.id}/merge`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target_id: target, reason: "人工核验为同一事件" }) });
      if (!response.ok) { const body = await response.json(); throw new Error(body.detail || "合并失败"); }
      setMergeTarget(""); await load(); await open(target);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "合并失败"); }
    finally { setWorking(false); }
  };
  const decide = async (action: "publish" | "ignore") => {
    if (!detail || !window.confirm(action === "publish" ? "确认审核通过并发布到选定业务？" : "确认忽略这条事件？")) return;
    setWorking(true);
    try {
      const response = await authenticatedFetch(API + `/api/v2/admin/events/${detail.id}${action === "publish" ? "/publish" : ""}`, action === "publish" ? { method: "POST" } : { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "ignored" }) });
      if (!response.ok) { const result = await response.json(); throw new Error(result.detail || "审核操作失败"); }
      if (action === "publish") setPublished({id: detail.id, scopes: detail.business_scopes});
      setDetail(null); await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "审核操作失败"); }
    finally { setWorking(false); }
  };
  return <section className="page-stack"><div className="ui-card"><h2 className="text-lg font-semibold text-ink">待审核事件 <span className="text-primary">{items.length}</span></h2><p className="mt-1 text-xs text-ink-muted">核对原始证据、AI 评分和目标业务后发布；未通过审核的候选事件不会进入公开事件接口。</p></div>{error && <p role="alert" className="ui-card text-sm text-danger">{error}</p>}
    {published && <div role="status" className="ui-card text-sm"><strong>事件 #{published.id} 已审核发布。</strong><span className="ml-2 text-ink-muted">板块刷新任务已提交，可查看前台：</span>{published.scopes.map(scope => { const target = ({technology_ecosystem:"/insights/hotspots",ai_applications:"/insights/app-launches",solutions:"/insights/solutions",community_insights:"/insights/community",competitor_dynamics:"/insights/competitors"} as Record<string,string>)[scope]; return target ? <Link key={scope} className="ml-3 text-primary" href={target}>{domains.find(item => item[0] === scope)?.[1]}</Link> : null; })}</div>}
    <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(22rem,.85fr)]"><div className="space-y-2">{items.map(item => <button key={item.id} type="button" onClick={() => void open(item.id)} className="ui-card w-full text-left hover:border-primary"><strong className="block text-sm text-ink">{item.title}</strong><span className="mt-1 block text-xs text-ink-muted">{item.event_type} · {item.evidence_count} 条证据 · {item.source_count} 个来源 · {new Date(item.last_seen_at).toLocaleString("zh-CN")}</span></button>)}{!items.length && <p className="ui-card text-sm text-ink-muted">暂无待审核事件</p>}</div>
      {detail && <article className="ui-card"><div className="flex items-start justify-between gap-3"><h3 className="text-lg font-semibold text-ink">{detail.title}</h3><button type="button" className="ui-button-secondary" onClick={() => setDetail(null)}>关闭</button></div><label className="mt-3 block text-xs text-ink-muted">标题<input className="ui-input mt-1 w-full" value={detail.title} onChange={event => setDetail({ ...detail, title: event.target.value })} /></label><label className="mt-3 block text-xs text-ink-muted">摘要<textarea className="ui-input mt-1 min-h-20 w-full" value={detail.summary || ""} onChange={event => setDetail({ ...detail, summary: event.target.value })} /></label><button type="button" disabled={working} onClick={() => void saveText()} className="ui-button-secondary mt-2">保存修改</button><dl className="mt-4 grid grid-cols-2 gap-3 text-xs"><div><dt className="text-ink-muted">事件类型</dt><dd>{detail.event_type}</dd></div><div><dt className="text-ink-muted">关联实体</dt><dd className="break-all">{detail.entity_key || "—"}</dd></div><div><dt className="text-ink-muted">AI 分析与评分</dt><dd><pre className="max-h-44 overflow-auto whitespace-pre-wrap break-all">{JSON.stringify(detail.scores || {}, null, 2)}</pre></dd></div></dl><fieldset className="mt-4 border-t border-grid pt-3"><legend className="text-xs font-medium text-ink">发布目标业务（首项为主业务）</legend><div className="mt-2 flex flex-wrap gap-3">{domains.map(([value, label]) => <label key={value} className="flex min-h-10 items-center gap-1 text-xs"><input type="checkbox" disabled={working} checked={detail.business_scopes.includes(value)} onChange={event => void saveScopes(event.target.checked ? [...detail.business_scopes, value] : detail.business_scopes.filter(item => item !== value))} />{label}</label>)}</div></fieldset><button type="button" disabled={working} onClick={() => void analyze()} className="ui-button-secondary mt-3">{detail.scores?.ai_analysis ? "重新 AI 分析" : "执行 AI 分析"}</button><h4 className="mt-4 border-t border-grid pt-3 text-sm font-semibold">原始证据</h4><div className="mt-2 max-h-72 space-y-2 overflow-auto">{detail.evidence.map(item => <div key={item.id} className="rounded-lg border border-grid p-2 text-xs"><p className="font-medium">{item.source_name} · {item.title}</p><p className="mt-1 text-ink-muted">发布时间 {item.published_at ? new Date(item.published_at).toLocaleString("zh-CN") : "未知"}</p>{item.original_summary && <p className="mt-1 text-ink-secondary">{item.original_summary}</p>}{item.canonical_url && <a className="mt-1 block break-all text-primary" href={item.canonical_url} target="_blank" rel="noreferrer">{item.canonical_url}</a>}</div>)}</div><div className="mt-4 flex flex-wrap justify-end gap-2"><input className="ui-input w-32" aria-label="合并目标事件 ID" inputMode="numeric" placeholder="目标事件 ID" value={mergeTarget} onChange={event => setMergeTarget(event.target.value)} /><button type="button" disabled={working} onClick={() => void merge()} className="ui-button-secondary">合并</button><button type="button" disabled={working} onClick={() => void decide("ignore")} className="ui-button-secondary">忽略</button><button type="button" disabled={working || !detail.business_scopes.length || !detail.scores?.ai_analysis} onClick={() => void decide("publish")} className="ui-button-primary">审核通过并发布</button></div></article>}</div>
  </section>;
}
