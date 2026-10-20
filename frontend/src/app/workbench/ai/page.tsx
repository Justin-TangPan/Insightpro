"use client";

import { usePreferences } from "@/lib/preferences";

export default function AIWorkPage() {
  const { preferences } = usePreferences();
  return <div className="page-stack"><div className="ui-card py-20 text-center text-sm text-ink-muted">{preferences.language === "en" ? "Insight Agent is open on this page." : "Insight Agent 已在当前页面中打开。"}</div></div>;
}
