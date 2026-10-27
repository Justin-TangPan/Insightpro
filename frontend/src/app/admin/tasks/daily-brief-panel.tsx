"use client";

import { useCallback, useEffect, useState } from "react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

type BriefItem = { title: string; summary: string; commentary: string; source_name: string; source_url: string };
type BriefVersion = {
  brief_date: string; version: number; status: string; generated_at: string; task_run_id: number | null;
  candidate_count: number; selected_count: number; email_status: string; email_error: string | null;
  email_sent_at: string | null; email_recipient_count: number; email_failed_count: number;
  email_template_version: string | null; trigger: string | null; started_at: string | null;
  finished_at: string | null; task_error: string | null;
  payload: { recent_judgments: { title: string; detail: string }[]; headline: BriefItem | null;
    quick_reads: BriefItem[]; candidate_sources?: { title: string; source_name: string; source_url: string }[]; error?: string };
};

const when = (value: string | null) => value ? new Date(value).toLocaleString("zh-CN", { timeZone: "Asia/Shanghai" }) : "—";

export default function DailyBriefPanel({ enabled, onUpdated }: { enabled: boolean; onUpdated: () => void }) {
  const [versions, setVersions] = useState<BriefVersion[]>([]);
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    const response = await authenticatedFetch(`${API}/api/admin/daily-ai-brief/versions`);
    if (!response.ok) throw new Error("简讯历史加载失败");
    setVersions((await response.json()).items || []);
  }, []);
  useEffect(() => { void load().catch(cause => setError(String(cause))); }, [load]);

  const action = async (name: string, path: string, method = "POST", body?: object) => {
    setBusy(name); setError(""); setMessage("");
    try {
      const response = await authenticatedFetch(`${API}${path}`, { method, ...(body ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}) });
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || `${name}失败`);
      setMessage(`${name}已提交，稍后刷新查看执行结果。`);
      await load(); onUpdated();
    } catch (cause) { setError(cause instanceof Error ? cause.message : `${name}失败`); }
    finally { setBusy(""); }
  };
  const detail = versions.find(item => `${item.brief_date}:${item.version}` === selected) || versions[0];
  const latest = versions[0];
  const button = (label: string, path: string, method = "POST", body?: object) =>
    <button type="button" className="ui-button-secondary min-h-11" disabled={!!busy} onClick={() => void action(label, path, method, body)}>{label}</button>;

  return <section className="ui-card" aria-labelledby="daily-brief-admin-title">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><h2 id="daily-brief-admin-title" className="type-h3 text-ink">每日 AI 洞察简讯</h2><p className="mt-1 text-sm text-ink-muted">AI 情报生成任务 · 生成一次，首页、AI 应用与商业邮件共用同一版本</p></div>
      <div className="flex flex-wrap gap-2">
        {button("立即执行", "/api/admin/tasks/daily_ai_brief/run")}
        {button("重新生成", "/api/daily-ai-brief/regenerate")}
        {button("重试商业邮件", "/api/admin/daily-ai-brief/retry-email")}
        {button(enabled ? "停用定时" : "启用定时", "/api/admin/tasks/daily_ai_brief/schedule", "PATCH", { enabled: !enabled })}
        <button type="button" className="ui-button-secondary min-h-11" onClick={() => void load().catch(cause => setError(String(cause)))}>刷新</button>
      </div>
    </div>
    {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
    {message && <p role="status" className="mt-3 text-sm text-primary">{message}</p>}
    <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(15rem,.7fr)_minmax(0,1.3fr)]">
      <div className="min-w-0"><h3 className="text-sm font-semibold text-ink">历史版本</h3><div className="mt-2 max-h-96 overflow-y-auto rounded-xl border border-grid">
        {versions.map(item => <button type="button" key={`${item.brief_date}:${item.version}`} onClick={() => setSelected(`${item.brief_date}:${item.version}`)} className={`block w-full border-b border-grid px-3 py-3 text-left text-sm last:border-0 hover:bg-primary/5 focus-visible:outline-2 focus-visible:outline-primary ${detail === item ? "bg-primary/5" : ""}`}>
          <span className="block font-semibold text-ink">{item.brief_date} · V{item.version}</span>
          <span className="mt-1 block text-xs text-ink-muted">{item.status} · {when(item.generated_at)} · 邮件{item.email_status}</span>
        </button>)}
        {!versions.length && <p className="p-4 text-sm text-ink-muted">暂无历史版本</p>}
      </div></div>
      {detail && <div className="min-w-0 rounded-xl border border-grid bg-surface p-4 text-sm text-ink-secondary">
        <h3 className="font-semibold text-ink">{detail.brief_date} · V{detail.version} {detail === latest ? "（最新版本）" : ""}</h3>
        <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
          <div>任务：{detail.task_run_id ? `#${detail.task_run_id}` : "历史生成"} · {detail.trigger || "—"}</div><div>执行：{when(detail.started_at)} → {when(detail.finished_at)}</div>
          <div>候选 {detail.candidate_count} · 入选 {detail.selected_count}</div><div>判断 {detail.payload.recent_judgments?.length || 0} · 头条 {detail.payload.headline ? 1 : 0} · 快读 {detail.payload.quick_reads?.length || 0}</div>
          <div>邮件：{detail.email_status} · 成功 {detail.email_recipient_count} · 失败 {detail.email_failed_count}</div><div>发送时间：{when(detail.email_sent_at)}</div>
          <div>邮件模板：{detail.email_template_version || "—"}</div><div>生成时间：{when(detail.generated_at)}</div>
        </dl>
        {(detail.task_error || detail.email_error || detail.payload.error) && <p role="alert" className="mt-3 rounded-lg bg-danger/5 p-3 text-danger">{detail.task_error || detail.email_error || detail.payload.error}</p>}
        <div className="mt-4 space-y-4">
          <div><h4 className="font-semibold text-ink">近日判断</h4>{detail.payload.recent_judgments?.map(item => <p key={item.title} className="mt-2"><strong>{item.title}</strong><br />{item.detail}</p>)}</div>
          <div><h4 className="font-semibold text-ink">头条详解</h4>{detail.payload.headline ? <p className="mt-2"><strong>{detail.payload.headline.title}</strong><br />摘要：{detail.payload.headline.summary}<br />点评：{detail.payload.headline.commentary}<br /><a className="text-primary underline" href={detail.payload.headline.source_url} target="_blank" rel="noopener noreferrer">{detail.payload.headline.source_name} · 查看原文</a></p> : <p className="mt-2 text-ink-muted">无高价值头条</p>}</div>
          <div><h4 className="font-semibold text-ink">今日快读</h4>{detail.payload.quick_reads?.map(item => <p key={item.source_url} className="mt-2"><strong>{item.title}</strong><br />摘要：{item.summary}<br />点评：{item.commentary}<br /><a className="text-primary underline" href={item.source_url} target="_blank" rel="noopener noreferrer">{item.source_name} · 查看原文</a></p>)}</div>
          <details><summary className="cursor-pointer font-semibold text-ink">候选情报来源（{detail.payload.candidate_sources?.length || 0}）</summary><ul className="mt-2 space-y-1">{detail.payload.candidate_sources?.map(item => <li key={item.source_url}><a className="text-primary underline" href={item.source_url} target="_blank" rel="noopener noreferrer">{item.title} · {item.source_name}</a></li>)}</ul></details>
        </div>
      </div>}
    </div>
  </section>;
}
