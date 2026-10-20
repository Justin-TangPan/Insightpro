"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";
import { usePreferences } from "@/lib/preferences";

export default function HotspotsError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  return (
    <section className="ui-card mx-auto max-w-xl py-12 text-center" role="alert">
      <AlertTriangle className="mx-auto h-8 w-8 text-warning" aria-hidden="true" />
      <h1 className="mt-4 type-h2 text-ink">{en ? "Could not load project insights" : "热点数据加载失败"}</h1>
      <p className="mt-2 text-sm text-ink-muted">{en ? "The data service may be recovering. Please try again shortly." : "数据服务可能正在恢复，请稍后重试。"}</p>
      <button type="button" onClick={reset} className="ui-button-primary mt-6">
        <RotateCcw className="h-4 w-4" aria-hidden="true" />{en ? "Reload" : "重新加载"}
      </button>
    </section>
  );
}
