"use client";

import Link from "next/link";
import { Play, RefreshCw, Wifi } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import Coverage from "../coverage/page";
import { useAuth } from "@/components/auth-provider";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { ExportButtons } from "../export-buttons";
import { usePreferences } from "@/lib/preferences";

type Source = { source_key: string; name: string; adapter: string; base_url?: string; business_scopes: string[]; authority: string; priority: number; schedule: Record<string, unknown>; enabled: boolean; health_status: string; last_success_at?: string; last_run_at?: string; last_new_count?: number; consecutive_failures?: number; success_rate?: number | null; source_role?: string; language?: string; last_error?: string };
type SourceDraft = { source_key: string; name: string; adapter: string; base_url: string; business_scopes: string[]; authority: string; priority: number; cron: string; source_role: string; language: string; topics: string[] };
type Preview = { title: string; url: string; published_at?: string; summary: string; language: string };
const scopes = ["technology_ecosystem", "ai_applications", "solutions", "community_insights", "competitor_dynamics"];
const roles = ["OFFICIAL", "MEDIA", "COMMUNITY", "ACADEMIC", "PLATFORM"];
const emptyDraft = (): SourceDraft => ({ source_key: "", name: "", adapter: "rss_feed", base_url: "", business_scopes: ["technology_ecosystem"], authority: "P1", priority: 100, cron: "45 8 * * *", source_role: "MEDIA", language: "zh", topics: [] });
export default function AdminSourcesPage() {
  const { user, loading } = useAuth();
  const params = useSearchParams();
  const domain = params.get("domain") || "";
  const sourceKey = params.get("source") || "";
  const [tab, setTab] = useState("list");
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [sources, setSources] = useState<Source[]>([]);
  const [error, setError] = useState("");
  const [working, setWorking] = useState("");
  const [draft, setDraft] = useState<SourceDraft>(emptyDraft);
  const [roleFilter, setRoleFilter] = useState("");
  const [businessFilter, setBusinessFilter] = useState("");
  const [preview, setPreview] = useState<Preview[] | null>(null);
  const load = useCallback(async () => {
    try {
      const response = await authenticatedFetch(API + "/api/v2/admin/sources");
      if (!response.ok) throw new Error(en ? "Could not load sources." : "数据源加载失败。");
      setSources((await response.json()).items || []);
      setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Error"); }
  }, [en]);
  useEffect(() => { if (user?.app_metadata?.role === "admin") void Promise.resolve().then(load); }, [load, user]);
  const toggle = async (source: Source) => {
    setWorking(source.source_key);
    try {
      const response = await authenticatedFetch(API + "/api/v2/admin/sources/" + encodeURIComponent(source.source_key) + "/enabled", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled: !source.enabled }) });
      if (!response.ok) throw new Error(en ? "Source update failed." : "数据源状态更新失败。");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Error"); }
    finally { setWorking(""); }
  };
  const save = async (source: Source) => {
    setWorking(source.source_key);
    try {
      const response = await authenticatedFetch(API + "/api/v2/admin/sources/" + encodeURIComponent(source.source_key), { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: source.name, base_url: source.base_url, priority: source.priority, authority: source.authority, business_scopes: source.business_scopes, source_role: source.source_role, language: source.language }) });
      if (!response.ok) throw new Error(en ? "Source settings could not be saved." : "数据源配置保存失败。");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Error"); }
    finally { setWorking(""); }
  };
  const saveSchedule = async (source: Source) => {
    setWorking(source.source_key);
    try {
      const response = await authenticatedFetch(API + "/api/v2/admin/sources/" + encodeURIComponent(source.source_key) + "/schedule", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cron: String(source.schedule.cron || "") }) });
      if (!response.ok) throw new Error(en ? "Schedule update failed." : "采集计划更新失败。");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Error"); }
    finally { setWorking(""); }
  };
  const run = async (source: Source) => {
    setWorking(source.source_key);
    try {
      const response = await authenticatedFetch(API + "/api/v2/admin/sources/" + encodeURIComponent(source.source_key) + "/run", { method: "POST" });
      if (!response.ok) throw new Error(en ? "Collector could not start." : "采集任务启动失败。");
      setError(en ? "Manual run accepted: " + source.name : "已提交手动采集：" + source.name);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Error"); }
    finally { setWorking(""); }
  };
  const testConnection = async (source: Source) => {
    setWorking(source.source_key);
    try {
      const response = await authenticatedFetch(API + "/api/v2/admin/sources/" + encodeURIComponent(source.source_key) + "/test", { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || (en ? "Connection test failed." : "连接测试失败。"));
      setPreview(result.items || []);
      setError(result.ok ? (en ? `Parsed ${result.items?.length || 0} preview items` : `解析成功，预览 ${result.items?.length || 0} 条`) : (result.error || (en ? "Connection failed." : "连接失败。")));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Error"); }
    finally { setWorking(""); }
  };
  const testDraft = async () => {
    setWorking("preview");
    setPreview(null);
    try {
      const response = await authenticatedFetch(API + "/api/v2/admin/sources/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ base_url: draft.base_url, adapter: draft.adapter, language: draft.language }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "测试抓取失败");
      setPreview(result.items);
      setError(`解析成功，共 ${result.count} 条，显示前 5 条`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "测试抓取失败"); }
    finally { setWorking(""); }
  };
  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setWorking("create");
    try {
      const response = await authenticatedFetch(API + "/api/v2/admin/sources", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(draft) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || (en ? "Source could not be created." : "数据源创建失败。"));
      setDraft(emptyDraft());
      setPreview(null);
      await load();
      setError(en ? "Source created disabled. Test it, then enable collection." : "数据源已创建并保持停用。请先测试连接，再启用采集。");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Error"); }
    finally { setWorking(""); }
  };
  if (loading) return <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "Checking access…" : "正在验证权限…"}</div>;
  if (user?.app_metadata?.role !== "admin") return <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "Administrator access required." : "需要管理员权限。"}</div>;
  return <div className="page-stack">
    <ExportButtons dataset="data_source" filters={domain ? { business_scope: domain } : {}} />
    <nav aria-label="数据源模块" className="flex flex-wrap gap-2"><button type="button" className={tab === "list" ? "ui-button-primary" : "ui-button-secondary"} onClick={() => setTab("list")}>来源列表</button><button type="button" className={tab === "coverage" ? "ui-button-primary" : "ui-button-secondary"} onClick={() => setTab("coverage")}>覆盖分析</button></nav>
    {tab === "coverage" ? <Coverage /> : null}
    {tab === "list" && <><SectionHeader badge="Admin / Sources" title={en ? "Sources" : "数据源"} subtitle={en ? "Control connected collectors and review source health." : "启停已接入来源、查看采集健康状态。"} action={<button className="ui-button-secondary" onClick={() => void load()}><RefreshCw size={15} />{en ? "Refresh" : "刷新"}</button>} />
    {error && <div role="status" className="ui-card py-3 text-sm text-ink-secondary">{error}</div>}
    <form className="ui-card grid gap-3 sm:grid-cols-2 xl:grid-cols-4" onSubmit={create}>
      <h2 className="type-h3 sm:col-span-2 xl:col-span-4">{en ? "Add discovery source" : "新增发现数据源"}</h2>
      <label className="text-xs text-ink-muted">Source Key<input required pattern="[a-z0-9][a-z0-9_-]+" maxLength={64} className="ui-input mt-1 min-h-10 w-full px-3 font-mono text-sm" value={draft.source_key} onChange={e => setDraft(value => ({ ...value, source_key: e.target.value }))} /></label>
      <label className="text-xs text-ink-muted">{en ? "Name" : "名称"}<input required maxLength={200} className="ui-input mt-1 min-h-10 w-full px-3 text-sm" value={draft.name} onChange={e => setDraft(value => ({ ...value, name: e.target.value }))} /></label>
      <label className="text-xs text-ink-muted">{en ? "Adapter" : "采集适配器"}<select className="ui-input mt-1 min-h-10 w-full px-3 text-sm" value={draft.adapter} onChange={e => { setDraft(value => ({ ...value, adapter: e.target.value })); setPreview(null); }}>{["rss_feed", "api_json", "html_links", "product_hunt_feed", "hacker_news_api", "hugging_face_api", "arxiv_api", "github_search_api"].map(adapter => <option key={adapter}>{adapter}</option>)}</select></label>
      <label className="text-xs text-ink-muted">HTTPS URL<input required type="url" pattern="https://.*" className="ui-input mt-1 min-h-10 w-full px-3 text-sm" value={draft.base_url} onChange={e => { setDraft(value => ({ ...value, base_url: e.target.value })); setPreview(null); }} /></label>
      <label className="text-xs text-ink-muted">来源角色<select className="ui-input mt-1 min-h-10 w-full px-3 text-sm" value={draft.source_role} onChange={e => setDraft(value => ({ ...value, source_role: e.target.value }))}>{roles.map(role => <option key={role}>{role}</option>)}</select></label>
      <label className="text-xs text-ink-muted">语言<select className="ui-input mt-1 min-h-10 w-full px-3 text-sm" value={draft.language} onChange={e => setDraft(value => ({ ...value, language: e.target.value }))}><option value="zh">中文</option><option value="en">English</option></select></label>
      <label className="text-xs text-ink-muted">主题范围（逗号分隔，留空表示全部）<input className="ui-input mt-1 min-h-10 w-full px-3 text-sm" value={draft.topics.join(",")} onChange={e => setDraft(value => ({ ...value, topics: e.target.value.split(",").map(topic => topic.trim()).filter(Boolean) }))} /></label>
      <label className="text-xs text-ink-muted">{en ? "Authority" : "可信级别"}<select className="ui-input mt-1 min-h-10 w-full px-3 text-sm" value={draft.authority} onChange={e => setDraft(value => ({ ...value, authority: e.target.value }))}>{["P0", "P1", "P2"].map(level => <option key={level}>{level}</option>)}</select></label>
      <label className="text-xs text-ink-muted">{en ? "Priority" : "优先级"}<input type="number" min={0} max={1000} className="ui-input mt-1 min-h-10 w-full px-3 text-sm" value={draft.priority} onChange={e => setDraft(value => ({ ...value, priority: Number(e.target.value) }))} /></label>
      <label className="text-xs text-ink-muted">{en ? "Schedule" : "采集计划（分 时 日 月 周）"}<input required className="ui-input mt-1 min-h-10 w-full px-3 font-mono text-sm" value={draft.cron} onChange={e => setDraft(value => ({ ...value, cron: e.target.value }))} /></label>
      <fieldset className="sm:col-span-2"><legend className="text-xs text-ink-muted">{en ? "Business scopes" : "业务范围"}</legend><div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">{scopes.map(scope => <label key={scope} className="flex min-h-8 items-center gap-2 text-xs text-ink-secondary"><input type="checkbox" checked={draft.business_scopes.includes(scope)} onChange={e => setDraft(value => ({ ...value, business_scopes: e.target.checked ? [...value.business_scopes, scope] : value.business_scopes.filter(item => item !== scope) }))} />{en ? scope : scope.replaceAll("_", " ")}</label>)}</div></fieldset>
      <div className="flex items-end gap-2"><button type="button" className="ui-button-secondary" disabled={!draft.base_url || working === "preview"} onClick={() => void testDraft()}>测试抓取</button><button type="submit" className="ui-button-primary" disabled={working === "create" || draft.business_scopes.length === 0 || preview === null}>{en ? "Save source" : "确认并保存"}</button></div>
    </form>
    {preview && <section className="ui-card"><h2 className="type-h3">抓取预览</h2>{preview.map(item => <div key={item.url} className="border-b py-2 text-sm"><a href={item.url} target="_blank" rel="noopener noreferrer" className="text-primary underline">{item.title}</a><p className="text-xs text-ink-muted">{item.published_at || "发布时间未知"} · {item.language} · {item.url}</p><p className="line-clamp-2 text-xs">{item.summary}</p></div>)}</section>}
    <div className="flex flex-wrap gap-3"><select aria-label="按来源角色筛选" className="ui-input px-3" value={roleFilter} onChange={e => setRoleFilter(e.target.value)}><option value="">全部角色</option>{roles.map(role => <option key={role}>{role}</option>)}</select><select aria-label="按业务筛选" className="ui-input px-3" value={businessFilter} onChange={e => setBusinessFilter(e.target.value)}><option value="">全部业务</option>{scopes.filter(scope => scope !== "solutions").map(scope => <option key={scope} value={scope}>{scope}</option>)}</select></div>
    <section className="grid gap-3 lg:grid-cols-2">{sources.filter(source => (!domain || source.business_scopes.includes(domain)) && (!businessFilter || source.business_scopes.includes(businessFilter)) && (!roleFilter || source.source_role === roleFilter) && (!sourceKey || source.source_key === sourceKey)).map(source => <article key={source.source_key} className="ui-card">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><h2 className="font-semibold text-ink">{source.name}</h2><span className={"ui-tag " + (source.health_status === "HEALTHY" ? "ui-tag-success" : ["HTTP_ERROR", "PARSER_ERROR", "RATE_LIMITED", "AI_ERROR", "AI_PARTIAL", "STALE"].includes(source.health_status) ? "ui-tag-danger" : "")}>{source.health_status}</span></div><p className="mt-1 font-mono text-[11px] text-ink-muted">{source.source_key} · {source.adapter} · {source.source_role || "PLATFORM"} · {source.language || "zh"}</p></div><label className="flex min-h-11 items-center gap-2 text-sm text-ink-secondary"><input type="checkbox" checked={source.enabled} disabled={working === source.source_key || (typeof source.schedule.task_key !== "string" && !source.enabled)} onChange={() => void toggle(source)} />{en ? "Enabled" : "启用"}</label></div>
      <div className="mt-3 flex flex-wrap gap-2"><label className="text-xs text-ink-muted">来源角色<select className="ui-input ml-2 px-2" value={source.source_role || "PLATFORM"} onChange={e => setSources(items => items.map(item => item.source_key === source.source_key ? { ...item, source_role: e.target.value } : item))}>{roles.map(role => <option key={role}>{role}</option>)}</select></label><label className="text-xs text-ink-muted">语言<select className="ui-input ml-2 px-2" value={source.language || "zh"} onChange={e => setSources(items => items.map(item => item.source_key === source.source_key ? { ...item, language: e.target.value } : item))}><option value="zh">中文</option><option value="en">English</option></select></label></div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2"><div className="sm:col-span-2 grid grid-cols-2 gap-2 text-xs text-ink-muted"><span>最近运行：{source.last_run_at ? new Date(source.last_run_at).toLocaleString() : "—"}</span><span>最近新增：{source.last_new_count ?? "—"}</span><span>连续失败：{source.consecutive_failures ?? "—"}</span><span>成功率：{source.success_rate == null ? "—" : `${source.success_rate}%`}</span></div><label className="text-xs text-ink-muted">{en ? "Name" : "名称"}<input className="ui-input mt-1 min-h-10 w-full px-3 text-sm" value={source.name} onChange={e => setSources(items => items.map(item => item.source_key === source.source_key ? { ...item, name: e.target.value } : item))} /></label><label className="text-xs text-ink-muted">HTTPS URL<input type="url" pattern="https://.*" className="ui-input mt-1 min-h-10 w-full px-3 text-sm" value={source.base_url || ""} onChange={e => setSources(items => items.map(item => item.source_key === source.source_key ? { ...item, base_url: e.target.value } : item))} /></label><label className="text-xs text-ink-muted">{en ? "Authority" : "可信级别"}<select className="ui-input mt-1 min-h-10 w-full px-3 text-sm" value={source.authority} onChange={e => setSources(items => items.map(item => item.source_key === source.source_key ? { ...item, authority: e.target.value } : item))}>{["P0", "P1", "P2"].map(level => <option key={level}>{level}</option>)}</select></label><label className="text-xs text-ink-muted">{en ? "Priority" : "优先级"}<input type="number" min={0} max={1000} className="ui-input mt-1 min-h-10 w-full px-3 text-sm" value={source.priority} onChange={e => setSources(items => items.map(item => item.source_key === source.source_key ? { ...item, priority: Number(e.target.value) } : item))} /></label><fieldset className="sm:col-span-2"><legend className="text-xs text-ink-muted">{en ? "Business scopes" : "业务范围"}</legend><div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">{scopes.map(scope => <label key={scope} className="flex min-h-8 items-center gap-2 text-xs text-ink-secondary"><input type="checkbox" checked={source.business_scopes.includes(scope)} onChange={e => setSources(items => items.map(item => item.source_key === source.source_key ? { ...item, business_scopes: e.target.checked ? [...item.business_scopes, scope] : item.business_scopes.filter(value => value !== scope) } : item))} />{en ? scope : scope.replaceAll("_", " ")}</label>)}</div></fieldset><div className="flex flex-wrap items-end gap-2 sm:col-span-2"><label className="min-w-48 flex-1 text-xs text-ink-muted">{en ? "Collector schedule (min hour day month weekday)" : "采集计划（分 时 日 月 周）"}<input aria-label={en ? "Collector schedule" : "采集计划"} className="ui-input mt-1 min-h-10 w-full px-3 font-mono text-sm" placeholder="30 8 * * *" value={String(source.schedule.cron || "")} onChange={e => setSources(items => items.map(item => item.source_key === source.source_key ? { ...item, schedule: { ...item.schedule, cron: e.target.value } } : item))} /></label><button type="button" className="ui-button-secondary" disabled={working === source.source_key || !source.schedule.task_key || !String(source.schedule.cron || "")} onClick={() => void saveSchedule(source)}>{en ? "Save schedule" : "保存计划"}</button><button type="button" className="ui-button-secondary" disabled={working === source.source_key || !source.business_scopes.length} onClick={() => void save(source)}>{en ? "Save settings" : "保存配置"}</button><p className="w-full text-[11px] text-ink-muted">{en ? "Sources sharing a collector task use the same schedule." : "共用采集任务的数据源会同步使用此计划。"}</p></div><div className="text-xs text-ink-muted"><span>{en ? "Last success" : "最近成功"}：</span>{source.last_success_at ? new Date(source.last_success_at).toLocaleString() : "—"}</div></div>
      {source.last_error && <p className="mt-3 rounded-lg bg-danger/5 px-3 py-2 text-xs text-danger">{source.last_error}</p>}
      <div className="mt-4 flex flex-wrap justify-end gap-2"><Link href={`/admin/tasks?domain=${source.business_scopes[0] || ""}`} className="ui-button-secondary">查看任务 / Pipeline</Link><Link href={`/admin/operations?tab=0&domain=${source.business_scopes[0] || ""}`} className="ui-button-secondary">查看候选</Link><button type="button" className="ui-button-secondary" disabled={working === source.source_key || !source.base_url} onClick={() => void testConnection(source)}><Wifi size={14} />{en ? "Test connection" : "测试连接"}</button><button type="button" className="ui-button-secondary" disabled={working === source.source_key || !source.enabled || typeof source.schedule.task_key !== "string"} onClick={() => void run(source)}><Play size={14} />{en ? "Run now" : "立即采集"}</button></div>
    </article>)}</section></>}
  </div>;
}
