export function taskStatus(task: { last_run: { status: string } | null }): "success" | "running" | "waiting" | "error" {
  if (task.last_run?.status === "failed") return "error";
  if (task.last_run?.status === "running") return "running";
  if (task.last_run?.status === "success") return "success";
  return "waiting";
}
