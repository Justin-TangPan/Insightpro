"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import {
  Copy,
  Download,
  FileText,
  FolderPlus,
  LoaderCircle,
  Paperclip,
  RotateCcw,
  Send,
  Sparkles,
  Square,
} from "lucide-react";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useToast } from "@/components/ui";
import { usePreferences } from "@/lib/preferences";
import { MarkdownMessage } from "./markdown-message";
import { recommendedActions, freeChatPrompts, formatBytes } from "./helpers";
import type { Session, Message, Artifact, ActionProposal, Interaction, Context } from "./types";

export function WorkPanel({
  pathname,
  session,
  messages,
  input,
  setInput,
  sending,
  workingStatus,
  send,
  downloadArtifact,
  stop,
  retryMessage,
  actionProposal,
  interaction,
  resolveInteraction,
  confirmAction,
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
  downloadArtifact(artifact: Artifact): Promise<void>;
  stop(): void;
  retryMessage(text: string, assistantIndex: number): void;
  actionProposal: ActionProposal | null;
  interaction: Interaction | null;
  resolveInteraction(answer: string): Promise<void>;
  confirmAction(): Promise<void>;
  error: string;
  setError(value: string): void;
}) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const { toast } = useToast();
  const [attachment, setAttachment] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const followOutput = useRef(true);
  useEffect(() => {
    if (!followOutput.current || !scrollRef.current) return;
    scrollRef.current.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: sending ? "auto" : "smooth",
    });
  }, [messages, sending]);
  const copyMessage = async (content: string) => {
    if (!navigator.clipboard)
      return setError(en ? "Copy is unsupported; select text manually" : "当前浏览器不支持复制，请手动选择文本");
    try {
      await navigator.clipboard.writeText(content);
      toast(en ? "Answer copied" : "回答已复制", "success");
    } catch {
      setError(en ? "Could not copy; select text manually" : "无法复制回答，请手动选择文本");
    }
  };
  const attach = async (files: FileList | null, saveToProject = false) => {
    if (!files?.length) return;
    const file = files[0];
    if (file.size > 2_000_000) return setError(en ? "Attachments must be under 2MB" : "附件不能超过 2MB");
    try {
      const content = (await file.text()).slice(0, 5000);
      setInput(`${input}${input ? "\n\n" : ""}${en ? `[Attachment: ${file.name}]` : `【附件：${file.name}】`}\n${content}`);
      setAttachment(`${file.name} · ${saveToProject ? (en ? "Saved as project context" : "已保存为项目背景材料") : (en ? "Visible only in this conversation" : "仅本轮对话可见")}`);
      if (saveToProject) {
        const contextId = session.context_snapshot?.context_id;
        if (!contextId) throw new Error(en ? "No solution practice linked to this conversation" : "当前对话未绑定方案实践");
        const requirement = await authenticatedFetch("/api/workbench/requirements", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: en ? `Attachment: ${file.name}` : `附件：${file.name}`, description: content, source_type: "solution", source_id: contextId }) });
        if (!requirement.ok) throw new Error(en ? "Could not save project context" : "无法保存项目背景材料");
        const item = await requirement.json() as { id: number };
        const linked = await authenticatedFetch(`/api/workbench/requirements/${item.id}/solutions/${contextId}`, { method: "POST" });
        if (!linked.ok) throw new Error(en ? "Could not link project context" : "背景材料关联失败");
      }
      setError("");
      toast(saveToProject ? (en ? `Saved to project context: ${file.name}` : `已保存到项目背景材料：${file.name}`) : (en ? `Added attachment: ${file.name}` : `已添加本轮附件：${file.name}`), "success");
    } catch {
      setError(en ? "Could not read this attachment; upload a text file" : "该附件无法读取，请上传文本类文件");
    }
  };
  const businessTitle = (
    session.context_snapshot as
      | (Context & { business_context?: { title?: string } })
      | undefined
  )?.business_context?.title;
  const contextualTitle = businessTitle || session.context_title;
  const [suggestedPrompts, setSuggestedPrompts] = useState(() =>
    freeChatPrompts(pathname, contextualTitle),
  );
  useEffect(() => {
    if (session.context_type !== "chat" || messages.length) return;
    let active = true;
    Promise.resolve().then(() => { if (active) setSuggestedPrompts(en ? ["Summarize this page", "Identify key risks", "Suggest next steps", "Plan a PoC"] : freeChatPrompts(pathname, contextualTitle)); });
    void authenticatedFetch("/api/agent/suggestions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: session.context_title || (en ? "Current page" : "当前页面"),
        path: pathname,
        context: session.context_snapshot || {},
      }),
    })
      .then(async (response) => {
        if (!response.ok) return;
        const data = (await response.json()) as { items?: string[] };
        if (active && data.items?.length) setSuggestedPrompts(data.items);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [contextualTitle, en, messages.length, pathname, session]);
  const emptyChat = session.context_type === "chat" && !messages.length;
  return (
    <>
      <div
        ref={scrollRef}
        onScroll={(event) => {
          const node = event.currentTarget;
          followOutput.current =
            node.scrollHeight - node.scrollTop - node.clientHeight < 96;
        }}
        className="agent-shell__messages min-h-0 flex-1 overflow-y-auto px-4 py-8"
      >
        <div
          className={`mx-auto max-w-3xl ${emptyChat ? "flex min-h-full items-center justify-center" : ""}`}
        >
          {emptyChat ? (
            <div className="w-full pb-20 text-center">
              <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-white">
                <Sparkles className="h-5 w-5" />
              </div>
              <h1 className="mt-5 text-2xl font-semibold tracking-tight text-ink">
                {en ? "What would you like to work on today?" : "今天想推进什么工作？"}
              </h1>
              <p className="mt-2 text-sm text-ink-muted">
                {en ? "Start research, analysis, design or implementation here." : "研究、分析、设计和实现，都可以从这里开始。"}
              </p>
              <div className="mx-auto mt-7 grid max-w-xl gap-2 text-left sm:grid-cols-2">
                {suggestedPrompts.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => setInput(item)}
                    className="agent-prompt-chip rounded-xl border px-4 py-3 text-sm text-ink-secondary hover:text-primary"
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
                  <p className="text-[11px] font-semibold text-primary">
                    {en ? "Suggested workflow" : "推荐工作配方"}
                  </p>
                  <h2 className="mt-1 text-sm font-semibold text-ink">
                    {session.task_title}
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-ink-secondary">
                    {session.default_prompt ||
                      (en ? "Create clear, actionable technical analysis for this context." : "围绕当前上下文完成清晰、可执行的技术分析。")}
                  </p>
                  {!messages.length && (
                    <button
                      type="button"
                      onClick={() =>
                        send(session.default_prompt || (en ? "Start the current task." : "请开始当前任务。"))
                      }
                      className="ui-button-primary mt-4"
                    >
                      {en ? "Start this workflow" : "使用此配方开始"}
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
                    className={`max-w-[88%] text-sm leading-7 ${message.role === "user" ? "agent-message-user whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-ink" : "agent-message-assistant min-w-0 rounded-2xl px-4 py-3 text-ink"}`}
                  >
                    {message.content || message.artifacts?.length ? (
                      message.role === "assistant" ? (
                        <>
                          {message.content && (
                            <MarkdownMessage>
                              {message.content}
                            </MarkdownMessage>
                          )}
                          {!!message.artifacts?.length && (
                            <div className="mt-3 grid gap-2 sm:grid-cols-2">
                              {message.artifacts.map((artifact) => (
                                <div
                                  key={artifact.id}
                                  className="flex min-w-0 items-center gap-3 rounded-xl border border-grid bg-white p-3 shadow-sm"
                                >
                                  <button
                                    type="button"
                                    onClick={() =>
                                      void downloadArtifact(artifact).catch(() =>
                                        setError(en ? "Could not download file" : "无法下载文件"),
                                      )
                                    }
                                    className="flex min-w-0 flex-1 items-center gap-3 text-left"
                                    aria-label={en ? `Download ${artifact.filename || artifact.title}` : `下载 ${artifact.filename || artifact.title}`}
                                  >
                                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary">
                                      <FileText className="h-4 w-4" />
                                    </span>
                                    <span className="min-w-0">
                                      <span className="block truncate text-xs font-semibold text-ink">
                                        {artifact.filename || artifact.title}
                                      </span>
                                      <span className="block truncate text-[10px] text-ink-muted">
                                        {artifact.mime_type || artifact.type} ·{" "}
                                        {formatBytes(artifact.size_bytes)}
                                      </span>
                                    </span>
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() =>
                                      void downloadArtifact(artifact).catch(() =>
                                        setError(en ? "Could not download file" : "无法下载文件"),
                                      )
                                    }
                                    className="rounded-lg p-2 text-ink-muted hover:bg-primary-soft hover:text-primary"
                                    aria-label={en ? `Download ${artifact.filename || artifact.title}` : `下载 ${artifact.filename || artifact.title}`}
                                  >
                                    <Download className="h-4 w-4" />
                                  </button>
                                </div>
                              ))}
                            </div>
                          )}
                          {!!message.content && (
                            <div className="mt-2 flex items-center gap-1 text-ink-muted opacity-70 transition group-hover:opacity-100">
                              <button
                                type="button"
                                onClick={() =>
                                  void copyMessage(message.content)
                                }
                                className="rounded-lg p-1.5 hover:bg-surface-subtle hover:text-primary"
                                aria-label={en ? "Copy answer" : "复制回答"}
                              >
                                <Copy className="h-3.5 w-3.5" />
                              </button>
                              <button
                                type="button"
                                disabled={
                                  sending || !messages[index - 1]?.content
                                }
                                onClick={() =>
                                  retryMessage(
                                    messages[index - 1].content,
                                    index,
                                  )
                                }
                                className="rounded-lg p-1.5 hover:bg-surface-subtle hover:text-primary disabled:opacity-30"
                                aria-label={en ? "Regenerate" : "重新生成"}
                              >
                                <RotateCcw className="h-3.5 w-3.5" />
                              </button>
                              {message.failed && (
                                <span className="ml-1 text-[11px] text-warning">
                                  {en ? "Generation stopped; retry" : "生成中断，可重试"}
                                </span>
                              )}
                            </div>
                          )}
                        </>
                      ) : (
                        message.content
                      )
                    ) : (
                      <span
                        role="status"
                        aria-live="polite"
                        className="inline-flex items-center gap-2 text-ink-muted"
                      >
                        <LoaderCircle
                          className="ui-spinner h-4 w-4 text-primary"
                          aria-hidden="true"
                        />
                        <span>{workingStatus}</span>
                      </span>
                    )}
                  </div>
                </article>
              ))}
              {messages.length > 0 && (
                <div className="mt-8 border-t border-grid pt-4">
                  {interaction?.session_id === session.id && (
                    <DecisionCard key={interaction.request_id} interaction={interaction} resolve={resolveInteraction} />
                  )}
                  {actionProposal && (
                    <div className="mb-4 rounded-xl border border-primary/30 bg-primary-soft p-4">
                      <p className="text-xs font-semibold text-primary">
                        {en ? "Agent proposes an action" : "Agent 提议执行操作"}
                      </p>
                      <p className="mt-1 text-sm font-medium text-ink">
                        {
                          (
                            {
                              create_requirement_draft: en ? "Create requirement draft" : "创建需求草稿",
                              create_solution_draft: en ? "Create solution draft" : "创建方案草稿",
                              append_note: en ? "Append business note" : "追加业务备注",
                              update_draft_content: en ? "Update draft content" : "更新草稿内容",
                            } as const
                          )[actionProposal.action]
                        }
                      </p>
                      <pre className="mt-2 max-h-36 overflow-auto whitespace-pre-wrap break-words text-xs leading-5 text-ink-secondary">
                        {JSON.stringify(actionProposal.payload, null, 2)}
                      </pre>
                      <button
                        type="button"
                        onClick={() =>
                          void confirmAction().catch((reason) =>
                            setError(
                              reason instanceof Error
                                ? reason.message
                                : (en ? "Could not perform action" : "无法执行操作"),
                            ),
                          )
                        }
                        className="ui-button-primary mt-3"
                      >
                        {en ? "Confirm action" : "确认执行"}
                      </button>
                      <p className="mt-2 text-[10px] text-ink-muted">
                        {en ? "Business data changes only after confirmation." : "确认前不会修改业务数据。"}
                      </p>
                    </div>
                  )}
                  <p className="text-xs font-medium text-ink-muted">{en ? "Next steps" : "下一步"}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(en ? ["Clarify the next step", "List validation risks", "Draft an action plan"] : recommendedActions(
                      session.task_key || "",
                      messages.length,
                    )).map((item) => (
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
        aria-label={en ? "Send message" : "发送消息"}
        className="agent-shell__composer border-t border-grid px-4 py-4"
      >
        <div className="agent-shell__input mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border p-2 shadow-[var(--shadow-input)]">
          <label
            className="flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-xl text-ink-muted hover:bg-surface-subtle hover:text-primary"
            aria-label={en ? "Upload to this conversation" : "上传到本次对话"}
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
          {session.context_type === "solution" && <label className="flex h-10 shrink-0 cursor-pointer items-center gap-1 rounded-xl px-2 text-[11px] text-ink-muted hover:bg-surface-subtle hover:text-primary" title={en ? "Save as project context" : "保存为项目背景材料"}><FolderPlus className="h-4 w-4" />{en ? "Save context" : "保存背景"}<input type="file" className="sr-only" accept=".txt,.md,.csv,.json,.yaml,.yml,.xml,.log" onChange={(event) => { void attach(event.target.files, true); event.target.value = ""; }} /></label>}
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
            placeholder={
              session.context_type === "chat"
                ? (en ? "Ask a question" : "自由提问")
                : (en ? "Ask a question or add task requirements" : "自由提问，或补充预置任务要求")
            }
            className="max-h-40 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none"
          />
          {sending ? (
            <button
              type="button"
              onClick={stop}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-ink text-white"
              aria-label={en ? "Stop generation" : "停止生成"}
            >
              <Square className="h-3.5 w-3.5 fill-current" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-white disabled:opacity-30"
              aria-label={en ? "Send" : "发送"}
            >
              <Send className="h-4 w-4" />
            </button>
          )}
        </div>
        {attachment && <p className="mx-auto mt-2 max-w-3xl truncate text-xs text-primary" role="status">{attachment}</p>}
        <p className="mt-2 text-center text-[10px] text-ink-muted">
          {en ? "AI output may be wrong; verify key conclusions." : "AI 生成内容可能有误，请核对关键结论。"}
        </p>
      </form>
    </>
  );
}

function DecisionCard({ interaction, resolve }: { interaction: Interaction; resolve(answer: string): Promise<void> }) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [selected, setSelected] = useState<string[]>([]);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submitting = useRef(false);
  return <form className="mb-4 rounded-xl border border-primary/30 bg-primary-soft p-4" onSubmit={async (event) => {
    event.preventDefault();
    if (submitting.current) return;
    const value = answer.trim() || (interaction.multi_select ? JSON.stringify(selected) : selected[0]);
    if (!value || (!answer.trim() && !selected.length)) return;
    submitting.current = true; setBusy(true); setError("");
    try { await resolve(value); } catch (reason) {
      setError(reason instanceof Error ? reason.message : (en ? "Could not submit decision" : "无法提交决策"));
    } finally { submitting.current = false; setBusy(false); }
  }}>
    <fieldset disabled={busy}>
      <legend className="text-sm font-medium text-ink">{interaction.question}</legend>
      <p className="mt-1 text-xs text-ink-muted">{en ? "Waiting for your decision" : "等待你的决策，确认后继续"}</p>
      <div className="my-3 grid gap-2">{interaction.choices.map((choice) => <label key={choice} className="flex items-center gap-2 text-sm">
        <input type={interaction.multi_select ? "checkbox" : "radio"} name={interaction.request_id} checked={selected.includes(choice)} onChange={(event) => {
          setAnswer("");
          setSelected(interaction.multi_select ? (event.target.checked ? [...selected, choice] : selected.filter((item) => item !== choice)) : [choice]);
        }} />{choice}
      </label>)}</div>
      <label className="block text-xs">{en ? "Add or enter your answer" : "补充或输入你的答案"}
        <textarea value={answer} maxLength={4000} onChange={(event) => setAnswer(event.target.value)} className="mt-1 block w-full rounded-lg border border-grid bg-white p-2 text-sm" />
      </label>
      <button type="submit" disabled={!selected.length && !answer.trim()} className="ui-button-primary mt-3">{busy ? (en ? "Submitting..." : "提交中…") : (en ? "Confirm and continue" : "确认并继续")}</button>
    </fieldset>
    {error && <p role="alert" className="mt-2 text-sm text-warning">{error}</p>}
  </form>;
}
