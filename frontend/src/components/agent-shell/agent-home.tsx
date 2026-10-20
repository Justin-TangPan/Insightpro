"use client";

import { Paperclip, Send, Sparkles } from "lucide-react";
import type { Session } from "./types";
import { usePreferences } from "@/lib/preferences";

export function AgentHome({
  input,
  setInput,
  sending,
  startFreeChat,
  send,
  setError,
}: {
  input: string;
  setInput(value: string): void;
  sending: boolean;
  startFreeChat(forCurrentPage?: boolean): Promise<Session>;
  send(text: string, session: Session): Promise<void>;
  setError(value: string): void;
}) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const examples = [
    en ? "Build an enterprise knowledge Q&A system" : "搭建企业知识库问答系统",
    en ? "Build a competitor intelligence platform" : "建设竞品情报分析平台",
    en ? "Plan a practical AI agent application" : "规划可落地的 AI Agent 应用",
  ];
  const submit = async (text: string) => {
    try {
      const item = await startFreeChat(true);
      await send(text, item);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : (en ? "Could not start a conversation" : "无法开始对话"));
    }
  };
  return (
    <main className="agent-home flex min-h-0 flex-1 flex-col">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void submit(input);
        }}
        className="flex flex-1 items-center justify-center overflow-y-auto px-5 py-12"
      >
        <div className="w-full max-w-4xl text-center">
          <div className="agent-home__badge mx-auto inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium text-primary-light">
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            {en ? "From business goal to practical solution" : "从业务目标到落地方案"}
          </div>
          <h1 className="mx-auto mt-7 max-w-4xl text-[clamp(2.25rem,5vw,4.5rem)] font-semibold leading-[1.05] tracking-[-.055em] text-ink">
            {en ? "Describe your business goal," : "描述你的业务目标，"}
            <br className="hidden sm:block" /> {en ? "InsightAgent turns it into a plan" : "InsightAgent 生成落地方案"}
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-ink-muted">
            {en ? "Organize requirements, plan architecture, assess resources, and create an actionable solution practice." : "自动梳理需求、规划技术架构、评估实施资源，并形成可执行的方案实践。"}
          </p>
          <div className="agent-home__composer mx-auto mt-10 max-w-4xl rounded-[1.5rem] border p-3 text-left shadow-[var(--shadow-input)]">
            <label htmlFor="agent-business-goal" className="sr-only">
              {en ? "Business goal" : "业务目标"}
            </label>
            <textarea
              id="agent-business-goal"
              rows={3}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={en ? "Describe your goal, such as a system that collects competitor updates and produces weekly reports." : "描述你的业务目标，例如：建设一个每天采集竞品动态、自动分析并生成周报的系统。"}
              className="max-h-56 min-h-28 w-full resize-none bg-transparent px-3 py-3 text-base leading-7 text-ink outline-none placeholder:text-ink-muted/70"
            />
            <div className="flex items-center justify-between gap-3 border-t border-grid px-1 pt-3">
              <label
                className="ui-icon-button cursor-pointer"
                aria-label={en ? "Upload background material" : "上传背景材料"}
                title={en ? "Upload background material" : "上传背景材料"}
              >
                <Paperclip className="h-4 w-4" aria-hidden="true" />
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
                            `${en ? `[Attachment: ${file.name}]` : `【附件：${file.name}】`}\n${content.slice(0, 6000)}`,
                          ),
                        );
                    else if (file) setError(en ? "Attachments must be under 2MB" : "附件不能超过 2MB");
                    event.target.value = "";
                  }}
                />
              </label>
              <button
                type="submit"
                disabled={!input.trim() || sending}
                className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:opacity-30"
              >
                {en ? "Generate plan" : "生成方案"} <Send className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>
          <div
            className="mx-auto mt-5 flex max-w-4xl flex-wrap items-center justify-center gap-2"
            aria-label={en ? "Example business goals" : "示例业务目标"}
          >
            <span className="mr-1 text-xs text-ink-muted">{en ? "Try:" : "试试："}</span>
            {examples.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => setInput(example)}
                className="agent-prompt-chip min-h-10 rounded-full border px-4 py-2 text-sm text-ink-secondary hover:text-ink"
              >
                {example}
              </button>
            ))}
          </div>
          <p className="mt-6 text-[11px] text-ink-muted">
            {en ? "AI output may be wrong; verify costs, architecture, and implementation requirements." : "AI 生成内容可能有误，请核对成本、架构与实施条件。"}
          </p>
        </div>
      </form>
    </main>
  );
}
