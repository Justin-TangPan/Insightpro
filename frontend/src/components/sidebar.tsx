"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BarChart3,
  Radio,
  Layers3,
  Settings,
  Shield,
  LogOut,
  Bot,
  Binoculars,
  MessagesSquare,
  Sparkles,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import type { LucideIcon } from "lucide-react";
import { usePreferences } from "@/lib/preferences";

interface NavItem {
  href: string;
  icon: LucideIcon;
  label: string;
  description: string;
}

const navItems: NavItem[] = [
  { href: "/", icon: BarChart3, label: "首页", description: "AI 热点与产业变化" },
  { href: "/insights/hotspots", icon: Radio, label: "GitHub", description: "项目趋势" },
  { href: "/insights/app-launches", icon: Sparkles, label: "AI 应用", description: "厂商 AI 应用发布与分析" },
  { href: "/insights/solutions", icon: Layers3, label: "解决方案", description: "方案目录与变化" },
  { href: "/insights/competitors", icon: Binoculars, label: "友商洞察", description: "厂商动态与对比" },
  { href: "/insights/community", icon: MessagesSquare, label: "社区洞察", description: "中文技术社区热点" },
  { href: "/workbench/solutions", icon: Bot, label: "方案实践", description: "可验证、可交付" },
  { href: "/workbench/ai", icon: Bot, label: "AI 工作区", description: "研究与产出" },
];

const navEnglish: Record<string, [string, string]> = {
  "/": ["Home", "Today's industry signals"],
  "/insights/hotspots": ["GitHub", "GitHub project trends"],
  "/insights/app-launches": ["AI Applications", "Vendor AI app launches"],
  "/insights/solutions": ["Solutions", "Catalog and changes"],
  "/insights/competitors": ["Competitor Insights", "Vendor updates"],
  "/insights/community": ["Community Insights", "Chinese developer trends"],
  "/workbench/solutions": ["Solution Practices", "Validated deliverables"],
  "/workbench/ai": ["Insight Agent", "Analysis and outputs"],
};

