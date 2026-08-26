(() => {
  const key = "opencode.global.dat:server";
  const workspace = "/workspace";
  let state = {};
  try { state = JSON.parse(localStorage.getItem(key) || "{}"); } catch {}
  const projects = state.projects || {};
  const local = Array.isArray(projects.local) ? projects.local : [];
  if (!local.some((project) => project.worktree === workspace)) {
    local.unshift({ worktree: workspace, expanded: true });
  }
  localStorage.setItem(key, JSON.stringify({
    ...state,
    list: Array.isArray(state.list) ? state.list : [],
    projects: { ...projects, local },
    lastProject: { ...(state.lastProject || {}), local: workspace },
    recentlyClosed: state.recentlyClosed || {},
  }));
})();
