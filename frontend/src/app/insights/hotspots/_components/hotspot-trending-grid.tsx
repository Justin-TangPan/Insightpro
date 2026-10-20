"use client";

import { HotspotTrendingCard } from "./hotspot-trending-card";
import type { TrendingItem, EvalItem } from "./hotspot-types";
import { usePreferences } from "@/lib/preferences";

interface HotspotTrendingGridProps {
  loading: boolean;
  displayData: TrendingItem[];
  displayEvaluations: EvalItem[];
  savingRepo: string;
  savedRepos: Set<string>;
  onSave: (item: TrendingItem) => void;
}

export function HotspotTrendingGrid({
  loading,
  displayData,
  displayEvaluations,
  savingRepo,
  savedRepos,
  onSave,
}: HotspotTrendingGridProps) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="ui-card animate-shimmer">
            <div className="h-5 w-2/3 bg-surface-subtle rounded mb-3" />
            <div className="h-4 w-full bg-surface-subtle rounded mb-2" />
            <div className="h-4 w-3/4 bg-surface-subtle rounded mb-4" />
            <div className="flex gap-3">
              <div className="h-5 w-14 bg-surface-subtle rounded-full" />
              <div className="h-5 w-14 bg-surface-subtle rounded-full" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (displayData.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-lg font-serif font-bold text-ink-muted">{en ? "No data" : "暂无数据"}</p>
        <p className="text-sm text-ink-muted mt-1">
          {en ? "Use Refresh above to get the latest data" : "点击上方手动刷新获取最新数据"}
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {displayData.map((item, i) => (
        <HotspotTrendingCard
          key={item.repo_url || i}
          item={item}
          index={i}
          evaluation={displayEvaluations.find((ev) => ev.repo_name === item.repo_name)}
          savingRepo={savingRepo}
          savedRepos={savedRepos}
          onSave={onSave}
        />
      ))}
    </div>
  );
}
