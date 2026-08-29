"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, Maximize2, Minimize2, Minus, X } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useAuth } from "@/components/auth-provider";

export function InsightAgentShell() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading } = useAuth();
  const full = pathname === "/insight-agent";
  const previousPath = useRef("/");
  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [connection, setConnection] = useState({ key: "", source: "" });
  const [contextTitle, setContextTitle] = useState("");
  const [agentSessionId, setAgentSessionId] = useState("");
  const [proposal, setProposal] = useState<{ id: string; action: string; payload?: { entity_type?: string } } | null>(null);
  const [error, setError] = useState("");
  const [position, setPosition] = useState<{ left: number; top: number } | null>(null);
  const targetUserId = full ? searchParams.get("target") || "" : "";
  const contextType = full ? searchParams.get("context_type") || "" : "";
  const contextId = full ? searchParams.get("context_id") || "" : "";
  const connectionKey = user ? `${user.id}:${targetUserId || user.id}:${contextType}:${contextId}` : "";

  useEffect(() => {
    if (!full && !pathname.startsWith("/auth/")) previousPath.current = pathname;
  }, [full, pathname]);

  useEffect(() => {
    if ((!full && !open) || !user || connection.key === connectionKey) return;
    let cancelled = false;
    const contextRequest = contextType && contextId
      ? authenticatedFetch("/api/agent/sessions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ context_type: contextType, context_id: contextId }) })
        .then(async response => {
          if (!response.ok) throw new Error("当前业务对象无法作为 Agent Context 使用");
          return response.json() as Promise<{ id: string; context_title: string }>;
        })
      : Promise.resolve(null);
    void contextRequest.then(context => authenticatedFetch("/api/auth/opencode/ticket", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...(targetUserId && { target_user_id: targetUserId }), ...(context && { agent_session_id: context.id }) }),
    }).then(response => {
      if (context) { setContextTitle(context.context_title); setAgentSessionId(context.id); setProposal(null); }
      else { setContextTitle(""); setAgentSessionId(""); setProposal(null); }
      return response;
    }))
      .then(async response => {
        if (!response.ok) throw new Error(response.status === 403 ? "当前账号未获 Insight-Agent 访问权限" : "Insight-Agent 授权失败");
        return response.json() as Promise<{ redirect_url: string }>;
      })
      .then(data => { if (!cancelled) setConnection({ key: connectionKey, source: data.redirect_url }); })
      .catch(reason => { if (!cancelled) setError(reason instanceof Error ? reason.message : "Insight-Agent 授权失败"); });
    return () => { cancelled = true; };
  }, [connection.key, connectionKey, contextId, contextType, full, open, targetUserId, user]);

  const show = () => {
    if (!user) {
      router.push("/auth/login?next=/insight-agent");
      return;
    }
    setOpen(true);
    setMinimized(false);
  };

  const close = () => {
    setOpen(false);
    setMinimized(false);
    if (full) router.push(previousPath.current);
  };

  const restore = () => {
    if (full) router.push(previousPath.current);
    setOpen(true);
    setMinimized(false);
  };

  const importDraft = async () => {
    if (!agentSessionId) return;
    try {
      const response = await authenticatedFetch(`/api/agent/sessions/${agentSessionId}/actions/import`, { method: "POST" });
      if (!response.ok) throw new Error("没有可确认的 Agent 草稿");
      const action = await response.json() as { id: string; action: string; payload?: { entity_type?: string } };
      setProposal(action);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "读取草稿失败"); }
  };

  const confirmDraft = async () => {
    if (!proposal) return;
    try {
      const response = await authenticatedFetch(`/api/agent/actions/${proposal.id}/confirm`, { method: "POST" });
      if (!response.ok) throw new Error("草稿确认失败");
      const item = await response.json() as { id: number };
      router.push(proposal.action === "create_requirement_draft" || proposal.payload?.entity_type === "requirement" ? `/workbench/requirements/${item.id}` : `/workbench/solutions/${item.id}`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "草稿确认失败"); }
  };

  const startDrag = (event: React.PointerEvent<HTMLElement>) => {
    if (full || (event.target as HTMLElement).closest("button")) return;
    const panel = event.currentTarget.parentElement;
    if (!panel) return;
    const rect = panel.getBoundingClientRect();
    const offsetX = event.clientX - rect.left;
    const offsetY = event.clientY - rect.top;
    const move = (pointer: PointerEvent) => setPosition({
      left: Math.max(8, Math.min(pointer.clientX - offsetX, window.innerWidth - rect.width - 8)),
      top: Math.max(72, Math.min(pointer.clientY - offsetY, window.innerHeight - 48)),
    });
    const stop = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop);
  };

  if (loading) return null;
  const visible = full || open;
  return (
    <>
      {!visible && !full && (
        <button type="button" onClick={show} className="fixed bottom-6 right-6 z-50 flex h-14 items-center gap-2 rounded-full bg-primary px-5 text-sm font-semibold text-white shadow-[var(--shadow-elevated)] transition hover:bg-primary-dark" aria-label="打开 Insight-Agent">
          <Bot className="h-5 w-5" /> Insight-Agent
        </button>
      )}
      <section
        aria-label="Insight-Agent"
        className={full
          ? "fixed bottom-0 right-0 top-16 z-20 flex flex-col bg-white lg:left-[250px]"
          : `fixed z-50 flex min-h-12 flex-col overflow-hidden rounded-2xl bg-white shadow-[var(--shadow-elevated)] ${visible ? "" : "pointer-events-none invisible"}`}
        style={full ? undefined : {
          left: position?.left,
          top: position?.top,
          right: position ? undefined : 24,
          bottom: position ? undefined : 24,
          width: minimized ? 320 : 900,
          height: minimized ? 48 : 720,
          maxWidth: "calc(100vw - 24px)",
          maxHeight: "calc(100vh - 80px)",
          resize: minimized ? "none" : "both",
        }}
      >
        <header onPointerDown={startDrag} className="flex h-12 shrink-0 cursor-move items-center justify-between bg-primary-dark px-4 text-white">
          <div className="flex min-w-0 items-center gap-2 text-sm font-semibold"><Bot className="h-4 w-4 shrink-0" /> Insight-Agent{contextTitle && <span className="truncate border-l border-white/25 pl-2 text-xs font-medium text-white/70">当前上下文：{contextTitle}</span>}</div>
          <div className="flex items-center gap-1">
            {full && agentSessionId && <button type="button" onClick={() => void (proposal ? confirmDraft() : importDraft())} className="rounded bg-white/15 px-2 py-1 text-xs font-semibold hover:bg-white/25">{proposal ? "确认创建草稿" : "读取 Agent 草稿"}</button>}
            {!full && <button type="button" onClick={() => setMinimized(value => !value)} className="rounded p-1.5 hover:bg-white/15" aria-label={minimized ? "展开" : "最小化"}>{minimized ? <Maximize2 className="h-4 w-4" /> : <Minus className="h-4 w-4" />}</button>}
            <button type="button" onClick={() => full ? restore() : router.push("/insight-agent")} className="rounded p-1.5 hover:bg-white/15" aria-label={full ? "还原浮窗" : "最大化"}>{full ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}</button>
            <button type="button" onClick={close} className="rounded p-1.5 hover:bg-white/15" aria-label="关闭"><X className="h-4 w-4" /></button>
          </div>
        </header>
        <div className={`min-h-0 flex-1 ${minimized ? "invisible" : "flex"}`}>
        {connection.source && connection.key === connectionKey ? (
          <iframe src={connection.source} title="Insight-Agent 原生工作区" className="min-h-0 flex-1 border-0 bg-white" allow="clipboard-read; clipboard-write" />
        ) : (
          <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-ink-muted">
            <div><Bot className="mx-auto mb-3 h-7 w-7 text-primary" /><p>{error || "正在连接 Insight-Agent…"}</p>{error && <button type="button" onClick={() => { setError(""); setConnection({ key: "retry", source: "" }); }} className="ui-button-secondary mt-4">重试</button>}</div>
          </div>
        )}
        </div>
      </section>
    </>
  );
}
