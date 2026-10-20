"use client";

import { usePreferences } from "@/lib/preferences";

export function HeaderDate() {
  const { preferences } = usePreferences();
  return <p className="text-sm font-semibold leading-tight tracking-tight text-ink">{new Date().toLocaleDateString(preferences.language === "en" ? "en-US" : "zh-CN", { month: "long", day: "numeric", year: "numeric" })}</p>;
}
