"use client";

import Link from "next/link";
import { parseEvaluationSections } from "@/lib/evaluation-sections";
import { plainIntelligenceText } from "@/lib/intelligence";
import { usePreferences } from "@/lib/preferences";
import { evalDimensions, levelClass, type EvalItem } from "./hotspot-types";

interface Props { ev: EvalItem; entityKey?: string }

export function HotspotEvaluationCard({ ev, entityKey }: Props) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const analysis = plainIntelligenceText(ev.intelligence?.analysis || ev.reasoning || "");
  const sections = parseEvaluationSections(analysis);
  const risk = sections.find(section => /风险|risk|挑战|challenge/i.test(section.label))?.content;
  const brief = ev.intelligence?.brief || ev.summary || sections.find(section => /价值|value|结论|summary/i.test(section.label))?.content;
  const pending = ev.evaluation_mode === "heuristic";
  return <article className="ecosystem-card evaluation-card">
    <div className="evaluation-card-head"><div className="min-w-0"><h3>{ev.repo_name}</h3><span>{ev.language || (en ? "Stack not reported" : "技术栈未标注")}</span></div><span className={`evaluation-status ${levelClass(ev.level)}`}>{ev.level}</span></div>
    <div className="evaluation-score"><div><span>{en ? "Overall score" : "综合评分"}</span><strong>{pending ? "—" : Number.isFinite(Number(ev.total)) ? Number(ev.total).toFixed(1) : "—"}<small> / 10</small></strong></div>{pending && <span className="evaluation-pending">{en ? "Rule estimate · AI pending" : "规则估算 · 待 AI 评估"}</span>}</div>
    <div className="evaluation-dimensions">{evalDimensions.map(d => { const value = Number(ev[d.key]); return <div key={d.key}><div><span>{en ? d.en : d.label}</span><strong>{pending || !Number.isFinite(value) ? "—" : value.toFixed(1)}</strong></div><div className="dimension-track"><span style={{ width: `${pending || !Number.isFinite(value) ? 0 : Math.max(0, Math.min(100, value * 10))}%` }} /></div></div>; })}</div>
    <div className="evaluation-conclusions"><p><b>{en ? "Value" : "核心价值"}</b><span>{brief || (en ? "No conclusion yet" : "暂无价值结论")}</span></p><p><b>{en ? "Risk" : "主要风险"}</b><span>{risk || (en ? "Not stated in assessment" : "评估中未明确标注")}</span></p><p><b>{en ? "Next" : "建议"}</b><span>{ev.recommendation || (en ? "No recommendation yet" : "暂无明确建议")}</span></p></div>
    {entityKey ? <Link className="evaluation-detail" href={`/repositories/${encodeURIComponent(entityKey)}`}>{en ? "View detailed assessment →" : "查看详细评估 →"}</Link> : <details className="evaluation-detail"><summary>{en ? "View detailed assessment" : "查看详细评估"}</summary><p>{analysis || (en ? "No detailed assessment yet" : "暂无详细分析")}</p></details>}
  </article>;
}
