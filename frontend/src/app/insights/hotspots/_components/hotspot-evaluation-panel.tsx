"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { HotspotEvaluationCard } from "./hotspot-evaluation-card";
import type { EvalItem, TrendingItem } from "./hotspot-types";
import { usePreferences } from "@/lib/preferences";

interface Props { historyDate: string; evalLoading: boolean; evalRefreshing: boolean; evalError: string; displayEvaluations: EvalItem[]; displayData: TrendingItem[]; onEvalRefresh: () => Promise<void> }
const filters = [
  { key: "all", label: "全部项目", en: "All projects", match: () => true },
  { key: "high", label: "高潜力项目", en: "High potential", match: (level: string) => /强烈推荐|Strongly Recommended/.test(level) },
  { key: "watch", label: "值得关注", en: "Worth watching", match: (level: string) => /值得做|Worth Doing|勉强|Marginal/.test(level) },
  { key: "no", label: "不建议", en: "Not recommended", match: (level: string) => /不建议|Not Recommended/.test(level) },
];

export function HotspotEvaluationPanel({ historyDate, evalLoading, evalRefreshing, evalError, displayEvaluations, displayData, onEvalRefresh }: Props) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [filter, setFilter] = useState("all");
  const [expanded, setExpanded] = useState(false);
  const selected = filters.find(item => item.key === filter) || filters[0];
  const matching = displayEvaluations.filter(item => selected.match(item.level));
  const visible = expanded ? matching : matching.slice(0, 3);
  return <section id="ecosystem-evaluation" className="ecosystem-section">
    <div className="ecosystem-section-head"><div><h2>{en ? "AI solution value assessment" : "AI 解决方案价值评估"}</h2><p>{historyDate ? `${historyDate} ${en ? "historical assessments" : "历史评估"}` : en ? "Existing project evaluations, condensed for quick comparison" : "复用现有评估结果，快速比较项目落地价值"}</p></div>{!historyDate && <button type="button" className="ecosystem-text-button" onClick={() => void onEvalRefresh()} disabled={evalRefreshing}><RefreshCw size={15} className={evalRefreshing ? "animate-spin" : ""} />{evalRefreshing ? (en ? "Evaluating" : "评估中") : (en ? "Re-evaluate" : "重新评估")}</button>}</div>
    <div className="ecosystem-tabs" role="group" aria-label={en ? "Evaluation filter" : "评估筛选"}>{filters.map(item => <button type="button" key={item.key} aria-pressed={filter === item.key} onClick={() => { setFilter(item.key); setExpanded(false); }}>{en ? item.en : item.label}<span>{displayEvaluations.filter(ev => item.match(ev.level)).length}</span></button>)}</div>
    {evalError && <p role="alert" className="ecosystem-alert">{evalError}</p>}
    {evalLoading ? <div className="evaluation-grid">{[0,1,2].map(i => <div key={i} className="ecosystem-card evaluation-card animate-pulse" />)}</div> : visible.length ? <><div className="evaluation-grid">{visible.map(ev => <HotspotEvaluationCard key={ev.repo_name} ev={ev} entityKey={displayData.find(item => item.repo_name === ev.repo_name)?.entity_key} />)}</div>{matching.length > 3 && <button type="button" className="ecosystem-more" onClick={() => setExpanded(!expanded)}>{expanded ? (en ? "Show fewer" : "收起") : (en ? `View all ${matching.length} assessments` : `查看全部 ${matching.length} 项评估`)}</button>}</> : <div className="ecosystem-empty">{en ? "No evaluations in this category" : "该分类暂无评估结果"}</div>}
  </section>;
}
