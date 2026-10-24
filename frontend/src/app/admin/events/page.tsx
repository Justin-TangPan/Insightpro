"use client";

import Link from "next/link";
import { Archive, GitFork, Merge, RefreshCw, RotateCw, Undo2, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { usePreferences } from "@/lib/preferences";

type Event = { id: number; title: string; event_type: string; business_scopes: string[]; tags: string[]; scores: Record<string, unknown>; last_seen_at: string; evidence_count: number; evidence_ids: number[]; source_count: number; event_key: string; status: "active" | "ignored" | "archived" | "merged" };
const scopeName: Record<string, string> = { technology_ecosystem: "技术生态", ai_applications: "AI 应用", solutions: "解决方案", community_insights: "社区洞察", competitor_dynamics: "友商动态" };

export default function AdminEventsPage() {
  const { user, loading } = useAuth();
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [events, setEvents] = useState<Event[]>([]);
  const [error, setError] = useState("");
  const [working, setWorking] = useState(0);
  const [mergeTargets, setMergeTargets] = useState<Record<number, string>>({});
  const [status, setStatus] = useState<"active" | "ignored" | "archived" | "all">("active");
  const [splitSelections, setSplitSelections] = useState<Record<number, number[]>>({});
  const [splitTitles, setSplitTitles] = useState<Record<number, string>>({});
  const load = useCallback(async () => {
    try {
      const response = await authenticatedFetch(API + "/api/v2/admin/events?limit=50&status=" + status);
      if (!response.ok) throw new Error(en ? "Could not load events." : "事件加载失败。");
      setEvents((await response.json()).items || []);
      setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Error"); }
  }, [en, status]);
  useEffect(() => { if (user?.app_metadata?.role === "admin") void Promise.resolve().then(load); }, [load, user]);
  const action = async (id: number, path: string, init: RequestInit, success: string) => {
    setWorking(id);
    try {
      const response = await authenticatedFetch(API + path, init);
      if (!response.ok) throw new Error((await response.text()).slice(0, 300));
      setError(success);
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Error"); }
    finally { setWorking(0); }
  };
  const merge = (event: Event) => {
    const target = Number(mergeTargets[event.id]);
    if (!Number.isInteger(target) || target <= 0 || target === event.id) {
      setError(en ? "Enter a different valid target event ID." : "请输入有效且不同的目标事件 ID。");
      return;
    }
    void action(event.id, "/api/v2/admin/events/" + event.id + "/merge", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target_id: target, reason: "管理员确认同一事件" }) }, en ? "Events merged." : "事件已合并。");
  };
  const split = (event: Event) => {
    const evidence_ids = splitSelections[event.id] || [];
    const title = (splitTitles[event.id] || "").trim();
    if (!title || !evidence_ids.length || evidence_ids.length >= event.evidence_ids.length) {
      setError(en ? "Choose some, but not all, evidence and enter a new title." : "请选择部分证据，并填写新事件标题。");
      return;
    }
    void action(event.id, "/api/v2/admin/events/" + event.id + "/split", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ evidence_ids, title, reason: "管理员纠正事件聚合" }) }, en ? "Event split." : "事件已拆分。");
  };
  if (loading) return <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "Checking access…" : "正在验证权限…"}</div>;
  if (user?.app_metadata?.role !== "admin") return <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "Administrator access required." : "需要管理员权限。"}</div>;
  return <div className="page-stack">
    <SectionHeader badge="Admin / Events" title={en ? "Events" : "事件管理"} subtitle={en ? "Correct classification, merge, restore or archive events." : "纠正分类、合并、恢复或归档事件。"} action={<button className="ui-button-secondary" onClick={() => void load()}><RefreshCw size={15} />{en ? "Refresh" : "刷新"}</button>} />
    <label className="flex max-w-xs flex-col gap-1 text-xs text-ink-muted">{en ? "Event status" : "事件状态"}<select className="ui-input min-h-10 px-3 text-sm" value={status} onChange={event => setStatus(event.target.value as typeof status)}>{([["active", en ? "Active" : "活动"], ["ignored", en ? "Ignored" : "已忽略"], ["archived", en ? "Archived" : "已归档"], ["all", en ? "All" : "全部"]] as const).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    {error && <div role="status" className="ui-card py-3 text-sm text-ink-secondary">{error}</div>}
    <section className="space-y-3">{events.map(event => <article key={event.id} className="ui-card">
      <div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><Link href={"/events/" + event.id} className="font-semibold text-ink hover:text-primary">{event.title}</Link><p className="mt-1 font-mono text-[11px] text-ink-muted">#{event.id} · {event.event_key}</p><p className="mt-2 text-xs text-ink-secondary">{event.evidence_count} {en ? "evidence" : "条证据"} · {event.source_count} {en ? "sources" : "个来源"} · {new Date(event.last_seen_at).toLocaleString()} · {event.status}</p></div><div className="flex flex-wrap gap-1">{event.business_scopes.map(scope => <span key={scope} className="ui-tag">{en ? scope : scopeName[scope] || scope}</span>)}</div></div>
      <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto]"><label className="text-xs text-ink-muted">{en ? "Category" : "事件分类"}<select aria-label={en ? "Category" : "事件分类"} className="ui-input mt-1 min-h-10 w-full px-3 text-sm" disabled={event.status === "merged"} value={event.event_type} onChange={e => setEvents(items => items.map(item => item.id === event.id ? { ...item, event_type: e.target.value } : item))}>{[event.event_type, "product_release", "ai_application", "github_trending", "solution_catalog_change", "community_topic", "competitor_update", "business_signal"].filter((item, index, items) => items.indexOf(item) === index).map(type => <option key={type}>{type}</option>)}</select></label><label className="text-xs text-ink-muted">{en ? "Tags" : "标签"}<input aria-label={en ? "Tags" : "标签"} className="ui-input mt-1 min-h-10 w-full px-3 text-sm" disabled={event.status === "merged"} value={event.tags.join(", ")} onChange={e => setEvents(items => items.map(item => item.id === event.id ? { ...item, tags: e.target.value.split(",").map(tag => tag.trim()).filter(Boolean).slice(0, 20) } : item))} /></label><button type="button" className="ui-button-secondary self-end" disabled={working === event.id || event.status === "merged"} onClick={() => void action(event.id, "/api/v2/admin/events/" + event.id, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ event_type: event.event_type, business_scopes: event.business_scopes, tags: event.tags }) }, en ? "Event saved." : "事件已保存。")}>{en ? "Save" : "保存"}</button></div>
      {event.status === "active" && event.evidence_ids.length > 1 && <details className="mt-3 border-t border-grid pt-3"><summary className="flex cursor-pointer list-none items-center gap-2 text-xs text-ink-secondary"><GitFork size={14} />{en ? "Split evidence into a new event" : "拆分部分证据为新事件"}</summary><div className="mt-3 space-y-3"><div className="flex flex-wrap gap-3">{event.evidence_ids.map(id => <label key={id} className="flex items-center gap-1.5 text-xs text-ink-muted"><input type="checkbox" checked={(splitSelections[event.id] || []).includes(id)} onChange={e => setSplitSelections(current => ({ ...current, [event.id]: e.target.checked ? [...(current[event.id] || []), id] : (current[event.id] || []).filter(value => value !== id) }))} />Evidence #{id}</label>)}</div><div className="flex flex-wrap gap-2"><input aria-label={en ? "New event title" : "新事件标题"} className="ui-input min-h-10 min-w-60 flex-1 px-3 text-sm" placeholder={en ? "New event title" : "新事件标题"} value={splitTitles[event.id] || ""} onChange={e => setSplitTitles(current => ({ ...current, [event.id]: e.target.value }))} /><button type="button" className="ui-button-secondary" disabled={working === event.id} onClick={() => split(event)}>{en ? "Create split event" : "创建拆分事件"}</button></div></div></details>}
      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-grid pt-3">{event.status === "active" && <button type="button" className="ui-button-secondary" disabled={working === event.id} onClick={() => void action(event.id, "/api/v2/admin/events/" + event.id + "/rescore", { method: "POST" }, en ? "Score updated." : "已重新评分。")}><RotateCw size={14} />{en ? "Re-score" : "重评分"}</button>}<div className="ml-auto flex flex-wrap gap-2">{event.status === "active" ? <><input aria-label={en ? "Merge target ID" : "合并目标事件 ID"} className="ui-input min-h-10 w-36 px-3 text-sm" inputMode="numeric" placeholder={en ? "Target event ID" : "目标事件 ID"} value={mergeTargets[event.id] || ""} onChange={e => setMergeTargets(current => ({ ...current, [event.id]: e.target.value }))} /><button type="button" className="ui-button-secondary" disabled={working === event.id} onClick={() => merge(event)}><Merge size={14} />{en ? "Merge" : "合并"}</button><button type="button" className="ui-button-secondary" disabled={working === event.id} onClick={() => void action(event.id, "/api/v2/admin/events/" + event.id, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "archived" }) }, en ? "Event archived." : "事件已归档。")}><Archive size={14} />{en ? "Archive" : "归档"}</button><button type="button" className="ui-button-secondary text-danger" disabled={working === event.id} onClick={() => void action(event.id, "/api/v2/admin/events/" + event.id, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "ignored" }) }, en ? "Event ignored." : "事件已忽略。")}><XCircle size={14} />{en ? "Ignore" : "忽略"}</button></> : event.status !== "merged" ? <button type="button" className="ui-button-secondary" disabled={working === event.id} onClick={() => void action(event.id, "/api/v2/admin/events/" + event.id, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "active" }) }, en ? "Event restored." : "事件已恢复。")}><Undo2 size={14} />{en ? "Restore" : "恢复"}</button> : null}</div></div>
    </article>)}</section>
    {!events.length && !error && <p className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "No active events." : "暂无活动事件。"}</p>}
  </div>;
}
