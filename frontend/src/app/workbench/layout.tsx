"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { usePreferences } from "@/lib/preferences";

const sections = [
  ["/workbench", "工作总览", "Overview"],
  ["/workbench/solutions", "方案实践", "Solution Practices"],
  ["/workbench/ai", "AI 助手", "AI Assistant"],
] as const;

export default function WorkbenchLayout({ children }: { children: React.ReactNode }) {
  const { preferences } = usePreferences();
  const pathname = usePathname();
  return <>
    <nav aria-label="工作区导航" className="mb-6 flex gap-1 overflow-x-auto rounded-xl border border-grid bg-white p-1 shadow-[var(--shadow-card)]">
      <Link href="/admin" className="shrink-0 rounded-lg px-4 py-2 text-sm font-medium text-ink-muted hover:bg-primary-soft hover:text-primary">{preferences.language === "en" ? "Back to admin" : "返回管理区"}</Link>
      {sections.map(([href, label, english]) => {
        const active = href === "/workbench" ? pathname === href : pathname.startsWith(href);
        return <Link key={href} href={href} aria-current={active ? "page" : undefined} className={`shrink-0 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${active ? "bg-primary text-white" : "text-ink-muted hover:bg-primary-soft hover:text-primary"}`}>{preferences.language === "en" ? english : label}</Link>;
      })}
    </nav>
    {children}
  </>;
}
