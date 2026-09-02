"use client";

import { FormEvent, PointerEvent, useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import {
  Bot,
  ChevronDown,
  ChevronUp,
  Code2,
  FolderOpen,
  GripHorizontal,
  Maximize2,
  MessageSquarePlus,
  Minimize2,
  Paperclip,
  PanelRightOpen,
  Send,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAuth } from "@/components/auth-provider";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

type Mode = "floating" | "split" | "full";
type Message = { role: "user" | "assistant"; content: string };
type Context = {
  title: string;
  summary?: string;
  context_type: string;
  content?: string;
  metadata?: Record<string, unknown>;
  source_url?: string;
  related_entities?: { title: string }[];
  supplement?: string;
  excluded_sections?: string[];
};
type Session = {
  id: string;
  title: string;
  context_type: string;
  context_title: string;
  context_snapshot?: Context;
  task_key?: string;
  task_title?: string;
  task_status?: string;
  default_prompt?: string;
  conversation?: Message[];
};
type RouteDetail = {
  contextType: "github_project" | "cloud_solution" | "requirement" | "solution";
  contextId: string;
  actionKey: string;
};
type Artifact = {
  id: string;
  title: string;
  type: string;
  knowledge_status: string;
  created_at: string;
};

const nextActions: Record<string, string[]> = {
  technology_research: ["创建 Requirement", "对比技术路线", "规划 PoC"],
  technology_value: ["创建 Requirement", "深入研究", "规划 PoC"],
  solution_analysis: ["技术架构分析", "形成我的 Solution", "规划 PoC"],
  solution_architecture: ["规划 PoC", "形成我的 Solution", "开始实现"],
  solution_design: ["规划 PoC", "开始实现", "生成技术材料"],
  requirement_analysis: ["完善需求", "设计 Solution", "关联已有 Solution"],
  requirement_refine: ["确认 Draft", "设计 Solution", "规划 PoC"],
  poc_plan: ["开始验证", "开始实现", "生成部署材料"],
  validation: ["回到架构设计", "开始实现", "生成测试报告"],
  implementation: ["查看工作文件", "开始验证", "生成部署材料"],
};

function contextItems(context?: Context) {
  if (!context) return [];
  return [
    context.summary && "对象描述",
    context.content && "业务内容",
    Object.keys(context.metadata || {}).length && "结构化信息",
    context.source_url && "来源链接",
    context.related_entities?.length && "关联业务对象",
  ].filter(Boolean) as string[];
}

const taskStages: Record<string, string> = {
  technology_research: "Discover / Understand", technology_value: "Understand",
  solution_analysis: "Understand", solution_architecture: "Design", solution_design: "Design",
  requirement_analysis: "Understand", requirement_refine: "Design", poc_plan: "PoC",
  validation: "Validate", implementation: "Build", materials: "Deliver",
};

function MarkdownMessage({ children }: { children: string }) {
  return (
    <div className="prose prose-sm max-w-none break-words prose-headings:mb-2 prose-headings:mt-5 prose-p:my-2 prose-pre:overflow-x-auto prose-pre:rounded-xl prose-pre:bg-[var(--color-code)] prose-pre:text-[var(--color-code-ink)] prose-code:before:content-none prose-code:after:content-none prose-a:text-primary prose-table:block prose-table:overflow-x-auto">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: (props) => <a {...props} target="_blank" rel="noreferrer" />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}

export function InsightAgentShell() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading } = useAuth();
  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [mode, setMode] = useState<Mode>("floating");
  const [session, setSession] = useState<Session | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [workingStatus, setWorkingStatus] = useState("Agent 正在工作…");
  const [contextOpen, setContextOpen] = useState(false);
  const [error, setError] = useState("");
  const [splitWidth, setSplitWidth] = useState(50);
  const [pendingDelete, setPendingDelete] = useState<Session | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [showWelcomeTip, setShowWelcomeTip] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const sessionRef = useRef<Session | null>(null);
  const messagesRef = useRef<Message[]>([]);
  const sendingRef = useRef(false);
  useEffect(() => {
    sessionRef.current = session;
    messagesRef.current = messages;
    sendingRef.current = sending;
  }, [session, messages, sending]);

  const refreshSessions = async () => {
    if (!user) return [];
    const response = await authenticatedFetch("/api/agent/chat/sessions");
    if (!response.ok) throw new Error("无法读取最近工作");
    const items = ((await response.json()) as { items: Session[] }).items;
    setSessions(items);
    return items;
  };
  const openSession = async (id: string, nextMode?: Mode) => {
    const response = await authenticatedFetch(`/api/agent/sessions/${id}`);
    if (!response.ok) throw new Error("无法读取当前工作");
    const item = (await response.json()) as Session;
    setSession(item);
    setMessages(item.conversation || []);
    setOpen(true);
    setMinimized(false);
    setError("");
    if (nextMode) setMode(nextMode);
  };
  const route = async (detail: RouteDetail) => {
    if (!user)
      return router.push(
        `/auth/login?next=${encodeURIComponent(pathname || "/")}`,
      );
    const response = await authenticatedFetch("/api/agent/routes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        context_type: detail.contextType,
        context_id: detail.contextId,
        action_key: detail.actionKey,
      }),
    });
    if (!response.ok)
      throw new Error(
        (await response.json().catch(() => ({}))).detail || "无法创建 AI 工作",
      );
    const item = (await response.json()) as Session;
    setSession(item);
    setMessages([]);
    setOpen(true);
    setMinimized(false);
    setMode("floating");
    void refreshSessions().catch(() => undefined);
  };
  const startFreeChat = async (forCurrentPage = false): Promise<Session> => {
    const response = await authenticatedFetch("/api/agent/chat/sessions", {
      method: "POST",
      headers: forCurrentPage ? { "Content-Type": "application/json" } : undefined,
      body: forCurrentPage ? JSON.stringify({ title: document.title || "当前页面", path: pathname || "/" }) : undefined,
    });
    if (!response.ok) throw new Error("无法创建自由讨论");
    const item = (await response.json()) as Session;
    setSession(item);
    setMessages([]);
    setOpen(true);
    setMinimized(false);
    setError("");
    void refreshSessions().catch(() => undefined);
    return item;
  };
  const discardEmptySession = async (candidate = session) => {
    if (!candidate || messages.length || sending) return;
    await authenticatedFetch(`/api/agent/chat/sessions/${candidate.id}`, { method: "DELETE" });
    if (session?.id === candidate.id) {
      setSession(null);
      setMessages([]);
      setInput("");
    }
    void refreshSessions().catch(() => undefined);
  };
  const deleteSession = async (id: string) => {
    setPendingDelete(sessions.find((item) => item.id === id) || null);
  };
  const confirmDeleteSession = async () => {
    if (!pendingDelete || deleting) return;
    const id = pendingDelete.id;
    setDeleting(true);
    const response = await authenticatedFetch(
      `/api/agent/chat/sessions/${id}`,
      { method: "DELETE" },
    );
    if (!response.ok) {
      setDeleting(false);
      throw new Error("无法删除对话");
    }
    if (session?.id === id) {
      setSession(null);
      setMessages([]);
      setInput("");
    }
    setPendingDelete(null);
    setDeleting(false);
    await refreshSessions();
  };
  const refreshArtifacts = async () => {
    if (!user) return;
    const response = await authenticatedFetch("/api/agent/artifacts");
    if (!response.ok) return;
    setArtifacts(((await response.json()) as { items: Artifact[] }).items);
  };
  const refreshContext = async () => {
    if (!session) return;
    const response = await authenticatedFetch(
      `/api/agent/sessions/${session.id}/context/refresh`,
      { method: "POST" },
    );
    if (!response.ok) throw new Error("无法刷新 Context");
    const item = (await response.json()) as Session;
    setSession(item);
  };
  const saveContext = async (
    supplement: string,
    excludedSections: string[],
  ) => {
    if (!session) return;
    const response = await authenticatedFetch(
      `/api/agent/sessions/${session.id}/context`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          supplement,
          excluded_sections: excludedSections,
        }),
      },
    );
    if (!response.ok) throw new Error("无法保存 Context 设置");
    setSession((await response.json()) as Session);
  };
  const saveArtifact = async () => {
    if (!session) return;
    const response = await authenticatedFetch(
      `/api/agent/sessions/${session.id}/artifacts`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: session.task_title || session.title,
          type: "Markdown",
        }),
      },
    );
    if (!response.ok)
      throw new Error(
        (await response.json().catch(() => ({}))).detail || "无法保存成果",
      );
    await refreshArtifacts();
  };
  const send = async (
    text: string,
    targetSession: Session | null = session,
  ) => {
    const message = text.trim();
    if (!message || sending || !targetSession) return;
    setMessages((current) => [
      ...current,
      { role: "user", content: message },
      { role: "assistant", content: "" },
    ]);
    setInput("");
    setSending(true);
    setWorkingStatus("正在生成回答…");
    setError("");
    try {
      const response = await authenticatedFetch("/api/agent/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, session_id: targetSession.id }),
      });
      if (!response.ok || !response.body)
        throw new Error(
          (await response.json().catch(() => ({}))).detail ||
            "Agent 暂时无法回答",
        );
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines)
          if (line.startsWith("data: ") && line !== "data: [DONE]") {
            const packet = JSON.parse(line.slice(6));
            if (packet.error) throw new Error(packet.error);
            if (packet.status) setWorkingStatus(packet.status);
            const content = packet.choices?.[0]?.delta?.content || "";
            if (content)
              flushSync(() =>
                setMessages((current) =>
                  current.map((item, index) =>
                    index === current.length - 1
                      ? { ...item, content: item.content + content }
                      : item,
                  ),
                ),
              );
          }
      }
      setSession((current) =>
        current ? { ...current, task_status: "working" } : current,
      );
    } catch (reason) {
      setMessages((current) => current.slice(0, -1));
      setError(reason instanceof Error ? reason.message : "Agent 暂时无法回答");
    } finally {
      setSending(false);
      void refreshSessions().catch(() => undefined);
    }
  };
  useEffect(() => {
    if (user)
      queueMicrotask(() => {
        void refreshSessions().catch(() => undefined);
        void refreshArtifacts();
      });
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (user && localStorage.getItem("insight_agent_welcome_dismissed") !== "1")
      queueMicrotask(() => setShowWelcomeTip(true));
  }, [user]);
  useEffect(() => {
    const handler = (event: Event) => {
      void route((event as CustomEvent<RouteDetail>).detail).catch((reason) =>
        setError(reason instanceof Error ? reason.message : "无法启动 AI 工作"),
      );
    };
    window.addEventListener("insight-agent:route", handler);
    return () => window.removeEventListener("insight-agent:route", handler);
  }, [user, pathname]); // eslint-disable-line react-hooks/exhaustive-deps
  const routeFull = pathname === "/insight-agent" || pathname === "/workbench/ai";
  const requestedSession = searchParams.get("session");
  const activeOpen = open || routeFull;
  const activeMode = routeFull ? "full" : mode;
  useEffect(() => {
    if (user && routeFull && requestedSession && session?.id !== requestedSession)
      queueMicrotask(() => void openSession(requestedSession).catch((reason) =>
        setError(reason instanceof Error ? reason.message : "无法打开 AI 工作"),
      ));
  }, [requestedSession, routeFull, user]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!routeFull) return;
    return () => {
      const current = sessionRef.current;
      if (current && !messagesRef.current.length && !sendingRef.current)
        void authenticatedFetch(`/api/agent/chat/sessions/${current.id}`, { method: "DELETE" });
    };
  }, [routeFull]);
  useEffect(() => {
    if (activeMode !== "floating" || !panelRef.current) return;
    for (const property of ["left", "top", "right", "bottom"])
      panelRef.current.style.removeProperty(property);
  }, [activeMode, activeOpen]);
  useEffect(() => {
    document.documentElement.dataset.agentSplit =
      activeMode === "split" && activeOpen ? "true" : "false";
    document.documentElement.style.setProperty(
      "--agent-split-width",
      `${splitWidth}vw`,
    );
    return () => {
      delete document.documentElement.dataset.agentSplit;
      document.documentElement.style.removeProperty("--agent-split-width");
    };
  }, [activeMode, activeOpen, splitWidth]);
  const drag = (event: PointerEvent<HTMLButtonElement>) => {
    if (mode !== "floating" || !panelRef.current) return;
    const panel = panelRef.current;
    const rect = panel.getBoundingClientRect();
    const startX = event.clientX;
    const startY = event.clientY;
    const move = (moveEvent: globalThis.PointerEvent) => {
      panel.style.left = `${Math.max(8, rect.left + moveEvent.clientX - startX)}px`;
      panel.style.top = `${Math.max(8, rect.top + moveEvent.clientY - startY)}px`;
      panel.style.right = "auto";
      panel.style.bottom = "auto";
    };
    const stop = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop);
  };
  const resizeSplit = () => {
    const move = (moveEvent: globalThis.PointerEvent) =>
      setSplitWidth(
        Math.max(
          35,
          Math.min(70, 100 - (moveEvent.clientX / window.innerWidth) * 100),
        ),
      );
    const stop = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop);
  };
  const closeAgent = () => {
    void discardEmptySession().catch(() => undefined);
    setOpen(false);
    setMinimized(false);
    setMode("floating");
    if (routeFull) router.push("/workbench");
  };
  const leaveFull = () => {
    void discardEmptySession().catch(() => undefined);
    setMode("floating");
    if (routeFull) router.back();
  };
  if (loading) return null;
  if (!activeOpen)
    return (
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
        {user && showWelcomeTip && (
          <div className="max-w-56 rounded-xl border border-grid bg-white p-3 text-xs text-ink-secondary shadow-[var(--shadow-elevated)]">
            <p>这里可以直接分析当前页面。</p>
            <button type="button" onClick={() => { localStorage.setItem("insight_agent_welcome_dismissed", "1"); setShowWelcomeTip(false); }} className="mt-2 text-xs font-medium text-primary">不再提示</button>
          </div>
        )}
        <button
          type="button"
          onClick={() => user ? void startFreeChat(true).catch((reason) => setError(reason instanceof Error ? reason.message : "无法创建对话")) : router.push(`/auth/login?next=${encodeURIComponent(pathname || "/")}`)}
          className="flex h-14 items-center gap-2 rounded-full bg-primary px-5 text-sm font-semibold text-white shadow-[var(--shadow-elevated)] transition hover:bg-primary-dark"
          aria-label="分析当前页面"
        >
          <Bot className="h-5 w-5" />
          AI 工作台
        </button>
      </div>
    );
  if (minimized)
    return (
      <button
        type="button"
        onClick={() => setMinimized(false)}
        className="fixed bottom-6 right-6 z-50 flex h-14 items-center justify-center rounded-full bg-primary text-white shadow-[var(--shadow-elevated)]"
        aria-label="还原 AI 工作台"
      >
        <Bot className="h-5 w-5" />
      </button>
    );
  const full = activeMode === "full";
  const split = activeMode === "split";
  const context = session?.context_snapshot;
  const panelClass = full
    ? "agent-full fixed bottom-0 right-0 top-16 z-20 flex overflow-hidden bg-paper"
    : split
      ? "fixed bottom-0 right-0 top-0 z-50 flex min-w-[420px] border-l border-grid bg-paper shadow-[var(--shadow-drawer)]"
      : "fixed bottom-6 right-6 z-50 flex h-[min(720px,calc(100vh-3rem))] w-[min(480px,calc(100vw-2rem))] min-w-[360px] resize overflow-hidden rounded-2xl border border-grid bg-paper shadow-[var(--shadow-elevated)]";
  return (
    <section
      ref={panelRef}
      style={split ? { width: `${splitWidth}%` } : undefined}
      className={panelClass}
      aria-label="AI 工作台"
    >
      {pendingDelete && (
        <div
          className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/30 p-4 backdrop-blur-[2px]"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-session-title"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !deleting)
              setPendingDelete(null);
          }}
        >
          <div className="w-full max-w-sm rounded-2xl border border-grid bg-white p-5 shadow-[var(--shadow-elevated)]">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-warning-soft text-warning">
              <Trash2 className="h-5 w-5" />
            </div>
            <h2 id="delete-session-title" className="mt-4 text-base font-semibold text-ink">
              删除这条对话？
            </h2>
            <p className="mt-2 truncate text-sm text-ink-secondary">
              {pendingDelete.task_title || pendingDelete.title}
            </p>
            <p className="mt-1 text-xs leading-5 text-ink-muted">
              对话及全部消息将被永久删除，此操作无法撤销。
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                disabled={deleting}
                onClick={() => setPendingDelete(null)}
                className="rounded-lg border border-grid px-4 py-2 text-sm font-medium text-ink-secondary hover:bg-surface-subtle disabled:opacity-50"
              >
                取消
              </button>
              <button
                type="button"
                disabled={deleting}
                onClick={() => void confirmDeleteSession().catch((reason) => setError(reason instanceof Error ? reason.message : "无法删除对话"))}
                className="rounded-lg bg-warning px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
              >
                {deleting ? "正在删除…" : "确认删除"}
              </button>
            </div>
          </div>
        </div>
      )}
      {split && (
        <button
          type="button"
          onPointerDown={resizeSplit}
          className="absolute -left-2 top-0 z-10 flex h-full w-4 cursor-col-resize items-center justify-center"
          aria-label="调整双屏宽度"
        >
          <span className="h-10 w-1 rounded-full bg-grid hover:bg-primary" />
        </button>
      )}
      {full && (
        <SessionRail
          sessions={sessions}
          session={session}
          openSession={openSession}
          startFreeChat={startFreeChat}
          deleteSession={deleteSession}
          artifacts={artifacts}
          setError={setError}
        />
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex min-h-14 items-center gap-2 border-b border-grid bg-white px-3">
          <button
            type="button"
            onPointerDown={drag}
            className={`${full ? "hidden" : "hidden sm:block"} cursor-grab rounded p-1 text-ink-muted hover:bg-surface-subtle`}
            aria-label="拖动浮窗"
          >
            <GripHorizontal className="h-4 w-4" />
          </button>
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-white">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-bold">
                {session?.task_title || "AI 工作台"}
              </p>
              <p className="truncate text-[11px] text-ink-muted">
                {session
                  ? `${session.context_title || "自由讨论"} · ${session.task_status === "waiting_confirmation" ? "等待确认" : "准备就绪"}`
                  : "需求、方案与 AI 工作"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {!full && (
              <>
                <select value={session?.id || ""} onChange={(event) => event.target.value && void openSession(event.target.value).catch((reason) => setError(reason instanceof Error ? reason.message : "无法打开对话"))} className="max-w-28 rounded border border-grid bg-white px-1 py-1 text-xs text-ink-secondary" aria-label="切换对话">
                  <option value="">对话</option>
                  {sessions.map((item) => <option key={item.id} value={item.id}>{item.task_title || item.title}</option>)}
                </select>
                <button type="button" onClick={() => void startFreeChat().catch((reason) => setError(reason instanceof Error ? reason.message : "无法创建对话"))} className="rounded p-2 text-ink-muted hover:bg-primary-soft hover:text-primary" aria-label="新对话"><MessageSquarePlus className="h-4 w-4" /></button>
              </>
            )}
            {!full && (
              <button
                type="button"
                onClick={() => setMode(split ? "floating" : "split")}
                className="rounded p-2 text-ink-muted hover:bg-primary-soft hover:text-primary"
                aria-label={split ? "还原浮窗" : "在右侧展开"}
              >
                <PanelRightOpen className="h-4 w-4" />
              </button>
            )}
            <button
              type="button"
              onClick={() => (full ? leaveFull() : setMode("full"))}
              className="rounded p-2 text-ink-muted hover:bg-primary-soft hover:text-primary"
              aria-label={full ? "还原右下角浮窗" : "进入完整 AI 工作台"}
            >
              {full ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </button>
            {!full && (
              <button
                type="button"
                onClick={() => setMinimized(true)}
                className="rounded p-2 text-ink-muted hover:bg-primary-soft hover:text-primary"
                aria-label="最小化"
              >
                <Minimize2 className="h-4 w-4" />
              </button>
            )}
            <button
              type="button"
              onClick={closeAgent}
              className="rounded p-2 text-ink-muted hover:bg-warning-soft hover:text-warning"
              aria-label="关闭"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </header>
        {session ? (
          <>
            {session.context_type !== "chat" && (
              <div className="border-b border-grid bg-surface-subtle px-4 py-2">
                <button
                  type="button"
                  onClick={() => setContextOpen((value) => !value)}
                  className="flex w-full items-center justify-between text-left"
                >
                  <span className="text-xs font-semibold text-ink">
                    当前上下文 · {context?.title || session.context_title}
                  </span>
                  {contextOpen ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </button>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[10px] font-medium text-primary">Solution Architect</span>
                  <span className="rounded-full bg-white px-2 py-0.5 text-[10px] text-ink-secondary">{taskStages[session.task_key || ""] || "Understand"}</span>
                  {contextItems(context).map((item) => (
                    <span
                      key={item}
                      className="rounded-full bg-white px-2 py-0.5 text-[10px] text-ink-secondary"
                    >
                      ✓ {item}
                    </span>
                  ))}
                </div>
                {contextOpen && context && (
                  <ContextEditor
                    context={context}
                    refresh={refreshContext}
                    save={saveContext}
                    setError={setError}
                  />
                )}
              </div>
            )}
            <WorkPanel
              session={session}
              messages={messages}
              input={input}
              setInput={setInput}
              sending={sending}
              workingStatus={workingStatus}
              send={send}
              saveArtifact={saveArtifact}
              error={error}
              setError={setError}
            />
          </>
        ) : (
          <AgentHome
            input={input}
            setInput={setInput}
            sending={sending}
            startFreeChat={startFreeChat}
            send={send}
            setError={setError}
            route={route}
          />
        )}
      </div>
    </section>
  );
}

function SessionRail({
  sessions,
  session,
  openSession,
  startFreeChat,
  deleteSession,
  artifacts,
  setError,
}: {
  sessions: Session[];
  session: Session | null;
  openSession(id: string): Promise<void>;
  startFreeChat(): Promise<Session>;
  deleteSession(id: string): Promise<void>;
  artifacts: Artifact[];
  setError(value: string): void;
}) {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-grid bg-surface-subtle lg:flex">
      <div className="p-3">
        <button
          type="button"
          onClick={() =>
            void startFreeChat().catch((reason) =>
              setError(
                reason instanceof Error ? reason.message : "无法创建对话",
              ),
            )
          }
          className="flex w-full items-center gap-2 rounded-lg border border-grid bg-white px-3 py-2.5 text-sm font-medium text-ink hover:bg-primary-soft"
        >
          <MessageSquarePlus className="h-4 w-4" />
          新对话
        </button>
      </div>
      <nav
        className="min-h-0 flex-1 overflow-y-auto px-2"
        aria-label="对话历史"
      >
        <p className="px-2 pb-2 text-[11px] font-medium text-ink-muted">最近</p>
        {sessions.map((item) => (
          <div
            key={item.id}
            className={`group mb-0.5 flex items-center rounded-lg ${session?.id === item.id ? "bg-white shadow-sm" : "hover:bg-white"}`}
          >
            <button
              type="button"
              onClick={() =>
                void openSession(item.id).catch((reason) =>
                  setError(
                    reason instanceof Error ? reason.message : "无法打开对话",
                  ),
                )
              }
              className="min-w-0 flex-1 px-3 py-2 text-left"
            >
              <p
                className={`truncate text-sm ${session?.id === item.id ? "font-medium text-ink" : "text-ink-secondary"}`}
              >
                {item.task_title || item.title}
              </p>
            </button>
            <button
              type="button"
              onClick={() =>
                void deleteSession(item.id).catch((reason) =>
                  setError(
                    reason instanceof Error ? reason.message : "无法删除对话",
                  ),
                )
              }
              className="mr-1 rounded p-1.5 text-ink-muted opacity-0 hover:bg-warning-soft hover:text-warning group-hover:opacity-100 focus:opacity-100"
              aria-label={`删除 ${item.task_title || item.title}`}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </nav>
      <div className="border-t border-grid p-3 text-xs text-ink-muted">
        <div className="flex items-center justify-between rounded-lg px-2 py-2">
          <span className="flex items-center gap-2">
            <FolderOpen className="h-4 w-4" />
            工作成果
          </span>
          <span>{artifacts.length}</span>
        </div>
      </div>
    </aside>
  );
}

function WorkPanel({
  session,
  messages,
  input,
  setInput,
  sending,
  workingStatus,
  send,
  saveArtifact,
  error,
  setError,
}: {
  session: Session;
  messages: Message[];
  input: string;
  setInput(value: string): void;
  sending: boolean;
  workingStatus: string;
  send(text: string): void;
  saveArtifact(): Promise<void>;
  error: string;
  setError(value: string): void;
}) {
  const attach = async (files: FileList | null) => {
    if (!files?.length) return;
    const file = files[0];
    if (file.size > 2_000_000) return setError("附件不能超过 2MB");
    try {
      setInput(
        `${input}${input ? "\n\n" : ""}【附件：${file.name}】\n${(await file.text()).slice(0, 6000)}`,
      );
      setError("");
    } catch {
      setError("该附件无法读取，请上传文本类文件");
    }
  };
  const emptyChat = session.context_type === "chat" && !messages.length;
  return (
    <>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-8">
        <div
          className={`mx-auto max-w-3xl ${emptyChat ? "flex min-h-full items-center justify-center" : ""}`}
        >
          {emptyChat ? (
            <div className="w-full pb-20 text-center">
              <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-white">
                <Sparkles className="h-5 w-5" />
              </div>
              <h1 className="mt-5 text-2xl font-semibold tracking-tight text-ink">
                今天想推进什么工作？
              </h1>
              <p className="mt-2 text-sm text-ink-muted">
                研究、分析、设计和实现，都可以从这里开始。
              </p>
              <div className="mx-auto mt-7 grid max-w-xl gap-2 text-left sm:grid-cols-2">
                {[
                  "调研一个新技术并给出结论",
                  "分析一个方案的架构与限制",
                  "把需求整理成可实施方案",
                  "规划 PoC 或开始 Coding",
                ].map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => setInput(item)}
                    className="rounded-xl border border-grid bg-white px-4 py-3 text-sm text-ink-secondary hover:border-primary hover:text-primary"
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {session.context_type !== "chat" && (
                <div className="mb-8 border-l-2 border-primary pl-4">
                  <p className="text-xs font-medium text-primary">当前任务</p>
                  <p className="mt-1 text-sm leading-6 text-ink-secondary">
                    {session.default_prompt ||
                      "围绕当前上下文完成清晰、可执行的技术分析。"}
                  </p>
                  {!messages.length && (
                    <button
                      type="button"
                      onClick={() =>
                        send(session.default_prompt || "请开始当前任务。")
                      }
                      className="mt-3 text-sm font-medium text-primary hover:underline"
                    >
                      开始任务
                    </button>
                  )}
                </div>
              )}
              {messages.map((message, index) => (
                <article
                  key={`${message.role}-${index}`}
                  className={`mb-6 flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[88%] text-sm leading-7 ${message.role === "user" ? "whitespace-pre-wrap rounded-2xl bg-primary-soft px-4 py-2.5 text-ink" : "min-w-0 text-ink"}`}
                  >
                    {message.content ? (
                      message.role === "assistant" ? (
                        <MarkdownMessage>{message.content}</MarkdownMessage>
                      ) : (
                        message.content
                      )
                    ) : (
                      <span className="animate-pulse text-ink-muted">{workingStatus}</span>
                    )}
                  </div>
                </article>
              ))}
              {messages.length > 0 && (
                <div className="mt-8 border-t border-grid pt-4">
                  <div className="flex justify-between">
                    <p className="text-xs font-medium text-ink-muted">下一步</p>
                    <button
                      type="button"
                      onClick={() => void saveArtifact().catch(() => undefined)}
                      className="text-xs font-medium text-primary"
                    >
                      保存为成果
                    </button>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(
                      nextActions[session.task_key || ""] || [
                        "继续处理",
                        "生成实施建议",
                      ]
                    ).map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => setInput(item)}
                        className="rounded-full border border-grid px-3 py-1.5 text-xs text-ink-secondary hover:border-primary hover:text-primary"
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
          {error && (
            <p
              role="alert"
              className="mt-4 rounded-lg bg-warning-soft p-3 text-xs text-warning"
            >
              {error}
            </p>
          )}
        </div>
      </div>
      <form
        onSubmit={(event: FormEvent) => {
          event.preventDefault();
          send(input);
        }}
        className="border-t border-grid bg-white px-4 py-4"
      >
        <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-grid bg-white p-2 shadow-[var(--shadow-input)] focus-within:border-primary">
          <label
            className="flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-xl text-ink-muted hover:bg-surface-subtle hover:text-primary"
            aria-label="上传附件"
          >
            <Paperclip className="h-4 w-4" />
            <input
              type="file"
              className="sr-only"
              accept=".txt,.md,.json,.csv,.yaml,.yml,.xml,.log,.py,.js,.ts,.tsx,.jsx,.java,.go,.rs,.tf"
              onChange={(event) => {
                void attach(event.target.files);
                event.target.value = "";
              }}
            />
          </label>
          <textarea
            rows={1}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send(input);
              }
            }}
            placeholder="在 AI 工作台中继续"
            className="max-h-40 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none"
          />
          <button
            type="submit"
            disabled={!input.trim() || sending}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-white disabled:opacity-30"
            aria-label="发送"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-2 text-center text-[10px] text-ink-muted">
          AI 生成内容可能有误，请核对关键结论。
        </p>
      </form>
    </>
  );
}

function AgentHome({
  input,
  setInput,
  sending,
  startFreeChat,
  send,
  setError,
  route,
}: {
  input: string;
  setInput(value: string): void;
  sending: boolean;
  startFreeChat(): Promise<Session>;
  send(text: string, session: Session): Promise<void>;
  setError(value: string): void;
  route(detail: RouteDetail): Promise<void>;
}) {
  const [suggestions, setSuggestions] = useState<
    { icon: typeof Sparkles; title: string; object: string; route?: RouteDetail }[]
  >([]);
  useEffect(() => {
    const load = async () => {
      const [hotspotsResponse, catalogResponse, solutionsResponse] = await Promise.all([
        authenticatedFetch("/api/github-trending?since=daily"),
        authenticatedFetch("/api/solutions/catalog"),
        authenticatedFetch("/api/workbench/solutions"),
      ]);
      const hotspots = hotspotsResponse.ok ? (await hotspotsResponse.json()).items || [] : [];
      const catalog = catalogResponse.ok ? (await catalogResponse.json()).items || [] : [];
      const solutions = solutionsResponse.ok ? await solutionsResponse.json() : [];
      const pick = <T,>(items: T[]) => items.length ? items[Math.floor(Math.random() * Math.min(items.length, 8))] : undefined;
      const hotspot = pick<{ repo_name: string }>(hotspots);
      const catalogItem = pick<{ id: number; title: string }>(catalog);
      const solution = pick<{ id: number; name: string }>(solutions);
      setSuggestions([
        { icon: Sparkles, title: "深度调研", object: hotspot?.repo_name || "暂无技术热点", route: hotspot && { contextType: "github_project", contextId: hotspot.repo_name, actionKey: "deep_research" } },
        { icon: Code2, title: "开始实现", object: solution?.name || "请先创建 Solution", route: solution && { contextType: "solution", contextId: String(solution.id), actionKey: "implement" } },
        { icon: FolderOpen, title: "方案分析", object: catalogItem?.title || "暂无 Solution Intelligence", route: catalogItem && { contextType: "cloud_solution", contextId: String(catalogItem.id), actionKey: "analyze" } },
      ]);
    };
    void load().catch(() => setSuggestions([]));
  }, []);
  const submit = async (text: string) => {
    try {
      const item = await startFreeChat();
      await send(text, item);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "无法开始对话");
    }
  };
  return (
    <main className="flex min-h-0 flex-1 flex-col bg-white">
      <div className="flex flex-1 items-center justify-center overflow-y-auto px-5 pb-16">
        <div className="w-full max-w-3xl text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-white shadow-[var(--shadow-brand)]">
            <Sparkles className="h-5 w-5" />
          </div>
          <h1 className="mt-6 text-3xl font-semibold tracking-tight text-ink">
            有什么可以一起完成？
          </h1>
          <p className="mt-3 text-sm text-ink-muted">
            直接描述目标，或从一个常用任务开始。
          </p>
          <div className="mx-auto mt-8 grid max-w-2xl gap-2 sm:grid-cols-3">
            {suggestions.map(({ icon: Icon, title, object, route: target }) => (
              <button
                key={title}
                type="button"
                disabled={!target}
                onClick={() => target && void route(target).catch((reason) => setError(reason instanceof Error ? reason.message : "无法启动任务"))}
                className="flex min-w-0 items-start gap-3 rounded-xl border border-grid px-4 py-3 text-left hover:border-primary hover:bg-primary-soft disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-ink-secondary">{title}</span>
                  <span className="mt-1 block truncate text-xs text-ink-muted">{object}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void submit(input);
        }}
        className="px-4 pb-5"
      >
        <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-grid bg-white p-2 shadow-[var(--shadow-input)] focus-within:border-primary">
          <label className="flex h-10 w-10 cursor-pointer items-center justify-center rounded-xl text-ink-muted hover:bg-surface-subtle hover:text-primary">
            <Paperclip className="h-4 w-4" />
            <input
              type="file"
              className="sr-only"
              accept=".txt,.md,.json,.csv,.yaml,.yml,.py,.js,.ts,.tsx,.tf"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file && file.size <= 2_000_000)
                  void file
                    .text()
                    .then((content) =>
                      setInput(
                        `【附件：${file.name}】\n${content.slice(0, 6000)}`,
                      ),
                    );
                else if (file) setError("附件不能超过 2MB");
                event.target.value = "";
              }}
            />
          </label>
          <textarea
            rows={1}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="描述要推进的需求、方案或任务"
            className="max-h-40 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none"
          />
          <button
            type="submit"
            disabled={!input.trim() || sending}
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-white disabled:opacity-30"
            aria-label="发送"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>
    </main>
  );
}

function ContextEditor({
  context,
  refresh,
  save,
  setError,
}: {
  context: Context;
  refresh(): Promise<void>;
  save(supplement: string, excluded: string[]): Promise<void>;
  setError(value: string): void;
}) {
  const [supplement, setSupplement] = useState(context.supplement || "");
  const [excluded, setExcluded] = useState<string[]>(
    context.excluded_sections || [],
  );
  return (
    <div className="mt-3 rounded-lg bg-white p-3 text-xs leading-5 text-ink-secondary">
      <p>{context.summary || "已注入当前业务对象的授权信息。"}</p>
      {context.source_url && (
        <a
          className="mt-2 block text-primary underline"
          href={context.source_url}
          target="_blank"
          rel="noreferrer"
        >
          查看来源
        </a>
      )}
      <textarea
        value={supplement}
        onChange={(event) => setSupplement(event.target.value)}
        placeholder="补充给 Agent 的上下文"
        className="mt-3 w-full rounded border border-grid p-2 text-xs"
        rows={2}
      />
      <div className="mt-2 flex flex-wrap gap-2">
        {["summary", "content", "metadata", "related_entities"].map((key) => (
          <label key={key} className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={excluded.includes(key)}
              onChange={() =>
                setExcluded((items) =>
                  items.includes(key)
                    ? items.filter((item) => item !== key)
                    : [...items, key],
                )
              }
            />
            不注入 {key}
          </label>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() =>
            void save(supplement, excluded).catch((reason) =>
              setError(
                reason instanceof Error ? reason.message : "无法保存 Context",
              ),
            )
          }
          className="text-xs font-semibold text-primary"
        >
          保存设置
        </button>
        <button
          type="button"
          onClick={() =>
            void refresh().catch((reason) =>
              setError(
                reason instanceof Error ? reason.message : "无法刷新 Context",
              ),
            )
          }
          className="text-xs font-semibold text-primary"
        >
          刷新业务 Context
        </button>
      </div>
    </div>
  );
}
