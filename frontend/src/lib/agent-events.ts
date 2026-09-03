export type AgentRoute = {
  contextType: "github_project" | "cloud_solution" | "requirement" | "solution";
  contextId: string;
  actionKey: string;
};

const routeEvent = "insight-agent:route";

export function emitAgentRoute(detail: AgentRoute, target: EventTarget = window) {
  target.dispatchEvent(new CustomEvent<AgentRoute>(routeEvent, { detail }));
}

export function subscribeAgentRoute(handler: (detail: AgentRoute) => void, target: EventTarget = window) {
  const listener = (event: Event) => handler((event as CustomEvent<AgentRoute>).detail);
  target.addEventListener(routeEvent, listener);
  return () => target.removeEventListener(routeEvent, listener);
}
