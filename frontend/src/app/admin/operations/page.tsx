"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { Suspense } from "react";
import Candidates from "../candidates/page";
import Events from "../events/page";
import Coverage from "../coverage/page";
import ReviewPanel from "./review-panel";

const tabs = ["候选", "事件", "审核", "覆盖分析"] as const;
function Content() {
  const router = useRouter();
  const params = useSearchParams();
  const tab = Math.min(3, Math.max(0, Number(params.get("tab") || 0) || 0));
  return <div className="page-stack"><header className="ui-card"><p className="text-xs font-semibold text-primary">INTELLIGENCE OPERATIONS</p><h1 className="mt-1 text-2xl font-semibold text-ink">情报运营</h1><p className="mt-2 text-sm text-ink-muted">候选发现 → 事件核验 → 人工审核 → 前台覆盖</p></header><nav aria-label="情报运营模块" className="flex flex-wrap gap-2">{tabs.map((label, index) => <button key={label} type="button" aria-current={tab === index ? "page" : undefined} onClick={() => router.push(`/admin/operations?tab=${index}`)} className={tab === index ? "ui-button-primary" : "ui-button-secondary"}>{label}</button>)}</nav>{tab === 0 ? <Candidates /> : tab === 2 ? <ReviewPanel /> : tab === 3 ? <Coverage /> : <Events />}</div>;
}
export default function OperationsPage() { return <Suspense fallback={<div className="ui-card">加载中…</div>}><Content /></Suspense>; }
