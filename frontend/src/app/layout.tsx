import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Bell } from "lucide-react";
import { SearchBar } from "@/components/search-bar";
import { Sidebar } from "@/components/sidebar";
import { MobileNavTrigger } from "@/components/mobile-nav";
import { PageTracker } from "@/components/page-tracker";
import { AuthProvider } from "@/components/auth-provider";
import { InsightAgentShell } from "@/components/insight-agent-shell";
import { Suspense } from "react";

const inter = Inter({
  subsets: ["latin"],
  weight: ['400', '500', '600', '700', '800'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: "InsightPro | 技术解决方案洞察平台",
  description: "持续跟踪技术项目与官方技术解决方案变化",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={inter.variable} suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: `try{const p=JSON.parse(localStorage.getItem('insight_preferences')||'{}'),r=document.documentElement;r.dataset.theme=p.theme||'green';r.dataset.density=p.density||'comfortable';r.dataset.motion=String(p.motion!==false);r.lang=p.language==='en'?'en':'zh-CN'}catch{}` }} /></head>
      <body className="bg-paper text-ink antialiased">
        <AuthProvider>
          <PageTracker />
          <div className="flex min-h-screen">
          <Sidebar />

          {/* Overlay for mobile */}
          <div id="sidebar-overlay" className="hidden fixed inset-0 bg-black/40 z-30 lg:hidden" />

          {/* Main */}
          <main className="min-w-0 flex-1 lg:pl-[250px]">
            <header className="sticky top-0 z-10 border-b border-grid/70 bg-paper/90 backdrop-blur-xl">
              <div className="flex h-16 items-center justify-between px-[var(--page-gutter)]">
                <div className="flex items-center gap-3">
                  <MobileNavTrigger />
                  <SearchBar />
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right hidden sm:block">
                    <p className="swiss-kicker text-ink-muted mb-0.5">Today</p>
                    <p className="text-sm font-semibold text-ink tracking-tight leading-tight">{new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
                  </div>
                  <div className="hidden h-6 w-px bg-grid sm:block" />
                  <button aria-label="查看通知" className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-white text-ink-secondary shadow-[var(--shadow-card)] transition-colors hover:bg-primary-soft hover:text-primary">
                    <Bell className="h-4 w-4" />
                    <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-warning ring-2 ring-white" />
                  </button>
                </div>
              </div>
            </header>

            <div className="page-shell">{children}</div>
          </main>
          </div>
          <Suspense fallback={null}><InsightAgentShell /></Suspense>
        </AuthProvider>
      </body>
    </html>
  );
}
