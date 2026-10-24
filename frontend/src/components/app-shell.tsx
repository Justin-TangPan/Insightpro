"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Moon, Sun, Shield, LogIn, LogOut, Search } from "lucide-react";
import { SearchBar } from "@/components/search-bar";
import { useAuth } from "@/components/auth-provider";
import { usePreferences } from "@/lib/preferences";

const links = [
  ["/", "首页"], ["/insights/hotspots", "技术生态"], ["/insights/app-launches", "AI 应用"],
  ["/insights/solutions", "解决方案"], ["/insights/community", "社区洞察"],
  ["/insights/competitors", "友商动态"],
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, signOut } = useAuth();
  const { preferences, updatePreferences } = usePreferences();
  const inAdmin = pathname.startsWith("/admin");
  const admin = pathname.startsWith("/admin") || pathname.startsWith("/workbench") || pathname === "/insight-agent";
  return <div className="min-h-screen">
    <header className={`app-header sticky top-0 z-30 border-b border-grid${pathname === "/" ? " app-header-home" : ""}`}>
      <div className="app-header-inner">
        <Link href="/" className="app-brand" aria-label="InsightPro 首页"><Image src="/brand/insightpro-logo.png" alt="" width={32} height={32} className="rounded-lg" priority /><span>InsightPro</span></Link>
        {!admin && <nav aria-label="洞察导航" className="app-top-navigation">
          {links.map(([href, label]) => <Link key={href} href={href} aria-current={pathname === href ? "page" : undefined}>{label}</Link>)}
        </nav>}
        <div className="app-header-actions">
          <div className="header-search"><SearchBar /></div>
          <Link href="/search" className="header-search-link ui-icon-button border border-grid bg-surface-elevated" aria-label="打开全局搜索"><Search className="h-4 w-4" /></Link>
          <button type="button" className="ui-icon-button border border-grid bg-surface-elevated" onClick={() => updatePreferences({ theme: preferences.theme === "dark" ? "light" : "dark" })} aria-label={preferences.theme === "dark" ? "切换浅色主题" : "切换深色主题"} title={preferences.theme === "dark" ? "浅色主题" : "深色主题"}>{preferences.theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}</button>
          {user?.app_metadata?.role === "admin" && <Link href={inAdmin ? "/" : "/admin"} aria-label={inAdmin ? "返回洞察区" : "进入管理区"} className="ui-icon-button border border-grid bg-surface-elevated"><Shield className="h-4 w-4" /></Link>}
          {!user && <Link href="/auth/login" aria-label="管理员登录" title="管理员登录" className="ui-icon-button border border-grid bg-surface-elevated"><LogIn className="h-4 w-4" /></Link>}
          {user && <button type="button" onClick={async () => { await signOut(); window.location.href = "/"; }} className="ui-icon-button border border-grid bg-surface-elevated" aria-label="退出登录" title="退出登录"><LogOut className="h-4 w-4" /></button>}
        </div>
      </div>
    </header>
    <main id="app-main" className={`page-shell${pathname === "/" ? " home-page-shell" : pathname === "/insights/hotspots" ? " ecosystem-page-shell" : pathname.startsWith("/insights/solutions") ? " solution-page-shell" : pathname.startsWith("/admin") ? " admin-page-shell" : ""}`}>{children}</main>
  </div>;
}
