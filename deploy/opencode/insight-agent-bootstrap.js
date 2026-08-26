(() => {
  const key = "opencode.global.dat:server";
  const workspace = "/workspace";
  const displayName = decodeURIComponent(document.cookie.match(/(?:^|; )insight_agent_name=([^;]*)/)?.[1] || "");
  let state = {};
  try { state = JSON.parse(localStorage.getItem(key) || "{}"); } catch {}
  const projects = state.projects || {};
  const local = Array.isArray(projects.local) ? projects.local : [];
  if (!local.some((project) => project.worktree === workspace)) {
    local.unshift({ worktree: workspace, expanded: true, ...(displayName && { name: displayName }) });
  } else if (displayName) {
    Object.assign(local.find((project) => project.worktree === workspace), { name: displayName });
  }
  localStorage.setItem(key, JSON.stringify({
    ...state,
    list: Array.isArray(state.list) ? state.list : [],
    projects: { ...projects, local },
    lastProject: { ...(state.lastProject || {}), local: workspace },
    recentlyClosed: state.recentlyClosed || {},
  }));
  if (displayName) {
    fetch("/project")
      .then((response) => response.json())
      .then((projects) => projects.find((project) => project.worktree === workspace)?.id)
      .then((id) => id && fetch(`/project/${id}?directory=${encodeURIComponent(workspace)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: displayName }),
      }))
      .catch(() => undefined);
  }
})();
