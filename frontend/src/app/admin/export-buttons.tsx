"use client";

import { useState } from "react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

type Dataset = "event" | "candidate" | "data_source" | "pipeline_run" | "inspection_result";

export function ExportButtons({ dataset, filters = {} }: { dataset: Dataset; filters?: Record<string, string> }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sort, setSort] = useState<"desc" | "asc">("desc");
  const download = async (format: "csv" | "xlsx") => {
    setBusy(true); setError("");
    try {
      const query = new URLSearchParams({ ...filters, format, sort,
        ...(dateFrom ? { date_from: dateFrom } : {}), ...(dateTo ? { date_to: dateTo } : {}) });
      const response = await authenticatedFetch(`${API}/api/admin/exports/${dataset}?${query}`);
      if (!response.ok) throw new Error((await response.json()).detail || "导出失败");
      const objectUrl = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = objectUrl; anchor.download = `${dataset}.${format}`;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "导出失败"); }
    finally { setBusy(false); }
  };
  return <div className="flex flex-wrap items-center gap-2"><label className="text-xs text-ink-muted">从 <input aria-label="导出开始日期" type="date" className="ui-input px-2 py-1" value={dateFrom} onChange={event => setDateFrom(event.target.value)} /></label><label className="text-xs text-ink-muted">到 <input aria-label="导出结束日期" type="date" className="ui-input px-2 py-1" value={dateTo} onChange={event => setDateTo(event.target.value)} /></label><select aria-label="导出排序" className="ui-input px-2 py-1 text-xs" value={sort} onChange={event => setSort(event.target.value as "desc" | "asc")}><option value="desc">最新优先</option><option value="asc">最早优先</option></select><button type="button" className="ui-button-secondary" disabled={busy} onClick={() => void download("csv")}>CSV</button><button type="button" className="ui-button-secondary" disabled={busy} onClick={() => void download("xlsx")}>XLSX</button>{error && <span role="alert" className="text-xs text-danger">{error}</span>}</div>;
}
