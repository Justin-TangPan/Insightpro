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
  const switchTab = (index: number) => {
    const next = new URLSearchParams(params.toString());
    next.set("tab", String(index));
    router.push(`/admin/system?${next.toString()}`);
  };
  return <div className="page-stack"><nav aria-label="系统设置模块" className="flex flex-wrap gap-2">{tabs.map((label, index) => <button key={label} type="button" aria-current={tab === index ? "page" : undefined} onClick={() => switchTab(index)} className={tab === index ? "ui-button-primary" : "ui-button-secondary"}>{label}</button>)}</nav>{tab === 0 ? <Llm /> : tab === 1 ? <Prompts /> : tab === 2 ? <Knowledge /> : tab === 3 ? <Users /> : tab === 4 ? <Emails /> : <Runtime />}</div>;
}
export default function SystemPage() { return <Suspense fallback={<div className="ui-card">加载中…</div>}><Content /></Suspense>; }
