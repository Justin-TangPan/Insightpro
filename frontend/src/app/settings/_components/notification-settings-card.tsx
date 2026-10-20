"use client";

import { Bell } from "lucide-react";
import { useState } from "react";
import { usePreferences } from "@/lib/preferences";

const notifications = [
  { label: "每日洞察日报", en: "Daily insights", desc: "按订阅者配置的星期和时间推送", descEn: "Sent on the subscriber's chosen day and time" },
  { label: "友商动态预警", en: "Competitor alerts", desc: "友商有重大动态时实时推送", descEn: "Sent when a major competitor update appears" },
  { label: "解决方案更新", en: "Solution updates", desc: "技术方案新增或发生变化时推送", descEn: "Sent when solutions are added or changed" },
  { label: "系统异常告警", en: "System alerts", desc: "API 或数据源异常时推送", descEn: "Sent when an API or data source fails" },
];

export function NotificationSettingsCard() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [toggles, setToggles] = useState(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("notification_toggles");
        if (saved) return JSON.parse(saved);
      } catch {}
    }
    return [true, true, true, false];
  });

  const handleToggle = (index: number) => {
    setToggles((prev: boolean[]) => {
      const next = prev.map((v, i) => (i === index ? !v : v));
      try { localStorage.setItem("notification_toggles", JSON.stringify(next)); } catch {}
      return next;
    });
  };

  return (
    <div className="ui-card">
      <div className="ui-card-header">
        <Bell className="h-4 w-4 text-ink-muted" />
        <h3 className="type-h3 text-ink">{en ? "Notifications" : "通知设置"}</h3>
      </div>
      <div className="space-y-0.5">
        {notifications.map((item, i) => (
          <div key={i} className="flex items-center justify-between rounded-lg px-3 py-2.5 odd:bg-surface-subtle/60">
            <div>
              <p className="text-sm font-medium text-ink">{en ? item.en : item.label}</p>
              <p className="text-xs text-ink-muted mt-0.5">{en ? item.descEn : item.desc}</p>
            </div>
            <button
              type="button"
              onClick={() => handleToggle(i)}
              className={`relative w-9 h-5 rounded-full cursor-pointer transition-colors ${toggles[i] ? "bg-primary" : "bg-grid"}`}
            >
              <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform ${toggles[i] ? "translate-x-[18px]" : "translate-x-0.5"}`} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
