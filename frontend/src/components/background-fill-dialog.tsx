"use client";

import { useEffect, useRef, useState } from "react";
import { Check, LoaderCircle, RefreshCw, Sparkles } from "lucide-react";
import { AppDialog, useToast } from "@/components/ui";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { hasReadableGithubSource } from "@/lib/background-fill";

type Props = {
  name: string;
  description: string;
  referenceUrl?: string | null;
  onApply: (content: string) => void;
};

type Status = "idle" | "reading" | "generating";

export function BackgroundFillDialog({ name, description, referenceUrl, onApply }: Props) {
  const { toast } = useToast();
  const request = useRef<AbortController>(null);
  const [open, setOpen] = useState(false);
  const [original, setOriginal] = useState("");
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState<Status>("idle");

  useEffect(() => () => request.current?.abort(), []);

  const close = () => {
    request.current?.abort();
    request.current = null;
    setStatus("idle");
    setOpen(false);
  };

  const generate = async (sourceDescription = original) => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setDraft("");
    setError("");
    setStatus(hasReadableGithubSource(referenceUrl || "") ? "reading" : "generating");
    try {
      const response = await authenticatedFetch("/api/agent/practice-background", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, description: sourceDescription, reference_url: referenceUrl || null }),
        signal: controller.signal,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "无法生成背景信息");
      setDraft(data.content || "");
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(reason instanceof Error ? reason.message : "无法生成背景信息");
    } finally {
      if (request.current === controller) {
        request.current = null;
        setStatus("idle");
      }
    }
  };

  const start = () => {
    setOriginal(description);
    setDraft("");
    setError("");
    setOpen(true);
    void generate(description);
  };

  const apply = () => {
    onApply(draft);
    toast("已采用 AI 草稿，点击保存后生效。", "success");
    close();
  };

  const busy = status !== "idle";
  const progress = status === "reading" ? "正在读取参考资料并生成背景…" : "正在生成背景…";

  return (
    <>
      <button type="button" disabled={!name.trim()} onClick={start} className="ui-button-secondary px-2.5 py-1.5 text-xs" aria-haspopup="dialog">
        <Sparkles className="h-3.5 w-3.5" />AI 填充
      </button>
      <AppDialog open={open} onClose={close} title="校对背景信息" description="AI 草稿不会直接覆盖，采用后仍需保存方案实践。" footer={<>
        <button type="button" onClick={close} className="ui-button-secondary">取消</button>
        {!busy && !error && draft && <button type="button" onClick={() => void generate()} className="ui-button-secondary"><RefreshCw className="h-4 w-4" />重新生成</button>}
        <button type="button" disabled={busy || !draft || Boolean(error)} onClick={apply} className="ui-button-primary"><Check className="h-4 w-4" />采用草稿</button>
      </>}>
        <div>
          {busy && <div className="flex min-h-64 flex-col items-center justify-center rounded-xl bg-surface-subtle text-center" aria-live="polite"><LoaderCircle className="h-6 w-6 animate-spin text-primary" /><p className="mt-3 text-sm font-semibold">{progress}</p><p className="mt-1 text-xs text-ink-muted">可随时取消，本次内容不会被修改。</p></div>}
          {!busy && error && <div role="alert" className="rounded-xl bg-warning-soft p-5"><p className="font-semibold text-warning">背景信息生成失败</p><p className="mt-1 text-sm text-warning">{error}</p><button type="button" onClick={() => void generate()} className="ui-button-secondary mt-4"><RefreshCw className="h-4 w-4" />重试</button></div>}
          {!busy && !error && draft && <div className="grid gap-4">
            <Preview label="当前内容 · 保留" content={original} empty="当前没有背景信息" />
            <Preview label="AI 草稿 · 待采用" content={draft} />
          </div>}
        </div>
      </AppDialog>
    </>
  );
}

function Preview({ label, content, empty = "" }: { label: string; content: string; empty?: string }) {
  return <section className="min-w-0 overflow-hidden rounded-xl border border-grid bg-surface-subtle"><h3 className="border-b border-grid bg-surface-elevated px-4 py-3 text-xs font-semibold text-ink-secondary">{label}</h3><div className="max-h-96 overflow-auto whitespace-pre-wrap break-words px-4 py-4 font-mono text-xs leading-6 text-ink-secondary">{content || <span className="font-sans text-ink-muted">{empty}</span>}</div></section>;
}
