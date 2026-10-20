"use client";

import { PointerEvent, useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import {
  Bot,
  ChevronDown,
  ChevronUp,
  GripHorizontal,
  History,
  Maximize2,
  MessageSquarePlus,
  Minimize2,
  PanelRightOpen,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { usePreferences } from "@/lib/preferences";
import {
  agentWelcomeStorageKey,
  extractPageText,
} from "@/lib/agent-page-context";
import {
  subscribeAgentRoute,
  type AgentRoute as RouteDetail,
} from "@/lib/agent-events";
import { AppDialog, ConfirmDialog, Tooltip, useToast } from "@/components/ui";
import { SessionRail } from "./agent-session-rail";
import { WorkPanel } from "./agent-work-panel";
import { AgentHome } from "./agent-home";
import { ContextEditor } from "./agent-context-editor";
import { contextItems } from "./helpers";
import { taskStages } from "./types";
import type {
  Mode,
  Message,
  Session,
  Artifact,
  ActionProposal,
  Interaction,
} from "./types";

export { InsightAgentShell };

const agentEnglish: Record<string, string> = {
  "Agent 正在工作…": "Agent is working...", "正在生成回答…": "Generating an answer...",
  "正在执行工具…": "Running tools...", "等待你的决策…": "Waiting for your decision...",
  "正在流式生成回答…": "Generating an answer...", "已收到决策，继续执行…": "Decision received; continuing...",
  "无法读取最近工作": "Could not load recent work", "无法读取当前工作": "Could not load this work",
  "无法创建对话": "Could not create a conversation", "无法打开对话": "Could not open conversation",
  "无法删除对话": "Could not delete conversation", "无法下载文件": "Could not download file",
  "无法刷新 Context": "Could not refresh context", "无法保存 Context 设置": "Could not save context settings",
  "无法执行业务操作": "Could not perform business action", "无法提交决策": "Could not submit decision",
  "无法启动 Insight Agent": "Could not start Insight Agent", "无法打开 Insight Agent": "Could not open Insight Agent",
  "Agent 暂时无法回答": "Agent cannot answer right now", "生成中断，可重试": "Generation stopped; retry",
  "已停止生成。": "Generation stopped.", "生成失败，可重试。": "Generation failed; retry.",
  "请先停止当前生成，再执行其他任务": "Stop the current generation before starting another task",
  "请先停止当前生成，再新建对话": "Stop the current generation before starting a new conversation",
  "无法创建 Insight Agent": "Could not create Insight Agent", "无法创建自由讨论": "Could not start a free discussion",
  "操作已确认并写入业务工作台": "Action confirmed and saved to the workbench",
};
const contextEnglish: Record<string, string> = { "对象描述": "Description", "业务内容": "Business content", "结构化信息": "Structured data", "来源链接": "Source link", "关联业务对象": "Related items" };

function InsightAgentShell() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading } = useAuth();
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [mode, setMode] = useState<Mode>("floating");
  const [session, setSession] = useState<Session | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [workingStatus, setWorkingStatus] = useState("Agent 正在工作…");
  const [contextOpen, setContextOpen] = useState(false);
  const [error, setError] = useState("");
  const [splitWidth, setSplitWidth] = useState(50);
  const [pendingDelete, setPendingDelete] = useState<Session | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [showSessions, setShowSessions] = useState(false);
  const [showWelcomeTip, setShowWelcomeTip] = useState(false);
  const [actionProposal, setActionProposal] = useState<ActionProposal | null>(
    null,
  );
  const [interaction, setInteraction] = useState<Interaction | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const sessionRef = useRef<Session | null>(null);
  const messagesRef = useRef<Message[]>([]);
  const sendingRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
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
  const loadPendingAction = async (sessionId: string) => {
    const response = await authenticatedFetch(
      `/api/agent/sessions/${sessionId}/actions/pending`,
    );
    setActionProposal(
      response.ok ? ((await response.json()) as ActionProposal | null) : null,
    );
  };
  const openSession = async (id: string, nextMode?: Mode) => {
    if (session && session.id !== id) await discardEmptySession(session);
    const response = await authenticatedFetch(`/api/agent/sessions/${id}`);
    if (!response.ok) throw new Error("无法读取当前工作");
    const item = (await response.json()) as Session;
    setSession(item);
    setMessages(item.conversation || []);
    void loadPendingAction(id);
    setOpen(true);
    setMinimized(false);
    setError("");
    if (nextMode) setMode(nextMode);
  };
  const route = async (detail: RouteDetail) => {
    if (sendingRef.current)
      throw new Error("请先停止当前生成，再执行其他任务");
    if (!user)
      return router.push(
        `/auth/login?next=${encodeURIComponent(pathname || "/")}`,
      );
    await discardEmptySession();
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
        (await response.json().catch(() => ({}))).detail ||
          "无法创建 Insight Agent",
      );
    const item = (await response.json()) as Session;
    setSession(item);
    setMessages([]);
    setActionProposal(null);
    setOpen(true);
    setMinimized(false);
    setMode("floating");
    await refreshSessions().catch(() => []);
  };
  const startFreeChat = async (
    forCurrentPage = false,
  ): Promise<Session> => {
    if (sendingRef.current)
      throw new Error("请先停止当前生成，再新建对话");
    await discardEmptySession();
    const response = await authenticatedFetch("/api/agent/chat/sessions", {
      method: "POST",
      headers: forCurrentPage
        ? { "Content-Type": "application/json" }
        : undefined,
      body: forCurrentPage
        ? JSON.stringify({
            title: document.title || "当前页面",
            path: pathname || "/",
            page_text: extractPageText(
              document.getElementById("app-main"),
            ),
          })
        : undefined,
    });
    if (!response.ok) throw new Error("无法创建自由讨论");
    const item = (await response.json()) as Session;
    setSession(item);
    setMessages([]);
    setActionProposal(null);
    setOpen(true);
    setMinimized(false);
    setError("");
    await refreshSessions().catch(() => []);
    return item;
  };
  const discardEmptySession = async (candidate = session) => {
    if (!candidate || messages.length || sending) return;
    await authenticatedFetch(`/api/agent/chat/sessions/${candidate.id}`, {
      method: "DELETE",
    });
    if (session?.id === candidate.id) {
      setSession(null);
      setMessages([]);
      setInput("");
    }
    await refreshSessions().catch(() => []);
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
  const downloadArtifact = async (artifact: Artifact) => {
    const response = await authenticatedFetch(
      `/api/agent/artifacts/${artifact.id}/download`,
    );
    if (!response.ok) throw new Error("无法下载文件");
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = artifact.filename || artifact.title || "agent-output";
    link.click();
    URL.revokeObjectURL(url);
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
    sendingRef.current = true;
    setSending(true);
    setWorkingStatus("正在生成回答…");
    setInteraction(null);
    setError("");
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await authenticatedFetch("/api/agent/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          session_id: targetSession.id,
        }),
        signal: controller.signal,
      });
      if (!response.ok || !response.body)
        throw new Error(
          (await response.json().catch(() => ({}))).detail ||
            "Agent 暂时无法回答",
        );
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let completed = false;
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
            if (packet.status && sessionRef.current?.id === targetSession.id) setWorkingStatus(packet.status);
            if (packet.type === "tool.start" && sessionRef.current?.id === targetSession.id)
              setWorkingStatus("正在执行工具…");
            if (packet.type === "interaction.request") {
              setInteraction({
                request_id: packet.request_id,
                session_id: targetSession.id,
                question: packet.question,
                choices: packet.choices || [],
                multi_select: !!packet.multi_select,
              });
              if (sessionRef.current?.id === targetSession.id) setWorkingStatus("等待你的决策…");
            }
            if (packet.type === "interaction.expire") setInteraction(null);
            if (packet.type === "interaction.resolved") {
              setInteraction((current) => current?.request_id === packet.request_id ? null : current);
              if (sessionRef.current?.id === targetSession.id) setWorkingStatus("正在流式生成回答…");
            }
            if (packet.type === "message.end") {
              completed = true;
              setInteraction((current) => current?.session_id === targetSession.id ? null : current);
              if (sessionRef.current?.id === targetSession.id) setMessages((current) => current.map((item, index) => index === current.length - 1
                ? { ...item, content: packet.text ?? item.content } : item));
            }
            if (packet.action_proposal && sessionRef.current?.id === targetSession.id)
              setActionProposal(packet.action_proposal as ActionProposal);
            if (packet.artifacts?.length) {
              const nextArtifacts = packet.artifacts as Artifact[];
              if (sessionRef.current?.id === targetSession.id) flushSync(() => setMessages((current) =>
                current.map((item, index) =>
                  index === current.length - 1
                    ? {
                        ...item,
                        artifacts: [
                          ...(item.artifacts || []),
                          ...nextArtifacts,
                        ],
                      }
                    : item,
                ),
              ));
            }
            const content =
              packet.type === "text.delta"
                ? packet.delta || packet.text || ""
                : packet.choices?.[0]?.delta?.content || "";
            if (content && sessionRef.current?.id === targetSession.id)
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
      if (!completed) throw new Error("生成中断，可重试");
      setSession((current) =>
        current?.id === targetSession.id ? { ...current, task_status: "done" } : current,
      );
    } catch (reason) {
      const stopped =
        reason instanceof DOMException && reason.name === "AbortError";
      if (sessionRef.current?.id === targetSession.id) setMessages((current) =>
        current.map((item, index) =>
          index === current.length - 1
            ? {
                ...item,
                content:
                  item.content ||
                  (stopped ? "已停止生成。" : "生成失败，可重试。"),
                failed: !stopped,
              }
            : item,
        ),
      );
      if (!stopped)
        setError(
          reason instanceof Error ? reason.message : "Agent 暂时无法回答",
        );
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      sendingRef.current = false;
      setSending(false);
      setInteraction((current) => current?.session_id === targetSession.id ? null : current);
      void refreshSessions().catch(() => undefined);
    }
  };
  const retryMessage = (text: string, assistantIndex: number) => {
    setMessages((current) =>
      current.slice(0, Math.max(0, assistantIndex - 1)),
    );
    void send(text);
  };
  const confirmAction = async () => {
    if (!actionProposal) return;
    const response = await authenticatedFetch(
      `/api/agent/actions/${actionProposal.id}/confirm`,
      { method: "POST" },
    );
    if (!response.ok)
      throw new Error(
        (await response.json().catch(() => ({}))).detail ||
          "无法执行业务操作",
      );
    setActionProposal(null);
    toast(en ? "Action confirmed and saved to the workbench" : "操作已确认并写入业务工作台", "success");
  };
  const resolveInteraction = async (answer: string) => {
    if (!interaction) return;
    const response = await authenticatedFetch(
      `/api/agent/interactions/${encodeURIComponent(interaction.request_id)}/resolve`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: interaction.session_id, answer }),
      },
    );
    if (!response.ok)
      throw new Error(
        (await response.json().catch(() => ({}))).detail || "无法提交决策",
      );
    setInteraction((current) => current?.request_id === interaction.request_id ? null : current);
    setWorkingStatus("已收到决策，继续执行…");
  };
  const stopGeneration = () => {
    const activeSession = sessionRef.current;
    abortRef.current?.abort();
    if (activeSession)
      void authenticatedFetch("/api/agent/chat/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: activeSession.id }),
      });
  };
  useEffect(() => {
    if (user)
      queueMicrotask(() => {
        void refreshSessions().catch(() => undefined);
      });
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (
      !user ||
      localStorage.getItem(agentWelcomeStorageKey(user.id)) === "1"
    )
      return;
    localStorage.setItem(agentWelcomeStorageKey(user.id), "1");
    const show = window.setTimeout(() => setShowWelcomeTip(true), 0);
    const timer = window.setTimeout(() => {
      setShowWelcomeTip(false);
    }, 2000);
    return () => {
      window.clearTimeout(show);
      window.clearTimeout(timer);
    };
  }, [user]);
  useEffect(
    () =>
      subscribeAgentRoute((detail) =>
        void route(detail).catch((reason) =>
          setError(
            reason instanceof Error
              ? reason.message
              : "无法启动 Insight Agent",
          ),
        ),
      ),
    [user, pathname], // eslint-disable-line react-hooks/exhaustive-deps
  );
  const routeFull =
    pathname === "/insight-agent" || pathname === "/workbench/ai";
  const workbenchFull = pathname === "/workbench/ai";
  const requestedSession = searchParams.get("session");
  const activeOpen = open || routeFull;
  const activeMode = routeFull ? "full" : mode;
  useEffect(() => {
    if (user && routeFull && requestedSession && session?.id !== requestedSession)
      queueMicrotask(() =>
        void openSession(requestedSession).catch((reason) =>
          setError(
            reason instanceof Error
              ? reason.message
              : "无法打开 Insight Agent",
          ),
        ),
      );
  }, [requestedSession, routeFull, user]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!routeFull) return;
    return () => {
      const current = sessionRef.current;
      if (current && !messagesRef.current.length && !sendingRef.current)
        void authenticatedFetch(
          `/api/agent/chat/sessions/${current.id}`,
          { method: "DELETE" },
        );
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
    stopGeneration();
    void discardEmptySession().catch(() => undefined);
    setOpen(false);
    setMinimized(false);
    setMode("floating");
    if (routeFull) router.push("/workbench");
  };
  const leaveFull = () => {
    stopGeneration();
    void discardEmptySession().catch(() => undefined);
    setMode("floating");
    if (routeFull) router.back();
  };
  if (loading || !user) return null;
  if (!activeOpen)
    return (
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
        {user && showWelcomeTip && (
          <div className="max-w-56 rounded-xl border border-grid bg-white p-3 text-xs text-ink-secondary shadow-[var(--shadow-elevated)]">
            <p>{en ? "Analyze the current page here." : "这里可以直接分析当前页面。"}</p>
            <button
              type="button"
              onClick={() => {
                localStorage.setItem(
                  agentWelcomeStorageKey(user.id),
                  "1",
                );
                setShowWelcomeTip(false);
              }}
              className="mt-2 text-xs font-medium text-primary"
            >
              {en ? "Dismiss" : "不再提示"}
            </button>
          </div>
        )}
        <button
          type="button"
          onClick={() =>
            user
              ? void startFreeChat(true).catch((reason) =>
                  setError(
                    reason instanceof Error
                      ? reason.message
                      : "无法创建对话",
                  ),
                )
              : router.push(
                  `/auth/login?next=${encodeURIComponent(pathname || "/")}`,
                )
          }
          className="flex h-14 w-14 items-center justify-center rounded-full bg-primary text-white shadow-[var(--shadow-elevated)] transition hover:bg-primary-dark"
          aria-label={en ? "Open Insight Agent" : "打开 Insight Agent"}
        >
          <Bot className="h-5 w-5" />
        </button>
      </div>
    );
  if (minimized)
    return (
      <button
        type="button"
        onClick={() => setMinimized(false)}
        className="fixed bottom-6 right-6 z-50 flex h-14 items-center justify-center rounded-full bg-primary text-white shadow-[var(--shadow-elevated)]"
        aria-label={en ? "Restore Insight Agent" : "还原 Insight Agent"}
      >
        <Bot className="h-5 w-5" />
      </button>
    );
  const full = activeMode === "full";
  const split = activeMode === "split";
  const context = session?.context_snapshot;
  const panelClass = workbenchFull
    ? "agent-shell agent-workbench fixed bottom-8 top-[9.5rem] z-20 flex overflow-hidden rounded-2xl border border-grid"
    : full
      ? "agent-shell agent-full fixed bottom-0 right-0 top-16 z-20 flex overflow-hidden bg-paper"
      : split
        ? "agent-shell fixed bottom-0 right-0 top-0 z-50 flex min-w-[420px] border-l border-grid bg-paper shadow-[var(--shadow-drawer)]"
        : "agent-shell fixed bottom-4 right-4 z-50 flex h-[min(680px,calc(100dvh-7rem))] w-[calc(100vw-2rem)] overflow-hidden rounded-2xl border border-grid bg-paper shadow-[var(--shadow-elevated)] sm:bottom-6 sm:right-6 sm:h-[min(760px,calc(100dvh-3rem))] sm:w-[min(520px,calc(100vw-2rem))] sm:resize";
  return (
    <section
      ref={panelRef}
      style={split ? { width: `${splitWidth}%` } : undefined}
      className={panelClass}
      aria-label="Insight Agent"
    >
      {showSessions && !full && (
        <AppDialog
          open={showSessions}
          onClose={() => setShowSessions(false)}
          title={en ? "Conversation history" : "对话历史"}
          description={en ? "Continue recent work or start a new conversation." : "继续最近的工作，或创建一条新的自由讨论。"}
          className="max-w-md"
        >
          <div className="mb-3">
            <button
              type="button"
              onClick={() =>
                void startFreeChat()
                  .then(() => setShowSessions(false))
                  .catch((reason) =>
                    setError(
                      reason instanceof Error
                        ? reason.message
                        : "无法创建对话",
                    ),
                  )
              }
              className="flex w-full items-center gap-2 rounded-xl bg-primary px-3 py-2.5 text-sm font-medium text-white"
            >
              <MessageSquarePlus className="h-4 w-4" />
              {en ? "New conversation" : "新建自由对话"}
            </button>
          </div>
          <nav
            className="max-h-[min(28rem,calc(100dvh-15rem))] overflow-y-auto px-2 pb-3"
            aria-label={en ? "Recent conversations" : "最近对话"}
          >
            {sessions.length ? (
              sessions.map((item) => (
                <div
                  key={item.id}
                  className={`group mb-1 flex items-center rounded-xl ${session?.id === item.id ? "bg-primary-soft" : "hover:bg-surface-subtle"}`}
                >
                  <button
                    type="button"
                    onClick={() =>
                      void openSession(item.id)
                        .then(() => setShowSessions(false))
                        .catch((reason) =>
                          setError(
                            reason instanceof Error
                              ? reason.message
                              : "无法打开对话",
                          ),
                        )
                    }
                    className="min-w-0 flex-1 px-3 py-2.5 text-left"
                  >
                    <span className="block truncate text-sm font-medium text-ink">
                      {item.task_title || item.title}
                    </span>
                    <span className="block truncate text-[11px] text-ink-muted">
                      {item.context_title || (en ? "Free discussion" : "自由讨论")}
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => void deleteSession(item.id)}
                    className="mr-2 rounded-lg p-2 text-ink-muted opacity-0 hover:bg-warning-soft hover:text-warning group-hover:opacity-100 focus:opacity-100"
                    aria-label={en ? `Delete ${item.task_title || item.title}` : `删除 ${item.task_title || item.title}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))
            ) : (
              <p className="px-3 py-8 text-center text-sm text-ink-muted">
                {en ? "No conversations yet; start one." : "还没有对话，先新建一个。"}
              </p>
            )}
          </nav>
        </AppDialog>
      )}
      <ConfirmDialog
        open={!!pendingDelete}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null);
        }}
        title={en ? "Delete this conversation?" : "删除这条对话？"}
        description={
          pendingDelete
            ? (en ? `"${pendingDelete.task_title || pendingDelete.title}" and all its messages will be deleted permanently.` : `"${pendingDelete.task_title || pendingDelete.title}"及全部消息将被永久删除。`)
            : undefined
        }
        confirmLabel={en ? "Delete" : "删除"}
        danger
        onConfirm={() => void confirmDeleteSession()}
      />
      {split && (
        <button
          type="button"
          onPointerDown={resizeSplit}
          className="absolute -left-2 top-0 z-10 flex h-full w-4 cursor-col-resize items-center justify-center"
          aria-label={en ? "Resize split view" : "调整双屏宽度"}
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
          setError={setError}
        />
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="agent-shell__header flex min-h-16 items-center gap-2 border-b border-grid px-4">
          <button
            type="button"
            onPointerDown={drag}
            className={`${full ? "hidden" : "hidden sm:block"} cursor-grab rounded p-1 text-ink-muted hover:bg-surface-subtle`}
            aria-label={en ? "Drag window" : "拖动浮窗"}
          >
            <GripHorizontal className="h-4 w-4" />
          </button>
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <div className="agent-shell__brand flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-white">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="flex items-center gap-2 truncate text-sm font-semibold">
                <span className="agent-live-dot h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                {session?.task_title || "Insight Agent"}
              </p>
              <p className="truncate text-[11px] text-ink-muted">
                {session
                  ? `${session.context_title || (en ? "Free discussion" : "自由讨论")} · ${session.task_status === "waiting_confirmation" ? (en ? "Waiting for confirmation" : "等待确认") : (en ? "Ready" : "准备就绪")}`
                  : (en ? "Solution Practices and Insight Agent" : "方案实践与 Insight Agent")}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {!full && (
              <Tooltip label={en ? "Open conversation history" : "打开对话历史"}>
                <button
                  type="button"
                  onClick={() => setShowSessions(true)}
                  className="ui-icon-button"
                  aria-label={en ? "Open conversation history" : "打开对话历史"}
                >
                  <History className="h-4 w-4" />
                </button>
              </Tooltip>
            )}
            {!full && (
              <button
                type="button"
                onClick={() => setMode(split ? "floating" : "split")}
                className="ui-icon-button hidden sm:inline-flex"
                aria-label={split ? (en ? "Restore floating window" : "还原浮窗") : (en ? "Expand on the right" : "在右侧展开")}
              >
                <PanelRightOpen className="h-4 w-4" />
              </button>
            )}
            <Tooltip
              label={full ? (en ? "Restore floating window" : "还原右下角浮窗") : (en ? "Open full Insight Agent" : "进入完整 Insight Agent")}
            >
              <button
                type="button"
                onClick={() => (full ? leaveFull() : setMode("full"))}
                className="ui-icon-button"
                aria-label={
                  full ? (en ? "Restore floating window" : "还原右下角浮窗") : (en ? "Open full Insight Agent" : "进入完整 Insight Agent")
                }
              >
                {full ? (
                  <Minimize2 className="h-4 w-4" />
                ) : (
                  <Maximize2 className="h-4 w-4" />
                )}
              </button>
            </Tooltip>
            {!full && (
              <Tooltip label={en ? "Minimize" : "最小化"}>
                <button
                  type="button"
                  onClick={() => setMinimized(true)}
                  className="ui-icon-button"
                  aria-label={en ? "Minimize" : "最小化"}
                >
                  <Minimize2 className="h-4 w-4" />
                </button>
              </Tooltip>
            )}
            <Tooltip label={en ? "Close Insight Agent" : "关闭 Insight Agent"}>
              <button
                type="button"
                onClick={closeAgent}
                className="ui-icon-button ui-icon-button-danger"
                aria-label={en ? "Close" : "关闭"}
              >
                <X className="h-4 w-4" />
              </button>
            </Tooltip>
          </div>
        </header>
        {session ? (
          <>
            {session.context_type !== "chat" && (
              <div className="border-b border-grid bg-surface-subtle px-4 py-2">
                <button
                  type="button"
                  onClick={() => setContextOpen((value) => !value)}
                  className="flex w-full items-center justify-between gap-3 rounded-lg px-1 py-1 text-left hover:bg-white/60"
                  aria-expanded={contextOpen}
                >
                  <span className="min-w-0">
                    <span className="flex items-center gap-2 text-xs font-semibold text-ink">
                      <span
                        className="h-2 w-2 rounded-full bg-primary"
                        aria-hidden="true"
                      />
                      {en ? "Work context linked" : "已绑定工作上下文"}
                    </span>
                    <span className="mt-0.5 block truncate text-[11px] text-ink-muted">
                      {context?.title || session.context_title}
                    </span>
                  </span>
                  {contextOpen ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </button>
                <div className="mt-2 flex flex-wrap gap-1.5 px-1">
                  <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[10px] font-medium text-primary">
                    {en ? ({ "理解": "Understand", "设计": "Design", "验证": "Validate", "实现": "Implement", "交付": "Deliver" }[taskStages[session.task_key || ""]] || "Analyze") : (taskStages[session.task_key || ""] || "分析")}
                  </span>
                  {contextItems(context).map((item) => (
                    <span
                      key={item}
                      className="rounded-full bg-white px-2 py-0.5 text-[10px] text-ink-secondary"
                    >
                      ✓ {en ? (contextEnglish[item] || item) : item}
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
              pathname={pathname || "/"}
              session={session}
              messages={messages}
              input={input}
              setInput={setInput}
              sending={sending}
              workingStatus={en ? (agentEnglish[workingStatus] || workingStatus) : workingStatus}
              send={send}
              downloadArtifact={downloadArtifact}
              stop={stopGeneration}
              retryMessage={retryMessage}
              actionProposal={actionProposal}
              interaction={interaction}
              resolveInteraction={resolveInteraction}
              confirmAction={confirmAction}
              error={en ? (agentEnglish[error] || error) : error}
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
          />
        )}
      </div>
    </section>
  );
}
