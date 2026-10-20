"use client";

import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import { optionalAuthenticatedFetch } from "@/lib/authenticated-fetch";

export type Preferences = {
  theme: "dark" | "light";
  language: "zh" | "en";
  density: "comfortable" | "compact";
  motion: boolean;
};

export const defaultPreferences: Preferences = { theme: "dark", language: "zh", density: "comfortable", motion: true };

export function applyPreferences(value: Preferences) {
  const root = document.documentElement;
  root.dataset.theme = value.theme;
  root.dataset.density = value.density;
  root.dataset.motion = String(value.motion);
  root.lang = value.language === "zh" ? "zh-CN" : "en";
}

export function usePreferences() {
  const [preferences, setPreferences] = useState(defaultPreferences);
  useEffect(() => {
    const load = () => {
    try {
      const raw = JSON.parse(localStorage.getItem("insight_preferences") || "{}");
      const stored = { ...defaultPreferences, ...raw, theme: raw.theme === "light" ? "light" : "dark", language: raw.language === "en" ? "en" : "zh", theme_version: 4 };
      localStorage.setItem("insight_preferences", JSON.stringify(stored));
      setPreferences(stored);
      applyPreferences(stored);
    } catch {}
    };
    load();
    window.addEventListener("insight-preferences", load);
    return () => window.removeEventListener("insight-preferences", load);
  }, []);
  const updatePreferences = (changes: Partial<Preferences>) => {
    const next = { ...preferences, ...changes };
    setPreferences(next);
    localStorage.setItem("insight_preferences", JSON.stringify(next));
    applyPreferences(next);
    if (changes.language) void optionalAuthenticatedFetch(`${API}/api/email/preference?language=${next.language}`, { method: "POST" }).catch(() => undefined);
    window.dispatchEvent(new Event("insight-preferences"));
  };
  return { preferences, updatePreferences };
}
