"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

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
    window.dispatchEvent(new CustomEvent("insight-agent:route", { detail: { contextType, contextId: String(contextId), actionKey } }));
  }}>{children}</button>;
}
