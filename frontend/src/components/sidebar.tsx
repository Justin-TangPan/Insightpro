"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Radio,
  Layers3,
  Settings,
  LogIn,
  LogOut,
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
  { href: "/settings", icon: Settings, label: "系统设置", description: "账号与配置" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, loading, signOut } = useAuth();
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
      className="fixed left-0 top-0 h-full w-[250px] flex-col bg-paper border-r border-grid z-40 -translate-x-full lg:translate-x-0 flex transition-transform duration-200"
    >
      <div className="h-[68px] flex items-center px-6 border-b border-grid">
        <Link href="/" onClick={closeMobile} className="flex items-center gap-2.5 group">
          <div className="h-9 w-9 bg-ink flex items-center justify-center text-paper font-bold text-lg">
            I
          </div>
          <div className="flex flex-col gap-[3px]">
            <span className="block text-lg font-bold leading-none tracking-tight text-ink">InsightPro</span>
            <span className="swiss-kicker leading-none text-ink-muted">Solution Intelligence</span>
          </div>
        </Link>
      </div>

      <nav className="flex-1 px-3 py-4 overflow-y-auto" onClick={closeMobile}>
        <div className="space-y-1">
          {navItems.map((item, index) => {
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 border-l-2 px-3 py-3 transition-colors ${
                  active
                    ? "border-ink bg-white text-ink"
                    : "border-transparent text-ink-muted hover:bg-white hover:text-ink"
                }`}
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center border border-grid bg-paper">
                  <item.icon className="h-4 w-4" strokeWidth={1.5} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-semibold text-ink-muted">{String(index + 1).padStart(2, "0")}</span>
                    <span className="text-sm font-semibold">{item.label}</span>
                  </div>
                  <p className="mt-0.5 truncate text-xs text-ink-muted">{item.description}</p>
                </div>
              </Link>
            );
          })}
        </div>
      </nav>

      <div className="border-t border-grid p-5">
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
              <div className="h-8 w-8 rounded-full bg-ink flex items-center justify-center text-paper text-[11px] font-bold">
                {userInitials}
              </div>
              <div className="flex-1 overflow-hidden">
                <p className="text-sm font-semibold truncate">{userName}</p>
                <p className="text-xs text-ink-muted truncate">{user.email}</p>
              </div>
            </div>
            <button
              onClick={async () => { await signOut(); window.location.href = "/"; }}
              className="w-full flex items-center px-2.5 py-1.5 text-xs text-ink-muted hover:text-ink transition-colors"
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
            <Link href="/auth/login" onClick={closeMobile} className="flex items-center px-2.5 py-1.5 text-xs text-ink hover:bg-white transition-colors font-semibold">
              <LogIn className="mr-2 h-3.5 w-3.5" strokeWidth={1.5} />
              登录 / 注册
            </Link>
          </>
        )}
      </div>
    </aside>
  );
}
