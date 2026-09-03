"use client";

import { FormEvent, PointerEvent, useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import {
  Bot,
  ChevronDown,
  ChevronUp,
  Copy,
  Code2,
  Download,
  FolderOpen,
  FileText,
  LoaderCircle,
  GripHorizontal,
  History,
  Maximize2,
  MessageSquarePlus,
  Minimize2,
  Paperclip,
  PanelRightOpen,
  Send,
  Sparkles,
  Square,
  RotateCcw,
  Trash2,
  X,
} from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAuth } from "@/components/auth-provider";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { agentWelcomeStorageKey, extractPageText } from "@/lib/agent-page-context";
import { subscribeAgentRoute, type AgentRoute as RouteDetail } from "@/lib/agent-events";
import { AppDialog, ConfirmDialog, Tooltip, useToast } from "@/components/ui";

type Mode = "floating" | "split" | "full";
type Message = { role: "user" | "assistant"; content: string; artifacts?: Artifact[]; failed?: boolean };
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
type Artifact = {
  id: string;
  session_id?: string;
  title: string;
  filename?: string;
  mime_type?: string;
  size_bytes?: number;
  type: string;
  knowledge_status: string;
  created_at: string;
  content?: string;
};

const nextActions: Record<string, string[]> = {
  technology_research: ["收纳为方案实践", "对比技术路线", "规划 PoC"],
  technology_value: ["收纳为方案实践", "深入研究", "规划 PoC"],
  solution_analysis: ["技术架构分析", "收纳为方案实践", "规划 PoC"],
  solution_architecture: ["规划 PoC", "完善方案实践", "开始实现"],
  solution_design: ["规划 PoC", "开始实现", "生成技术材料"],
  requirement_analysis: ["完善背景", "形成方案实践", "关联已有实践"],
  requirement_refine: ["确认背景", "形成方案实践", "规划 PoC"],
  poc_plan: ["开始验证", "开始实现", "生成部署材料"],
  validation: ["回到架构设计", "开始实现", "生成测试报告"],
  implementation: ["查看工作文件", "开始验证", "生成部署材料"],
};

const nextActionVariants: Record<string, string[][]> = {
  technology_research: [["提炼关键结论", "补充竞品对比", "列出 PoC 验证项"], ["判断落地价值", "识别技术风险", "生成调研摘要"], ["输出选型建议", "拆解依赖条件", "形成决策清单"]],
  technology_value: [["量化业务价值", "识别落地依赖", "给出是否验证建议"], ["分析替代方案", "补齐风险证据", "生成决策摘要"]],
  solution_analysis: [["提炼方案亮点", "识别架构限制", "给出适用边界"], ["对比替代路线", "补充风险与缺口", "整理决策摘要"]],
  solution_architecture: [["输出组件关系", "检查集成边界", "列出架构风险"], ["补齐非功能要求", "生成部署拓扑", "规划验证路径"]],
  solution_practice: [["校对实践背景", "补齐事实与缺口", "整理方案目录"], ["生成架构契约", "规划实施步骤", "检查交付材料"]],
  solution_design: [["细化实施阶段", "补充验收标准", "识别设计风险"], ["输出组件清单", "规划部署路径", "生成技术摘要"]],
  requirement_analysis: [["补齐需求缺口", "提炼验收标准", "识别范围风险"], ["整理业务目标", "拆解非功能要求", "形成需求摘要"]],
  requirement_refine: [["检查需求边界", "补充约束条件", "生成确认清单"], ["完善验收标准", "整理待确认项", "形成可执行草稿"]],
  poc_plan: [["定义成功指标", "拆解验证步骤", "列出环境依赖"], ["补充退出条件", "识别 PoC 风险", "生成执行清单"]],
  validation: [["列出验证证据", "检查通过标准", "整理测试范围"], ["补充异常场景", "生成验证报告", "规划后续处置"]],
  implementation: [["拆解文件变更", "制定测试策略", "检查实现风险"], ["生成执行计划", "识别依赖阻塞", "准备部署材料"]],
  materials: [["整理交付目录", "检查引用完整性", "生成材料摘要"], ["补充待确认内容", "统一术语格式", "导出交付清单"]],
};

