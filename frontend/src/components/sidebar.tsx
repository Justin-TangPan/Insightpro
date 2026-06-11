"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, BarChart3, Settings, History,
  Activity, Zap, Globe, Lightbulb, ShieldCheck, Monitor,
  BookOpen, FolderOpen, ChevronDown, Pickaxe, Gavel, Sparkles
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/* ── Collapsible Nav Group ── */
interface NavItem {
  href: string;
  icon: LucideIcon;
  label: string;
  indent?: boolean;
}

function NavGroup({ label, icon: Icon, items, defaultOpen = false }: {
  label: string;
  icon: LucideIcon;
  items: NavItem[];
  defaultOpen?: boolean;
}) {
  const pathname = usePathname();
  const isActive = items.some((item) => pathname === item.href);
  const [open, setOpen] = useState(defaultOpen || isActive);

  useEffect(() => {
    if (isActive) setOpen(true);
  }, [isActive]);

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between rounded-lg px-3 py-2 text-[13px] font-semibold text-ink-secondary hover:text-ink hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Icon className="h-4 w-4 text-ink-muted" />
          {label}
        </div>
        <ChevronDown
          className={`h-3.5 w-3.5 text-ink-muted transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="pl-3 space-y-px py-1">
          {items.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center rounded-md px-3 py-1.5 text-[13px] transition-colors ${
                item.indent ? "pl-6" : ""
              } ${
                pathname === item.href
                  ? "text-ink font-semibold bg-slate-50"
                  : "text-ink-secondary hover:text-ink hover:bg-slate-50"
              }`}
            >
              <item.icon className="h-3.5 w-3.5 mr-2 text-ink-muted" />
              {item.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Single Nav Link ── */
function NavLink({ href, icon: Icon, label }: { href: string; icon: LucideIcon; label: string }) {
  const pathname = usePathname();
  const isActive = pathname === href;

  return (
    <Link
      href={href}
      className={`group flex items-center rounded-lg px-3 py-2 text-[13px] transition-colors ${
        isActive
          ? "bg-slate-50 font-semibold text-ink border border-slate-200/60"
          : "text-ink-secondary hover:text-ink hover:bg-slate-50"
      }`}
    >
      <Icon className="mr-2.5 h-4 w-4 text-ink-muted" />
      {label}
    </Link>
  );
}

/* ── Full Sidebar ── */
export function Sidebar() {
  const pathname = usePathname();

  // 移动端点击链接后自动关闭侧边栏
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
      className="fixed left-0 top-0 h-full w-[250px] flex-col bg-white border-r border-slate-200 z-40 -translate-x-full lg:translate-x-0 flex transition-transform duration-200"
    >
      {/* Logo */}
      <div className="h-[68px] flex items-center px-6 border-b border-slate-100">
        <Link href="/" onClick={closeMobile} className="flex items-center gap-2.5 group">
          <div className="h-9 w-9 rounded-lg bg-slate-900 flex items-center justify-center text-white font-serif font-bold text-lg">
            I
          </div>
          <div>
            <span className="text-[15px] font-serif font-bold tracking-tight text-ink block leading-tight">InsightPro</span>
            <span className="text-[9px] font-semibold text-ink-muted uppercase tracking-[0.15em]">Business Intelligence</span>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4 overflow-y-auto" onClick={closeMobile}>
        {/* 市场洞察 */}
        <NavGroup
          label="市场洞察"
          icon={LayoutDashboard}
          defaultOpen={true}
          items={[
            { href: "/", icon: LayoutDashboard, label: "今日洞察" },
            { href: "/insights/industry", icon: Activity, label: "行业全景" },
            { href: "/insights/industry/cases", icon: FolderOpen, label: "案例库", indent: true },
            { href: "/insights/hotspots", icon: Zap, label: "热点追踪" },
            { href: "/insights/competitors", icon: ShieldCheck, label: "友商洞察" },
            { href: "/insights/policy", icon: BookOpen, label: "政策法规" },
            { href: "/insights/news", icon: Globe, label: "商业快讯" },
          ]}
        />

        <div className="h-px bg-slate-100 my-2 mx-2" />

        {/* 商机发现 */}
        <NavGroup
          label="商机发现"
          icon={Lightbulb}
          defaultOpen={false}
          items={[
            { href: "/insights/market", icon: Sparkles, label: "市场情报" },
            { href: "/insights/demand", icon: Pickaxe, label: "需求挖掘" },
            { href: "/insights/bidding", icon: Gavel, label: "招标信息" },
            { href: "/insights/opportunities", icon: Lightbulb, label: "增长机会" },
          ]}
        />

        <div className="h-px bg-slate-100 my-2 mx-2" />

        {/* 数据分析 */}
        <NavGroup
          label="数据分析"
          icon={BarChart3}
          defaultOpen={false}
          items={[
            { href: "/dashboard", icon: Monitor, label: "数据大屏" },
            { href: "/reports", icon: BarChart3, label: "深度研报" },
            { href: "/history", icon: History, label: "历史日报" },
          ]}
        />
      </nav>

      {/* User */}
      <div className="border-t border-slate-100 p-4">
        <div className="flex items-center gap-2.5 mb-2.5">
          <div className="h-8 w-8 rounded-full bg-slate-800 flex items-center justify-center text-white text-[11px] font-bold">
            JT
          </div>
          <div className="flex-1 overflow-hidden">
            <p className="text-[13px] font-semibold truncate">Justin Tang</p>
            <p className="text-[10px] text-ink-muted font-medium">Premium Plan</p>
          </div>
        </div>
        <Link href="/settings" onClick={closeMobile} className="flex items-center rounded-md px-2.5 py-1.5 text-xs text-ink-muted hover:text-ink hover:bg-slate-50 transition-colors">
          <Settings className="mr-2 h-3.5 w-3.5" />
          系统设置
        </Link>
      </div>
    </aside>
  );
}
