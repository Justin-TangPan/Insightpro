import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

export type RequirementStatus = "draft" | "active" | "planned" | "completed" | "archived";
export type Priority = "low" | "medium" | "high" | "critical";
export type SolutionStatus = "draft" | "active" | "deprecated" | "archived";

export interface Requirement {
  id: number;
  title: string;
  description: string;
  status: RequirementStatus;
  priority: Priority;
  source_type: string;
  source_id: string | null;
  source_url: string | null;
  solution_count?: number;
  solutions?: Solution[];
  created_at: string;
  updated_at: string;
}

export interface Solution {
  id: number;
  name: string;
  description: string;
  category: string;
  status: SolutionStatus;
  version: string;
  reference_url: string | null;
  requirement_count?: number;
  requirements?: Requirement[];
  created_at: string;
  updated_at: string;
}

export const requirementStatusLabels: Record<RequirementStatus, string> = {
  draft: "草稿", active: "进行中", planned: "已规划", completed: "已完成", archived: "已归档",
};
export const priorityLabels: Record<Priority, string> = {
  low: "低", medium: "中", high: "高", critical: "紧急",
};
export const solutionStatusLabels: Record<SolutionStatus, string> = {
  draft: "草稿", active: "使用中", deprecated: "已弃用", archived: "已归档",
};

export async function workbenchFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await authenticatedFetch(`${API}/api/workbench${path}`, init);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `请求失败：${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export const formatWorkbenchDate = (value: string) => new Date(value).toLocaleString("zh-CN", {
  month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
});
