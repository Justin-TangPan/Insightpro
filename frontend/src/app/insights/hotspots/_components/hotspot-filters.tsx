"use client";

import { CalendarDays, RefreshCw } from "lucide-react";
import { periods } from "./hotspot-types";
import { usePreferences } from "@/lib/preferences";

interface HotspotFiltersProps {
  period: string;
  onPeriodChange: (period: string) => void;
  showHistory: boolean;
  onToggleHistory: () => void;
  refreshing: boolean;
  onRefresh: () => void;
}

export function HotspotFilters({
  period,
  onPeriodChange,
  showHistory,
  onToggleHistory,
  refreshing,
  onRefresh,
}: HotspotFiltersProps) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  return (
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div className="flex gap-1.5">
        {periods.map((p) => (
          <button
            key={p.key}
            onClick={() => onPeriodChange(p.key)}
            className={`ui-button-secondary ${
              period === p.key
                ? "!bg-primary !text-white !shadow-[var(--shadow-brand)]"
                : ""
            }`}
          >
            <p.icon className="h-3.5 w-3.5" />
            {en ? p.en : p.label}
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <button
          onClick={onToggleHistory}
          className={`ui-button-secondary ${
            showHistory ? "!bg-primary !text-white" : ""
          }`}
        >
          <CalendarDays className="h-3.5 w-3.5" />
          {en ? "History" : "历史记录"}
        </button>
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="ui-button-secondary"
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`}
          />
          {refreshing ? (en ? "Refreshing..." : "刷新中...") : (en ? "Refresh" : "手动刷新")}
        </button>
      </div>
    </div>
  );
}
