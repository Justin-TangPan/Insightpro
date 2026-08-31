"use client";

import { FormEvent, Suspense, useEffect, useRef, useState } from "react";
import { Bot, ChevronLeft, LoaderCircle, MessageSquarePlus, Send, Sparkles, Trash2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useAuth } from "@/components/auth-provider";

type Message = { role: "user" | "assistant"; content: string };
type AgentSession = { id: string; title: string; context_type: string; context_title: string; updated_at: string };

function contextPrompt(title: string) {
  return `请分析当前${title ? `“${title}”` : "洞察"}：说明它解决什么问题、适合哪些场景、主要风险，以及下一步建议。`;
}

const recommendations: Record<string, string[]> = {
  github_project: ["这个项目解决什么问题？", "评估它的技术成熟度和引入风险", "给出 PoC 验证清单"],
  cloud_solution: ["这个方案适合哪些业务场景？", "分析落地依赖与实施步骤", "与现有技术栈如何集成？"],
  requirement: ["把这个需求拆成可执行任务", "识别需求的关键风险与边界", "推荐可关联的解决方案方向"],
  solution: ["评审这个方案的完整性", "找出当前方案的技术风险", "给出下一版演进建议"],
  default: ["帮我比较两种技术路线", "梳理一个方案的落地路径", "给出技术决策的风险清单"],
};

function InlineMarkdown({ text }: { text: string }) {
  return <>{text.split(/(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^\s)]+\))/g).map((part, index) => {
    if (/^`[^`]+`$/.test(part)) return <code key={index} className="rounded bg-ink/8 px-1.5 py-0.5 font-mono text-[0.82em]">{part.slice(1, -1)}</code>;
    if (/^\*\*[^*]+\*\*$/.test(part)) return <strong key={index} className="font-bold">{part.slice(2, -2)}</strong>;
    const link = part.match(/^\[([^\]]+)\]\(([^\s)]+)\)$/);
    return link ? <a key={index} href={link[2]} target="_blank" rel="noreferrer" className="underline decoration-primary/40 underline-offset-4 hover:text-primary">{link[1]}</a> : part;
  })}</>;
}

function Markdown({ content }: { content: string }) {
  return <div className="space-y-2">{content.split("```").map((section, index) => index % 2 ? <pre key={index} className="overflow-x-auto rounded-xl bg-ink p-3 text-xs leading-6 text-white"><code>{section.replace(/^\w*\n/, "")}</code></pre> : section.split("\n").map((line, lineIndex) => {
    const key = `${index}-${lineIndex}`;
    if (/^###\s+/.test(line)) return <h3 key={key} className="pt-2 text-base font-bold"><InlineMarkdown text={line.slice(4)} /></h3>;
    if (/^##\s+/.test(line)) return <h2 key={key} className="pt-3 text-lg font-bold"><InlineMarkdown text={line.slice(3)} /></h2>;
    if (/^#\s+/.test(line)) return <h1 key={key} className="pt-3 text-xl font-bold"><InlineMarkdown text={line.slice(2)} /></h1>;
    if (/^[-*]\s+/.test(line)) return <div key={key} className="flex gap-2"><span className="pt-2 text-primary">•</span><span><InlineMarkdown text={line.slice(2)} /></span></div>;
    const ordered = line.match(/^(\d+)\.\s+(.*)$/);
    if (ordered) return <div key={key} className="flex gap-2"><span className="font-mono text-primary">{ordered[1]}.</span><span><InlineMarkdown text={ordered[2]} /></span></div>;
    return line ? <p key={key}><InlineMarkdown text={line} /></p> : <div key={key} className="h-1" />;
  }))}</div>;
}

function InsightAgentPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading } = useAuth();
  const contextType = searchParams.get("context_type") || "";
  const contextId = searchParams.get("context_id") || "";
  const initialized = useRef("");
  const [contextTitle, setContextTitle] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const suggestionItems = recommendations[contextType] || recommendations.default;

  const refreshSessions = async () => {
    const response = await authenticatedFetch("/api/agent/chat/sessions");
    if (!response.ok) throw new Error("无法读取会话列表");
    const data = await response.json() as { items: AgentSession[] };
    setSessions(data.items);
    return data.items;
  };

  const openSession = async (id: string) => {
    const response = await authenticatedFetch(`/api/agent/sessions/${id}`);
    if (!response.ok) throw new Error("无法读取该会话");
    const session = await response.json() as { id: string; title: string; context_title: string; conversation?: Message[] };
    setSessionId(session.id); setContextTitle(session.context_title); setMessages(session.conversation || []); setError("");
  };

  const send = async (text: string, activeSessionId = sessionId) => {
    const message = text.trim();
    if (!message || sending) return;
    setMessages(current => [...current, { role: "user", content: message }, { role: "assistant", content: "" }]);
    setInput(""); setSending(true); setError("");
    try {
      let targetSessionId = activeSessionId;
      if (!targetSessionId) {
        const created = await authenticatedFetch("/api/agent/chat/sessions", { method: "POST" });
        if (!created.ok) throw new Error("无法创建新会话");
        targetSessionId = (await created.json() as { id: string }).id;
        setSessionId(targetSessionId); setContextTitle("");
      }
      const response = await authenticatedFetch("/api/agent/chat/stream", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message, session_id: targetSessionId }) });
      if (!response.ok || !response.body) throw new Error((await response.json().catch(() => ({}))).detail || "Agent 暂时无法回答");
      const reader = response.body.getReader();
      const decoder = new TextDecoder(); let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n"); buffer = lines.pop() || "";
        for (const line of lines) {
          if (!line.startsWith("data: ") || line === "data: [DONE]") continue;
          try {
            const chunk = JSON.parse(line.slice(6));
            const content = chunk.choices?.[0]?.delta?.content || "";
            if (content) setMessages(current => current.map((item, index) => index === current.length - 1 ? { ...item, content: item.content + content } : item));
          } catch { /* Ignore provider keep-alives and malformed frames. */ }
        }
      }
    } catch (reason) {
      setMessages(current => current.slice(0, -1));
      setError(reason instanceof Error ? reason.message : "Agent 暂时无法回答");
    } finally { setSending(false); void refreshSessions().catch(() => undefined); }
  };

  useEffect(() => {
    if (!user || !contextType || !contextId) return;
    const key = `${contextType}:${contextId}`;
    if (initialized.current === key) return;
    initialized.current = key;
    void authenticatedFetch("/api/agent/sessions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ context_type: contextType, context_id: contextId }) })
      .then(async response => {
        if (!response.ok) throw new Error("当前洞察无法作为 Agent Context 使用");
        return response.json() as Promise<{ id: string; context_title: string }>;
      })
      .then(context => { setSessionId(context.id); setContextTitle(context.context_title); void refreshSessions().catch(() => undefined); void send(contextPrompt(context.context_title), context.id); })
      .catch(reason => setError(reason instanceof Error ? reason.message : "上下文初始化失败"));
  // Context is intentionally initialized once per URL target.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contextId, contextType, user]);

  useEffect(() => {
    if (!loading && !user) router.replace("/auth/login?next=/insight-agent");
  }, [loading, router, user]);

  useEffect(() => {
    if (!user || contextType || contextId) return;
    let cancelled = false;
    void authenticatedFetch("/api/agent/chat/sessions")
      .then(response => response.ok ? response.json() as Promise<{ items: AgentSession[] }> : Promise.reject(new Error("无法读取会话列表")))
      .then(data => { if (!cancelled) setSessions(data.items); })
      .catch(reason => { if (!cancelled) setError(reason instanceof Error ? reason.message : "会话初始化失败"); });
    return () => { cancelled = true; };
  }, [contextId, contextType, user]);

  const newChat = async () => {
    const response = await authenticatedFetch("/api/agent/chat/sessions", { method: "POST" });
    if (!response.ok) throw new Error("无法创建新会话");
    const session = await response.json() as { id: string; title: string };
    setSessionId(session.id); setContextTitle(""); setMessages([]); setError(""); initialized.current = ""; router.replace("/insight-agent"); await refreshSessions();
  };
  const removeSession = async (id: string) => {
    const response = await authenticatedFetch(`/api/agent/chat/sessions/${id}`, { method: "DELETE" });
    if (!response.ok) throw new Error("无法删除会话");
    const remaining = await refreshSessions();
    if (id === sessionId) { if (remaining[0]) await openSession(remaining[0].id); else await newChat(); }
  };
  const submit = (event: FormEvent) => { event.preventDefault(); void send(input); };

  if (loading) return null;
  if (!user) return null;

  return <div className="-mx-[var(--page-gutter)] -my-8 flex h-[calc(100vh-4rem)] min-h-[640px] overflow-hidden bg-[#f7faf8] text-ink">
    <aside className="hidden w-72 shrink-0 flex-col bg-primary-dark p-4 text-white md:flex">
      <div className="flex items-center gap-2 px-2 py-3"><div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/12"><Sparkles className="h-4 w-4" /></div><div><p className="text-sm font-bold">Insight-Agent</p><p className="text-[10px] text-white/55">技术决策工作台</p></div></div>
      <button type="button" onClick={() => void newChat().catch(reason => setError(reason instanceof Error ? reason.message : "无法创建新会话"))} className="mt-6 flex items-center gap-2 rounded-xl border border-white/15 bg-white/10 px-3 py-2.5 text-left text-sm font-semibold transition hover:bg-white/16"><MessageSquarePlus className="h-4 w-4" />新对话</button>
      <div className="mt-7 min-h-0 flex-1 overflow-y-auto"><p className="px-2 text-[10px] font-semibold tracking-[0.16em] text-white/45">最近会话</p><div className="mt-2 space-y-1">{sessions.map(item => <div key={item.id} className={`group flex items-center rounded-xl ${item.id === sessionId ? "bg-white/12" : "hover:bg-white/7"}`}><button type="button" onClick={() => void openSession(item.id).catch(reason => setError(reason instanceof Error ? reason.message : "无法读取会话"))} className="min-w-0 flex-1 px-3 py-3 text-left"><p className="truncate text-sm font-medium">{item.title}</p><p className="mt-1 truncate text-xs text-white/50">{item.context_title ? `洞察 · ${item.context_title}` : "自由讨论"}</p></button><button type="button" onClick={() => void removeSession(item.id).catch(reason => setError(reason instanceof Error ? reason.message : "无法删除会话"))} className="mr-2 hidden rounded p-1.5 text-white/45 hover:bg-white/10 hover:text-white group-hover:block" aria-label={`删除 ${item.title}`}><Trash2 className="h-3.5 w-3.5" /></button></div>)}</div></div>
      <div className="mt-auto border-t border-white/10 px-2 pt-4 text-xs leading-5 text-white/52">回答基于当前会话与已授权洞察生成。</div>
    </aside>
    <main className="flex min-w-0 flex-1 flex-col">
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-grid/70 bg-white/80 px-5 backdrop-blur"><div className="flex min-w-0 items-center gap-3"><button type="button" onClick={() => router.back()} className="rounded-lg p-2 text-ink-muted hover:bg-primary-soft hover:text-primary" aria-label="返回"><ChevronLeft className="h-5 w-5" /></button><div><p className="text-sm font-bold">{contextTitle || "Insight-Agent"}</p><p className="text-xs text-ink-muted">{contextTitle ? "正在分析当前洞察" : "从一个技术问题开始"}</p></div></div><span className="hidden rounded-full bg-primary-soft px-3 py-1 text-xs font-semibold text-primary sm:inline-flex">在线分析</span></header>
      <section className="flex-1 overflow-y-auto px-5 py-8 sm:px-10"><div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
        {!messages.length && <div className="py-16 text-center"><div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-soft text-primary"><Bot className="h-7 w-7" /></div><h1 className="mt-5 text-2xl font-bold tracking-tight">{contextTitle ? `从“${contextTitle}”开始` : "今天想判断什么？"}</h1><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink-muted">我会根据当前洞察类型推荐下一步问题，也可以直接输入你的目标。</p><div className="mx-auto mt-6 flex max-w-lg flex-wrap justify-center gap-2">{suggestionItems.map(item => <button key={item} type="button" onClick={() => void send(item)} className="cursor-pointer rounded-full border border-grid bg-white px-3 py-2 text-xs text-ink-secondary transition hover:border-primary hover:text-primary">{item}</button>)}</div></div>}
        {messages.map((item, index) => <article key={`${item.role}-${index}`} className={`flex gap-3 ${item.role === "user" ? "flex-row-reverse" : ""}`}><div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${item.role === "assistant" ? "bg-primary text-white" : "bg-ink text-white"}`}>{item.role === "assistant" ? <Bot className="h-4 w-4" /> : user.email?.slice(0, 1).toUpperCase()}</div><div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-7 ${item.role === "assistant" ? "bg-white shadow-[var(--shadow-card)]" : "bg-primary text-white"}`}>{item.content ? <Markdown content={item.content} /> : <LoaderCircle className="h-4 w-4 animate-spin" />}</div></article>)}
        {error && <p role="alert" className="rounded-xl bg-warning-soft px-4 py-3 text-sm text-warning">{error}</p>}
      </div></section>
      <form onSubmit={submit} className="border-t border-grid/70 bg-white px-5 py-4 sm:px-10"><div className="mx-auto flex max-w-3xl items-end gap-3 rounded-2xl border border-grid bg-surface-subtle p-2 transition focus-within:border-primary focus-within:ring-3 focus-within:ring-primary-soft"><textarea value={input} onChange={event => setInput(event.target.value)} onKeyDown={event => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(input); } }} rows={1} placeholder="输入问题，Enter 发送，Shift + Enter 换行" className="max-h-32 min-h-10 flex-1 resize-none bg-transparent px-3 py-2 text-sm outline-none placeholder:text-ink-muted" /><button type="submit" disabled={!input.trim() || sending} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-white transition hover:bg-primary-dark disabled:opacity-40" aria-label="发送"><Send className="h-4 w-4" /></button></div><p className="mx-auto mt-2 max-w-3xl px-2 text-[11px] text-ink-muted">Insight-Agent 可能出错；重要技术决策请核验原始资料。</p></form>
    </main>
  </div>;
}

export default function InsightAgentPageRoute() {
  return <Suspense fallback={null}><InsightAgentPage /></Suspense>;
}