function recommendedActions(taskKey: string, turn: number) {
  const variants = nextActionVariants[taskKey];
  if (variants?.length) return variants[turn % variants.length];
  return nextActions[taskKey] || ["继续处理", "生成实施建议"];
}

function freeChatPrompts(pathname: string, title = "当前页面") {
  const subject = title.trim().slice(0, 24) || "当前页面";
  if (subject !== "当前页面") return [`“${subject}”解决什么问题？`, `分析“${subject}”的关键风险`, `提炼“${subject}”的核心结论`, `如何验证“${subject}”的可行性？`];
  if (pathname.includes("hotspots")) return ["这个项目解决什么问题？", "评估成熟度和落地风险", "给出 PoC 验证建议", "对比可替代技术"];
  if (pathname.includes("solutions")) return ["提炼这个方案的关键能力", "分析架构与适用边界", "整理成解决方案实践", "列出实施风险"];
  if (pathname.includes("workbench")) return ["继续完善当前方案", "检查背景信息缺口", "规划下一步实施", "生成可交付材料"];
  return ["帮我提炼页面关键信息", "分析潜在风险和机会", "给出下一步行动建议", "把内容整理成方案实践"];
}

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
  technology_research: "理解", technology_value: "理解",
  solution_analysis: "理解", solution_architecture: "设计", solution_design: "设计",
  requirement_analysis: "理解", requirement_refine: "设计", poc_plan: "验证",
  validation: "验证", implementation: "实现", materials: "交付",
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

const formatBytes = (size = 0) => size < 1024 ? `${size} B` : `${(size / 1024).toFixed(size < 10240 ? 1 : 0)} KB`;

