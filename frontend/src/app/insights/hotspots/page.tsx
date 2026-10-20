"use client";

import { SectionHeader } from "@/components/section-header";
import { Clock, ArrowUpRight } from "lucide-react";
import { HotspotTrendingGrid } from "./_components/hotspot-trending-grid";
import { HotspotEvaluationPanel } from "./_components/hotspot-evaluation-panel";
import {
  HotspotHistoryPanel,
  HistoryDateIndicator,
} from "./_components/hotspot-history-panel";
import { HotspotFilters } from "./_components/hotspot-filters";
import { useHotspotData } from "./_components/use-hotspot-data";
import { usePreferences } from "@/lib/preferences";

export default function HotspotsPage() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const {
    period, source, date, loading, refreshing,
    showHistory, historyLoading, historyDate,
    evalLoading, evalRefreshing, evalError,
    savingRepo, savedRepos, saveError,
    displayData, displayEvaluations, displayEvalSummary,
    history,
    setPeriod, setHistoryDate, setShowHistory,
    handleRefresh, handleEvalRefresh, savePractice,
  } = useHotspotData();

  return (
    <div className="page-stack">
      <SectionHeader
        badge="GitHub"
        title="GitHub"
        subtitle={en ? "Discover trending GitHub projects, with source-backed analysis" : "发现 GitHub 热门项目，结合来源分析价值"}
        image="https://images.unsplash.com/photo-1618401471353-b98afee0b2eb?w=1200&q=80"
        action={
          <div className="flex items-center gap-2 text-xs text-ink-muted">
            <Clock className="h-3.5 w-3.5" />
            <span>{en ? "Auto update: daily at 08:30" : "自动更新：每天 08:30"}</span>
            <span className="mx-1">·</span>
            <span>{source === "live" ? (en ? "Live" : "实时抓取") : source === "database" ? (en ? "Stored" : "本地存储") : (en ? "No data" : "暂无数据")}</span>
          </div>
        }
      />

      <HotspotFilters
        period={period}
        onPeriodChange={(p) => { setPeriod(p); setHistoryDate(""); }}
        showHistory={showHistory}
        onToggleHistory={() => setShowHistory(!showHistory)}
        refreshing={refreshing}
        onRefresh={handleRefresh}
      />

      {showHistory && (
        <HotspotHistoryPanel history={history} historyLoading={historyLoading} historyDate={historyDate} onDateSelect={setHistoryDate} />
      )}

      <HistoryDateIndicator historyDate={historyDate} />

      {saveError && <div role="alert" className="rounded-xl bg-warning-soft px-4 py-3 text-sm text-warning">{saveError}</div>}

      <HotspotTrendingGrid
        loading={loading} displayData={displayData} displayEvaluations={displayEvaluations}
        savingRepo={savingRepo} savedRepos={savedRepos} onSave={savePractice}
      />

      {period === "daily" && (
        <HotspotEvaluationPanel
          historyDate={historyDate} evalLoading={evalLoading} evalRefreshing={evalRefreshing} evalError={evalError}
          displayEvaluations={displayEvaluations} displayEvalSummary={displayEvalSummary}
          onEvalRefresh={handleEvalRefresh}
        />
      )}

      <div className="flex items-center justify-between rounded-xl bg-surface-subtle px-5 py-3.5 text-xs text-ink-muted">
        <span>{en ? `Showing ${displayData.length} projects` : `当前显示 ${displayData.length} 个项目`}</span>
        <div className="flex items-center gap-4">
          <span>{en ? "Updated:" : "数据更新时间："} {date || "—"}</span>
          <a href="https://github.com/trending" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-primary hover:underline font-medium">
            {en ? "GitHub Trending" : "GitHub 官方 Trending"} <ArrowUpRight className="h-3 w-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
