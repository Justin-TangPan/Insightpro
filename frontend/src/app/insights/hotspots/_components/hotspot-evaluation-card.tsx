"use client";

import { ExternalLink } from "lucide-react";
import { evalDimensions, levelClass, type EvalItem } from "./hotspot-types";
import { usePreferences } from "@/lib/preferences";
import { ExpandableText } from "@/components/expandable-text";
import { parseEvaluationSections } from "@/lib/evaluation-sections";

interface HotspotEvaluationCardProps {
  ev: EvalItem;
  index: number;
}

export function HotspotEvaluationCard({ ev, index }: HotspotEvaluationCardProps) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const brief = ev.intelligence?.brief || ev.summary;
  const analysis = ev.intelligence?.analysis || ev.reasoning;
  const reasoningSections = parseEvaluationSections(analysis || "");
  const repeatedSummary = brief?.trim() === analysis?.trim();
  return (
    <div
      key={ev.repo_name || index}
      className="rounded-xl bg-surface-subtle p-4 transition-colors hover:bg-primary-soft/60"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex h-5 w-5 items-center justify-center rounded-md gradient-primary text-white text-[10px] font-bold shrink-0">
            {index + 1}
          </span>
          {ev.repo_url ? (
            <a
              href={ev.repo_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-semibold text-ink hover:text-primary truncate flex items-center gap-1"
            >
              {ev.repo_name}{" "}
              <ExternalLink className="h-3 w-3 shrink-0" />
            </a>
          ) : (
            <span className="text-sm font-semibold text-ink truncate">
              {ev.repo_name}
            </span>
          )}
        </div>
        <span
          className={`shrink-0 px-2 py-0.5 rounded-full text-[11px] font-semibold border ${levelClass(ev.level)}`}
        >
          {ev.level}
        </span>
      </div>
      {ev.evaluation_mode === "heuristic" && <p className="mb-2 text-[10px] font-semibold text-warning">{en ? "Rule-based estimate · AI pending" : "规则估算 · 等待 AI 分析"}</p>}
      <div className="grid grid-cols-4 gap-1.5 mb-2">
        {evalDimensions.map((d) => {
          const v = Number(ev[d.key]) || 0;
          return (
            <div key={d.key}>
              <div className="flex items-center justify-between text-[10px] text-ink-muted mb-0.5">
                <span>{en ? d.en : d.label}</span>
                <span className="font-semibold text-ink-secondary">
                  {v.toFixed(1)}
                </span>
              </div>
              <div className="h-1.5 bg-surface-subtle rounded-full overflow-hidden">
                <div
                  className="h-full gradient-primary rounded-full"
                  style={{ width: `${Math.min(100, v * 10)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-[11px] text-ink-muted">{en ? "Score" : "总分"}</span>
        <span className="text-base font-bold text-primary">
          {Number(ev.total || 0).toFixed(1)}
        </span>
        <span className="text-[11px] text-ink-muted">/ 10</span>
      </div>
      {brief && !repeatedSummary && <ExpandableText lines={2} en={en} className="mb-3 text-sm leading-6 text-ink-secondary">{brief}</ExpandableText>}
      {reasoningSections.length > 0 ? (
        <dl className="space-y-3 rounded-xl border border-grid bg-surface-elevated p-4">
          {reasoningSections.map((section) => (
            <div key={section.label} className="grid min-w-0 gap-1.5 border-b border-grid/60 pb-3 last:border-0 last:pb-0 sm:grid-cols-[5rem_minmax(0,1fr)] sm:gap-3">
              <dt><span className="inline-flex rounded-md bg-primary-soft px-2.5 py-1 text-xs font-bold text-primary">{section.label}</span></dt>
              <dd className="[overflow-wrap:anywhere] text-sm leading-6 text-ink">{section.content}</dd>
            </div>
          ))}
        </dl>
      ) : analysis ? (
        <ExpandableText lines={2} en={en} className="text-sm leading-6 text-ink-secondary">
          {analysis}
        </ExpandableText>
      ) : null}
      {ev.recommendation && (
        <ExpandableText lines={1} en={en} className="mt-2 text-sm leading-6 text-ink-secondary">
          {`${en ? "Next step: " : "建议："}${ev.recommendation}`}
        </ExpandableText>
      )}
    </div>
  );
}
