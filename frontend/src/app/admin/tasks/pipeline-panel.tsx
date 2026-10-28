"use client";
import { ExportButtons } from "../export-buttons";

import { useCallback, useEffect, useState } from "react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

const domains = [
  ["technology_ecosystem", "技术生态"], ["ai_applications", "AI 应用"], ["solutions", "解决方案"],
  ["community_insights", "社区洞察"], ["competitor_dynamics", "友商动态"],
] as const;
type Step = { key: string; stage: string; status: string; result?: Record<string, unknown>; error?: string; output_count?: number | null; failed_count?: number; duration_ms?: number };
type Run = { id: number; task_key: string; status: string; started_at: string; finished_at?: string; result?: { domain: string; steps: Step[] }; error?: string };

export default function PipelinePanel({ initialDomain }: { initialDomain: string }) {
  const [domain, setDomain] = useState(domains.some(item => item[0] === initialDomain) ? initialDomain : "ai_applications");
  const [runs, setRuns] = useState<Run[]>([]);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try {
      const response = await authenticatedFetch(API + "/api/admin/pipelines");
      if (!response.ok) throw new Error("Pipeline 状态加载失败");
      setRuns((await response.json()).items || []);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Pipeline 状态加载失败"); }
  }, []);
  useEffect(() => { void Promise.resolve().then(load); const timer = window.setInterval(() => { if (document.visibilityState === "visible") void load(); }, 5000); return () => window.clearInterval(timer); }, [load]);
  useEffect(() => { if (domains.some(item => item[0] === initialDomain)) void Promise.resolve().then(() => setDomain(initialDomain)); }, [initialDomain]);
  const latest = runs.find(run => run.task_key === `pipeline:${domain}`);
  const active = latest?.status === "running";
  const execute = async (resume = false) => {
    if (!window.confirm(resume ? "从失败节点继续执行？" : `确认一键执行${domains.find(item => item[0] === domain)?.[1]}采集与分析链路？`)) return;
    setWorking(true); setError("");
    try {
      const path = `/api/admin/pipelines/${domain}/run${resume ? `?resume_from=${latest?.id}` : ""}`;
      const response = await authenticatedFetch(API + path, { method: "POST" });
      if (!response.ok) { const body = await response.json(); throw new Error(body.detail || "Pipeline 启动失败"); }
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Pipeline 启动失败"); }
    finally { setWorking(false); }
  };
  return <section className="ui-card"><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs font-semibold text-primary">PIPELINE</p><h2 className="mt-1 text-lg font-semibold text-ink">任务执行流</h2><p className="mt-1 text-xs text-ink-muted">调用现有采集、发现、AI 分析与板块刷新任务；每步结果来自实际执行记录。</p></div><div className="flex flex-wrap items-end gap-2"><label className="text-xs text-ink-muted">所属业务<select value={domain} onChange={event => setDomain(event.target.value)} className="ui-input mt-1 min-h-11 px-3 text-sm">{domains.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><button type="button" className="ui-button-primary" disabled={working || active} onClick={() => void execute(false)}>{active ? "执行中…" : "一键执行"}</button>{latest?.status === "failed" && <button type="button" className="ui-button-secondary" disabled={working} onClick={() => void execute(true)}>从失败节点继续</button>}</div></div>
    <div className="mt-3"><ExportButtons dataset="pipeline_run" filters={{ business_scope: domain }} /></div>
    {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
    {latest && <p className="mt-4 text-xs text-ink-muted">运行 #{latest.id} · {new Date(latest.started_at).toLocaleString("zh-CN")} · {latest.status === "running" ? "执行中" : latest.status === "success" ? "已完成" : "失败"}</p>}
    <ol className="mt-4 grid gap-2 lg:grid-cols-4">{(latest?.result?.steps || []).map((step, index) => <li key={step.key} className="rounded-xl border border-grid bg-surface p-3"><span className="text-xs text-ink-muted">{index + 1} · {step.stage}</span><h3 className="mt-1 text-sm font-semibold text-ink">{step.key}</h3><p className={step.status === "failed" ? "mt-2 text-xs text-danger" : "mt-2 text-xs text-primary"}>{step.status === "success" ? "完成" : step.status === "running" ? "执行中" : step.status === "failed" ? "失败" : "等待"}</p><dl className="mt-2 grid grid-cols-2 gap-1 text-xs text-ink-muted"><div><dt>输入</dt><dd>未记录</dd></div><div><dt>输出</dt><dd>{step.output_count ?? "未记录"}</dd></div><div><dt>过滤</dt><dd>未记录</dd></div><div><dt>失败</dt><dd>{step.failed_count ?? "—"}</dd></div><div><dt>耗时</dt><dd>{step.duration_ms == null ? "—" : `${(step.duration_ms / 1000).toFixed(1)} 秒`}</dd></div></dl>{step.error && <p className="mt-2 break-words text-xs text-danger">{step.error}</p>}{step.result && <details className="mt-2 text-xs text-ink-secondary"><summary className="cursor-pointer">查看输入输出结果</summary><pre className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap break-all">{JSON.stringify(step.result, null, 2)}</pre></details>}</li>)}</ol>
    {!latest && <p className="mt-4 text-sm text-ink-muted">该业务还没有手动 Pipeline 运行记录。</p>}
  </section>;
}