export function InsightAgentShell() {
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
  const [showArtifacts, setShowArtifacts] = useState(false);
  const [showSessions, setShowSessions] = useState(false);
  const [artifactPreview, setArtifactPreview] = useState<Artifact | null>(null);
  const [showWelcomeTip, setShowWelcomeTip] = useState(false);
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
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
  const refreshModels = async () => {
    if (!user) return;
    const response = await authenticatedFetch("/api/agent/models");
    if (!response.ok) return;
    const data = (await response.json()) as { items: string[]; default: string };
    setModels(data.items);
    setSelectedModel((current) => current || data.default);
  };
  const openSession = async (id: string, nextMode?: Mode) => {
    if (sendingRef.current) throw new Error("请先停止当前生成，再切换对话");
    if (session && session.id !== id) await discardEmptySession(session);
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
    if (sendingRef.current) throw new Error("请先停止当前生成，再执行其他任务");
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
        (await response.json().catch(() => ({}))).detail || "无法创建 AI 工作",
      );
    const item = (await response.json()) as Session;
    setSession(item);
    setMessages([]);
    setOpen(true);
    setMinimized(false);
    setMode("floating");
    await refreshSessions().catch(() => []);
  };
  const startFreeChat = async (forCurrentPage = false): Promise<Session> => {
    if (sendingRef.current) throw new Error("请先停止当前生成，再新建对话");
    await discardEmptySession();
    const response = await authenticatedFetch("/api/agent/chat/sessions", {
      method: "POST",
      headers: forCurrentPage ? { "Content-Type": "application/json" } : undefined,
      body: forCurrentPage ? JSON.stringify({ title: document.title || "当前页面", path: pathname || "/", page_text: extractPageText(document.getElementById("app-main")) }) : undefined,
    });
    if (!response.ok) throw new Error("无法创建自由讨论");
    const item = (await response.json()) as Session;
    setSession(item);
    setMessages([]);
    setOpen(true);
    setMinimized(false);
    setError("");
    await refreshSessions().catch(() => []);
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
  const refreshArtifacts = async () => {
    if (!user) return;
    const response = await authenticatedFetch("/api/agent/artifacts");
    if (!response.ok) return;
    setArtifacts(((await response.json()) as { items: Artifact[] }).items);
  };
  const showWorkspaceFiles = () => {
    setShowArtifacts(true);
    if (!artifactPreview && artifacts[0])
      void openArtifact(artifacts[0].id).catch((reason) =>
        setError(reason instanceof Error ? reason.message : "无法读取文件"),
      );
  };
  const openArtifact = async (id: string) => {
    const response = await authenticatedFetch(`/api/agent/artifacts/${id}`);
    if (!response.ok) throw new Error("无法读取文件");
    setArtifactPreview((await response.json()) as Artifact);
    setShowArtifacts(true);
  };
  const downloadArtifact = async (artifact: Artifact) => {
    const response = await authenticatedFetch(`/api/agent/artifacts/${artifact.id}/download`);
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
  const saveArtifact = async (content = "") => {
    if (!session) return;
    const response = await authenticatedFetch(
      `/api/agent/sessions/${session.id}/artifacts`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: session.task_title || session.title,
          type: "Markdown",
          content,
        }),
      },
    );
    if (!response.ok)
      throw new Error(
        (await response.json().catch(() => ({}))).detail || "无法保存成果",
      );
    await refreshArtifacts();
    toast("已保存为工作文件", "success");
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
    setError("");
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await authenticatedFetch("/api/agent/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, session_id: targetSession.id, model: selectedModel || undefined }),
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
            if (packet.artifacts?.length) {
              const nextArtifacts = packet.artifacts as Artifact[];
              setArtifacts((current) => [
                ...nextArtifacts,
                ...current.filter((item) => !nextArtifacts.some((next) => next.id === item.id)),
              ]);
              setMessages((current) =>
                current.map((item, index) =>
                  index === current.length - 1
                    ? { ...item, artifacts: [...(item.artifacts || []), ...nextArtifacts] }
                    : item,
                ),
              );
            }
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
      const stopped = reason instanceof DOMException && reason.name === "AbortError";
      setMessages((current) => current.map((item, index) => index === current.length - 1
        ? { ...item, content: item.content || (stopped ? "已停止生成。" : "生成失败，可重试。"), failed: !stopped }
        : item));
      if (!stopped) setError(reason instanceof Error ? reason.message : "Agent 暂时无法回答");
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      sendingRef.current = false;
      setSending(false);
      void refreshSessions().catch(() => undefined);
    }
  };
  const retryMessage = (text: string, assistantIndex: number) => {
    setMessages((current) => current.slice(0, Math.max(0, assistantIndex - 1)));
    void send(text);
  };
  useEffect(() => {
    if (user)
      queueMicrotask(() => {
        void refreshSessions().catch(() => undefined);
        void refreshArtifacts();
        void refreshModels();
      });
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!user || localStorage.getItem(agentWelcomeStorageKey(user.id)) === "1") return;
    localStorage.setItem(agentWelcomeStorageKey(user.id), "1");
    const show = window.setTimeout(() => setShowWelcomeTip(true), 0);
    const timer = window.setTimeout(() => {
      setShowWelcomeTip(false);
    }, 2000);
    return () => { window.clearTimeout(show); window.clearTimeout(timer); };
  }, [user]);
  useEffect(() => subscribeAgentRoute((detail) => {
      void route(detail).catch((reason) =>
        setError(reason instanceof Error ? reason.message : "无法启动 AI 工作"),
      );
    }), [user, pathname]); // eslint-disable-line react-hooks/exhaustive-deps
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
    abortRef.current?.abort();
    void discardEmptySession().catch(() => undefined);
    setOpen(false);
    setMinimized(false);
    setMode("floating");
    if (routeFull) router.push("/workbench");
  };
  const leaveFull = () => {
    abortRef.current?.abort();
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
            <button type="button" onClick={() => { localStorage.setItem(agentWelcomeStorageKey(user.id), "1"); setShowWelcomeTip(false); }} className="mt-2 text-xs font-medium text-primary">不再提示</button>
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
      : "fixed bottom-6 right-6 z-50 flex h-[min(720px,calc(100vh-3rem))] w-[min(480px,calc(100vw-2rem))] resize overflow-hidden rounded-2xl border border-grid bg-paper shadow-[var(--shadow-elevated)]";
  return (
    <section
      ref={panelRef}
      style={split ? { width: `${splitWidth}%` } : undefined}
      className={panelClass}
      aria-label="AI 工作台"
    >
      {showArtifacts && (
        <AppDialog open={showArtifacts} onClose={() => setShowArtifacts(false)} title="工作文件与成果" description="预览、下载或继续沉淀本次 AI 工作的产物。" className="max-w-3xl">
            <div className="grid h-[min(560px,calc(100dvh-13rem))] min-h-0 md:grid-cols-[220px_minmax(0,1fr)]">
              <div className="min-h-0 overflow-y-auto border-r border-grid p-3">{artifacts.length ? artifacts.map((item) => <div key={item.id} className={`mb-1 flex items-center gap-1 rounded-lg ${artifactPreview?.id === item.id ? "bg-primary-soft" : "hover:bg-surface-subtle"}`}><button type="button" onClick={() => void openArtifact(item.id).catch((reason) => setError(reason instanceof Error ? reason.message : "无法读取文件"))} className="min-w-0 flex-1 px-3 py-2 text-left"><p className="truncate text-sm font-medium text-ink-secondary">{item.filename || item.title}</p><p className="text-[10px] text-ink-muted">{item.mime_type || item.type} · {formatBytes(item.size_bytes)} · {new Date(item.created_at).toLocaleDateString("zh-CN")}</p></button><button type="button" onClick={() => void downloadArtifact(item).catch((reason) => setError(reason instanceof Error ? reason.message : "无法下载文件"))} className="rounded p-2 text-ink-muted hover:text-primary" aria-label={`下载 ${item.filename || item.title}`}><Download className="h-4 w-4" /></button></div>) : <p className="p-4 text-center text-sm text-ink-muted">还没有可下载文件。</p>}</div>
              <div className="min-h-0 overflow-y-auto p-5">{artifactPreview ? <><div className="mb-4 flex items-center justify-between gap-4"><div className="min-w-0"><h3 className="truncate font-semibold text-ink">{artifactPreview.filename || artifactPreview.title}</h3><p className="text-xs text-ink-muted">{artifactPreview.mime_type || artifactPreview.type} · {formatBytes(artifactPreview.size_bytes)}</p></div><button type="button" onClick={() => void downloadArtifact(artifactPreview).catch((reason) => setError(reason instanceof Error ? reason.message : "无法下载文件"))} className="ui-button-secondary shrink-0 text-xs"><Download className="h-3.5 w-3.5" />下载</button></div>{artifactPreview.mime_type === "text/markdown" || artifactPreview.filename?.endsWith(".md") ? <MarkdownMessage>{artifactPreview.content || ""}</MarkdownMessage> : <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-xl bg-surface-subtle p-4 text-xs leading-6 text-ink-secondary">{artifactPreview.content || ""}</pre>}</> : <div className="flex h-full items-center justify-center text-sm text-ink-muted">选择一个文件预览。</div>}</div>
            </div>
        </AppDialog>
      )}
      {showSessions && !full && (
        <AppDialog open={showSessions} onClose={() => setShowSessions(false)} title="对话历史" description="继续最近的工作，或创建一条新的自由讨论。" className="max-w-md">
            <div className="mb-3"><button type="button" onClick={() => void startFreeChat().then(() => setShowSessions(false)).catch((reason) => setError(reason instanceof Error ? reason.message : "无法创建对话"))} className="flex w-full items-center gap-2 rounded-xl bg-primary px-3 py-2.5 text-sm font-medium text-white"><MessageSquarePlus className="h-4 w-4" />新建自由对话</button></div>
            <nav className="max-h-[min(28rem,calc(100dvh-15rem))] overflow-y-auto px-2 pb-3" aria-label="最近对话">
              {sessions.length ? sessions.map((item) => <div key={item.id} className={`group mb-1 flex items-center rounded-xl ${session?.id === item.id ? "bg-primary-soft" : "hover:bg-surface-subtle"}`}><button type="button" onClick={() => void openSession(item.id).then(() => setShowSessions(false)).catch((reason) => setError(reason instanceof Error ? reason.message : "无法打开对话"))} className="min-w-0 flex-1 px-3 py-2.5 text-left"><span className="block truncate text-sm font-medium text-ink">{item.task_title || item.title}</span><span className="block truncate text-[11px] text-ink-muted">{item.context_title || "自由讨论"}</span></button><button type="button" onClick={() => void deleteSession(item.id)} className="mr-2 rounded-lg p-2 text-ink-muted opacity-0 hover:bg-warning-soft hover:text-warning group-hover:opacity-100 focus:opacity-100" aria-label={`删除 ${item.task_title || item.title}`}><Trash2 className="h-3.5 w-3.5" /></button></div>) : <p className="px-3 py-8 text-center text-sm text-ink-muted">还没有对话，先新建一个。</p>}
            </nav>
        </AppDialog>
      )}
      <ConfirmDialog open={!!pendingDelete} onOpenChange={(open) => { if (!open) setPendingDelete(null); }} title="删除这条对话？" description={pendingDelete ? `“${pendingDelete.task_title || pendingDelete.title}”及全部消息将被永久删除。` : undefined} confirmLabel="删除" danger onConfirm={() => void confirmDeleteSession()} />
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
          showWorkspaceFiles={showWorkspaceFiles}
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
                  : "方案实践与 AI 工作"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {!!models.length && (
              <label className="mr-1 hidden items-center gap-1.5 rounded-lg border border-grid bg-surface-subtle px-2 sm:flex">
                <span className="sr-only">当前模型</span>
                <select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)} className="h-8 max-w-[9rem] cursor-pointer bg-transparent text-[11px] font-medium text-ink-secondary outline-none" aria-label="切换模型">
                  {models.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
            )}
            {!full && <Tooltip label="打开对话历史"><button type="button" onClick={() => setShowSessions(true)} className="ui-icon-button" aria-label="打开对话历史"><History className="h-4 w-4" /></button></Tooltip>}
            {!full && (
              <button
                type="button"
                onClick={() => setMode(split ? "floating" : "split")}
                className="ui-icon-button hidden sm:inline-flex"
                aria-label={split ? "还原浮窗" : "在右侧展开"}
              >
                <PanelRightOpen className="h-4 w-4" />
              </button>
            )}
            <Tooltip label="文件与成果"><button type="button" onClick={showWorkspaceFiles} className="ui-icon-button" aria-label="打开文件与成果"><FolderOpen className="h-4 w-4" /></button></Tooltip>
            <Tooltip label={full ? "还原右下角浮窗" : "进入完整 AI 工作台"}><button
              type="button"
              onClick={() => (full ? leaveFull() : setMode("full"))}
              className="ui-icon-button"
              aria-label={full ? "还原右下角浮窗" : "进入完整 AI 工作台"}
            >
              {full ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </button></Tooltip>
            {!full && (
              <Tooltip label="最小化"><button
                type="button"
                onClick={() => setMinimized(true)}
                className="ui-icon-button"
                aria-label="最小化"
              >
                <Minimize2 className="h-4 w-4" />
              </button></Tooltip>
            )}
            <Tooltip label="关闭 AI 工作台"><button
              type="button"
              onClick={closeAgent}
              className="ui-icon-button ui-icon-button-danger"
              aria-label="关闭"
            >
              <X className="h-4 w-4" />
            </button></Tooltip>
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
                      <span className="h-2 w-2 rounded-full bg-primary" aria-hidden="true" />
                      已绑定工作上下文
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
                  <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[10px] font-medium text-primary">{taskStages[session.task_key || ""] || "分析"}</span>
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
              pathname={pathname || "/"}
              session={session}
              messages={messages}
              input={input}
              setInput={setInput}
              sending={sending}
              workingStatus={workingStatus}
              send={send}
              saveArtifact={saveArtifact}
              openArtifact={openArtifact}
              downloadArtifact={downloadArtifact}
              stop={() => abortRef.current?.abort()}
              retryMessage={retryMessage}
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
  showWorkspaceFiles,
  setError,
}: {
  sessions: Session[];
  session: Session | null;
  openSession(id: string): Promise<void>;
  startFreeChat(): Promise<Session>;
  deleteSession(id: string): Promise<void>;
  artifacts: Artifact[];
  showWorkspaceFiles(): void;
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
        <button type="button" onClick={showWorkspaceFiles} className="flex w-full items-center justify-between rounded-lg px-2 py-2 text-left hover:bg-white hover:text-primary">
          <span className="flex items-center gap-2">
            <FolderOpen className="h-4 w-4" />
            文件与成果
          </span>
          <span>{artifacts.length}</span>
        </button>
      </div>
    </aside>
  );
}

function WorkPanel({
  pathname,
  session,
  messages,
  input,
  setInput,
  sending,
  workingStatus,
  send,
  saveArtifact,
  openArtifact,
  downloadArtifact,
  stop,
  retryMessage,
  error,
  setError,
}: {
  pathname: string;
  session: Session;
  messages: Message[];
  input: string;
  setInput(value: string): void;
  sending: boolean;
  workingStatus: string;
  send(text: string): void;
  saveArtifact(content?: string): Promise<void>;
  openArtifact(id: string): Promise<void>;
  downloadArtifact(artifact: Artifact): Promise<void>;
  stop(): void;
  retryMessage(text: string, assistantIndex: number): void;
  error: string;
  setError(value: string): void;
}) {
  const { toast } = useToast();
  const scrollRef = useRef<HTMLDivElement>(null);
  const followOutput = useRef(true);
  useEffect(() => {
    if (!followOutput.current || !scrollRef.current) return;
    scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: sending ? "auto" : "smooth" });
  }, [messages, sending]);
  const copyMessage = async (content: string) => {
    if (!navigator.clipboard) return setError("当前浏览器不支持复制，请手动选择文本");
    try {
      await navigator.clipboard.writeText(content);
      toast("回答已复制", "success");
    } catch {
      setError("无法复制回答，请手动选择文本");
    }
  };
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
  const businessTitle = (session.context_snapshot as (Context & { business_context?: { title?: string } }) | undefined)?.business_context?.title;
  const contextualTitle = businessTitle || session.context_title;
  const [suggestedPrompts, setSuggestedPrompts] = useState(() => freeChatPrompts(pathname, contextualTitle));
  useEffect(() => {
    if (session.context_type !== "chat" || messages.length) return;
    let active = true;
    void authenticatedFetch("/api/agent/suggestions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: session.context_title || "当前页面", path: pathname, context: session.context_snapshot || {} }),
    }).then(async (response) => {
      if (!response.ok) return;
      const data = (await response.json()) as { items?: string[] };
      if (active && data.items?.length) setSuggestedPrompts(data.items);
    }).catch(() => undefined);
    return () => { active = false; };
  }, [contextualTitle, messages.length, pathname, session]);
  const emptyChat = session.context_type === "chat" && !messages.length;
  return (
    <>
      <div ref={scrollRef} onScroll={(event) => { const node = event.currentTarget; followOutput.current = node.scrollHeight - node.scrollTop - node.clientHeight < 96; }} className="min-h-0 flex-1 overflow-y-auto px-4 py-8">
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
                {suggestedPrompts.map((item) => (
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
                <div className="mb-8 rounded-xl border border-grid bg-surface-subtle p-4">
                  <p className="text-[11px] font-semibold text-primary">推荐工作配方</p>
                  <h2 className="mt-1 text-sm font-semibold text-ink">{session.task_title}</h2>
                  <p className="mt-2 text-sm leading-6 text-ink-secondary">
                    {session.default_prompt ||
                      "围绕当前上下文完成清晰、可执行的技术分析。"}
                  </p>
                  {!messages.length && (
                    <button
                      type="button"
                      onClick={() =>
                        send(session.default_prompt || "请开始当前任务。")
                      }
                      className="ui-button-primary mt-4"
                    >
                      使用此配方开始
                    </button>
                  )}
                </div>
              )}
              {messages.map((message, index) => (
                <article
                  key={`${message.role}-${index}`}
                  className={`group mb-6 flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[88%] text-sm leading-7 ${message.role === "user" ? "whitespace-pre-wrap rounded-2xl bg-primary-soft px-4 py-2.5 text-ink" : "min-w-0 text-ink"}`}
                  >
                    {message.content || message.artifacts?.length ? (
                      message.role === "assistant" ? (
                        <>
                          {message.content && <MarkdownMessage>{message.content}</MarkdownMessage>}
                          {!!message.artifacts?.length && (
                            <div className="mt-3 grid gap-2 sm:grid-cols-2">
                              {message.artifacts.map((artifact) => (
                                <div key={artifact.id} className="flex min-w-0 items-center gap-3 rounded-xl border border-grid bg-white p-3 shadow-sm">
                                  <button type="button" onClick={() => void openArtifact(artifact.id).catch(() => setError("无法读取文件"))} className="flex min-w-0 flex-1 items-center gap-3 text-left">
                                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary"><FileText className="h-4 w-4" /></span>
                                    <span className="min-w-0"><span className="block truncate text-xs font-semibold text-ink">{artifact.filename || artifact.title}</span><span className="block truncate text-[10px] text-ink-muted">{artifact.mime_type || artifact.type} · {formatBytes(artifact.size_bytes)}</span></span>
                                  </button>
                                  <button type="button" onClick={() => void downloadArtifact(artifact).catch(() => setError("无法下载文件"))} className="rounded-lg p-2 text-ink-muted hover:bg-primary-soft hover:text-primary" aria-label={`下载 ${artifact.filename || artifact.title}`}><Download className="h-4 w-4" /></button>
                                </div>
                              ))}
                            </div>
                          )}
                          {!!message.content && (
                            <div className="mt-2 flex items-center gap-1 text-ink-muted opacity-70 transition group-hover:opacity-100">
                              <button type="button" onClick={() => void copyMessage(message.content)} className="rounded-lg p-1.5 hover:bg-surface-subtle hover:text-primary" aria-label="复制回答"><Copy className="h-3.5 w-3.5" /></button>
                              <button type="button" disabled={sending || !messages[index - 1]?.content} onClick={() => retryMessage(messages[index - 1].content, index)} className="rounded-lg p-1.5 hover:bg-surface-subtle hover:text-primary disabled:opacity-30" aria-label="重新生成"><RotateCcw className="h-3.5 w-3.5" /></button>
                              <button type="button" onClick={() => void saveArtifact(message.content).catch((reason) => setError(reason instanceof Error ? reason.message : "无法保存成果"))} className="rounded-lg p-1.5 hover:bg-surface-subtle hover:text-primary" aria-label="保存为成果"><FolderOpen className="h-3.5 w-3.5" /></button>
                              {message.failed && <span className="ml-1 text-[11px] text-warning">生成中断，可重试</span>}
                            </div>
                          )}
                        </>
                      ) : (
                        message.content
                      )
                    ) : (
                      <span role="status" aria-live="polite" className="inline-flex items-center gap-2 text-ink-muted">
                        <LoaderCircle className="ui-spinner h-4 w-4 text-primary" aria-hidden="true" />
                        <span>{workingStatus}</span>
                      </span>
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
                      recommendedActions(session.task_key || "", messages.length)
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
        aria-busy={sending}
        aria-label="发送消息"
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
            placeholder={session.context_type === "chat" ? "自由提问" : "自由提问，或补充预置任务要求"}
            className="max-h-40 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none"
          />
          {sending ? <button type="button" onClick={stop} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-ink text-white" aria-label="停止生成"><Square className="h-3.5 w-3.5 fill-current" /></button> : <button type="submit" disabled={!input.trim()} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-white disabled:opacity-30" aria-label="发送"><Send className="h-4 w-4" /></button>}
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
        { icon: Code2, title: "开始实现", object: solution?.name || "请先收纳方案实践", route: solution && { contextType: "solution", contextId: String(solution.id), actionKey: "implement" } },
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
            placeholder="描述要推进的方案实践或任务"
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
        {[["summary", "摘要"], ["content", "正文"], ["metadata", "结构化信息"], ["related_entities", "关联材料"]].map(([key, label]) => (
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
            不注入{label}
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