export function Sidebar() {
  const pathname = usePathname();
  const { user, loading, signOut } = useAuth();
  const { preferences, updatePreferences } = usePreferences();
  const english = preferences.language === "en";
  const userName = user?.user_metadata?.name || user?.email?.split("@")[0] || "";
  const userInitials = userName ? userName.slice(0, 2).toUpperCase() : "??";
  const [collapsed, setCollapsed] = useState(() => typeof window !== "undefined" && localStorage.getItem("insight_sidebar_collapsed") === "true");
  const [settingsOpen, setSettingsOpen] = useState(false);

  const closeMobile = () => {
    if (window.innerWidth < 768) {
      const sidebar = document.getElementById("sidebar");
      const overlay = document.getElementById("sidebar-overlay");
      sidebar?.classList.add("-translate-x-full");
      sidebar?.classList.remove("translate-x-0");
      overlay?.classList.add("hidden");
    }
  };

  useEffect(() => {
    document.documentElement.dataset.sidebarCollapsed = String(collapsed);
    const handleResize = () => {
      if (window.innerWidth >= 768) {
        document.getElementById("sidebar-overlay")?.classList.add("hidden");
        document.getElementById("sidebar")?.classList.remove("translate-x-0");
        document.getElementById("sidebar")?.classList.add("md:translate-x-0");
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [collapsed]);
  const toggleCollapsed = () => {
    const value = !collapsed; setCollapsed(value); localStorage.setItem("insight_sidebar_collapsed", String(value)); document.documentElement.dataset.sidebarCollapsed = String(value);
  };

  return (
    <aside
      id="sidebar"
      className={`app-sidebar fixed bottom-4 left-4 top-20 z-40 flex ${collapsed ? "w-[64px]" : "w-[232px]"} -translate-x-[calc(100%+1rem)] flex-col rounded-2xl border border-grid/80 transition-[width,transform] duration-200 md:translate-x-0`}
    >
      <div className={`flex h-16 items-center ${collapsed ? "justify-center px-2" : "px-4"}`}>
        <Link href="/" onClick={closeMobile} className={collapsed ? "hidden" : "flex items-center gap-2.5"}>
          <Image src="/brand/insightpro-logo.png" alt="" width={38} height={38} className="h-9 w-9 rounded-lg object-cover" priority />
          <div className="flex flex-col gap-[3px]">
            <span className="sidebar-brand block text-lg font-bold leading-none tracking-tight">InsightPro</span>
            <span className="sidebar-muted text-xs leading-none">{english ? "AI industry radar & insights" : "AI 产业雷达与洞察平台"}</span>
          </div>
        </Link>
        <button type="button" onClick={closeMobile} className="ml-auto rounded-lg p-2 text-ink-muted hover:bg-white/5 hover:text-primary-light md:hidden" aria-label={english ? "Close navigation" : "关闭导航"}><X className="h-4 w-4" /></button>
        <button type="button" onClick={toggleCollapsed} className="ml-auto hidden rounded-lg p-2 text-ink-muted hover:bg-white/5 hover:text-primary-light md:block" aria-label={collapsed ? (english ? "Expand sidebar" : "展开侧边栏") : (english ? "Collapse sidebar" : "折叠侧边栏")}>{collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}</button>
      </div>

      <nav className={`${collapsed ? "px-2" : "px-3"} flex-1 overflow-y-auto py-5`} onClick={closeMobile}>
        <div className="space-y-1.5">
          {navItems.filter(item => user || !item.href.startsWith("/workbench")).map((item) => {
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <div key={item.href}>
                <Link
                  href={item.href}
                  title={collapsed ? (english ? navEnglish[item.href][0] : item.label) : undefined}
                  aria-current={active ? "page" : undefined}
                  className={`sidebar-link flex items-center ${collapsed ? "justify-center px-2" : "gap-3 px-3"} rounded-xl py-3 transition-all`}
                >
                  <div className="sidebar-icon flex h-8 w-8 shrink-0 items-center justify-center rounded-lg">
                    <item.icon className="h-4 w-4" strokeWidth={1.5} />
                  </div>
                  <div className={`${collapsed ? "hidden" : "min-w-0"}`}>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold">{english ? navEnglish[item.href][0] : item.label}</span>
                    </div>
                      <p className="sidebar-muted mt-0.5 truncate text-xs">{english ? navEnglish[item.href][1] : item.description}</p>
                  </div>
                </Link>
              </div>
            );
          })}
        </div>
      </nav>

      <div className="relative m-3">
        {settingsOpen && <div role="dialog" aria-label={english ? "Settings" : "系统设置"} className="absolute bottom-full left-0 z-50 mb-2 w-56 rounded-xl border border-grid bg-white p-4 text-ink shadow-[var(--shadow-elevated)]"><p className="text-sm font-semibold"> {english ? "Display settings" : "界面设置"}</p><label className="mt-4 block text-xs text-ink-muted"> {english ? "Theme" : "主题"}</label><div className="mt-2 grid grid-cols-2 gap-2">{(["dark", "light"] as const).map(theme => <button key={theme} type="button" onClick={() => updatePreferences({ theme })} aria-pressed={preferences.theme === theme} className={`rounded-lg border px-3 py-2 text-xs font-medium ${preferences.theme === theme ? "border-primary text-primary" : "border-grid text-ink-secondary"}`}>{theme === "dark" ? (english ? "Dark" : "深色") : (english ? "Light" : "浅色")}</button>)}</div><label className="mt-4 block text-xs text-ink-muted"> {english ? "Density" : "界面密度"}<select value={preferences.density} onChange={event => updatePreferences({ density: event.target.value as typeof preferences.density })} className="ui-input mt-2 w-full px-3 text-sm"><option value="comfortable">{english ? "Comfortable" : "舒适"}</option><option value="compact">{english ? "Compact" : "紧凑"}</option></select></label><label className="mt-3 block text-xs text-ink-muted"> {english ? "Language" : "语言"}<select value={preferences.language} onChange={event => updatePreferences({ language: event.target.value as typeof preferences.language })} className="ui-input mt-2 w-full px-3 text-sm"><option value="zh">简体中文</option><option value="en">English</option></select></label>{user && <Link href="/settings" onClick={() => setSettingsOpen(false)} className="ui-link mt-4 inline-flex text-xs"> {english ? "Account and more settings" : "账号与更多设置"}</Link>}{!loading && !user && <Link href="/auth/login" onClick={() => { setSettingsOpen(false); closeMobile(); }} className="ui-link mt-4 inline-flex text-xs">{english ? "Internal preview sign in" : "内测用户登录"}</Link>}</div>}
        <div className={`mb-2 flex ${collapsed ? "justify-center" : "justify-end"} gap-2`}><button type="button" onClick={() => setSettingsOpen(value => !value)} aria-expanded={settingsOpen} className="ui-icon-button bg-white text-ink-secondary shadow-[var(--shadow-card)]" title={english ? "Settings" : "系统设置"}><Settings className="h-4 w-4" /></button>{user?.app_metadata?.role === "admin" && <Link href="/admin" className="ui-icon-button bg-primary-dark text-white shadow-[var(--shadow-card)]" title={english ? "Admin" : "平台管理后台"} aria-label={english ? "Admin" : "平台管理后台"}><Shield className="h-4 w-4" /></Link>}</div>
      {(loading || user) && <div className={`sidebar-profile ${collapsed ? "hidden" : ""} rounded-xl p-3`}>
        {loading ? (
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-full bg-grid animate-pulse" />
            <div className="flex-1">
              <div className="h-3 w-20 bg-grid animate-pulse mb-1" />
              <div className="h-2 w-16 bg-grid animate-pulse" />
            </div>
          </div>
        ) : user ? (
          <>
            <div className="flex items-center gap-2.5 mb-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-white">
                {userInitials}
              </div>
              <div className="flex-1 overflow-hidden">
                <p className="text-sm font-semibold truncate">{userName}</p>
                <p className="sidebar-muted text-xs truncate">{user.email}</p>
              </div>
            </div>
            <button
              onClick={async () => { await signOut(); window.location.href = "/"; }}
              className="sidebar-muted flex w-full items-center rounded-lg px-2.5 py-2 text-xs transition-colors hover:bg-white/10 hover:text-white"
            >
              <LogOut className="mr-2 h-3.5 w-3.5" strokeWidth={1.5} />
              {english ? "Sign out" : "退出登录"}
            </button>
          </>
        ) : null}
      </div>}
      </div>
    </aside>
  );
}
