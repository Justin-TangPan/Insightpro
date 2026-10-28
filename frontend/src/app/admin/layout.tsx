"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ClipboardList, Database, LayoutDashboard, Radar, Settings2 } from "lucide-react";
import { useAuth } from "@/components/auth-provider";

const navigation = [
  { href: "/admin", label: "总览", icon: LayoutDashboard, paths: ["/admin"] },
  { href: "/admin/tasks", label: "任务中心", icon: ClipboardList, paths: ["/admin/tasks", "/admin/jobs", "/admin/scheduler"] },
  { href: "/admin/sources", label: "数据源", icon: Database, paths: ["/admin/sources"] },
  { href: "/admin/operations", label: "情报运营", icon: Radar, paths: ["/admin/operations", "/admin/events", "/admin/candidates", "/admin/coverage"] },
  { href: "/admin/system", label: "系统设置", icon: Settings2, paths: ["/admin/system", "/admin/llm", "/admin/prompts", "/admin/knowledge", "/admin/users", "/admin/access", "/admin/emails", "/admin/runtime", "/admin/dashboard"] },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useAuth();
  if (pathname === "/admin/login") return <>{children}</>;
  if (loading) return null;
  if (user?.app_metadata?.role !== "admin") return null;
  const current = navigation.find(item => item.paths.some(path => pathname === path || (path !== "/admin" && pathname.startsWith(`${path}/`))))?.href || "/admin";
  return <div className="admin-frame">
    <label className="admin-mobile-nav">管理模块<select value={current} onChange={event => router.push(event.target.value)}>{navigation.map(item => <option key={item.href} value={item.href}>{item.label}</option>)}</select></label>
    <aside className="admin-navigation" aria-label="管理导航">
      <div className="admin-navigation-title">InsightPro 管理区</div>
      <nav aria-label="一级导航" className="admin-navigation-group">
        {navigation.map(item => <Link key={item.href} href={item.href} aria-current={current === item.href ? "page" : undefined} className="admin-navigation-link"><item.icon size={17} strokeWidth={1.8} aria-hidden="true" /><span className="admin-navigation-copy"><strong>{item.label}</strong></span></Link>)}
      </nav>
    </aside>
    <div className="admin-content">{children}</div>
  </div>;
}
