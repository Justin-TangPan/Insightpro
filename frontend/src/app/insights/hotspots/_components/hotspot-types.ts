import { Zap, Activity, TrendingUp } from "lucide-react";
import type { Intelligence } from "@/lib/intelligence";

// ── Interfaces ──────────────────────────────────────────────

export interface TrendingItem {
  repo_name: string;
  repo_url: string;
  description: string;
  language: string;
  stars: string;
  forks: string;
  today_stars: string;
  category: string;
}

export interface TrendingResponse {
  items: TrendingItem[];
  source: string;
  count: number;
  date: string;
}

export interface HistoryEntry {
  date: string;
  items: TrendingItem[];
  evaluations: EvalItem[];
}

export interface EvalItem {
  intelligence?: Intelligence;
  repo_name: string;
  repo_url: string | null;
  language: string | null;
  stars: string | null;
  summary: string | null;
  d1: number;
  d2: number;
  d3: number;
  d4: number;
  total: number;
  level: string;
  recommendation: string;
  reasoning: string;
  eval_time: string | null;
  evaluation_mode?: "ai" | "heuristic";
}

export interface EvalResponse {
  date: string;
  items: EvalItem[];
  count: number;
  summary: {
    strong: number;
    worth: number;
    marginal: number;
    not_recommended: number;
  };
}

// ── Constants ───────────────────────────────────────────────

export const evalDimensions = [
  { key: "d1", label: "客户痛点", en: "Customer pain" },
  { key: "d2", label: "场景适配", en: "Scenario fit" },
  { key: "d3", label: "业务与云价值", en: "Business value" },
  { key: "d4", label: "标准化交付", en: "Replication" },
] as const;

export const levelStyles: Record<string, string> = {
  "强烈推荐": "bg-primary-soft text-primary border-primary/20",
  "值得做": "bg-warning-soft text-warning border-warning/20",
  "勉强": "bg-warning-soft text-warning border-warning/20",
  "不建议": "bg-warning-soft text-warning border-warning/20",
};

export function levelClass(level: string) {
  if (level.includes("强烈推荐") || level.includes("Strongly Recommended")) return levelStyles["强烈推荐"];
  if (level.includes("值得做") || level.includes("Worth Doing")) return levelStyles["值得做"];
  if (level.includes("勉强") || level.includes("Marginal")) return levelStyles["勉强"];
  return levelStyles["不建议"];
}

export const periods = [
  { key: "daily", label: "今日", en: "Today", icon: Zap },
  { key: "weekly", label: "本周", en: "This week", icon: Activity },
  { key: "monthly", label: "本月", en: "This month", icon: TrendingUp },
];

export const langColors: Record<string, string> = {
  Python: "bg-primary",
  TypeScript: "bg-primary-dark",
  JavaScript: "bg-primary-light",
  Rust: "bg-ink-secondary",
  Go: "bg-primary",
  Java: "bg-primary-dark",
  "C++": "bg-primary-light",
  C: "bg-ink-muted",
  Ruby: "bg-primary",
  PHP: "bg-primary-dark",
  Shell: "bg-primary-light",
  Kotlin: "bg-primary",
  Swift: "bg-ink-secondary",
  Dart: "bg-primary-light",
  Vue: "bg-primary",
  Svelte: "bg-primary-dark",
  Jupyter: "bg-ink-muted",
};
