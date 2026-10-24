"use client";

import { HotspotTrendingCard } from "./hotspot-trending-card";
import type { TrendingItem, HistoryEntry } from "./hotspot-types";
import { usePreferences } from "@/lib/preferences";

interface Props {
  loading: boolean;
  displayData: TrendingItem[];
  history: HistoryEntry[];
  savingRepo: string;
  savedRepos: Set<string>;
  onSave: (item: TrendingItem) => void;
}

export function HotspotTrendingGrid({ loading, displayData, history, savingRepo, savedRepos, onSave }: Props) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  if (loading) return <div className="project-grid" aria-label={en ? "Loading projects" : "正在加载项目"}>{Array.from({ length: 4 }, (_, i) => <div key={i} className="ecosystem-card project-card animate-pulse" />)}</div>;
  if (!displayData.length) return <div className="ecosystem-empty">{en ? "No projects found for this filter" : "当前筛选条件下暂无项目"}</div>;
  return <div className="project-grid">{displayData.slice(0, 4).map((item, index) => <HotspotTrendingCard key={item.repo_url || index} item={item} index={index} history={history} savingRepo={savingRepo} savedRepos={savedRepos} onSave={onSave} />)}</div>;
}
