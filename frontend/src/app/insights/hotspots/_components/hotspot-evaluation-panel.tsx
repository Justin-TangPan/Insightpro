"use client";

import { RefreshCw, Zap } from "lucide-react";
import { HotspotEvaluationCard } from "./hotspot-evaluation-card";
import type { EvalItem, EvalResponse } from "./hotspot-types";
import { usePreferences } from "@/lib/preferences";

interface HotspotEvaluationPanelProps {
  historyDate: string;
  evalLoading: boolean;
  evalRefreshing: boolean;
  evalError: string;
  displayEvaluations: EvalItem[];
  displayEvalSummary: EvalResponse["summary"] | null;
  onEvalRefresh: () => Promise<void>;
}

export function HotspotEvaluationPanel({
  historyDate,
  evalLoading,
  evalRefreshing,
  evalError,
  displayEvaluations,
  displayEvalSummary,
  onEvalRefresh,
}: HotspotEvaluationPanelProps) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  return (
    <div className="ui-card">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="type-h3 flex items-center gap-2 text-ink">
            <Zap className="h-4 w-4 text-primary" />
            {en ? "AI solution value evaluation" : "AI 解决方案价值评估"}
          </h3>
          <p className="text-xs text-ink-muted mt-0.5">
            {historyDate
              ? (en ? `${historyDate} historical evaluation` : `${historyDate} 历史评估`)
              : (en ? "Project briefs and solution value for today's projects" : "为当日项目生成用途速读，并评估客户价值、业务价值与交付复制性")}
          </p>
        </div>
        {!historyDate && (
          <button
            onClick={onEvalRefresh}
            disabled={evalRefreshing}
            className="ui-button-secondary"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${evalRefreshing ? "animate-spin" : ""}`}
            />
            {evalRefreshing ? (en ? "Evaluating..." : "评估中...") : (en ? "Re-evaluate" : "重新评估")}
          </button>
        )}
      </div>

      {evalError && <p role="alert" className="mb-3 text-xs text-warning">{evalError}</p>}
      {evalLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="h-28 bg-surface-subtle animate-shimmer rounded-xl"
            />
          ))}
        </div>
      ) : displayEvaluations.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-sm text-ink-muted">{en ? "No evaluations yet" : "暂无评估结果"}</p>
          <p className="text-xs text-ink-muted mt-1">
            {en ? "Use Re-evaluate to run AI analysis (scheduled daily at 08:35)" : "点击右上角重新评估触发 AI 分析（每日 08:35 自动执行）"}
          </p>
        </div>
      ) : (
        <>
          {displayEvalSummary && (
            <div className="flex flex-wrap gap-2 mb-4 text-xs font-semibold">
              <span className="ui-tag">
                {en ? "Strongly recommended" : "强烈推荐"} {displayEvalSummary.strong}
              </span>
              <span className="ui-tag">
                {en ? "Worth doing" : "值得做"} {displayEvalSummary.worth}
              </span>
              <span className="ui-tag ui-tag-warning">
                {en ? "Marginal" : "勉强可做"} {displayEvalSummary.marginal}
              </span>
              <span className="ui-tag ui-tag-warning">
                {en ? "Not recommended" : "不建议"} {displayEvalSummary.not_recommended}
              </span>
            </div>
          )}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {displayEvaluations.map((ev, i) => (
              <HotspotEvaluationCard
                key={ev.repo_name || i}
                ev={ev}
                index={i}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
