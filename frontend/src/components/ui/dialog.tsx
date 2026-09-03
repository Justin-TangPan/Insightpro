"use client";

import { ReactNode, useEffect, useId, useRef, useState } from "react";
import { X } from "lucide-react";
import { ActionButton } from "./action-button";

export function AppDialog({ open, onClose, title, description, children, footer, busy = false, className = "" }: { open: boolean; onClose(): void; title: string; description?: string; children?: ReactNode; footer?: ReactNode; busy?: boolean; className?: string }) {
  const ref = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLElement | null>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      trigger.current = document.activeElement as HTMLElement | null;
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
      trigger.current?.focus();
    }
    return () => {
      if (dialog.open) dialog.close();
      trigger.current?.focus();
    };
  }, [open]);

  return <dialog ref={ref} aria-labelledby={titleId} aria-describedby={description ? descriptionId : undefined} onCancel={(event) => { event.preventDefault(); if (!busy) onClose(); }} onClick={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }} className={`ui-dialog m-auto w-[min(32rem,calc(100vw-2rem))] max-h-[calc(100dvh-2rem)] overflow-auto rounded-2xl border border-grid bg-white p-0 text-ink shadow-[var(--shadow-elevated)] backdrop:bg-ink/45 backdrop:backdrop-blur-[2px] ${className}`}>
    <div className="flex items-start gap-4 border-b border-grid px-5 py-4 sm:px-6"><div className="min-w-0 flex-1"><h2 id={titleId} className="text-base font-semibold text-ink">{title}</h2>{description && <p id={descriptionId} className="mt-1 text-sm leading-6 text-ink-muted">{description}</p>}</div><button type="button" disabled={busy} onClick={onClose} className="rounded-lg p-2 text-ink-muted hover:bg-surface-subtle hover:text-ink" aria-label="关闭"><X className="h-4 w-4" /></button></div>
    {children && <div className="px-5 py-5 sm:px-6">{children}</div>}
    {footer && <div className="flex flex-col-reverse gap-2 border-t border-grid px-5 py-4 sm:flex-row sm:justify-end sm:px-6">{footer}</div>}
  </dialog>;
}

export function ConfirmDialog({ open, onOpenChange, title, description, confirmLabel = "确认", onConfirm, danger = false }: { open: boolean; onOpenChange(open: boolean): void; title: string; description?: string; confirmLabel?: string; onConfirm(): void | Promise<void>; danger?: boolean }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const confirm = async () => {
    setPending(true);
    setError("");
    try { await onConfirm(); onOpenChange(false); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "操作失败，请重试"); }
    finally { setPending(false); }
  };
  return <AppDialog open={open} onClose={() => onOpenChange(false)} title={title} description={description} busy={pending} footer={<><ActionButton type="button" disabled={pending} onClick={() => onOpenChange(false)} className="ui-button-secondary">取消</ActionButton><ActionButton type="button" onClick={confirm} pendingLabel="处理中…" className={danger ? "ui-button-danger" : "ui-button-primary"}>{confirmLabel}</ActionButton></>}>{error && <p role="alert" className="rounded-lg bg-warning-soft px-3 py-2 text-sm text-warning">{error}</p>}</AppDialog>;
}
