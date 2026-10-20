"use client";

import {
  Star,
  GitFork,
  TrendingUp,
  ExternalLink,
  BookmarkPlus,
  Bot,
  Check,
} from "lucide-react";
import { AgentAction } from "@/components/agent-action";
import { useAuth } from "@/components/auth-provider";
import { usePreferences } from "@/lib/preferences";
import { langColors, type TrendingItem, type EvalItem } from "./hotspot-types";
import { ExpandableText } from "@/components/expandable-text";

interface HotspotTrendingCardProps {
  item: TrendingItem;
  index: number;
  evaluation?: EvalItem;
  savingRepo: string;
  savedRepos: Set<string>;
  onSave: (item: TrendingItem) => void;
}

export function HotspotTrendingCard({
  item,
  index,
  evaluation,
  savingRepo,
  savedRepos,
  onSave,
}: HotspotTrendingCardProps) {
  const { preferences } = usePreferences();
  const { user } = useAuth();
  const en = preferences.language === "en";
  return (
    <article
      key={item.repo_url || index}
      className="group ui-card hover:shadow-[var(--shadow-card-hover)] hover:-translate-y-0.5 transition-all duration-300"
    >
      <div className="flex items-start justify-between mb-2.5">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="flex h-6 w-6 items-center justify-center rounded-md gradient-primary text-white text-[10px] font-bold shrink-0">
              {index + 1}
            </span>
            <a
              href={item.repo_url}
              target="_blank"
              rel="noopener noreferrer"
              className="serif-heading truncate text-sm text-ink transition-colors group-hover:text-primary"
            >
              {item.repo_name}
            </a>
          </div>
          <p className="text-xs text-ink-secondary leading-relaxed line-clamp-2 ml-8 min-h-[2rem]">
            {item.description || (en ? "No description" : "暂无描述")}
          </p>
          {(evaluation?.intelligence?.brief || evaluation?.summary) && (
            <div className="ml-8 mt-3 border-l-2 border-primary/40 pl-3">
              <span className="text-[10px] font-bold uppercase tracking-wider text-primary">
                {en ? "Project brief" : "项目简述"}
              </span>
              <ExpandableText lines={3} en={en} className="mt-1 text-xs leading-relaxed text-ink">
                {evaluation?.intelligence?.brief || evaluation?.summary || ""}
              </ExpandableText>
            </div>
          )}
          {evaluation?.intelligence?.analysis && evaluation.evaluation_mode !== "heuristic" && <div className="ml-8 mt-3 border-l-2 border-lemon pl-3"><span className="text-[10px] font-bold uppercase tracking-wider text-primary">{en ? "AI analysis" : "AI 分析"}</span><ExpandableText lines={2} en={en} className="mt-1 text-xs leading-relaxed text-ink">{evaluation.intelligence.analysis}</ExpandableText></div>}
        </div>
        <a
          href={item.repo_url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={en ? `View ${item.repo_name}` : `查看 ${item.repo_name}`}
        >
          <ExternalLink className="h-4 w-4 text-ink-muted group-hover:text-primary shrink-0 ml-3 transition-colors" />
        </a>
      </div>
      <div className="flex flex-wrap items-center gap-3 ml-8 mt-2.5">
        {item.language && item.language !== "N/A" && (
          <span className="flex items-center gap-1.5 text-xs font-medium text-ink-secondary">
            <span
              className={`h-2.5 w-2.5 rounded-full ${langColors[item.language] || "bg-ink-muted"}`}
            />
            {item.language}
          </span>
        )}
        <span className="flex items-center gap-1 text-xs text-ink-muted">
          <Star className="h-3 w-3" /> {item.stars}
        </span>
        <span className="flex items-center gap-1 text-xs text-ink-muted">
          <GitFork className="h-3 w-3" /> {item.forks}
        </span>
        {item.today_stars && (
          <span className="flex items-center gap-1 text-xs font-semibold text-primary bg-primary-soft px-2 py-0.5 rounded-full">
            <TrendingUp className="h-3 w-3" /> {item.today_stars}
          </span>
        )}
        <div className="ml-auto flex shrink-0 gap-2">
          {user && <button
            type="button"
            disabled={savingRepo === item.repo_url || savedRepos.has(item.repo_url)}
            onClick={() => onSave(item)}
            className="ui-button-secondary px-3 py-1.5 text-xs"
          >
            {savedRepos.has(item.repo_url) ? (
              <Check className="h-3.5 w-3.5" />
            ) : (
              <BookmarkPlus className="h-3.5 w-3.5" />
            )}
            {savingRepo === item.repo_url
              ? (en ? "Saving" : "收纳中")
              : savedRepos.has(item.repo_url)
                ? (en ? "Saved" : "已收纳")
                : (en ? "Save as practice" : "收纳方案实践")}
          </button>}
          <AgentAction
            contextType="github_project"
            contextId={item.repo_name}
            actionKey="deep_research"
            className="ui-button-secondary px-3 py-1.5 text-xs"
          >
            <Bot className="h-3.5 w-3.5" />
            {en ? "Deep research" : "深入研究"}
          </AgentAction>
        </div>
      </div>
    </article>
  );
}
