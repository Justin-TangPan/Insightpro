"use client";

import { usePreferences, type Preferences } from "@/lib/preferences";
import { Palette, Languages, SlidersHorizontal } from "lucide-react";

interface AppearancePreferencesCardProps {
  preferences: Preferences;
  updatePreferences: (updates: Partial<Preferences>) => void;
}

export function AppearancePreferencesCard({ preferences, updatePreferences }: AppearancePreferencesCardProps) {
  return (
    <div className="ui-card lg:col-span-2">
      <div className="ui-card-header">
        <div className="flex items-center gap-2.5"><Palette className="h-4 w-4 text-ink-muted" /><h3 className="type-h3 text-ink">{preferences.language === "en" ? "Appearance & Preferences" : "外观与偏好"}</h3></div>
      </div>
      <div className="grid gap-5 md:grid-cols-2">
        <div>
          <label className="mb-2 flex items-center gap-2 text-xs font-semibold text-ink-muted"><Palette className="h-3.5 w-3.5" />{preferences.language === "en" ? "Theme color" : "主题色"}</label>
          <div className="flex flex-wrap gap-2">
            {([["dark", "深色主题", "#111117"], ["light", "浅色主题", "#f7f7f8"]] as [Preferences["theme"], string, string][]).map(([value, label, color]) => (
              <button key={value} type="button" aria-pressed={preferences.theme === value} onClick={() => updatePreferences({ theme: value })} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium ${preferences.theme === value ? "bg-primary-soft text-primary ring-1 ring-primary/30" : "bg-surface-subtle text-ink-secondary"}`}>
                <span className="h-3.5 w-3.5 rounded-full" style={{ backgroundColor: color }} />{preferences.language === "en" ? (value === "dark" ? "Dark theme" : "Light theme") : label}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <label className="text-xs font-semibold text-ink-muted"><span className="mb-2 flex items-center gap-2"><Languages className="h-3.5 w-3.5" />{preferences.language === "en" ? "Language" : "语言"}</span><select value={preferences.language} onChange={event => updatePreferences({ language: event.target.value as Preferences["language"] })} className="ui-input w-full px-3 text-sm"><option value="zh">简体中文</option><option value="en">English</option></select></label>
          <label className="text-xs font-semibold text-ink-muted"><span className="mb-2 flex items-center gap-2"><SlidersHorizontal className="h-3.5 w-3.5" />{preferences.language === "en" ? "Density" : "界面密度"}</span><select value={preferences.density} onChange={event => updatePreferences({ density: event.target.value as Preferences["density"] })} className="ui-input w-full px-3 text-sm"><option value="comfortable">{preferences.language === "en" ? "Comfortable" : "舒适"}</option><option value="compact">{preferences.language === "en" ? "Compact" : "紧凑"}</option></select></label>
          <label className="flex items-end gap-2 pb-2 text-xs font-semibold text-ink-muted"><input type="checkbox" checked={preferences.motion} onChange={event => updatePreferences({ motion: event.target.checked })} className="accent-primary" />{preferences.language === "en" ? "Animations" : "界面动效"}</label>
        </div>
      </div>
    </div>
  );
}
