"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const sections = [
  ["/workbench", "概览"],
  ["/workbench/requirements", "需求"],
  ["/workbench/solutions", "方案"],
  ["/workbench/ai", "AI 工作 · 文件 · 成果"],
] as const;

export default function WorkbenchLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return <>
    <nav aria-label="AI 工作台" className="mb-6 flex gap-1 overflow-x-auto rounded-xl border border-grid bg-white p-1 shadow-[var(--shadow-card)]">
      {sections.map(([href, label]) => {
        const active = href === "/workbench" ? pathname === href : pathname.startsWith(href);
        return <Link key={href} href={href} aria-current={active ? "page" : undefined} className={`shrink-0 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${active ? "bg-primary text-white" : "text-ink-muted hover:bg-primary-soft hover:text-primary"}`}>{label}</Link>;
      })}
    </nav>
    {children}
  </>;
}
