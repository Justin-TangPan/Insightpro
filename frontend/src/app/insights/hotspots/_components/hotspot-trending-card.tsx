"use client";

import { Bookmark, Check, GitFork, Star, TrendingUp } from "lucide-react";
import { usePreferences } from "@/lib/preferences";
import { historySeries, metric, projectTags, sparkline } from "./ecosystem-data";
import type { HistoryEntry, TrendingItem } from "./hotspot-types";

interface Props {
  item: TrendingItem;
  index: number;
  history: HistoryEntry[];
  savingRepo: string;
  savedRepos: Set<string>;
  onSave: (item: TrendingItem) => void;
}

export function HotspotTrendingCard({ item, index, history, savingRepo, savedRepos, onSave }: Props) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const name = item.repo_name.split("/").at(-1) || item.repo_name;
  const series = historySeries(history, entry => entry.repo_name === item.repo_name);
  const points = sparkline(series);
  return <article className="ecosystem-card project-card">
    <div className="project-card-head"><span className="rank-badge">{index + 1}</span><span className="project-mark">{name.slice(0, 2).toUpperCase()}</span><div className="min-w-0"><h3 title={item.repo_name}>{name}</h3><span title={item.repo_name}>{item.repo_name}</span></div></div>
    <p className="project-description">{item.description || (en ? "No project description available" : "暂无项目简介")}</p>
    <div className="project-tags">{projectTags(item, en).map(tag => <span key={tag}>{tag}</span>)}</div>
    <div className="project-trend" aria-label={points ? (en ? `Observed growth across ${series.length} days` : `近 ${series.length} 次采集增长趋势`) : (en ? "History unavailable" : "暂无历史趋势")}>
      {points ? <svg viewBox="0 0 100 34" preserveAspectRatio="none" aria-hidden="true"><polyline points={points} /></svg> : <span>{en ? "History unavailable" : "暂无历史趋势"}</span>}
    </div>
    <div className="project-stats"><span><Star size={13} />{metric(item.stars).toLocaleString()}</span><span><GitFork size={13} />{metric(item.forks).toLocaleString()}</span><strong><TrendingUp size={13} />+{metric(item.today_stars).toLocaleString()}</strong></div>
    <div className="project-actions"><a href={item.repo_url} target="_blank" rel="noopener noreferrer">{en ? "View project" : "查看项目"}</a><button type="button" onClick={() => onSave(item)} disabled={savingRepo === item.repo_url || savedRepos.has(item.repo_url)} title={en ? "Save as a solution practice for follow-up" : "收纳为方案实践，便于后续跟踪"} aria-label={en ? `Follow ${item.repo_name} by saving as a solution practice` : `关注 ${item.repo_name} 并收纳为方案实践`}><Bookmark size={14} />{savedRepos.has(item.repo_url) ? (en ? "Saved" : "已关注") : savingRepo === item.repo_url ? (en ? "Saving" : "保存中") : (en ? "Follow" : "关注")}{savedRepos.has(item.repo_url) && <Check size={12} />}</button></div>
  </article>;
}
