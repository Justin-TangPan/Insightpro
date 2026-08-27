(() => {
  const key = "opencode.global.dat:server";
  const displayName = decodeURIComponent(document.cookie.match(/(?:^|; )insight_agent_name=([^;]*)/)?.[1] || "");
  let workspace = "";
  const ready = fetch("/__insight/context")
    .then((response) => response.json())
    .then((context) => {
      workspace = context.workspace;
      let state = {};
      try { state = JSON.parse(localStorage.getItem(key) || "{}"); } catch {}
      const projects = state.projects || {};
      const local = (Array.isArray(projects.local) ? projects.local : []).filter((project) => project.worktree === workspace);
      if (!local.length) local.push({ worktree: workspace, expanded: true, ...(displayName && { name: displayName }) });
      else if (displayName) Object.assign(local[0], { name: displayName });
      localStorage.setItem(key, JSON.stringify({
        ...state,
        list: Array.isArray(state.list) ? state.list : [],
        projects: { ...projects, local },
        lastProject: { ...(state.lastProject || {}), local: workspace },
        recentlyClosed: state.recentlyClosed || {},
      }));
      if (displayName) fetch("/project")
        .then((response) => response.json())
        .then((items) => items.find((project) => project.worktree === workspace)?.id)
        .then((id) => id && fetch(`/project/${id}?directory=${encodeURIComponent(workspace)}`, {
          method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: displayName }),
        }))
        .catch(() => undefined);
      return context;
    });

  window.addEventListener("message", async (event) => {
    const question = event.data?.type === "insight-agent-question" && event.data.question;
    if (!question || (document.referrer && event.origin !== new URL(document.referrer).origin)) return;
    try {
      await ready;
      const session = await fetch(`/session?directory=${encodeURIComponent(workspace)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: question }),
      }).then((response) => {
        if (!response.ok) throw new Error("create session failed");
        return response.json();
      });
      await fetch(`/session/${session.id}/message?directory=${encodeURIComponent(workspace)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ parts: [{ type: "text", text: question }] }),
      });
      const workspaceKey = btoa(workspace).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
      location.assign(`/${workspaceKey}/session/${session.id}`);
    } catch {
      // Native UI remains usable if a prompt cannot be submitted.
    }
  });
})();
