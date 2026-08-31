"use client";

import { Bot } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";

export function InsightAgentShell() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useAuth();

  if (loading || pathname === "/insight-agent") return null;
  return <button type="button" onClick={() => router.push(user ? "/insight-agent" : "/auth/login?next=/insight-agent")} className="fixed bottom-6 right-6 z-50 flex h-14 cursor-pointer items-center gap-2 rounded-full bg-primary px-5 text-sm font-semibold text-white shadow-[var(--shadow-elevated)] transition hover:bg-primary-dark" aria-label="打开 Insight-Agent"><Bot className="h-5 w-5" /> Insight-Agent</button>;
}
