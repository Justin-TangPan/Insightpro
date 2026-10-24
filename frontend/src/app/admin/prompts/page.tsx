"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { usePreferences } from "@/lib/preferences";

type Prompt = { id: number; prompt_name: string; scenario: string; version: number; status: "draft" | "published" | "archived"; system_prompt: string; user_prompt_template: string; created_at: string; published_at?: string };
export default function AdminPromptsPage() {
  const { user, loading } = useAuth();
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [items, setItems] = useState<Prompt[]>([]);
  const [name, setName] = useState("daily_board_github");
  const [scenario, setScenario] = useState("business_board");
  const [system, setSystem] = useState("");
  const [template, setTemplate] = useState("");
  const [error, setError] = useState("");
  const [working, setWorking] = useState(0);
  const load = useCallback(async () => {
    const response = await authenticatedFetch(API + "/api/v2/admin/prompts");
    if (!response.ok) throw new Error(en ? "Prompt versions unavailable." : "Prompt 版本加载失败。");
    setItems((await response.json()).items || []);
  }, [en]);
  useEffect(() => { if (user?.app_metadata?.role === "admin") void Promise.resolve().then(() => load().catch(cause => setError(cause.message))); }, [load, user]);
  const save = async () => {
    setWorking(-1);
    try {
      const response = await authenticatedFetch(API + "/api/v2/admin/prompts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prompt_name: name, scenario, system_prompt: system, user_prompt_template: template }) });
      if (!response.ok) throw new Error((await response.text()).slice(0, 300));
      setSystem(""); setTemplate(""); await load();
      setError(en ? "Draft version created." : "草稿版本已创建。");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Error"); }
    finally { setWorking(0); }
  };
  const transition = async (item: Prompt, action: "publish" | "rollback") => {
    setWorking(item.id);
    try {
      const response = await authenticatedFetch(API + "/api/v2/admin/prompts/" + item.id + "/" + action, { method: "POST" });
      if (!response.ok) throw new Error((await response.text()).slice(0, 300));
      await load();
      setError(action === "publish" ? (en ? "Prompt published." : "Prompt 已发布。")
        : (en ? "Prompt rolled back." : "Prompt 已回滚。"));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Error"); }
    finally { setWorking(0); }
  };
  if (loading) return <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "Checking access…" : "正在验证权限…"}</div>;
  if (user?.app_metadata?.role !== "admin") return <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "Administrator access required." : "需要管理员权限。"}</div>;
  return <div className="page-stack">
    <SectionHeader badge="Admin / Prompts" title={en ? "Prompt versions" : "Prompt 版本"} subtitle={en ? "Create drafts, publish a version and roll back while keeping its history." : "创建草稿、发布指定版本或回滚；每次分析保存使用的 Prompt 版本。"} />
    {error && <div role="status" className="ui-card py-3 text-sm text-ink-secondary">{error}</div>}
    <section className="ui-card"><h2 className="type-h3">{en ? "New draft" : "创建草稿版本"}</h2><div className="mt-4 grid gap-3 sm:grid-cols-2"><label className="text-xs text-ink-muted">Prompt name<input className="ui-input mt-1 min-h-10 w-full px-3 text-sm" value={name} onChange={e => setName(e.target.value)} /></label><label className="text-xs text-ink-muted">{en ? "Scenario" : "使用场景"}<input className="ui-input mt-1 min-h-10 w-full px-3 text-sm" value={scenario} onChange={e => setScenario(e.target.value)} /></label></div><label className="mt-3 block text-xs text-ink-muted">System Prompt<textarea className="ui-input mt-1 min-h-36 w-full p-3 text-sm" value={system} onChange={e => setSystem(e.target.value)} maxLength={20000} /></label><label className="mt-3 block text-xs text-ink-muted">User template<textarea className="ui-input mt-1 min-h-24 w-full p-3 text-sm" value={template} onChange={e => setTemplate(e.target.value)} maxLength={20000} /></label><div className="mt-3 flex justify-end"><button type="button" disabled={working !== 0 || name.length < 3 || scenario.length < 3 || system.length < 20} className="ui-button-primary" onClick={() => void save()}>{en ? "Save draft" : "保存草稿"}</button></div></section>
    <section className="space-y-3">{items.map(item => <article key={item.id} className="ui-card"><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-semibold text-ink">{item.prompt_name} · v{item.version}</h3><p className="mt-1 text-xs text-ink-muted">{item.scenario} · {item.status} · {new Date(item.created_at).toLocaleString()}</p></div><span className={"ui-tag " + (item.status === "published" ? "ui-tag-success" : "")}>{item.status}</span></div><details className="mt-3"><summary className="cursor-pointer text-xs text-primary">{en ? "View prompt" : "查看 Prompt"}</summary><pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-surface-subtle p-3 text-xs text-ink-secondary">{item.system_prompt}{item.user_prompt_template ? "\n\n" + item.user_prompt_template : ""}</pre></details>{item.status !== "published" && <div className="mt-3 flex justify-end"><button type="button" disabled={working !== 0} className="ui-button-secondary" onClick={() => void transition(item, item.status === "draft" ? "publish" : "rollback")}>{item.status === "draft" ? (en ? "Publish" : "发布") : (en ? "Rollback to this version" : "回滚到此版本")}</button></div>}</article>)}</section>
    {!items.length && <div className="ui-card py-10 text-center text-sm text-ink-muted">{en ? "No prompt versions yet." : "暂无 Prompt 版本记录。"}</div>}
  </div>;
}
