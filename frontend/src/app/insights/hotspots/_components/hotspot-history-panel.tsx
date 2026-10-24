"use client";

import { CalendarDays } from "lucide-react";
import type { HistoryEntry } from "./hotspot-types";
import { usePreferences } from "@/lib/preferences";

interface HotspotHistoryPanelProps {
  history: HistoryEntry[];
  historyLoading: boolean;
  historyDate: string;
  onDateSelect: (date: string) => void;
}

export function HotspotHistoryPanel({
  history,
  historyLoading,
  historyDate,
  onDateSelect,
}: HotspotHistoryPanelProps) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  return (
    <div className="ui-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="type-h3 text-ink">{en ? "Crawl history (last 14 days)" : "历史抓取记录（近 14 天）"}</h3>
        {historyDate && (
          <button
            onClick={() => onDateSelect("")}
            className="text-xs font-semibold text-primary hover:underline"
          >
            ← {en ? "Back to today" : "返回今日数据"}
          </button>
        )}
      </div>
      {historyLoading ? (
        <div className="grid grid-cols-7 gap-2">
          {[...Array(7)].map((_, i) => (
            <div
              key={i}
              className="h-14 bg-surface-subtle animate-shimmer rounded-xl"
            />
          ))}
        </div>
      ) : history.length === 0 ? (
        <p className="text-sm text-ink-muted text-center py-6">
          {en ? "History will appear after the first daily collection." : "首次完成每日采集后，这里会显示历史记录。"}
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {history.map((h) => (
            <button
              key={h.date}
              onClick={() => onDateSelect(h.date === historyDate ? "" : h.date)}
              className={`flex flex-col items-center px-3.5 py-2.5 rounded-xl transition-all ${
                historyDate === h.date
                  ? "gradient-primary text-white shadow-md shadow-primary/20"
                  : "bg-surface-subtle border border-grid hover:border-primary/30"
              }`}
            >
              <span className="text-xs font-semibold uppercase tracking-wider">
                {new Date(h.date).toLocaleDateString(en ? "en-US" : "zh-CN", {
                  weekday: "short",
                })}
              </span>
              <span className="text-base font-bold">{h.date.slice(8)}</span>
              <span
                className={`text-xs ${historyDate === h.date ? "text-white/70" : "text-ink-muted"}`}
              >
                {h.items.length} {en ? "items" : "项"}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

interface HistoryDateIndicatorProps {
  historyDate: string;
}

export function HistoryDateIndicator({ historyDate }: HistoryDateIndicatorProps) {
  const { preferences } = usePreferences();
  if (!historyDate) return null;
  return (
    <div className="flex items-center gap-2 text-sm font-semibold text-primary bg-primary-soft border border-primary/20 rounded-xl px-4 py-2 w-fit">
      <CalendarDays className="h-4 w-4" />
      {preferences.language === "en" ? `Viewing history for ${historyDate}` : `正在查看 ${historyDate} 的历史数据`}
    </div>
  );
}
