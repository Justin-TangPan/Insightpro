"use client";

import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, CircleAlert, Info, X } from "lucide-react";

type Tone = "info" | "success" | "error";
type Toast = { id: number; message: string; tone: Tone };
type ToastApi = { toast(message: string, tone?: Tone): void };
const ToastContext = createContext<ToastApi | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const nextId = useRef(0);
  const timers = useRef(new Set<number>());
  const dismiss = useCallback((id: number) => setItems((current) => current.filter((item) => item.id !== id)), []);
  const toast = useCallback((message: string, tone: Tone = "info") => {
    const id = ++nextId.current;
    setItems((current) => [...current, { id, message, tone }]);
    const timer = window.setTimeout(() => { dismiss(id); timers.current.delete(timer); }, 4000);
    timers.current.add(timer);
  }, [dismiss]);
  useEffect(() => () => { for (const timer of timers.current) window.clearTimeout(timer); }, []);
  const value = useMemo(() => ({ toast }), [toast]);
  return <ToastContext.Provider value={value}>{children}<div className="fixed bottom-5 right-4 z-[100] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2" aria-live="polite" aria-atomic="false">{items.map((item) => { const Icon = item.tone === "success" ? CheckCircle2 : item.tone === "error" ? CircleAlert : Info; return <div key={item.id} role={item.tone === "error" ? "alert" : "status"} className={`ui-toast ui-toast-${item.tone} flex items-start gap-3 rounded-xl border bg-white px-4 py-3 shadow-[var(--shadow-elevated)]`}><Icon className="mt-0.5 h-4 w-4 shrink-0" /><p className="min-w-0 flex-1 text-sm leading-5 text-ink-secondary">{item.message}</p><button type="button" onClick={() => dismiss(item.id)} className="rounded p-1 text-ink-muted hover:bg-surface-subtle" aria-label="关闭通知"><X className="h-3.5 w-3.5" /></button></div>; })}</div></ToastContext.Provider>;
}

export function useToast() {
  const value = useContext(ToastContext);
  if (!value) throw new Error("useToast must be used within ToastProvider");
  return value;
}
