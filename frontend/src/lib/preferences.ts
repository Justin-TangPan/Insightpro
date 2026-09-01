"use client";

import { useEffect, useState } from "react";

export type Preferences = {
  theme: "green" | "mono" | "orange" | "blue" | "purple";
  language: "zh" | "en";
  density: "comfortable" | "compact";
  motion: boolean;
};

export const defaultPreferences: Preferences = { theme: "blue", language: "zh", density: "comfortable", motion: true };

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
      const stored = { ...defaultPreferences, ...raw, theme_version: 3 };
      localStorage.setItem("insight_preferences", JSON.stringify(stored));
      setPreferences(stored);
      applyPreferences(stored);
    } catch {}
    };
    load();
    window.addEventListener("insight-preferences", load);
    return () => window.removeEventListener("insight-preferences", load);
  }, []);
  const updatePreferences = (changes: Partial<Preferences>) => setPreferences(current => {
    const next = { ...current, ...changes };
    localStorage.setItem("insight_preferences", JSON.stringify(next));
    applyPreferences(next);
    window.dispatchEvent(new Event("insight-preferences"));
    return next;
  });
  return { preferences, updatePreferences };
}
