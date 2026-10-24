export type Intelligence = {
  kind: "github_project" | "cloud_solution" | "competitor_update" | "ai_application";
  key: string;
  title: string;
  brief: string;
  analysis: string | null;
  source: string | null;
  analysis_id: number | string | null;
  solution_value?: string;
  open_source_projects?: string;
  cloud_resources?: string;
};

export function plainIntelligenceText(value: string): string {
  return value
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/\*\*(.*?)\*\*|__(.*?)__/g, (_, strong: string, underscore: string) => strong || underscore)
    .replace(/`([^`]+)`/g, "$1")
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
