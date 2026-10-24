"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BookOpenCheck, Bot, CalendarClock, ChartNoAxesCombined, ClipboardList, Cpu, Database, FileClock, LayoutDashboard, Mail, Radar, ScanSearch, ShieldCheck, UsersRound } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useAuth } from "@/components/auth-provider";

const groups = [
  { title: "总览", items: [["/admin", "管理首页"]] },
  { title: "系统管理", items: [
    ["/admin/jobs", "任务日志", "进度与失败"], ["/admin/scheduler", "调度配置", "定时任务"],
    ["/admin/sources", "来源管理", "采集源"], ["/admin/llm", "LLM 设置", "模型服务"],
    ["/admin/users", "用户管理", "账号权限"],
  ] },
  { title: "情报运营", items: [
    ["/admin/events", "事件管理"], ["/admin/candidates", "发现候选"],
    ["/admin/coverage", "覆盖与审计"], ["/admin/dashboard", "数据看板"],
  ] },
  { title: "AI 与插件", items: [
    ["/workbench/ai", "AI 工作区"], ["/admin/prompts", "Prompt 管理"],
    ["/admin/knowledge", "知识与产物"], ["/admin/emails", "邮件管理"],
  ] },
] as const;
const icons: Record<string, LucideIcon> = {
  "/admin": LayoutDashboard, "/admin/jobs": FileClock, "/admin/scheduler": CalendarClock,
  "/admin/sources": Database, "/admin/llm": Cpu, "/admin/users": UsersRound,
  "/admin/events": ClipboardList, "/admin/candidates": ScanSearch,
  "/admin/coverage": Radar, "/admin/dashboard": ChartNoAxesCombined,
  "/workbench/ai": Bot, "/admin/prompts": ShieldCheck,
  "/admin/knowledge": BookOpenCheck, "/admin/emails": Mail,
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user?.app_metadata?.role !== "admin") return <div className="ui-card py-12 text-center">需要管理员权限。</div>;

  return <div className="admin-frame">
    <label className="admin-mobile-nav">管理模块
      <select value={pathname} onChange={event => router.push(event.target.value)}>
        {groups.map(group => <optgroup key={group.title} label={group.title}>{group.items.map(([href, label]) => <option key={href} value={href}>{label}</option>)}</optgroup>)}
      </select>
    </label>
    <aside className="admin-navigation" aria-label="管理导航">
      <div className="admin-navigation-title">管理区</div>
      {groups.map(group => <nav key={group.title} aria-label={group.title} className="admin-navigation-group">
        <h2>{group.title}</h2>
        {group.items.map(([href, label, description]) => {
          const active = href === "/admin" ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
          const Icon = icons[href];
          return <Link key={href} href={href} aria-current={active ? "page" : undefined} className="admin-navigation-link"><Icon size={17} strokeWidth={1.8} aria-hidden="true" /><span className="admin-navigation-copy"><strong>{label}</strong>{description && <small>{description}</small>}</span></Link>;
        })}
      </nav>)}
    </aside>
    <div className="admin-content">{children}</div>
  </div>;
}
