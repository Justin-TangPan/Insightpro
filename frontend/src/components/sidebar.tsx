"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Radio,
  Layers3,
  Blocks,
  ClipboardList,
  Settings,
  LogIn,
  LogOut,
  Bot,
  User as UserIcon,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import type { LucideIcon } from "lucide-react";

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
  { href: "/workbench/solutions", icon: Blocks, label: "Solutions", description: "自有技术方案" },
  { href: "/workbench/requirements", icon: ClipboardList, label: "Requirements", description: "需求与方案关联" },
  { href: "/settings", icon: Settings, label: "系统设置", description: "账号与配置" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, loading, signOut } = useAuth();
  const openCodeUrl = process.env.NEXT_PUBLIC_OPENCODE_URL || "http://159.138.89.233:4096";
  const userName = user?.user_metadata?.name || user?.email?.split("@")[0] || "";
  const userInitials = userName ? userName.slice(0, 2).toUpperCase() : "??";

  const closeMobile = () => {
    if (window.innerWidth < 1024) {
      const sidebar = document.getElementById("sidebar");
      const overlay = document.getElementById("sidebar-overlay");
      sidebar?.classList.add("-translate-x-full");
      sidebar?.classList.remove("translate-x-0");
      overlay?.classList.add("hidden");
    }
  };

  return (
    <aside
      id="sidebar"
      className="fixed left-0 top-0 z-40 flex h-full w-[250px] -translate-x-full flex-col border-r border-grid/70 bg-surface-subtle transition-transform duration-200 lg:translate-x-0"
    >
      <div className="flex h-16 items-center px-5">
        <Link href="/" onClick={closeMobile} className="flex items-center gap-2.5 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-lg font-bold text-white shadow-[0_8px_18px_rgba(23,107,70,0.18)]">
            I
          </div>
          <div className="flex flex-col gap-[3px]">
            <span className="block text-lg font-bold leading-none tracking-tight text-ink">InsightPro</span>
            <span className="swiss-kicker leading-none text-ink-muted">Solution Intelligence</span>
          </div>
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-5" onClick={closeMobile}>
        <div className="space-y-1.5">
          {navItems.map((item, index) => {
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <div key={item.href}>
                {item.href === "/workbench/solutions" && <p className="swiss-kicker px-3 pb-2 pt-5 text-primary">工作台</p>}
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 rounded-xl px-3 py-3 transition-all ${
                    active
                      ? "bg-white text-primary shadow-[var(--shadow-card)]"
                      : "text-ink-muted hover:bg-white/70 hover:text-ink"
                  }`}
                >
                  <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${active ? "bg-primary-soft text-primary" : "bg-white/60"}`}>
                    <item.icon className="h-4 w-4" strokeWidth={1.5} />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] font-semibold text-ink-muted">{String(index + 1).padStart(2, "0")}</span>
                      <span className="text-sm font-semibold">{item.label}</span>
                    </div>
                    <p className="mt-0.5 truncate text-xs text-ink-muted">{item.description}</p>
                  </div>
                </Link>
              </div>
            );
          })}
          <div>
            <p className="swiss-kicker px-3 pb-2 pt-5 text-primary">AI 工作区</p>
            <a
              href={openCodeUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 rounded-xl px-3 py-3 text-ink-muted transition-all hover:bg-white/70 hover:text-ink"
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/60">
                <Bot className="h-4 w-4" strokeWidth={1.5} />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] font-semibold text-ink-muted">07</span>
                  <span className="text-sm font-semibold">OpenCode / AI Agent</span>
                </div>
                <p className="mt-0.5 truncate text-xs text-ink-muted">AI 工作执行环境</p>
              </div>
            </a>
          </div>
        </div>
      </nav>

      <div className="m-3 rounded-xl bg-white/70 p-3">
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
