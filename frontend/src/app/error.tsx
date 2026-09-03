"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <section className="ui-card mx-auto max-w-xl py-12 text-center" role="alert">
      <AlertTriangle className="mx-auto h-8 w-8 text-warning" aria-hidden="true" />
      <h1 className="mt-4 type-h2 text-ink">页面暂时无法加载</h1>
      <p className="mt-2 text-sm text-ink-muted">数据服务可能正在恢复，请稍后重试。已有内容不会受到影响。</p>
      <button type="button" onClick={reset} className="ui-button-primary mt-6">
        <RotateCcw className="h-4 w-4" aria-hidden="true" />重新加载
      </button>
    </section>
  );
}
