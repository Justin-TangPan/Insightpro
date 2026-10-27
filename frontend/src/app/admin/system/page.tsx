"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import Llm from "../llm/page";
import Prompts from "../prompts/page";
import Knowledge from "../knowledge/page";
import Users from "../users/page";
import Emails from "../emails/page";
import Runtime from "../runtime/page";

const tabs = ["模型", "Prompt", "知识库", "用户权限", "通知", "系统参数"] as const;
function Content() {
  const router = useRouter();
  const params = useSearchParams();
  const tab = Math.min(5, Math.max(0, Number(params.get("tab") || 0) || 0));
  return <div className="page-stack"><header className="ui-card"><p className="text-xs font-semibold text-primary">SYSTEM SETTINGS</p><h1 className="mt-1 text-2xl font-semibold text-ink">系统设置</h1><p className="mt-2 text-sm text-ink-muted">模型、分析能力、知识、权限和通知</p></header><nav aria-label="系统设置模块" className="flex flex-wrap gap-2">{tabs.map((label, index) => <button key={label} type="button" aria-current={tab === index ? "page" : undefined} onClick={() => router.push(`/admin/system?tab=${index}`)} className={tab === index ? "ui-button-primary" : "ui-button-secondary"}>{label}</button>)}</nav>{tab === 0 ? <Llm /> : tab === 1 ? <Prompts /> : tab === 2 ? <Knowledge /> : tab === 3 ? <Users /> : tab === 4 ? <Emails /> : <Runtime />}</div>;
}
export default function SystemPage() { return <Suspense fallback={<div className="ui-card">加载中…</div>}><Content /></Suspense>; }
