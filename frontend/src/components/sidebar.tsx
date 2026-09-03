"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BarChart3,
  Radio,
  Layers3,
  Settings,
  Shield,
  LogIn,
  LogOut,
  Bot,
  User as UserIcon,
  PanelLeftClose,
  PanelLeftOpen,
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
  { href: "/", icon: BarChart3, label: "首页洞察", description: "技术方案简报" },
  { href: "/insights/hotspots", icon: Radio, label: "技术热点", description: "GitHub 项目" },
  { href: "/insights/solutions", icon: Layers3, label: "解决方案洞察", description: "方案目录与变化" },
  { href: "/workbench", icon: Bot, label: "AI 工作台", description: "方案实践与 AI 工作" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, loading, signOut } = useAuth();
  const { preferences } = usePreferences();
  const english = preferences.language === "en";
  const userName = user?.user_metadata?.name || user?.email?.split("@")[0] || "";
  const userInitials = userName ? userName.slice(0, 2).toUpperCase() : "??";
  const [collapsed, setCollapsed] = useState(() => typeof window !== "undefined" && localStorage.getItem("insight_sidebar_collapsed") === "true");
  const managementItems: NavItem[] = [
    { href: "/settings", icon: Settings, label: "系统设置", description: "个人偏好与账号" },
    ...(user?.app_metadata?.role === "admin" ? [{ href: "/admin", icon: Shield, label: "平台管理", description: "用户与平台配置" }] : []),
  ];

  const closeMobile = () => {
    if (window.innerWidth < 1024) {
      const sidebar = document.getElementById("sidebar");
      const overlay = document.getElementById("sidebar-overlay");
      sidebar?.classList.add("-translate-x-full");
      sidebar?.classList.remove("translate-x-0");
      overlay?.classList.add("hidden");
    }
  };

  useEffect(() => {
    document.documentElement.dataset.sidebarCollapsed = String(collapsed);
  }, [collapsed]);
  const toggleCollapsed = () => {
    const value = !collapsed; setCollapsed(value); localStorage.setItem("insight_sidebar_collapsed", String(value)); document.documentElement.dataset.sidebarCollapsed = String(value);
  };

  return (
    <aside
      id="sidebar"
      className={`fixed left-0 top-0 z-40 flex h-full ${collapsed ? "w-[78px]" : "w-[250px]"} -translate-x-full flex-col border-r border-grid/80 bg-[#eef1f5] transition-[width,transform] duration-200 lg:translate-x-0`}
    >
      <div className={`flex h-16 items-center ${collapsed ? "justify-center px-2" : "px-5"}`}>
        <Link href="/" onClick={closeMobile} className="flex items-center gap-2.5 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-lg font-bold text-white shadow-[var(--shadow-brand)]">
            I
          </div>
          <div className={`${collapsed ? "hidden" : "flex"} flex-col gap-[3px]`}>
            <span className="block text-lg font-bold leading-none tracking-tight text-ink">InsightPro</span>
            <span className="swiss-kicker leading-none text-ink-muted">Solution Intelligence</span>
          </div>
        </Link>
        <button type="button" onClick={toggleCollapsed} className={`ml-auto hidden rounded-lg p-2 text-ink-muted hover:bg-white hover:text-primary lg:block ${collapsed ? "absolute -right-10 bg-paper shadow-[var(--shadow-card)]" : ""}`} aria-label={collapsed ? "展开侧边栏" : "折叠侧边栏"}>{collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}</button>
      </div>

      <nav className={`${collapsed ? "px-2" : "px-3"} flex-1 overflow-y-auto py-5`} onClick={closeMobile}>
        <div className="space-y-1.5">
          {navItems.map((item, index) => {
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <div key={item.href}>
                {item.href === "/workbench" && !collapsed && <p className="swiss-kicker px-3 pb-2 pt-5 text-primary">{english ? "AI Workbench" : "AI 工作台"}</p>}
                <Link
                  href={item.href}
                  title={collapsed ? item.label : undefined}
                  className={`flex items-center ${collapsed ? "justify-center px-2" : "gap-3 px-3"} rounded-xl py-3 transition-all ${
                    active
                      ? "bg-white text-primary ring-1 ring-primary/10"
                      : "text-ink-muted hover:bg-white/70 hover:text-ink"
                  }`}
                >
                  <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${active ? "bg-primary-soft text-primary" : "bg-white/60"}`}>
                    <item.icon className="h-4 w-4" strokeWidth={1.5} />
                  </div>
                  <div className={`${collapsed ? "hidden" : "min-w-0"}`}>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] font-semibold text-ink-muted">{String(index + 1).padStart(2, "0")}</span>
                      <span className="text-sm font-semibold">{english ? ({ "首页洞察": "Home", "技术热点": "Tech Trends", "解决方案洞察": "Solution Insights", "系统设置": "Settings" }[item.label] || item.label) : item.label}</span>
                    </div>
                      <p className="mt-0.5 truncate text-xs text-ink-muted">{english ? ({ "技术方案简报": "Solution brief", "GitHub 项目": "GitHub projects", "方案目录与变化": "Catalog and changes", "自有技术方案": "Managed solutions", "需求与方案关联": "Requirements and links", "个人偏好与账号": "Account and preferences", "用户与平台配置": "Users and platform" }[item.description] || item.description) : item.description}</p>
                  </div>
                </Link>
              </div>
            );
          })}
          <div>
            {!collapsed && <p className="swiss-kicker px-3 pb-2 pt-5 text-primary">{english ? "System" : "系统管理"}</p>}
            {managementItems.map((item, index) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return <Link key={item.href} href={item.href} title={collapsed ? item.label : undefined} className={`mb-1.5 flex items-center ${collapsed ? "justify-center px-2" : "gap-3 px-3"} rounded-xl py-3 transition-all ${active ? "bg-white text-primary ring-1 ring-primary/10" : "text-ink-muted hover:bg-white/70 hover:text-ink"}`}>
                <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${active ? "bg-primary-soft text-primary" : "bg-white/60"}`}><item.icon className="h-4 w-4" strokeWidth={1.5} /></div>
                <div className={`${collapsed ? "hidden" : "min-w-0"}`}><div className="flex items-center gap-2"><span className="font-mono text-[10px] font-semibold text-ink-muted">{String(index + 5).padStart(2, "0")}</span><span className="text-sm font-semibold">{english ? ({ "系统设置": "Settings", "平台管理": "Administration" }[item.label] || item.label) : item.label}</span></div><p className="mt-0.5 truncate text-xs text-ink-muted">{item.description}</p></div>
              </Link>;
            })}
          </div>
        </div>
      </nav>

      <div className={`${collapsed ? "hidden" : "m-3"} rounded-xl bg-white/70 p-3`}>
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
                <p className="text-xs text-ink-muted truncate">{user.email}</p>
              </div>
            </div>
            <button
              onClick={async () => { await signOut(); window.location.href = "/"; }}
              className="flex w-full items-center rounded-lg px-2.5 py-2 text-xs text-ink-muted transition-colors hover:bg-primary-soft hover:text-primary"
            >
              <LogOut className="mr-2 h-3.5 w-3.5" strokeWidth={1.5} />
              退出登录
            </button>
          </>
        ) : (
          <>
            <div className="flex items-center gap-2.5 mb-2.5">
              <div className="h-8 w-8 rounded-full bg-grid flex items-center justify-center">
                <UserIcon className="h-4 w-4 text-ink-muted" strokeWidth={1.5} />
              </div>
              <div className="flex-1">
                <p className="text-sm text-ink-secondary">未登录</p>
              </div>
            </div>
            <Link href="/auth/login" onClick={closeMobile} className="ui-button-primary w-full">
              <LogIn className="mr-2 h-3.5 w-3.5" strokeWidth={1.5} />
              登录 / 注册
            </Link>
          </>
        )}
      </div>
    </aside>
  );
}
