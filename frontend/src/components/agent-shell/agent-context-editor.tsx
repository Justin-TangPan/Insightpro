"use client";

import { useState } from "react";
import type { Context } from "./types";
import { usePreferences } from "@/lib/preferences";

export function ContextEditor({
  context,
  refresh,
  save,
  setError,
}: {
  context: Context;
  refresh(): Promise<void>;
  save(supplement: string, excluded: string[]): Promise<void>;
  setError(value: string): void;
}) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [supplement, setSupplement] = useState(context.supplement || "");
  const [excluded, setExcluded] = useState<string[]>(
    context.excluded_sections || [],
  );
  return (
    <div className="mt-3 rounded-lg bg-white p-3 text-xs leading-5 text-ink-secondary">
      <p>{context.summary || (en ? "Authorized context for this work item is available." : "已注入当前业务对象的授权信息。")}</p>
      {context.source_url && (
        <a
          className="mt-2 block text-primary underline"
          href={context.source_url}
          target="_blank"
          rel="noreferrer"
        >
          {en ? "View source" : "查看来源"}
        </a>
      )}
      <textarea
        value={supplement}
        onChange={(event) => setSupplement(event.target.value)}
        placeholder={en ? "Additional context for Agent" : "补充给 Agent 的上下文"}
        className="mt-3 w-full rounded border border-grid p-2 text-xs"
        rows={2}
      />
      <div className="mt-2 flex flex-wrap gap-2">
        {(
          [
            ["summary", "摘要"],
            ["content", "正文"],
            ["metadata", "结构化信息"],
            ["related_entities", "关联材料"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={excluded.includes(key)}
              onChange={() =>
                setExcluded((items) =>
                  items.includes(key)
                    ? items.filter((item) => item !== key)
                    : [...items, key],
                )
              }
            />
            {en ? `Exclude ${{ summary: "summary", content: "content", metadata: "structured data", related_entities: "related materials" }[key]}` : `不注入${label}`}
          </label>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() =>
            void save(supplement, excluded).catch((reason) =>
              setError(
                reason instanceof Error ? reason.message : (en ? "Could not save context" : "无法保存 Context"),
              ),
            )
          }
          className="text-xs font-semibold text-primary"
        >
          {en ? "Save settings" : "保存设置"}
        </button>
        <button
          type="button"
          onClick={() =>
            void refresh().catch((reason) =>
              setError(
                reason instanceof Error ? reason.message : (en ? "Could not refresh context" : "无法刷新 Context"),
              ),
            )
          }
          className="text-xs font-semibold text-primary"
        >
          {en ? "Refresh context" : "刷新业务 Context"}
        </button>
      </div>
    </div>
  );
}
