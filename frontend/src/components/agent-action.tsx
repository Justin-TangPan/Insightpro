"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import { emitAgentRoute } from "@/lib/agent-events";

type AgentActionProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  contextType: "github_project" | "cloud_solution" | "requirement" | "solution";
  contextId: string | number;
  actionKey: string;
  children: ReactNode;
};

export function AgentAction({ contextType, contextId, actionKey, children, onClick, ...props }: AgentActionProps) {
  return <button {...props} type="button" onClick={event => {
    onClick?.(event);
    if (event.defaultPrevented) return;
    emitAgentRoute({ contextType, contextId: String(contextId), actionKey });
  }}>{children}</button>;
}
