"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { usePreferences } from "@/lib/preferences";

const sections = [
  ["/admin", "平台管理", "Platform overview"],
  ["/admin/runtime", "运行与数据", "Runtime & data"],
  ["/admin/access", "用户与权限", "Users & access"],
  ["/admin/knowledge", "知识库与产物", "Knowledge & artifacts"],
  ["/admin/dashboard", "数据看板", "Analytics dashboard"],
  ["/admin/tasks", "任务中心", "Task center"],
] as const;

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { preferences } = usePreferences();
  const english = preferences.language === "en";

  return <>
    <nav aria-label={english ? "Platform administration" : "平台管理"} className="sticky top-16 z-20 mb-5 flex flex-wrap gap-1 rounded-xl border border-grid bg-surface-elevated/95 p-1 shadow-[var(--shadow-card)] backdrop-blur">
      {sections.map(([href, label, englishLabel]) => {
        const active = href === "/admin" ? pathname === href : pathname.startsWith(href);
        return <Link key={href} href={href} aria-current={active ? "page" : undefined} className={`shrink-0 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${active ? "bg-primary text-white" : "text-ink-muted hover:bg-primary-soft hover:text-primary"}`}>
          {english ? englishLabel : label}
        </Link>;
      })}
    </nav>
    {children}
  </>;
}
