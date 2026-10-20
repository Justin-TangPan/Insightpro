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
