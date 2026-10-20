"use client";

import { MessageSquarePlus, Trash2 } from "lucide-react";
import type { Session } from "./types";
import { usePreferences } from "@/lib/preferences";

export function SessionRail({
  sessions,
  session,
  openSession,
  startFreeChat,
  deleteSession,
  setError,
}: {
  sessions: Session[];
  session: Session | null;
  openSession(id: string): Promise<void>;
  startFreeChat(forCurrentPage?: boolean): Promise<Session>;
  deleteSession(id: string): Promise<void>;
  setError(value: string): void;
}) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  return (
    <aside className="agent-session-rail hidden w-64 shrink-0 flex-col border-r border-grid bg-surface-subtle lg:flex">
      <div className="p-3">
        <button
          type="button"
          onClick={() =>
            void startFreeChat().catch((reason) =>
              setError(
                reason instanceof Error ? reason.message : (en ? "Could not create conversation" : "无法创建对话"),
              ),
            )
          }
          className="flex w-full items-center gap-2 rounded-lg border border-grid bg-white px-3 py-2.5 text-sm font-medium text-ink hover:bg-primary-soft"
        >
          <MessageSquarePlus className="h-4 w-4" />
          {en ? "New conversation" : "新对话"}
        </button>
      </div>
      <nav
        className="min-h-0 flex-1 overflow-y-auto px-2"
        aria-label={en ? "Conversation history" : "对话历史"}
      >
        <p className="px-2 pb-2 text-[11px] font-medium text-ink-muted">{en ? "Recent" : "最近"}</p>
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
                    reason instanceof Error ? reason.message : (en ? "Could not open conversation" : "无法打开对话"),
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
                    reason instanceof Error ? reason.message : (en ? "Could not delete conversation" : "无法删除对话"),
                  ),
                )
              }
              className="mr-1 rounded p-1.5 text-ink-muted opacity-0 hover:bg-warning-soft hover:text-warning group-hover:opacity-100 focus:opacity-100"
              aria-label={en ? `Delete ${item.task_title || item.title}` : `删除 ${item.task_title || item.title}`}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </nav>
    </aside>
  );
}
